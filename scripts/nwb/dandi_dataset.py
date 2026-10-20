"""Represent a published DANDI dandiset as lazily streamed NWB assets."""

from __future__ import annotations

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
)

from sanpy.sanpyLogger import get_logger
from dandi_transport import FsspecNwbTransport

logger = get_logger(__name__)

_RTOL = 1e-9
_ATOL = 1e-12
_MAX_ABS_CURRENT_NA = 1000.0
_CURRENT_UNIT_TO_NA = {
    "A": 1e9,
    "mA": 1e6,
    "uA": 1e3,
    "nA": 1.0,
    "pA": 1e-3,
}


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
class NwbHeaderMetadata:
    """Describe a compatible intracellular current-clamp NWB asset.

    Attributes:
        subject_id: NWB subject identifier, when present.
        session_id: NWB session identifier, when present.
        acquisition_datetime: ISO-formatted session start time.
        num_sweeps: Number of response sweeps.
        num_channels: Number of response electrodes.
        sample_rate_hz: Common sweep sampling rate.
        samples_per_sweep: Common response sample count.
        sweep_duration_seconds: Time from the first through last sample.
        has_stimulus: Whether at least one sweep has a current stimulus.
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
        status: Header inspection result, either ``ready`` or ``error``.
        error: Header inspection error text, or ``None``.
        subject_id: NWB subject identifier, when available.
        session_id: NWB session identifier, when available.
        acquisition_datetime: ISO-formatted acquisition time, when available.
        num_sweeps: Number of response sweeps, when available.
        sample_rate_hz: Common sample rate, when available.
        samples_per_sweep: Common sample count, when available.
        duration_seconds: Common sweep duration, when available.
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

    def to_row(self) -> dict[str, object]:
        """Return a complete row suitable for tables and data frames.

        Returns:
            New dictionary whose keys match the public summary attributes.
        """
        return {field.name: getattr(self, field.name) for field in fields(self)}


@dataclass(frozen=True)
class DandiRecording:
    """Store one materialized current-clamp recording in SanPy units.

    Attributes:
        header: Header metadata validated while opening the asset.
        time_seconds: Sweep-local time, with one column per sweep.
        voltage_mv: Membrane voltage in millivolts.
        current_na: Command current in nanoamps, or ``None`` when every sweep
            lacks a usable stimulus.
        warnings: Nonfatal data-normalization messages.
    """

    header: NwbHeaderMetadata
    time_seconds: np.ndarray
    voltage_mv: np.ndarray
    current_na: np.ndarray | None
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
    """Store renderer-independent voltage and optional current plot data.

    Attributes:
        voltage: Membrane-voltage plot data.
        current: Command-current plot data, or ``None`` without a stimulus.
    """

    voltage: DandiTracePlotData
    current: DandiTracePlotData | None


@dataclass(frozen=True)
class DandiSweep:
    """Store one fully materialized current-clamp sweep in SanPy units.

    Attributes:
        header: Header metadata validated while opening the asset.
        sweep_index: Zero-based sweep position in the NWB recording table.
        time_seconds: Complete sweep-local time values.
        voltage_mv: Complete membrane-voltage values in millivolts.
        current_na: Complete command-current values in nanoamps, or ``None``.
        warnings: Nonfatal data-normalization messages.
    """

    header: NwbHeaderMetadata
    sweep_index: int
    time_seconds: np.ndarray
    voltage_mv: np.ndarray
    current_na: np.ndarray | None
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
        voltage_time, voltage_values = _min_max_downsample(
            self.time_seconds,
            self.voltage_mv,
            max_points=max_points,
        )
        voltage = DandiTracePlotData(
            time_seconds=voltage_time,
            values=voltage_values,
            x_axis_label="Time (s)",
            y_axis_label="Voltage (mV)",
        )
        current: DandiTracePlotData | None = None
        if self.current_na is not None:
            current_time, current_values = _min_max_downsample(
                self.time_seconds,
                self.current_na * 1000.0,
                max_points=max_points,
            )
            current = DandiTracePlotData(
                time_seconds=current_time,
                values=current_values,
                x_axis_label="Time (s)",
                y_axis_label="Current (pA)",
            )
        return DandiSweepPlotData(voltage=voltage, current=current)


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
        self._header_error: str | None = None
        self._sweep_cache_key: tuple[int, str | None] | None = None
        self._sweep_cache: DandiSweep | None = None

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
            Validated current-clamp header metadata.

        Raises:
            DandiDatasetError: If the remote asset cannot be opened.
            UnsupportedNwbError: If SanPy cannot represent the recording.
        """
        if self._header is not None and not refresh:
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
            header = self.load_header()
        except (DandiDatasetError, UnsupportedNwbError) as error:
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
            )
        return DandiAssetSummary(
            index=index,
            asset_id=self.metadata.asset_id,
            path=self.metadata.path,
            size_mb=round(self.metadata.size_bytes / 1_000_000, 2),
            status="ready",
            error=None,
            subject_id=header.subject_id,
            session_id=header.session_id,
            acquisition_datetime=header.acquisition_datetime,
            num_sweeps=header.num_sweeps,
            sample_rate_hz=header.sample_rate_hz,
            samples_per_sweep=header.samples_per_sweep,
            duration_seconds=header.sweep_duration_seconds,
        )

    def load_recording(
        self,
        current_unit_override: str | None = None,
    ) -> DandiRecording:
        """Stream and materialize all current-clamp sweeps from this asset.

        Args:
            current_unit_override: Optional physical unit of the raw stored
                stimulus values. When omitted, NWB conversion metadata is used.

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
                    current_unit_override=current_unit_override,
                )
        except UnsupportedNwbError:
            raise
        except Exception as error:
            raise DandiDatasetError(
                f'Could not load remote NWB asset "{self.metadata.path}": {error}'
            ) from error
        self._header = header
        self._header_error = None
        return recording

    def load_sweep(
        self,
        sweep_index: int,
        current_unit_override: str | None = None,
    ) -> DandiSweep:
        """Stream and materialize one current-clamp sweep from this asset.

        The most recently loaded sweep is retained in memory. An identical
        subsequent request returns the same result object.

        Args:
            sweep_index: Zero-based sweep position in the NWB recording table.
            current_unit_override: Optional physical unit of the raw stored
                stimulus values. When omitted, NWB conversion metadata is used.

        Returns:
            Complete selected sweep converted to display-independent SanPy units.

        Raises:
            IndexError: If ``sweep_index`` is outside the recording.
            DandiDatasetError: If the remote asset cannot be opened or read.
            UnsupportedNwbError: If SanPy cannot represent the sweep.
        """
        cache_key = (sweep_index, current_unit_override)
        if self._sweep_cache_key == cache_key and self._sweep_cache is not None:
            return self._sweep_cache
        try:
            with self._open_nwbfile() as nwbfile:
                header, references = _inspect_nwbfile(nwbfile)
                if sweep_index < 0 or sweep_index >= len(references):
                    raise IndexError(
                        f"Sweep index {sweep_index} is outside 0..{len(references) - 1}"
                    )
                sweep = _materialize_sweep(
                    header,
                    references[sweep_index],
                    sweep_index=sweep_index,
                    current_unit_override=current_unit_override,
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
        transport: FsspecNwbTransport | None = None,
    ) -> None:
        """Initialize a parsed dandiset without performing network access.

        Args:
            parsed_url: Parsed whole-dandiset URL with an explicit published version.
            transport: Optional remote-file transport override.
        """
        self._parsed_url = parsed_url
        self.dandiset_id = str(parsed_url.dandiset_id)
        self.version = str(parsed_url.version_id)
        self.transport = transport or FsspecNwbTransport()
        self._assets: tuple[DandiNwbAsset, ...] = ()

    @classmethod
    def from_url(
        cls,
        resource: str,
        transport: FsspecNwbTransport | None = None,
    ) -> DandiDataset:
        """Parse a whole published dandiset identifier without loading assets.

        Args:
            resource: DANDI identifier or canonical whole-dandiset URL.
            transport: Optional remote-file transport override.

        Returns:
            Unloaded published dandiset collection.

        Raises:
            DandiDatasetError: If the resource is not an explicitly versioned,
                published, whole production DANDI dandiset.
        """
        try:
            parsed_url = parse_dandi_url(resource)
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
                _dandiset,
                remote_assets,
            ):
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

    def __init__(self, transport: FsspecNwbTransport, content_url: str) -> None:
        """Initialize a remote NWB context manager.

        Args:
            transport: Transport used to open the remote content URL.
            content_url: Direct DANDI asset URL.
        """
        self._transport = transport
        self._content_url = content_url
        self._remote_context: object | None = None
        self._remote_file: object | None = None
        self._h5_file: h5py.File | None = None
        self._io: NWBHDF5IO | None = None

    def __enter__(self) -> NWBFile:
        """Open all remote NWB resources.

        Returns:
            NWB file whose lazy datasets remain accessible inside the context.
        """
        self._remote_context = self._transport.open(self._content_url)
        self._remote_file = self._remote_context.__enter__()  # type: ignore[attr-defined]
        self._h5_file = h5py.File(self._remote_file, mode="r")
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
        if self._h5_file is not None:
            self._h5_file.close()
        if self._remote_context is not None:
            self._remote_context.__exit__(  # type: ignore[attr-defined]
                exception_type,
                exception,
                traceback,
            )


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


def _inspect_nwbfile(
    nwbfile: NWBFile,
) -> tuple[
    NwbHeaderMetadata,
    list[tuple[TimeSeriesReference, Optional[TimeSeriesReference]]],
]:
    """Validate current-clamp structure without reading response values.

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

    for sweep, (response_reference, stimulus_reference) in enumerate(references):
        response = response_reference.timeseries
        if not isinstance(response, (CurrentClampSeries, IZeroClampSeries)):
            raise UnsupportedNwbError(
                f"Sweep {sweep} response is {type(response).__name__}, not current clamp"
            )
        if response.unit != "volts":
            raise UnsupportedNwbError(
                f"Sweep {sweep} response unit must be 'volts'; got {response.unit!r}"
            )
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
        if not isinstance(stimulus, CurrentClampStimulusSeries):
            raise UnsupportedNwbError(
                f"Sweep {sweep} stimulus is {type(stimulus).__name__}, not current clamp"
            )
        if stimulus.unit != "amperes":
            raise UnsupportedNwbError(
                f"Sweep {sweep} stimulus unit must be 'amperes'; got {stimulus.unit!r}"
            )
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
    )
    return header, references


def _materialize_recording(
    header: NwbHeaderMetadata,
    references: list[tuple[TimeSeriesReference, Optional[TimeSeriesReference]]],
    current_unit_override: str | None = None,
) -> DandiRecording:
    """Read validated voltage and current values into rectangular arrays.

    Args:
        header: Previously validated header metadata.
        references: Ordered response and optional stimulus references.
        current_unit_override: Optional unit of raw stored stimulus values.

    Returns:
        Materialized recording in SanPy units.

    Raises:
        UnsupportedNwbError: If trace timestamps are irregular or misaligned.
    """
    sweeps = [
        _materialize_sweep(
            header,
            reference_pair,
            sweep_index=sweep_index,
            current_unit_override=current_unit_override,
        )
        for sweep_index, reference_pair in enumerate(references)
    ]
    times = [sweep.time_seconds for sweep in sweeps]
    voltages = [sweep.voltage_mv for sweep in sweeps]
    currents = [sweep.current_na for sweep in sweeps]
    missing_stimuli: list[int] = []
    for sweep_index, current in enumerate(currents):
        if current is None:
            missing_stimuli.append(sweep_index)

    warnings: list[str] = []
    current_matrix: np.ndarray | None
    if len(missing_stimuli) == len(currents):
        current_matrix = None
        warnings.append("No usable current-clamp stimuli were present")
    else:
        current_matrix = np.column_stack(
            [
                np.zeros_like(voltages[sweep]) if current is None else current
                for sweep, current in enumerate(currents)
            ]
        )
        if missing_stimuli:
            warnings.append(
                f"Inserted zero current for missing stimulus sweeps {missing_stimuli}"
            )
    if current_unit_override is not None and current_matrix is not None:
        warnings.append(
            f"Interpreted raw stimulus values as {current_unit_override} by explicit override"
        )

    return DandiRecording(
        header=header,
        time_seconds=np.column_stack(times),
        voltage_mv=np.column_stack(voltages),
        current_na=current_matrix,
        warnings=tuple(warnings),
    )


def _materialize_sweep(
    header: NwbHeaderMetadata,
    references: tuple[TimeSeriesReference, Optional[TimeSeriesReference]],
    sweep_index: int,
    current_unit_override: str | None = None,
) -> DandiSweep:
    """Read one validated voltage/current pair into complete arrays.

    Args:
        header: Validated recording header metadata.
        references: Response and optional stimulus references for one sweep.
        sweep_index: Zero-based sweep position used in labels and the result.
        current_unit_override: Optional unit of raw stored stimulus values.

    Returns:
        Materialized sweep in SanPy units.

    Raises:
        UnsupportedNwbError: If timestamps are irregular or misaligned.
    """
    response_reference, stimulus_reference = references
    response = response_reference.timeseries
    response_time = _reference_timestamps(
        response_reference, label=f"response for sweep {sweep_index}"
    )
    local_time = response_time - float(response_time[0])
    _validate_regular_time(local_time, label=f"response for sweep {sweep_index}")
    response_values = _reference_values(
        response_reference, label=f"response for sweep {sweep_index}"
    )
    voltage = (
        response_values * float(response.conversion) + float(response.offset)
    ) * 1e3

    warnings: list[str] = []
    current: np.ndarray | None = None
    if stimulus_reference is None:
        warnings.append("No usable current-clamp stimulus was present")
    else:
        stimulus = stimulus_reference.timeseries
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
        current = _convert_current_to_na(
            stimulus_values,
            conversion=float(stimulus.conversion),
            offset_amperes=float(stimulus.offset),
            stored_unit_override=current_unit_override,
            label=f"stimulus for sweep {sweep_index}",
        )
        if current_unit_override is not None:
            warnings.append(
                f"Interpreted raw stimulus values as {current_unit_override} by "
                "explicit override"
            )

    return DandiSweep(
        header=header,
        sweep_index=sweep_index,
        time_seconds=local_time.astype(np.float64, copy=False),
        voltage_mv=voltage.astype(np.float64, copy=False),
        current_na=None if current is None else current.astype(np.float64, copy=False),
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


def _convert_current_to_na(
    stored_values: np.ndarray,
    conversion: float,
    offset_amperes: float,
    stored_unit_override: str | None,
    label: str,
) -> np.ndarray:
    """Convert stored NWB current values to nanoamps in one place.

    Args:
        stored_values: Raw numeric stimulus values from the NWB dataset.
        conversion: NWB multiplier that converts stored values to amperes.
        offset_amperes: NWB offset applied after conversion, in amperes.
        stored_unit_override: Explicit physical unit for raw values, or ``None``
            to follow NWB metadata.
        label: Human-readable series location used in errors.

    Returns:
        Current values in nanoamps.

    Raises:
        UnsupportedNwbError: If values are nonfinite, an override is unknown,
            or the converted magnitude exceeds SanPy's whole-cell limit.
    """
    if stored_unit_override is None:
        current_na = (stored_values * conversion + offset_amperes) * 1e9
        conversion_description = (
            f"NWB conversion={conversion!r}, offset={offset_amperes!r} A"
        )
    else:
        try:
            scale_to_na = _CURRENT_UNIT_TO_NA[stored_unit_override]
        except KeyError as error:
            supported = ", ".join(_CURRENT_UNIT_TO_NA)
            raise UnsupportedNwbError(
                f"{label} current-unit override {stored_unit_override!r} is not "
                f"supported; choose one of {supported}"
            ) from error
        current_na = stored_values * scale_to_na + offset_amperes * 1e9
        conversion_description = (
            f"explicit raw-unit override={stored_unit_override!r}, "
            f"NWB offset={offset_amperes!r} A"
        )

    if not np.isfinite(current_na).all():
        raise UnsupportedNwbError(f"{label} converted current contains nonfinite values")
    max_absolute_na = float(np.max(np.abs(current_na), initial=0.0))
    if max_absolute_na > _MAX_ABS_CURRENT_NA:
        raw_min = float(np.min(stored_values))
        raw_max = float(np.max(stored_values))
        raise UnsupportedNwbError(
            f"{label} converts to {max_absolute_na:g} nA, exceeding SanPy's "
            f"whole-cell limit of {_MAX_ABS_CURRENT_NA:g} nA. Raw range is "
            f"{raw_min:g} to {raw_max:g}; {conversion_description}. The NWB "
            "scaling metadata may be incomplete; provide an explicit stored-current "
            "unit only when the correct unit is known."
        )
    return current_na.astype(np.float64, copy=False)


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

    responses: dict[int, CurrentClampSeries | IZeroClampSeries] = {}
    for series in nwbfile.acquisition.values():
        if isinstance(series, (CurrentClampSeries, IZeroClampSeries)):
            sweep_number = _require_sweep_number(series)
            if sweep_number in responses:
                raise UnsupportedNwbError(
                    f"Multiple responses use sweep number {sweep_number}"
                )
            responses[sweep_number] = series
    if not responses:
        raise UnsupportedNwbError("NWB file contains no current-clamp responses")

    stimuli: dict[int, CurrentClampStimulusSeries] = {}
    for series in nwbfile.stimulus.values():
        if isinstance(series, CurrentClampStimulusSeries):
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
