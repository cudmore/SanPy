"""Build, validate, and reopen a local-only DANDI Dandiset."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from dandi.dandiset import Dandiset
from dandi.organize import FileOperationMode, OrganizeInvalid, organize
from dandi.validate._core import validate
from dandi.validate._types import Severity, ValidationResult

LOGGER = logging.getLogger(__name__)
_DANDISET_IDENTIFIER_PATTERN = re.compile(r"^(?:DANDI:)?(?P<digits>\d{6})$")


@dataclass(frozen=True)
class LocalDandisetReport:
    """Report an organized and reopened local Dandiset.

    Attributes:
        path: Local Dandiset root.
        identifier: Normalized ``DANDI:######`` identifier.
        asset_paths: Organized asset paths relative to the Dandiset root.
        validation_results: Complete DANDI validation findings.
    """

    path: Path
    identifier: str
    asset_paths: tuple[str, ...]
    validation_results: tuple[ValidationResult, ...]

    @property
    def blocking_validation_count(self) -> int:
        """Return validation findings that prevent a clean Dandiset.

        Returns:
            Number of warning-or-higher validation findings.
        """
        return sum(
            result.severity is not None and result.severity >= Severity.WARNING
            for result in self.validation_results
        )


class LocalDandisetBuilder:
    """Organize verified NWB exports into a fresh local Dandiset."""

    def __init__(
        self,
        output_directory: Path,
        identifier: str,
        name: str,
        description: str,
    ) -> None:
        """Initialize and validate local Dandiset metadata.

        Args:
            output_directory: Fresh directory to create.
            identifier: Six-digit or ``DANDI:######`` local identifier.
            name: Human-readable Dandiset title.
            description: Human-readable Dandiset description.

        Raises:
            ValueError: If metadata is empty or the identifier is malformed.
        """
        self._output_directory = output_directory.expanduser().resolve()
        self._identifier = _normalize_identifier(identifier)
        if not name.strip():
            raise ValueError("Local Dandiset name must not be empty")
        if not description.strip():
            raise ValueError("Local Dandiset description must not be empty")
        self._name = name
        self._description = description

    def build(self, nwb_paths: Sequence[Path]) -> LocalDandisetReport:
        """Create, organize, validate, and reopen a local Dandiset.

        Args:
            nwb_paths: Verified staged NWB files to copy and organize.

        Returns:
            Local Dandiset report including organized assets and validation.

        Raises:
            FileExistsError: If the destination already exists.
            FileNotFoundError: If a staged NWB file is missing.
            ValueError: If no NWB files were supplied.
        """
        if self._output_directory.exists():
            raise FileExistsError(
                f"Refusing to replace local Dandiset: {self._output_directory}"
            )
        resolved_paths = tuple(path.expanduser().resolve() for path in nwb_paths)
        if not resolved_paths:
            raise ValueError("At least one verified NWB file is required")
        missing = [path for path in resolved_paths if not path.is_file()]
        if missing:
            raise FileNotFoundError(f"Staged NWB files are missing: {missing}")

        self._output_directory.mkdir(parents=True)
        local_dandiset = Dandiset(self._output_directory, allow_empty=True)
        local_dandiset.update_metadata(
            {
                "identifier": self._identifier,
                "name": self._name,
                "description": self._description,
            }
        )
        if self._identifier == "DANDI:000000":
            LOGGER.warning(
                "Using synthetic local Dandiset identifier DANDI:000000; "
                "replace it with a real DANDI Sandbox draft identifier before upload"
            )
        organize(
            paths=[str(path) for path in resolved_paths],
            dandiset_path=str(self._output_directory),
            invalid=OrganizeInvalid.FAIL,
            files_mode=FileOperationMode.COPY,
        )

        reopened = Dandiset(self._output_directory)
        asset_paths = tuple(asset.path for asset in reopened.assets())
        validation_results = tuple(validate(self._output_directory))
        return LocalDandisetReport(
            path=self._output_directory,
            identifier=self._identifier,
            asset_paths=asset_paths,
            validation_results=validation_results,
        )


def _normalize_identifier(identifier: str) -> str:
    """Normalize a six-digit development Dandiset identifier.

    Args:
        identifier: Six digits with an optional ``DANDI:`` prefix.

    Returns:
        Identifier in ``DANDI:######`` form.

    Raises:
        ValueError: If the identifier does not contain exactly six digits.
    """
    match = _DANDISET_IDENTIFIER_PATTERN.fullmatch(identifier.strip())
    if match is None:
        raise ValueError(
            f"Dandiset identifier must contain six digits; got {identifier!r}"
        )
    return f"DANDI:{match.group('digits')}"
