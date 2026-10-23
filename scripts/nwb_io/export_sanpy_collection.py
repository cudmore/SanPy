"""Export a folder-backed SanPy analysis collection to individual NWB files."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import sanpy

from export_sanpy_banalysis_to_nwb import (
    NwbExportMetadata,
    NwbExportVerifier,
    SanPyNwbExporter,
)

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class DandisetExportConfig:
    """Configure one local SanPy collection export.

    Attributes:
        source_directory: Folder opened as a SanPy ``analysisDir``.
        output_directory: Destination local Dandiset directory.
        dandiset_identifier: Six-digit local Dandiset identifier.
        name: Human-readable local Dandiset title.
        description: Human-readable local Dandiset description.
        species: Scientific name applied explicitly to every subject.
        timezone_name: IANA timezone for naive runtime acquisition values.
        fallback_acquisition_datetime: Development fallback used when runtime
            acquisition metadata is absent.
        selected_file_keys: Optional stable file-key subset; ``None`` exports all.
    """

    source_directory: Path
    output_directory: Path
    dandiset_identifier: str
    name: str
    description: str
    species: str
    timezone_name: str
    fallback_acquisition_datetime: datetime
    selected_file_keys: tuple[str, ...] | None = None


@dataclass(frozen=True)
class RecordingExportResult:
    """Report the outcome of exporting one SanPy recording.

    Attributes:
        row_index: Row label in the loaded ``analysisDir``.
        ordinal: One-based position in this export operation.
        file_key: Stable source identity relative to the analysis directory.
        subject_id: Explicit synthetic development subject identifier.
        cell_id: Explicit synthetic development cell identifier.
        output_path: Staged NWB path, or ``None`` after failure.
        had_saved_analysis: Whether the loaded ``bAnalysis`` reports analysis.
        used_fallback_acquisition_datetime: Whether the configured fallback was used.
        error: Failure message, or ``None`` after success.
    """

    row_index: int
    ordinal: int
    file_key: str
    subject_id: str
    cell_id: str
    output_path: Path | None
    had_saved_analysis: bool
    used_fallback_acquisition_datetime: bool
    error: str | None

    @property
    def succeeded(self) -> bool:
        """Return whether this recording was exported and verified.

        Returns:
            True when the result has an output path and no error.
        """
        return self.output_path is not None and self.error is None


@dataclass(frozen=True)
class CollectionExportReport:
    """Report every requested recording export.

    Attributes:
        source_directory: Folder opened as the source ``analysisDir``.
        results: Per-recording outcomes in export order.
    """

    source_directory: Path
    results: tuple[RecordingExportResult, ...]

    @property
    def successful_paths(self) -> tuple[Path, ...]:
        """Return paths for every successful staged NWB export.

        Returns:
            Successful output paths in export order.
        """
        return tuple(
            result.output_path
            for result in self.results
            if result.output_path is not None and result.error is None
        )

    @property
    def failure_count(self) -> int:
        """Return the number of failed requested exports.

        Returns:
            Number of results containing an error.
        """
        return sum(result.error is not None for result in self.results)


class SanPyNwbCollectionExporter:
    """Export requested ``analysisDir`` recordings through the single-file API."""

    def __init__(self, config: DandisetExportConfig) -> None:
        """Validate and retain collection export configuration.

        Args:
            config: Complete local export configuration.

        Raises:
            ValueError: If required development configuration is invalid.
        """
        if not config.species.strip():
            raise ValueError("Collection species must not be empty")
        if config.fallback_acquisition_datetime.tzinfo is None:
            raise ValueError("Fallback acquisition datetime must include a timezone")
        self._config = config

    def export(self, staging_directory: Path) -> CollectionExportReport:
        """Export selected recordings into a fresh staging directory.

        Args:
            staging_directory: New directory receiving unorganized NWB files.

        Returns:
            Complete per-recording export report.

        Raises:
            FileExistsError: If the staging directory already exists.
            FileNotFoundError: If the source directory does not exist.
            ValueError: If a requested stable file key is unknown.
        """
        source_directory = self._config.source_directory.expanduser().resolve()
        if not source_directory.is_dir():
            raise FileNotFoundError(
                f"SanPy analysis directory does not exist: {source_directory}"
            )
        staging_directory = staging_directory.expanduser().resolve()
        if staging_directory.exists():
            raise FileExistsError(
                f"Refusing to replace staging directory: {staging_directory}"
            )
        staging_directory.mkdir(parents=True)

        analysis_directory = sanpy.analysisDir(path=str(source_directory))
        selected_rows = self._selected_rows(analysis_directory)
        results = tuple(
            self._export_row(
                analysis_directory=analysis_directory,
                row_index=row_index,
                ordinal=ordinal,
                staging_directory=staging_directory,
            )
            for ordinal, row_index in enumerate(selected_rows, start=1)
        )
        return CollectionExportReport(
            source_directory=source_directory,
            results=results,
        )

    def _selected_rows(self, analysis_directory: sanpy.analysisDir) -> tuple[int, ...]:
        """Resolve configured file keys to ``analysisDir`` row labels.

        Args:
            analysis_directory: Loaded SanPy collection.

        Returns:
            Requested row labels in deterministic collection order.

        Raises:
            ValueError: If any configured file key is unknown.
        """
        all_rows = tuple(int(row_index) for row_index in analysis_directory.index)
        selected_keys = self._config.selected_file_keys
        if selected_keys is None:
            return all_rows
        requested = set(selected_keys)
        rows = tuple(
            row_index
            for row_index in all_rows
            if analysis_directory.get_file_key(row_index) in requested
        )
        found = {
            analysis_directory.get_file_key(row_index) for row_index in rows
        }
        missing = sorted(requested - found)
        if missing:
            raise ValueError(f"Unknown analysisDir file keys: {missing}")
        return rows

    def _export_row(
        self,
        analysis_directory: sanpy.analysisDir,
        row_index: int,
        ordinal: int,
        staging_directory: Path,
    ) -> RecordingExportResult:
        """Export and verify one collection row without stopping later rows.

        Args:
            analysis_directory: Loaded source collection.
            row_index: Source row label.
            ordinal: One-based export position.
            staging_directory: Directory receiving the new NWB file.

        Returns:
            Successful or failed recording result.
        """
        file_key = analysis_directory.get_file_key(row_index)
        # NWB Subject identifies the biological organism. These ordinal IDs are
        # explicit development placeholders, not identities inferred from names.
        subject_id = f"development-subject-{ordinal:03d}"
        cell_id = f"development-cell-{ordinal:03d}"
        output_path = staging_directory / f"sanpy-recording-{ordinal:03d}.nwb"
        analysis = analysis_directory.get_analysis_for_file_key(file_key)
        if analysis is None:
            return RecordingExportResult(
                row_index=row_index,
                ordinal=ordinal,
                file_key=file_key,
                subject_id=subject_id,
                cell_id=cell_id,
                output_path=None,
                had_saved_analysis=False,
                used_fallback_acquisition_datetime=False,
                error="SanPy could not load the recording",
            )
        had_saved_analysis = bool(analysis.isAnalyzed())
        try:
            export_metadata = self._recording_metadata(
                analysis,
                subject_id,
                cell_id,
            )
            exporter = SanPyNwbExporter(
                analysis,
                metadata=export_metadata,
                timezone_name=self._config.timezone_name,
            )
            written_path = exporter.export(output_path)
            NwbExportVerifier(analysis, written_path).verify()
            return RecordingExportResult(
                row_index=row_index,
                ordinal=ordinal,
                file_key=file_key,
                subject_id=subject_id,
                cell_id=cell_id,
                output_path=written_path,
                had_saved_analysis=had_saved_analysis,
                used_fallback_acquisition_datetime=(
                    exporter.used_fallback_acquisition_datetime
                ),
                error=None,
            )
        except Exception as error:
            LOGGER.exception(f'Could not export SanPy recording "{file_key}"')
            return RecordingExportResult(
                row_index=row_index,
                ordinal=ordinal,
                file_key=file_key,
                subject_id=subject_id,
                cell_id=cell_id,
                output_path=None,
                had_saved_analysis=had_saved_analysis,
                used_fallback_acquisition_datetime=False,
                error=str(error),
            )

    def _recording_metadata(
        self,
        analysis: sanpy.bAnalysis,
        subject_id: str,
        cell_id: str,
    ) -> NwbExportMetadata:
        """Map optional SanPy experimental fields into NWB subject metadata.

        Args:
            analysis: Loaded SanPy runtime recording.
            subject_id: Explicit synthetic development subject identity.
            cell_id: Explicit synthetic development cell identity.

        Returns:
            Valid single-recording export metadata.
        """
        metadata = analysis.metaData
        return NwbExportMetadata(
            subject_id=subject_id,
            cell_id=cell_id,
            species=self._config.species,
            fallback_acquisition_datetime=(
                self._config.fallback_acquisition_datetime
            ),
            age=_optional_text(metadata.get("age")),
            sex=_nwb_sex(metadata.get("sex")),
            genotype=_optional_text(metadata.get("genotype")),
        )


def _optional_text(value: object) -> str | None:
    """Normalize an optional SanPy metadata value.

    Args:
        value: Candidate metadata value.

    Returns:
        Stripped text or ``None`` for an empty value.
    """
    text = str(value or "").strip()
    return text or None


def _nwb_sex(value: object) -> str | None:
    """Map SanPy sex vocabulary to conventional NWB values.

    Args:
        value: SanPy sex metadata value.

    Returns:
        NWB ``M``, ``F``, ``U``, or ``O`` value, or ``None`` when unknown.
    """
    normalized = str(value or "").strip().lower()
    return {
        "male": "M",
        "female": "F",
        "unclassified": "U",
        "not_applicable": "O",
        "unknown": "U",
        "": "U",
    }.get(normalized, "U")
