"""Represent a published DANDI dandiset as lazily streamed NWB assets."""

from __future__ import annotations

import re
from dataclasses import dataclass, fields
from typing import Optional

import h5py
import numpy as np
import pandas as pd
from dandi.dandiapi import RemoteAsset
from dandi.dandiarchive import DandisetURL, parse_dandi_url
from pynwb import NWBHDF5IO, NWBFile
from pynwb.base import TimeSeriesReference
from pynwb.icephys import (
    CurrentClampSeries,
    CurrentClampStimulusSeries,
    IZeroClampSeries,
    PatchClampSeries,
    VoltageClampSeries,
    VoltageClampStimulusSeries,
)

from sanpy.sanpyLogger import get_logger
from dandi_transport import LindiNwbTransport, NwbTransport

logger = get_logger(__name__)

_RTOL = 1e-9
_ATOL = 1e-12
_DANDI_DOI_PATTERN = re.compile(
    r"^https://doi\.org/10\.48324/dandi\.(?P<dandiset>\d{6})/"
    r"(?P<version>[^/?#]+)$",
    flags=re.IGNORECASE,
)


class DandiDatasetError(RuntimeError):
    """Report an invalid DANDI resource or failed remote operation."""


class UnsupportedNwbError(DandiDatasetError):
    """Report NWB data that the current SanPy data model cannot represent."""


@dataclass(frozen=True)
class DandiAssetMetadata:
    """Store inexpensive metadata returned by the DANDI asset API.

    Attributes:
        asset_id: Immutable DANDI asset identifier.
        path: Asset path relative to the dandiset root.
        size_bytes: Remote asset size in bytes.
        created: API creation timestamp, when available.
        modified: API modification timestamp, when available.
    """

    asset_id: str
    path: str
    size_bytes: int
    created: str | None
    modified: str | None


@dataclass(frozen=True)
class DandiDatasetMetadata:
    """Store published metadata describing one immutable dandiset version.

    Attributes:
        dandiset_id: Six-digit DANDI identifier.
        version: Published dandiset version.
        name: Published dandiset title.
        description: Published dandiset description.
        doi: Published DOI, when present.
        url: Canonical DANDI Archive URL.
        citation: Published dataset citation.
    """

    dandiset_id: str
    version: str
    name: str
    description: str
    doi: str | None
    url: str
    citation: str


@dataclass(frozen=True)
class NwbHeaderMetadata:
    """Describe a compatible intracellular NWB recording.

    Attributes:
        subject_id: NWB subject identifier, when present.
        session_id: NWB session identifier, when present.
        acquisition_datetime: ISO-formatted session start time.
        num_sweeps: Number of response sweeps.
        num_channels: Number of response electrodes.
        sample_rate_hz: Common sweep sampling rate.
        samples_per_sweep: Common response sample count.
        sweep_duration_seconds: Time from the first through last sample.
        has_stimulus: Whether at least one sweep has a stimulus.
        clamp_mode: Recording mode, either current clamp or voltage clamp.
    """

    subject_id: str | None
    session_id: str | None
    acquisition_datetime: str
    num_sweeps: int
    num_channels: int
    sample_rate_hz: float
    samples_per_sweep: int
    sweep_duration_seconds: float
    has_stimulus: bool
    clamp_mode: str

    def __str__(self) -> str:
        """Return one metadata field per line.

        Returns:
            Multiline header text beginning with the class name.
        """
        lines = [type(self).__name__]
        for field in fields(self):
            lines.append(f"  {field.name}: {getattr(self, field.name)}")
        return "\n".join(lines)


@dataclass(frozen=True)
class DandiAssetSummary:
    """Store one table-ready summary of a remote NWB recording.

    Attributes:
        index: Zero-based asset position in the dandiset collection.
        asset_id: Immutable DANDI asset identifier.
        path: Asset path relative to the dandiset root.
        size_mb: Asset size in decimal megabytes.
        status: Header inspection result, either ``summary ready`` or ``error``.
        error: Header inspection error text, or ``None``.
        subject_id: NWB subject identifier, when available.
        session_id: NWB session identifier, when available.
        acquisition_datetime: ISO-formatted acquisition time, when available.
        num_sweeps: Number of response sweeps, when available.
        sample_rate_hz: Common sample rate, when available.
        samples_per_sweep: Common sample count, when available.
        duration_seconds: Common sweep duration, when available.
        clamp_mode: Recording clamp mode, when available.
    """

    index: int
    asset_id: str
    path: str
    size_mb: float
    status: str
    error: str | None
    subject_id: str | None
    session_id: str | None
    acquisition_datetime: str | None
    num_sweeps: int | None
    sample_rate_hz: float | None
    samples_per_sweep: int | None
    duration_seconds: float | None
    clamp_mode: str | None

    def to_row(self) -> dict[str, object]:
        """Return a complete row suitable for tables and data frames.

        Returns:
            New dictionary whose keys match the public summary attributes.
        """
        return {field.name: getattr(self, field.name) for field in fields(self)}


@dataclass(frozen=True)
class DandiRecording:
    """Store one materialized intracellular recording in NWB base units.

    Attributes:
        header: Header metadata validated while opening the asset.
        time_seconds: Sweep-local time, with one column per sweep.
        response_values: Response values after NWB conversion and offset.
        response_unit: Declared NWB response base unit.
        stimulus_values: Stimulus values after NWB conversion and offset, or
            ``None`` when every sweep lacks a usable stimulus.
        stimulus_unit: Declared NWB stimulus base unit, when present.
        warnings: Nonfatal data-normalization messages.
    """

    header: NwbHeaderMetadata
    time_seconds: np.ndarray
    response_values: np.ndarray
    response_unit: str
    stimulus_values: np.ndarray | None
    stimulus_unit: str | None
    warnings: tuple[str, ...]


@dataclass(frozen=True)
class DandiTracePlotData:
    """Store one renderer-independent trace prepared for interactive plotting.

    Attributes:
        time_seconds: Downsampled time values in seconds.
        values: Downsampled signal values in the displayed unit.
        x_axis_label: Human-readable horizontal-axis label.
        y_axis_label: Human-readable vertical-axis label.
    """

    time_seconds: np.ndarray
    values: np.ndarray
    x_axis_label: str
    y_axis_label: str


@dataclass(frozen=True)
class DandiSweepPlotData:
    """Store renderer-independent response and optional stimulus plot data.

    Attributes:
        response: Recorded response plot data.
        stimulus: Command-stimulus plot data, or ``None`` without a stimulus.
    """

    response: DandiTracePlotData
    stimulus: DandiTracePlotData | None


@dataclass(frozen=True)
class DandiSweep:
    """Store one fully materialized intracellular sweep in NWB base units.

    Attributes:
        header: Header metadata validated while opening the asset.
        sweep_index: Zero-based sweep position in the NWB recording table.
        time_seconds: Complete sweep-local time values.
        response_values: Complete response values after NWB conversion and offset.
        response_unit: Declared NWB response base unit.
        stimulus_values: Complete stimulus values after NWB conversion and offset.
        stimulus_unit: Declared NWB stimulus base unit, when present.
        warnings: Nonfatal data-normalization messages.
    """

    header: NwbHeaderMetadata
    sweep_index: int
    time_seconds: np.ndarray
    response_values: np.ndarray
    response_unit: str
    stimulus_values: np.ndarray | None
    stimulus_unit: str | None
    warnings: tuple[str, ...]

    def to_plot_data(self, max_points: int = 5000) -> DandiSweepPlotData:
        """Create labeled plot data while preserving narrow signal extrema.

        Each trace is independently reduced with a min/max envelope. The
        complete arrays on this sweep remain unchanged.

        Args:
            max_points: Maximum plotted points in each output trace.

        Returns:
            Renderer-independent voltage and optional current traces.

        Raises:
            ValueError: If fewer than four plot points are requested.
        """
        response_time, response_values = _min_max_downsample(
            self.time_seconds,
            self.response_values,
            max_points=max_points,
        )
        response = DandiTracePlotData(
            time_seconds=response_time,
            values=response_values,
            x_axis_label="Time (s)",
            y_axis_label=_quantity_axis_label(self.response_unit),
        )
        stimulus: DandiTracePlotData | None = None
        if self.stimulus_values is not None and self.stimulus_unit is not None:
            stimulus_time, stimulus_values = _min_max_downsample(
                self.time_seconds,
                self.stimulus_values,
                max_points=max_points,
            )
            stimulus = DandiTracePlotData(
                time_seconds=stimulus_time,
                values=stimulus_values,
                x_axis_label="Time (s)",
                y_axis_label=_quantity_axis_label(self.stimulus_unit),
            )
        return DandiSweepPlotData(response=response, stimulus=stimulus)


class DandiNwbAsset:
    """Provide lazy header and recording access for one remote NWB asset."""

    def __init__(
        self,
        dataset: DandiDataset,
        metadata: DandiAssetMetadata,
    ) -> None:
        """Initialize a remote NWB asset.

        Args:
            dataset: Owning published dandiset.
            metadata: Inexpensive DANDI API metadata for this asset.
        """
        self._dataset = dataset
        self.metadata = metadata
        self._header: NwbHeaderMetadata | None = None
        self._header_is_validated = False
        self._header_error: str | None = None
        self._sweep_cache_key: int | None = None
        self._sweep_cache: DandiSweep | None = None
        self._sweep_plot_cache: dict[
            tuple[int, int], DandiSweepPlotData
        ] = {}

    @property
    def header(self) -> NwbHeaderMetadata | None:
        """Return cached NWB header metadata, when already inspected.

        Returns:
            Cached header metadata or ``None``.
        """
        return self._header

    @property
    def header_error(self) -> str | None:
        """Return the most recent header-inspection error.

        Returns:
            Error text or ``None`` when inspection has not failed.
        """
        return self._header_error

    def load_header(self, refresh: bool = False) -> NwbHeaderMetadata:
        """Read and cache NWB metadata without materializing trace values.

        Args:
            refresh: Whether to reread a previously cached header.

        Returns:
            Validated intracellular header metadata.

        Raises:
            DandiDatasetError: If the remote asset cannot be opened.
            UnsupportedNwbError: If SanPy cannot represent the recording.
        """
        if self._header is not None and self._header_is_validated and not refresh:
            return self._header
        try:
            with self._open_nwbfile() as nwbfile:
                header, _references = _inspect_nwbfile(nwbfile)
        except UnsupportedNwbError as error:
            self._header_error = str(error)
            raise
        except Exception as error:
            self._header_error = str(error)
            raise DandiDatasetError(
                f'Could not inspect remote NWB asset "{self.metadata.path}": {error}'
            ) from error
        self._header = header
        self._header_is_validated = True
        self._header_error = None
        return header

    def load_summary(self, index: int) -> DandiAssetSummary:
        """Inspect this asset and return one table-ready summary row.

        Header failures are represented in the returned summary rather than
        raised, allowing callers to continue inspecting other assets.

        Args:
            index: Zero-based position of this asset in its collection.

        Returns:
            Successful or failed header summary with stable asset identity.
        """
        try:
            if self._header is None:
                with self._open_nwbfile() as nwbfile:
                    self._header = _summarize_nwbfile(nwbfile)
            header = self._header
        except Exception as error:
            self._header_error = str(error)
            return DandiAssetSummary(
                index=index,
                asset_id=self.metadata.asset_id,
                path=self.metadata.path,
                size_mb=round(self.metadata.size_bytes / 1_000_000, 2),
                status="error",
                error=str(error),
                subject_id=None,
                session_id=None,
                acquisition_datetime=None,
                num_sweeps=None,
                sample_rate_hz=None,
                samples_per_sweep=None,
                duration_seconds=None,
                clamp_mode=None,
            )
        return DandiAssetSummary(
            index=index,
            asset_id=self.metadata.asset_id,
            path=self.metadata.path,
            size_mb=round(self.metadata.size_bytes / 1_000_000, 2),
            status="summary ready",
            error=None,
            subject_id=header.subject_id,
            session_id=header.session_id,
            acquisition_datetime=header.acquisition_datetime,
            num_sweeps=header.num_sweeps,
            sample_rate_hz=header.sample_rate_hz,
            samples_per_sweep=header.samples_per_sweep,
            duration_seconds=header.sweep_duration_seconds,
            clamp_mode=header.clamp_mode,
        )

    def load_recording(self) -> DandiRecording:
        """Stream and materialize all compatible sweeps from this asset.

        Returns:
            Recording arrays converted to SanPy time, voltage, and current units.

        Raises:
            DandiDatasetError: If the remote asset cannot be opened or read.
            UnsupportedNwbError: If SanPy cannot represent the recording.
        """
        try:
            with self._open_nwbfile() as nwbfile:
                header, references = _inspect_nwbfile(nwbfile)
                recording = _materialize_recording(
                    header,
                    references,
                )
        except UnsupportedNwbError:
            raise
        except Exception as error:
            raise DandiDatasetError(
                f'Could not load remote NWB asset "{self.metadata.path}": {error}'
            ) from error
        self._header = header
        self._header_is_validated = True
        self._header_error = None
        return recording

    def load_sweep(
        self,
        sweep_index: int,
    ) -> DandiSweep:
        """Stream and materialize one intracellular sweep from this asset.

        The most recently loaded sweep is retained in memory. An identical
        subsequent request returns the same result object.

        Args:
            sweep_index: Zero-based sweep position in the NWB recording table.

        Returns:
            Complete selected sweep converted to display-independent SanPy units.

        Raises:
            IndexError: If ``sweep_index`` is outside the recording.
            DandiDatasetError: If the remote asset cannot be opened or read.
            UnsupportedNwbError: If SanPy cannot represent the sweep.
        """
        cache_key = sweep_index
        if self._sweep_cache_key == cache_key and self._sweep_cache is not None:
            return self._sweep_cache
        try:
            with self._open_nwbfile() as nwbfile:
                references = _collect_sweep_references(nwbfile)
                if sweep_index < 0 or sweep_index >= len(references):
                    raise IndexError(
                        f"Sweep index {sweep_index} is outside 0..{len(references) - 1}"
                    )
                header = self._header or _summarize_nwbfile(nwbfile, references)
                sweep = _materialize_sweep(
                    header,
                    references[sweep_index],
                    sweep_index=sweep_index,
                )
        except (IndexError, UnsupportedNwbError):
            raise
        except Exception as error:
            raise DandiDatasetError(
                f'Could not load remote NWB asset "{self.metadata.path}": {error}'
            ) from error
        self._header = header
        self._header_error = None
        self._sweep_cache_key = cache_key
        self._sweep_cache = sweep
        return sweep

    def load_sweep_plot_data(
        self,
        sweep_index: int,
        max_points: int = 5000,
    ) -> DandiSweepPlotData:
        """Load and cache renderer-independent plot data for one sweep.

        Args:
            sweep_index: Zero-based sweep position in the NWB recording table.
            max_points: Maximum plotted points in each output trace.

        Returns:
            Cached or newly loaded voltage and optional current plot data.

        Raises:
            IndexError: If ``sweep_index`` is outside the recording.
            DandiDatasetError: If the remote asset cannot be opened or read.
            UnsupportedNwbError: If SanPy cannot represent the sweep.
            ValueError: If fewer than four plot points are requested.
        """
        cache_key = (sweep_index, max_points)
        cached = self._sweep_plot_cache.get(cache_key)
        if cached is not None:
            return cached
        sweep = self.load_sweep(sweep_index)
        plot_data = sweep.to_plot_data(max_points=max_points)
        self._sweep_plot_cache[cache_key] = plot_data
        return plot_data

    def _open_nwbfile(self) -> _OpenNwbFile:
        """Create a context manager for this asset's remote NWB file.

        Returns:
            Context manager yielding an open ``NWBFile``.
        """
        content_url = self._dataset._resolve_content_url(self.metadata.asset_id)
        return _OpenNwbFile(self._dataset.transport, content_url)


class DandiDataset:
    """Represent one immutable published dandiset containing NWB assets."""

    def __init__(
        self,
        parsed_url: DandisetURL,
        transport: NwbTransport | None = None,
    ) -> None:
        """Initialize a parsed dandiset without performing network access.

        Args:
            parsed_url: Parsed whole-dandiset URL with an explicit published version.
            transport: Optional remote-file transport override.
        """
        self._parsed_url = parsed_url
        self.dandiset_id = str(parsed_url.dandiset_id)
        self.version = str(parsed_url.version_id)
        self.transport = transport or LindiNwbTransport()
        self._assets: tuple[DandiNwbAsset, ...] = ()
        self._metadata: DandiDatasetMetadata | None = None

    @classmethod
    def from_url(
        cls,
        resource: str,
        transport: NwbTransport | None = None,
    ) -> DandiDataset:
        """Parse a whole published dandiset identifier without loading assets.

        Args:
            resource: DANDI identifier, canonical whole-dandiset URL, or
                published DANDI DOI URL.
            transport: Optional remote-file transport override.

        Returns:
            Unloaded published dandiset collection.

        Raises:
            DandiDatasetError: If the resource is not an explicitly versioned,
                published, whole production DANDI dandiset.
        """
        normalized_resource = _normalize_dandi_resource(resource)
        try:
            parsed_url = parse_dandi_url(normalized_resource)
        except Exception as error:
            raise DandiDatasetError(
                f'Could not parse DANDI resource "{resource}": {error}'
            ) from error
        if not isinstance(parsed_url, DandisetURL):
            raise DandiDatasetError(
                "The resource must identify a whole dandiset, not an asset or folder"
            )
        if parsed_url.version_id is None:
            raise DandiDatasetError("An explicit published dandiset version is required")
        if str(parsed_url.version_id).lower() == "draft":
            raise DandiDatasetError("Draft dandisets are not supported")
        instance_name = str(parsed_url.instance.name)
        if instance_name != "dandi":
            raise DandiDatasetError(
                f'Only the production DANDI instance is supported; got "{instance_name}"'
            )
        return cls(parsed_url=parsed_url, transport=transport)

    @property
    def assets(self) -> tuple[DandiNwbAsset, ...]:
        """Return the currently loaded immutable NWB asset collection.

        Returns:
            Assets loaded by ``load_assets()``, or an empty tuple beforehand.
        """
        return self._assets

    @property
    def metadata(self) -> DandiDatasetMetadata | None:
        """Return cached published dandiset metadata.

        Returns:
            Published metadata loaded by ``load_metadata()`` or ``load_assets()``.
        """
        return self._metadata

    def load_metadata(self, refresh: bool = False) -> DandiDatasetMetadata:
        """Fetch and cache published dandiset-level metadata.

        Args:
            refresh: Whether to replace already cached metadata.

        Returns:
            Typed published metadata for this dandiset version.

        Raises:
            DandiDatasetError: If the DANDI metadata request fails.
        """
        if self._metadata is not None and not refresh:
            return self._metadata
        try:
            with self._parsed_url.navigate(strict=True) as (
                _client,
                remote_dandiset,
                _remote_assets,
            ):
                raw_metadata = remote_dandiset.get_raw_metadata()
        except Exception as error:
            raise DandiDatasetError(
                f"Could not load metadata for DANDI:{self.dandiset_id}/{self.version}: "
                f"{error}"
            ) from error
        self._metadata = _dataset_metadata(
            raw_metadata,
            dandiset_id=self.dandiset_id,
            version=self.version,
        )
        return self._metadata

    def __len__(self) -> int:
        """Return the number of loaded NWB assets.

        Returns:
            Number of assets loaded by ``load_assets()``.
        """
        return len(self._assets)

    def __getitem__(self, index: int) -> DandiNwbAsset:
        """Return one loaded NWB asset by integer position.

        Args:
            index: Zero-based asset position. Negative tuple-style indexes are
                accepted.

        Returns:
            Lazy NWB asset at the requested position.

        Raises:
            IndexError: If the position is outside the loaded asset collection.
        """
        return self._assets[index]

    def load_assets(self, refresh: bool = False) -> tuple[DandiNwbAsset, ...]:
        """Fetch inexpensive metadata for all NWB assets in this dandiset.

        Args:
            refresh: Whether to replace an already loaded asset catalog.

        Returns:
            Immutable assets sorted by DANDI-relative path.

        Raises:
            DandiDatasetError: If the DANDI API request fails.
        """
        if self._assets and not refresh:
            return self._assets
        try:
            with self._parsed_url.navigate(strict=True) as (
                _client,
                remote_dandiset,
                remote_assets,
            ):
                if self._metadata is None:
                    self._metadata = _dataset_metadata(
                        remote_dandiset.get_raw_metadata(),
                        dandiset_id=self.dandiset_id,
                        version=self.version,
                    )
                metadata = [
                    _asset_metadata(asset)
                    for asset in remote_assets
                    if str(asset.path).lower().endswith(".nwb")
                ]
        except Exception as error:
            raise DandiDatasetError(
                f"Could not list assets for DANDI:{self.dandiset_id}/{self.version}: "
                f"{error}"
            ) from error
        metadata.sort(key=lambda item: item.path)
        self._assets = tuple(DandiNwbAsset(self, item) for item in metadata)
        return self._assets

    def get_asset(self, asset_id_or_path: str) -> DandiNwbAsset:
        """Return one loaded asset by immutable ID or dandiset-relative path.

        Args:
            asset_id_or_path: Exact asset ID or relative NWB path.

        Returns:
            Matching asset.

        Raises:
            KeyError: If no loaded asset matches the requested identity.
        """
        for asset in self._assets:
            if asset.metadata.asset_id == asset_id_or_path:
                return asset
            if asset.metadata.path == asset_id_or_path:
                return asset
        raise KeyError(asset_id_or_path)

    def to_dataframe(self) -> pd.DataFrame:
        """Return an independent table of asset and cached header metadata.

        Returns:
            One row per loaded NWB asset.
        """
        rows: list[dict[str, object]] = []
        for asset in self._assets:
            header = asset.header
            rows.append(
                {
                    "asset_id": asset.metadata.asset_id,
                    "path": asset.metadata.path,
                    "size_bytes": asset.metadata.size_bytes,
                    "created": asset.metadata.created,
                    "modified": asset.metadata.modified,
                    "header_status": (
                        "compatible"
                        if header is not None and asset._header_is_validated
                        else "summary ready"
                        if header is not None
                        else "error"
                        if asset.header_error is not None
                        else "not inspected"
                    ),
                    "header_error": asset.header_error,
                    "subject_id": None if header is None else header.subject_id,
                    "session_id": None if header is None else header.session_id,
                    "num_sweeps": None if header is None else header.num_sweeps,
                    "sample_rate_hz": (
                        None if header is None else header.sample_rate_hz
                    ),
                    "sweep_duration_seconds": (
                        None if header is None else header.sweep_duration_seconds
                    ),
                    "has_stimulus": None if header is None else header.has_stimulus,
                    "clamp_mode": None if header is None else header.clamp_mode,
                }
            )
        return pd.DataFrame(rows)

    def _resolve_content_url(self, asset_id: str) -> str:
        """Resolve a fresh immutable content URL for one asset.

        Args:
            asset_id: Immutable DANDI asset identifier.

        Returns:
            Direct HTTP content URL.
        """
        with self._parsed_url.get_client() as client:
            dandiset = client.get_dandiset(self.dandiset_id, self.version)
            asset = dandiset.get_asset(asset_id)
            return str(asset.get_content_url(follow_redirects=1, strip_query=True))


class _OpenNwbFile:
    """Own the nested remote-file, HDF5, and PyNWB resource stack."""

    def __init__(self, transport: NwbTransport, content_url: str) -> None:
        """Initialize a remote NWB context manager.

        Args:
            transport: Transport used to open the remote content URL.
            content_url: Direct DANDI asset URL.
        """
        self._transport = transport
        self._content_url = content_url
        self._remote_context: object | None = None
        self._h5_file: h5py.File | None = None
        self._io: NWBHDF5IO | None = None

    def __enter__(self) -> NWBFile:
        """Open all remote NWB resources.

        Returns:
            NWB file whose lazy datasets remain accessible inside the context.
        """
        self._remote_context = self._transport.open_h5(self._content_url)
        self._h5_file = self._remote_context.__enter__()  # type: ignore[attr-defined]
        self._io = NWBHDF5IO(file=self._h5_file, load_namespaces=True)
        return self._io.read()

    def __exit__(
        self,
        exception_type: type[BaseException] | None,
        exception: BaseException | None,
        traceback: object | None,
    ) -> None:
        """Close all resources in reverse order.

        Args:
            exception_type: Exception class raised inside the context, if any.
            exception: Exception instance raised inside the context, if any.
            traceback: Exception traceback, if any.
        """
        if self._io is not None:
            self._io.close()
        if self._remote_context is not None:
            self._remote_context.__exit__(  # type: ignore[attr-defined]
                exception_type,
                exception,
                traceback,
            )


def _normalize_dandi_resource(resource: str) -> str:
    """Normalize a supported DANDI DOI URL into a published identifier.

    Args:
        resource: DANDI identifier, canonical URL, or supported DOI URL.

    Returns:
        Original resource or normalized published DANDI identifier.
    """
    match = _DANDI_DOI_PATTERN.fullmatch(resource.strip())
    if match is None:
        return resource
    return f"DANDI:{match.group('dandiset')}/{match.group('version')}"


def _asset_metadata(asset: RemoteAsset) -> DandiAssetMetadata:
    """Convert one DANDI client asset into stable inexpensive metadata.

    Args:
        asset: Remote asset returned while enumerating a dandiset.

    Returns:
        Script-local asset metadata.
    """
    return DandiAssetMetadata(
        asset_id=str(asset.identifier),
        path=str(asset.path),
        size_bytes=int(asset.size),
        created=None if asset.created is None else str(asset.created),
        modified=None if asset.modified is None else str(asset.modified),
    )


def _dataset_metadata(
    raw_metadata: dict[str, object],
    dandiset_id: str,
    version: str,
) -> DandiDatasetMetadata:
    """Convert raw published DANDI metadata into the stable backend model.

    Args:
        raw_metadata: Raw version metadata returned by the DANDI API.
        dandiset_id: Six-digit DANDI identifier.
        version: Published dandiset version.

    Returns:
        Typed subset used by command-line and graphical clients.
    """
    doi_value = raw_metadata.get("doi")
    doi = None if doi_value in (None, "") else str(doi_value)
    if doi is not None:
        doi = doi.removeprefix("https://doi.org/")
    return DandiDatasetMetadata(
        dandiset_id=dandiset_id,
        version=version,
        name=str(raw_metadata.get("name") or ""),
        description=str(raw_metadata.get("description") or ""),
        doi=doi,
        url=str(
            raw_metadata.get("url")
            or f"https://dandiarchive.org/dandiset/{dandiset_id}/{version}"
        ),
        citation=str(raw_metadata.get("citation") or ""),
    )


def _series_semantics(
    response: object,
    stimulus: object | None,
    label: str,
) -> tuple[str, str, str | None]:
    """Validate series roles and return their NWB base units.

    Args:
        response: Candidate patch-clamp response series.
        stimulus: Candidate patch-clamp stimulus series, when present.
        label: Human-readable location used in validation errors.

    Returns:
        Clamp mode, response unit, and optional stimulus unit.

    Raises:
        UnsupportedNwbError: If series types or declared units are incompatible.
    """
    if isinstance(response, (CurrentClampSeries, IZeroClampSeries)):
        mode = "current clamp"
        response_unit = "volts"
        stimulus_unit = "amperes"
        stimulus_type = CurrentClampStimulusSeries
    elif isinstance(response, VoltageClampSeries):
        mode = "voltage clamp"
        response_unit = "amperes"
        stimulus_unit = "volts"
        stimulus_type = VoltageClampStimulusSeries
    else:
        raise UnsupportedNwbError(
            f"{label} response type {type(response).__name__} is unsupported"
        )
    if response.unit != response_unit:
        raise UnsupportedNwbError(
            f"{label} response unit must be {response_unit!r}; got {response.unit!r}"
        )
    if stimulus is None:
        return mode, response_unit, None
    if not isinstance(stimulus, stimulus_type):
        raise UnsupportedNwbError(
            f"{label} stimulus type {type(stimulus).__name__} is incompatible "
            f"with {mode}"
        )
    if stimulus.unit != stimulus_unit:
        raise UnsupportedNwbError(
            f"{label} stimulus unit must be {stimulus_unit!r}; got {stimulus.unit!r}"
        )
    return mode, response_unit, stimulus_unit


def _summarize_nwbfile(
    nwbfile: NWBFile,
    references: list[
        tuple[TimeSeriesReference, Optional[TimeSeriesReference]]
    ]
    | None = None,
) -> NwbHeaderMetadata:
    """Read table metadata without exhaustive all-sweep timing validation.

    Args:
        nwbfile: Open NWB file.
        references: Optional previously collected response/stimulus references.

    Returns:
        Lightweight recording summary suitable for a remote catalog.

    Raises:
        UnsupportedNwbError: If basic intracellular structure is unavailable.
    """
    sweep_references = references or _collect_sweep_references(nwbfile)
    electrode_ids: set[str] = set()
    has_stimulus = False
    clamp_mode: str | None = None
    for sweep_index, (response_reference, stimulus_reference) in enumerate(
        sweep_references
    ):
        response = response_reference.timeseries
        mode, _response_unit, _stimulus_unit = _series_semantics(
            response,
            stimulus_reference.timeseries if stimulus_reference is not None else None,
            label=f"sweep {sweep_index}",
        )
        if clamp_mode is None:
            clamp_mode = mode
        elif mode != clamp_mode:
            raise UnsupportedNwbError("NWB asset mixes clamp modes")
        electrode_id = getattr(response.electrode, "object_id", None)
        if electrode_id is None:
            raise UnsupportedNwbError(
                f"Sweep {sweep_index} response has no electrode ID"
            )
        electrode_ids.add(str(electrode_id))
        has_stimulus = has_stimulus or stimulus_reference is not None

    if len(electrode_ids) != 1:
        raise UnsupportedNwbError(
            f"The NWB reader requires one electrode; found {len(electrode_ids)}"
        )
    if clamp_mode is None:
        raise UnsupportedNwbError("NWB file contains no usable response sweeps")
    first_response = sweep_references[0][0]
    sample_interval, duration, _start = _reference_timing_summary(
        first_response,
        label="first response",
    )
    subject_id = None
    if nwbfile.subject is not None and nwbfile.subject.subject_id is not None:
        subject_id = str(nwbfile.subject.subject_id)
    session_id = None if nwbfile.session_id is None else str(nwbfile.session_id)
    return NwbHeaderMetadata(
        subject_id=subject_id,
        session_id=session_id,
        acquisition_datetime=nwbfile.session_start_time.isoformat(),
        num_sweeps=len(sweep_references),
        num_channels=len(electrode_ids),
        sample_rate_hz=1.0 / sample_interval,
        samples_per_sweep=int(first_response.count),
        sweep_duration_seconds=duration,
        has_stimulus=has_stimulus,
        clamp_mode=clamp_mode,
    )


def _inspect_nwbfile(
    nwbfile: NWBFile,
) -> tuple[
    NwbHeaderMetadata,
    list[tuple[TimeSeriesReference, Optional[TimeSeriesReference]]],
]:
    """Validate intracellular structure without reading response values.

    Args:
        nwbfile: Open NWB file.

    Returns:
        Header metadata and ordered response/stimulus references.

    Raises:
        UnsupportedNwbError: If SanPy cannot represent the recording.
    """
    references = _collect_sweep_references(nwbfile)
    electrode_ids: set[str] = set()
    common_interval: float | None = None
    common_duration: float | None = None
    common_count: int | None = None
    has_stimulus = False
    clamp_mode: str | None = None

    for sweep, (response_reference, stimulus_reference) in enumerate(references):
        response = response_reference.timeseries
        mode, _response_unit, _stimulus_unit = _series_semantics(
            response,
            stimulus_reference.timeseries if stimulus_reference is not None else None,
            label=f"sweep {sweep}",
        )
        if clamp_mode is None:
            clamp_mode = mode
        elif mode != clamp_mode:
            raise UnsupportedNwbError("NWB asset mixes clamp modes")
        electrode_id = getattr(response.electrode, "object_id", None)
        if electrode_id is None:
            raise UnsupportedNwbError(f"Sweep {sweep} response has no electrode ID")
        electrode_ids.add(str(electrode_id))

        interval, duration, _start = _reference_timing(
            response_reference,
            label=f"response for sweep {sweep}",
        )
        count = int(response_reference.count)
        common_interval = _require_common_float(
            common_interval, interval, f"Sweep {sweep} sample interval"
        )
        common_duration = _require_common_float(
            common_duration, duration, f"Sweep {sweep} duration"
        )
        if common_count is None:
            common_count = count
        elif count != common_count:
            raise UnsupportedNwbError(
                f"Sweep {sweep} has {count} samples; expected {common_count}"
            )

        if stimulus_reference is None:
            continue
        has_stimulus = True
        stimulus = stimulus_reference.timeseries
        if getattr(stimulus.electrode, "object_id", None) != electrode_id:
            raise UnsupportedNwbError(
                f"Sweep {sweep} stimulus and response reference different electrodes"
            )
        stimulus_interval, stimulus_duration, _stimulus_start = _reference_timing(
            stimulus_reference,
            label=f"stimulus for sweep {sweep}",
        )
        if int(stimulus_reference.count) != count:
            raise UnsupportedNwbError(
                f"Sweep {sweep} stimulus and response lengths differ"
            )
        if not np.isclose(stimulus_interval, interval, rtol=_RTOL, atol=_ATOL):
            raise UnsupportedNwbError(
                f"Sweep {sweep} stimulus and response sample intervals differ"
            )
        if not np.isclose(stimulus_duration, duration, rtol=_RTOL, atol=_ATOL):
            raise UnsupportedNwbError(
                f"Sweep {sweep} stimulus and response durations differ"
            )

    if len(electrode_ids) != 1:
        raise UnsupportedNwbError(
            f"The NWB reader requires one electrode; found {len(electrode_ids)}"
        )
    if common_interval is None or common_duration is None or common_count is None:
        raise UnsupportedNwbError("NWB file contains no usable response sweeps")
    if clamp_mode is None:
        raise UnsupportedNwbError("NWB file contains no usable response sweeps")

    subject_id = None
    if nwbfile.subject is not None and nwbfile.subject.subject_id is not None:
        subject_id = str(nwbfile.subject.subject_id)
    session_id = None if nwbfile.session_id is None else str(nwbfile.session_id)
    header = NwbHeaderMetadata(
        subject_id=subject_id,
        session_id=session_id,
        acquisition_datetime=nwbfile.session_start_time.isoformat(),
        num_sweeps=len(references),
        num_channels=len(electrode_ids),
        sample_rate_hz=1.0 / common_interval,
        samples_per_sweep=common_count,
        sweep_duration_seconds=common_duration,
        has_stimulus=has_stimulus,
        clamp_mode=clamp_mode,
    )
    return header, references


def _materialize_recording(
    header: NwbHeaderMetadata,
    references: list[tuple[TimeSeriesReference, Optional[TimeSeriesReference]]],
) -> DandiRecording:
    """Read validated response and stimulus values into rectangular arrays.

    Args:
        header: Previously validated header metadata.
        references: Ordered response and optional stimulus references.
    Returns:
        Materialized recording in declared NWB base units.

    Raises:
        UnsupportedNwbError: If trace timestamps are irregular or misaligned.
    """
    sweeps = [
        _materialize_sweep(
            header,
            reference_pair,
            sweep_index=sweep_index,
        )
        for sweep_index, reference_pair in enumerate(references)
    ]
    times = [sweep.time_seconds for sweep in sweeps]
    responses = [sweep.response_values for sweep in sweeps]
    stimuli = [sweep.stimulus_values for sweep in sweeps]
    missing_stimuli: list[int] = []
    for sweep_index, stimulus in enumerate(stimuli):
        if stimulus is None:
            missing_stimuli.append(sweep_index)

    warnings: list[str] = []
    stimulus_matrix: np.ndarray | None
    if len(missing_stimuli) == len(stimuli):
        stimulus_matrix = None
        warnings.append("No usable stimuli were present")
    else:
        stimulus_matrix = np.column_stack(
            [
                np.zeros_like(responses[sweep]) if stimulus is None else stimulus
                for sweep, stimulus in enumerate(stimuli)
            ]
        )
        if missing_stimuli:
            warnings.append(
                f"Inserted zero stimulus for missing sweeps {missing_stimuli}"
            )

    return DandiRecording(
        header=header,
        time_seconds=np.column_stack(times),
        response_values=np.column_stack(responses),
        response_unit=sweeps[0].response_unit,
        stimulus_values=stimulus_matrix,
        stimulus_unit=sweeps[0].stimulus_unit,
        warnings=tuple(warnings),
    )


def _materialize_sweep(
    header: NwbHeaderMetadata,
    references: tuple[TimeSeriesReference, Optional[TimeSeriesReference]],
    sweep_index: int,
) -> DandiSweep:
    """Read one validated response/stimulus pair into complete arrays.

    Args:
        header: Validated recording header metadata.
        references: Response and optional stimulus references for one sweep.
        sweep_index: Zero-based sweep position used in labels and the result.
    Returns:
        Materialized sweep in declared NWB base units.

    Raises:
        UnsupportedNwbError: If timestamps are irregular or misaligned.
    """
    response_reference, stimulus_reference = references
    response = response_reference.timeseries
    stimulus = None if stimulus_reference is None else stimulus_reference.timeseries
    _mode, response_unit, stimulus_unit = _series_semantics(
        response,
        stimulus,
        label=f"sweep {sweep_index}",
    )
    electrode_id = getattr(response.electrode, "object_id", None)
    if electrode_id is None:
        raise UnsupportedNwbError(f"Sweep {sweep_index} response has no electrode ID")
    response_time = _reference_timestamps(
        response_reference, label=f"response for sweep {sweep_index}"
    )
    local_time = response_time - float(response_time[0])
    _validate_regular_time(local_time, label=f"response for sweep {sweep_index}")
    response_values = _reference_values(
        response_reference, label=f"response for sweep {sweep_index}"
    )
    converted_response = _apply_nwb_conversion(response_values, response)

    warnings: list[str] = []
    converted_stimulus: np.ndarray | None = None
    if stimulus_reference is None:
        warnings.append("No usable stimulus was present")
    else:
        assert stimulus is not None
        if getattr(stimulus.electrode, "object_id", None) != electrode_id:
            raise UnsupportedNwbError(
                f"Sweep {sweep_index} stimulus and response reference different "
                "electrodes"
            )
        stimulus_time = _reference_timestamps(
            stimulus_reference, label=f"stimulus for sweep {sweep_index}"
        )
        stimulus_local_time = stimulus_time - float(stimulus_time[0])
        _validate_regular_time(
            stimulus_local_time, label=f"stimulus for sweep {sweep_index}"
        )
        if not np.allclose(stimulus_local_time, local_time, rtol=_RTOL, atol=_ATOL):
            raise UnsupportedNwbError(
                f"Sweep {sweep_index} stimulus and response sample times do not align"
            )
        stimulus_values = _reference_values(
            stimulus_reference, label=f"stimulus for sweep {sweep_index}"
        )
        converted_stimulus = _apply_nwb_conversion(stimulus_values, stimulus)

    return DandiSweep(
        header=header,
        sweep_index=sweep_index,
        time_seconds=local_time.astype(np.float64, copy=False),
        response_values=converted_response,
        response_unit=response_unit,
        stimulus_values=converted_stimulus,
        stimulus_unit=stimulus_unit,
        warnings=tuple(warnings),
    )


def _min_max_downsample(
    time_seconds: np.ndarray,
    values: np.ndarray,
    max_points: int,
) -> tuple[np.ndarray, np.ndarray]:
    """Reduce a trace with a time-ordered min/max envelope.

    Args:
        time_seconds: Complete one-dimensional time values.
        values: Complete one-dimensional signal values.
        max_points: Maximum number of returned points.

    Returns:
        Time and signal arrays containing each bin's extrema in temporal order.

    Raises:
        ValueError: If inputs differ in shape or fewer than four points are allowed.
    """
    if time_seconds.ndim != 1 or values.ndim != 1:
        raise ValueError("Plot traces must be one-dimensional")
    if time_seconds.shape != values.shape:
        raise ValueError("Plot time and value arrays must have matching shapes")
    if max_points < 4:
        raise ValueError("max_points must be at least 4")
    if len(values) <= max_points:
        return time_seconds, values

    bin_count = max_points // 2
    edges = np.linspace(0, len(values), bin_count + 1, dtype=np.int64)
    selected: list[int] = []
    for start, stop in zip(edges[:-1], edges[1:]):
        if stop <= start:
            continue
        segment = values[start:stop]
        minimum = int(start + np.argmin(segment))
        maximum = int(start + np.argmax(segment))
        if minimum == maximum:
            selected.append(minimum)
        elif minimum < maximum:
            selected.extend((minimum, maximum))
        else:
            selected.extend((maximum, minimum))
    indexes = np.asarray(selected, dtype=np.int64)
    return time_seconds[indexes], values[indexes]


def _apply_nwb_conversion(stored_values: np.ndarray, series: object) -> np.ndarray:
    """Apply the NWB conversion and offset without additional unit scaling.

    Args:
        stored_values: Selected raw values from an NWB series dataset.
        series: PyNWB series providing ``conversion`` and ``offset``.

    Returns:
        Values expressed in the series' declared NWB base unit.

    Raises:
        UnsupportedNwbError: If converted values are not finite.
    """
    converted = (
        stored_values * float(series.conversion) + float(series.offset)
    ).astype(np.float64, copy=False)
    if not np.isfinite(converted).all():
        raise UnsupportedNwbError(
            f"Series {series.name!r} contains nonfinite converted values"
        )
    return converted


def _quantity_axis_label(unit: str) -> str:
    """Return a concise physical-quantity label for an NWB base unit.

    Args:
        unit: Declared NWB unit.

    Returns:
        Axis label for volts, amperes, or an otherwise unknown unit.
    """
    labels = {"volts": "Voltage (V)", "amperes": "Current (A)"}
    return labels.get(unit, f"Signal ({unit})")


def _collect_sweep_references(
    nwbfile: NWBFile,
) -> list[tuple[TimeSeriesReference, Optional[TimeSeriesReference]]]:
    """Collect ordered response and optional stimulus references.

    Args:
        nwbfile: Open NWB file.

    Returns:
        Ordered response/stimulus pairs.

    Raises:
        UnsupportedNwbError: If references cannot be paired unambiguously.
    """
    recordings = nwbfile.intracellular_recordings
    if recordings is not None and len(recordings) > 0:
        frame = recordings.to_dataframe(ignore_category_ids=True)
        response_column = ("responses", "response")
        stimulus_column = ("stimuli", "stimulus")
        template_column = ("stimuli", "stimulus_template")
        if response_column not in frame.columns:
            raise UnsupportedNwbError(
                "IntracellularRecordingsTable has no response-reference column"
            )
        references: list[
            tuple[TimeSeriesReference, Optional[TimeSeriesReference]]
        ] = []
        for sweep, (_index, row) in enumerate(frame.iterrows()):
            response = _require_reference(
                row[response_column], label=f"response for sweep {sweep}"
            )
            stimulus = _optional_reference(
                row[stimulus_column] if stimulus_column in frame.columns else None
            )
            if stimulus is None and template_column in frame.columns:
                stimulus = _optional_reference(row[template_column])
            references.append((response, stimulus))
        return references

    responses: dict[
        int, CurrentClampSeries | IZeroClampSeries | VoltageClampSeries
    ] = {}
    for series in nwbfile.acquisition.values():
        if isinstance(
            series,
            (CurrentClampSeries, IZeroClampSeries, VoltageClampSeries),
        ):
            sweep_number = _require_sweep_number(series)
            if sweep_number in responses:
                raise UnsupportedNwbError(
                    f"Multiple responses use sweep number {sweep_number}"
                )
            responses[sweep_number] = series
    if not responses:
        raise UnsupportedNwbError("NWB file contains no supported clamp responses")

    stimuli: dict[int, CurrentClampStimulusSeries | VoltageClampStimulusSeries] = {}
    for series in nwbfile.stimulus.values():
        if isinstance(series, (CurrentClampStimulusSeries, VoltageClampStimulusSeries)):
            sweep_number = _require_sweep_number(series)
            if sweep_number in stimuli:
                raise UnsupportedNwbError(
                    f"Multiple stimuli use sweep number {sweep_number}"
                )
            stimuli[sweep_number] = series
    orphan_sweeps = sorted(set(stimuli).difference(responses))
    if orphan_sweeps:
        raise UnsupportedNwbError(
            f"Stimuli have no matching responses for sweeps {orphan_sweeps}"
        )

    return [
        (
            TimeSeriesReference(0, len(response.data), response),
            None
            if sweep_number not in stimuli
            else TimeSeriesReference(
                0,
                len(stimuli[sweep_number].data),
                stimuli[sweep_number],
            ),
        )
        for sweep_number, response in sorted(responses.items())
    ]


def _require_sweep_number(series: PatchClampSeries) -> int:
    """Return one valid nonnegative integer sweep number.

    Args:
        series: Patch-clamp series requiring a sweep association.

    Returns:
        Normalized sweep number.

    Raises:
        UnsupportedNwbError: If no valid sweep number is present.
    """
    try:
        value = float(series.sweep_number)
    except (TypeError, ValueError) as error:
        raise UnsupportedNwbError(
            f"Series {series.name!r} has invalid sweep number {series.sweep_number!r}"
        ) from error
    if not np.isfinite(value) or not value.is_integer() or value < 0:
        raise UnsupportedNwbError(
            f"Series {series.name!r} has invalid sweep number {series.sweep_number!r}"
        )
    return int(value)


def _optional_reference(value: object) -> TimeSeriesReference | None:
    """Return a valid reference when one is present.

    Args:
        value: Candidate table value.

    Returns:
        Valid reference or ``None``.
    """
    if not isinstance(value, TimeSeriesReference) or not value.isvalid():
        return None
    return value


def _require_reference(value: object, label: str) -> TimeSeriesReference:
    """Return a valid reference or report its table location.

    Args:
        value: Candidate table value.
        label: Human-readable reference location.

    Returns:
        Valid reference.

    Raises:
        UnsupportedNwbError: If the reference is missing or invalid.
    """
    reference = _optional_reference(value)
    if reference is None:
        raise UnsupportedNwbError(f"NWB file has no valid {label}")
    return reference


def _reference_timing_summary(
    reference: TimeSeriesReference,
    label: str,
) -> tuple[float, float, float]:
    """Read minimal timing values without materializing a complete time axis.

    Args:
        reference: Valid NWB time-series reference.
        label: Human-readable reference location.

    Returns:
        Sample interval, duration, and starting time in seconds.

    Raises:
        UnsupportedNwbError: If basic timing metadata is invalid.
    """
    count = int(reference.count)
    if count < 2:
        raise UnsupportedNwbError(f"{label} must contain at least two samples")
    series = reference.timeseries
    start_index = int(reference.idx_start)
    if series.timestamps is None:
        rate = float(series.rate)
        if not np.isfinite(rate) or rate <= 0:
            raise UnsupportedNwbError(f"{label} sampling rate must be positive")
        sample_interval = 1.0 / rate
        start = float(series.starting_time) + start_index * sample_interval
        return sample_interval, (count - 1) * sample_interval, start

    timestamps = series.timestamps
    first = float(timestamps[start_index])
    second = float(timestamps[start_index + 1])
    last = float(timestamps[start_index + count - 1])
    if not np.isfinite([first, second, last]).all():
        raise UnsupportedNwbError(f"{label} timestamps must be finite")
    sample_interval = second - first
    if sample_interval <= 0 or last < second:
        raise UnsupportedNwbError(f"{label} timestamps must be strictly increasing")
    return sample_interval, last - first, first


def _reference_timing(
    reference: TimeSeriesReference,
    label: str,
) -> tuple[float, float, float]:
    """Read timing metadata without reading response or stimulus values.

    Args:
        reference: Valid NWB time-series reference.
        label: Human-readable reference location.

    Returns:
        Sample interval, duration, and starting time in seconds.

    Raises:
        UnsupportedNwbError: If timing is invalid or irregular.
    """
    timestamps = _reference_timestamps(reference, label)
    local_time = timestamps - float(timestamps[0])
    sample_interval = _validate_regular_time(local_time, label)
    return sample_interval, float(local_time[-1]), float(timestamps[0])


def _reference_timestamps(
    reference: TimeSeriesReference,
    label: str,
) -> np.ndarray:
    """Materialize one selected time axis without reading trace values.

    Args:
        reference: Valid NWB time-series reference.
        label: Human-readable reference location.

    Returns:
        One-dimensional timestamps in seconds.

    Raises:
        UnsupportedNwbError: If timestamps are invalid.
    """
    count = int(reference.count)
    if count < 2:
        raise UnsupportedNwbError(f"{label} must contain at least two samples")
    series = reference.timeseries
    start_index = int(reference.idx_start)
    if series.timestamps is None:
        rate = float(series.rate)
        if not np.isfinite(rate) or rate <= 0:
            raise UnsupportedNwbError(f"{label} sampling rate must be positive")
        first = float(series.starting_time) + start_index / rate
        return first + np.arange(count, dtype=np.float64) / rate
    timestamps = np.asarray(reference.timestamps, dtype=np.float64)
    if timestamps.ndim != 1 or len(timestamps) != count:
        raise UnsupportedNwbError(f"{label} timestamps have an invalid shape")
    if not np.isfinite(timestamps).all():
        raise UnsupportedNwbError(f"{label} timestamps must be finite")
    return timestamps


def _reference_values(
    reference: TimeSeriesReference,
    label: str,
) -> np.ndarray:
    """Materialize one selected numeric trace.

    Args:
        reference: Valid NWB time-series reference.
        label: Human-readable reference location.

    Returns:
        One-dimensional floating-point values.

    Raises:
        UnsupportedNwbError: If values are masked or nonnumeric.
    """
    values = np.asanyarray(reference.data)
    if np.ma.isMaskedArray(values) and np.ma.getmaskarray(values).any():
        raise UnsupportedNwbError(f"{label} contains masked data")
    values = np.asarray(values)
    if values.ndim != 1 or not np.issubdtype(values.dtype, np.number):
        raise UnsupportedNwbError(f"{label} data must be one-dimensional and numeric")
    return values.astype(np.float64, copy=False)


def _validate_regular_time(timestamps: np.ndarray, label: str) -> float:
    """Validate a strictly increasing, regular time axis.

    Args:
        timestamps: Time values in seconds.
        label: Human-readable reference location.

    Returns:
        Sample interval in seconds.

    Raises:
        UnsupportedNwbError: If the time axis is invalid.
    """
    if len(timestamps) < 2:
        raise UnsupportedNwbError(f"{label} must contain at least two samples")
    intervals = np.diff(timestamps)
    if np.any(intervals <= 0):
        raise UnsupportedNwbError(f"{label} timestamps must be strictly increasing")
    interval = float(intervals[0])
    if not np.allclose(intervals, interval, rtol=_RTOL, atol=_ATOL):
        raise UnsupportedNwbError(f"{label} uses irregular sampling")
    return interval


def _require_common_float(
    expected: float | None,
    actual: float,
    label: str,
) -> float:
    """Require a floating-point value to match earlier sweeps.

    Args:
        expected: Existing common value or ``None`` for the first sweep.
        actual: Current sweep value.
        label: Human-readable value description.

    Returns:
        Common value.

    Raises:
        UnsupportedNwbError: If the current value differs.
    """
    if expected is None:
        return actual
    if not np.isclose(actual, expected, rtol=_RTOL, atol=_ATOL):
        raise UnsupportedNwbError(f"{label} {actual} differs from {expected}")
    return expected
