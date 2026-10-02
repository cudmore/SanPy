"""Focused tests for the public analysis-directory API."""

from pathlib import Path
import shutil

import sanpy


def test_analysis_dir_discovers_default_loaders(tmp_path: Path) -> None:
    """Scan a fresh folder without requiring a loader dictionary.

    Args:
        tmp_path: Pytest-managed temporary directory.
    """
    source = Path(__file__).parent / "data" / "2021_07_20_0010.abf"
    recording = tmp_path / source.name
    shutil.copy2(source, recording)

    directory = sanpy.analysisDir(
        path=str(tmp_path),
        autoLoad=False,
        folderDepth=1,
    )

    # Default discovery must not populate the explicit loader configuration.
    # Existing HDF5 catalogs use that distinction to decide whether to sync.
    assert directory._fileLoaderDict is None
    assert directory.numFiles == 1
    assert directory.get_file_key(0) == recording.name
    analysis = directory.get_analysis_for_file_key(recording.name)
    assert analysis is not None
    assert analysis.fileLoader is not None
    assert analysis.fileLoader.numSweeps == 18
