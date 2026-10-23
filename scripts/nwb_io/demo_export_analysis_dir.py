"""Export a development SanPy ``analysisDir`` into a local Dandiset."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from zoneinfo import ZoneInfo

from export_sanpy_collection import (
    CollectionExportReport,
    DandisetExportConfig,
    SanPyNwbCollectionExporter,
)
from local_dandiset import LocalDandisetBuilder, LocalDandisetReport

SOURCE_DIRECTORY = Path("/Users/cudmore/data/nwb/001261-dandi-export")
OUTPUT_DIRECTORY = Path("/Users/cudmore/data/nwb/001261-sanpy-dandiset")
DEVELOPMENT_DANDISET_IDENTIFIER = "000000"
DEVELOPMENT_SPECIES = "Mus musculus"
DEVELOPMENT_TIMEZONE = "America/New_York"
DEVELOPMENT_FALLBACK_DATETIME = datetime(
    1970,
    1,
    1,
    0,
    0,
    tzinfo=ZoneInfo(DEVELOPMENT_TIMEZONE),
)


def _config() -> DandisetExportConfig:
    """Return the explicit local development configuration.

    Returns:
        Configuration for the agreed local SanPy collection fixture.
    """
    return DandisetExportConfig(
        source_directory=SOURCE_DIRECTORY,
        output_directory=OUTPUT_DIRECTORY,
        dandiset_identifier=DEVELOPMENT_DANDISET_IDENTIFIER,
        name="SanPy current-clamp development export",
        description=(
            "Local development export of SanPy current-clamp recordings to NWB. "
            "Synthetic subject and Dandiset identifiers must be replaced before "
            "upload."
        ),
        species=DEVELOPMENT_SPECIES,
        timezone_name=DEVELOPMENT_TIMEZONE,
        fallback_acquisition_datetime=DEVELOPMENT_FALLBACK_DATETIME,
        selected_file_keys=None,
    )


def _print_collection_report(report: CollectionExportReport) -> None:
    """Print concise per-recording collection export results.

    Args:
        report: Completed collection export report.
    """
    for result in report.results:
        status = "ok" if result.succeeded else f"error: {result.error}"
        fallback = " [fallback datetime]" if result.used_fallback_acquisition_datetime else ""
        analyzed = "analyzed" if result.had_saved_analysis else "not analyzed"
        print(
            f"{result.ordinal:03d} {result.subject_id} {result.cell_id} {analyzed}: "
            f"{result.file_key} -> {status}{fallback}"
        )
    print(
        f"Exported {len(report.successful_paths)} of {len(report.results)} "
        f"recordings; failures: {report.failure_count}"
    )


def _print_dandiset_report(report: LocalDandisetReport) -> None:
    """Print the organized local Dandiset result.

    Args:
        report: Completed local Dandiset report.
    """
    print(f"Local Dandiset: {report.path}")
    print(f"Identifier: {report.identifier}")
    print(f"Organized assets: {len(report.asset_paths)}")
    print(f"Blocking validation findings: {report.blocking_validation_count}")
    for result in report.validation_results:
        if result.severity is not None:
            print(f"  {result.severity.name} {result.id}: {result.message}")


def main() -> int:
    """Export the configured SanPy collection and build a local Dandiset.

    Returns:
        Zero after a clean local Dandiset, otherwise one.
    """
    logging.basicConfig(
        level=logging.INFO,
        format="{levelname}: {message}",
        style="{",
    )
    config = _config()
    config.output_directory.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(
        prefix="sanpy-nwb-staging-",
        dir=config.output_directory.parent,
    ) as temporary_directory:
        staging_directory = Path(temporary_directory) / "exports"
        collection_report = SanPyNwbCollectionExporter(config).export(
            staging_directory
        )
        _print_collection_report(collection_report)
        if collection_report.failure_count:
            print("Local Dandiset was not built because requested exports failed.")
            return 1
        dandiset_report = LocalDandisetBuilder(
            output_directory=config.output_directory,
            identifier=config.dandiset_identifier,
            name=config.name,
            description=config.description,
        ).build(collection_report.successful_paths)
    _print_dandiset_report(dandiset_report)
    return 0 if dandiset_report.blocking_validation_count == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
