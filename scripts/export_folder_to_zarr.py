"""Export an existing SanPy analysis folder to SanPy Zarr."""

from __future__ import annotations

import argparse
from pathlib import Path

import sanpy
from sanpy.io.zarr_export.exporter import export_collection


def export_folder(
    source_folder: Path,
    destination: Path,
    *,
    table_format: str = "both",
    overwrite: bool = False,
) -> Path:
    """Export a SanPy folder and its persisted analyses.

    Args:
        source_folder: Folder containing source recordings and
            ``sanpy_recording_db.h5``.
        destination: Output directory ending in ``.sanpy.zarr``.
        table_format: Table representation: ``csv``, ``parquet``, or
            ``both``.
        overwrite: Replace an existing destination when true.

    Returns:
        Absolute path to the completed SanPy Zarr collection.

    Raises:
        FileNotFoundError: If the folder or HDF5 catalog does not exist.
        RuntimeError: If no supported analyses can be loaded.
    """
    source_folder = source_folder.expanduser().resolve()
    h5_path = source_folder / "sanpy_recording_db.h5"

    if not source_folder.is_dir():
        raise FileNotFoundError(f"SanPy folder not found: {source_folder}")
    if not h5_path.is_file():
        raise FileNotFoundError(f"SanPy HDF5 catalog not found: {h5_path}")

    analysis_directory = sanpy.analysisDir(str(source_folder), autoLoad=False)
    analyses = []

    for row_index in range(analysis_directory.numFiles):
        analysis = analysis_directory.getAnalysis(
            row_index,
            allowAutoLoad=True,
        )
        if analysis is None:
            continue

        source_path = Path(analysis.fileLoader.filepath)
        if source_path.suffix.lower() in {".abf", ".sanpy"}:
            analyses.append(analysis)

    if not analyses:
        raise RuntimeError(
            f"No ABF- or .sanpy-backed analyses found in {source_folder}"
        )

    return export_collection(
        analyses,
        destination,
        name=source_folder.name,
        table_format=table_format,
        overwrite=overwrite,
    )


def main() -> None:
    """Run the folder exporter from the command line."""
    parser = argparse.ArgumentParser()
    parser.add_argument("source_folder", type=Path)
    parser.add_argument("destination", type=Path)
    parser.add_argument(
        "--table-format",
        choices=("csv", "parquet", "both"),
        default="both",
    )
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args()

    output = export_folder(
        args.source_folder,
        args.destination,
        table_format=args.table_format,
        overwrite=args.overwrite,
    )
    print(output)


if __name__ == "__main__":
    main()
