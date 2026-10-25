"""Create and reopen local-only DANDI Dandisets of SanPy NWB files."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import os
from pathlib import Path
import re
import tempfile
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator

from sanpy.io.nwb.recording import NwbRecordingMetadata, read_recording, write_recording

_IDENTIFIER_PATTERN = re.compile(r"^(?:DANDI:)?(?P<digits>\d{6})$")


class DandisetMetadata(BaseModel):
    """Describe the required metadata for a local Dandiset."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    identifier: str
    name: str
    description: str

    @field_validator("identifier")
    @classmethod
    def _normalize_identifier(cls, value: str) -> str:
        """Normalize a DANDI identifier.

        Args:
            value: Six digits with an optional ``DANDI:`` prefix.

        Returns:
            Identifier in ``DANDI:######`` form.

        Raises:
            ValueError: If the value is not a six-digit identifier.
        """
        match = _IDENTIFIER_PATTERN.fullmatch(value.strip())
        if match is None:
            raise ValueError("Dandiset identifier must contain exactly six digits")
        return f"DANDI:{match.group('digits')}"

    @field_validator("name", "description")
    @classmethod
    def _require_text(cls, value: str) -> str:
        """Require nonempty descriptive text.

        Args:
            value: Candidate text.

        Returns:
            Stripped nonempty text.

        Raises:
            ValueError: If the text is empty.
        """
        value = value.strip()
        if not value:
            raise ValueError("Dandiset name and description must not be empty")
        return value


@dataclass(frozen=True)
class DandisetWriteReport:
    """Report the result of one local Dandiset export.

    Attributes:
        path: Completed local Dandiset root.
        source_rows: Source analysis-directory rows in export order.
        asset_paths: Organized NWB paths relative to the Dandiset root.
        validation_messages: Nonblocking DANDI validation findings.
    """

    path: Path
    source_rows: tuple[int, ...]
    asset_paths: tuple[str, ...]
    validation_messages: tuple[str, ...]


@dataclass(frozen=True)
class LocalDandiset:
    """Represent a reopened local Dandiset.

    Attributes:
        path: Local Dandiset root.
        asset_paths: NWB paths relative to the root.
    """

    path: Path
    asset_paths: tuple[str, ...]

    def read_recording(self, asset: int | str) -> Any:
        """Load one NWB asset through the shared SanPy decoder.

        Args:
            asset: Zero-based asset index or exact relative asset path.

        Returns:
            Materialized SanPy ``bAnalysis``.

        Raises:
            KeyError: If a string asset path is not in this Dandiset.
        """
        if isinstance(asset, int):
            relative_path = self.asset_paths[asset]
        else:
            if asset not in self.asset_paths:
                raise KeyError(asset)
            relative_path = asset
        return read_recording(self.path / relative_path)


def write_dandiset(
    analysis_dir: Any,
    destination: str | Path,
    row_indices: Sequence[int],
    recording_metadata: Mapping[int, NwbRecordingMetadata],
    dandiset_metadata: DandisetMetadata,
) -> DandisetWriteReport:
    """Export selected analysis-directory rows as one atomic local Dandiset.

    Args:
        analysis_dir: SanPy ``analysisDir`` containing the selected rows.
        destination: New local Dandiset directory.
        row_indices: Explicit, nonempty source-row selection.
        recording_metadata: Per-row NWB metadata keyed by the selected rows.
        dandiset_metadata: Required Dandiset-level metadata.

    Returns:
        Completed export report.

    Raises:
        FileExistsError: If the destination already exists.
        ValueError: If selection, metadata, analysis loading, or validation fails.
        ImportError: If the optional DANDI dependencies are unavailable.
    """
    rows = tuple(row_indices)
    if not rows:
        raise ValueError("At least one analysis-directory row must be selected")
    if len(set(rows)) != len(rows) or any(row < 0 for row in rows):
        raise ValueError("Selected row indices must be unique nonnegative integers")
    if set(recording_metadata) != set(rows):
        raise ValueError("Recording metadata keys must exactly match selected rows")

    output = Path(destination).expanduser().resolve()
    if output.exists():
        raise FileExistsError(f"Refusing to replace local Dandiset: {output}")
    output.parent.mkdir(parents=True, exist_ok=True)

    try:
        from dandi.dandiset import Dandiset
        from dandi.organize import FileOperationMode, OrganizeInvalid, organize
        from dandi.validate._core import validate
        from dandi.validate._types import Severity
    except ImportError as error:
        raise ImportError(
            "Local Dandiset writing requires the SanPy 'dandi' extra"
        ) from error

    with tempfile.TemporaryDirectory(
        prefix=f".{output.name}-", dir=output.parent
    ) as temporary_directory:
        workspace = Path(temporary_directory)
        inputs = workspace / "inputs"
        completed = workspace / "completed"
        inputs.mkdir()
        staged_paths: list[Path] = []
        for row in rows:
            analysis = analysis_dir.getAnalysis(row, allowAutoLoad=True)
            if analysis is None or analysis.loadError:
                raise ValueError(f"Could not load selected analysis-directory row {row}")
            staged_paths.append(
                write_recording(
                    analysis,
                    inputs / f"recording-row-{row:06d}.nwb",
                    recording_metadata[row],
                )
            )

        completed.mkdir()
        local_dandiset = Dandiset(completed, allow_empty=True)
        local_dandiset.update_metadata(dandiset_metadata.model_dump())
        organize(
            paths=[str(path) for path in staged_paths],
            dandiset_path=str(completed),
            invalid=OrganizeInvalid.FAIL,
            files_mode=FileOperationMode.COPY,
        )
        reopened = Dandiset(completed)
        asset_paths = tuple(sorted(asset.path for asset in reopened.assets()))
        findings = tuple(validate(completed))
        blocking = tuple(
            finding
            for finding in findings
            if finding.severity is not None and finding.severity >= Severity.ERROR
        )
        if blocking:
            raise ValueError(f"DANDI validation failed: {blocking}")
        validation_messages = tuple(str(finding) for finding in findings)
        os.replace(completed, output)

    return DandisetWriteReport(
        path=output,
        source_rows=rows,
        asset_paths=asset_paths,
        validation_messages=validation_messages,
    )


def read_dandiset(path: str | Path) -> LocalDandiset:
    """Reopen a local Dandiset containing NWB assets.

    Args:
        path: Existing local Dandiset root.

    Returns:
        Local Dandiset with deterministically ordered asset paths.

    Raises:
        ValueError: If the path is not a Dandiset or contains no NWB assets.
    """
    root = Path(path).expanduser().resolve()
    if not (root / "dandiset.yaml").is_file():
        raise ValueError(f"Local Dandiset has no dandiset.yaml: {root}")
    assets = tuple(
        str(asset.relative_to(root))
        for asset in sorted(root.rglob("*.nwb"))
        if asset.is_file()
    )
    if not assets:
        raise ValueError(f"Local Dandiset contains no NWB assets: {root}")
    return LocalDandiset(path=root, asset_paths=assets)
