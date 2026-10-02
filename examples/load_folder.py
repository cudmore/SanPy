"""Load a folder-backed collection of SanPy recordings and analyses."""

from pathlib import Path

import sanpy


def main() -> None:
    """Summarize an analysis directory and load one saved analysis.

    Raises:
        RuntimeError: If the example recording or its analysis cannot be found.
    """
    # Locate the bundled example-data folder relative to the SanPy repository.
    sanpy_root = Path(__file__).resolve().parents[1]
    example_data_path = sanpy_root / "sanpy/user_files/SanPy-User-Files/example-data"

    # Build the folder catalog without eagerly loading every recording into memory.
    analysis_directory = sanpy.analysisDir(
        path=str(example_data_path),
        autoLoad=False,
        folderDepth=1,
    )

    # Print a concise summary of the complete folder.
    print(analysis_directory)
    print(f"Files: {analysis_directory.numFiles}")

    # The file table contains recording metadata and saved-analysis status. Work
    # with a copy so this display code cannot modify the analysis directory.
    file_table = analysis_directory.copy()
    summary_columns = ["File", "Sweeps", "Dur(s)", "Mode", "N"]
    print(file_table[summary_columns].to_string(index=False))

    # Stable file keys are paths relative to the analysis directory. They avoid
    # relying on a row number, which can change when the table is sorted.
    file_key = "stochastic-hh.sanpy"
    row_index = analysis_directory.get_row_for_file_key(file_key)
    if row_index is None:
        raise RuntimeError(f"Recording is not in the analysis directory: {file_key}")
    print(f"{file_key} is at row {row_index}")

    # Load the recording and its saved analysis on demand from the folder catalog.
    analysis = analysis_directory.get_analysis_for_file_key(file_key)
    if analysis is None:
        raise RuntimeError(f"Could not load recording and analysis: {file_key}")
    print(analysis)


if __name__ == "__main__":
    main()
