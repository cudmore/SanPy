"""Tests for core ABF, TIFF, and sweep-access file-loader behavior."""

from pathlib import Path

import numpy as np

import sanpy
from sanpy.fileloaders.fileLoader_abf import fileLoader_abf
from sanpy.fileloaders.fileLoader_base import fileLoader_base
from sanpy.fileloaders.fileLoader_tif import fileLoader_tif


def test_file_loader_abf(test_data_dir: Path) -> None:
    """Load an ABF and calculate a derivative matching its sweep shape.

    Args:
        test_data_dir: Stable test-only data directory.
    """
    loader = fileLoader_abf(str(test_data_dir / "2021_07_20_0010.abf"))

    assert not loader.getLoadError()
    assert loader.loadFileType == ".abf"
    assert loader.sweepLabelX == "sec"
    loader._getDerivative()
    assert loader.filteredDeriv.shape == loader.sweepX.shape


def test_get_sweep_y_ignores_current_sweep() -> None:
    """Return the requested sweep column without reading currentSweep."""

    class _SweepLoader(fileLoader_base):
        """Load two synthetic sweeps."""

        def loadFile(self) -> None:
            """Store a two-column recording."""
            points = 4
            time = np.arange(points) / 1000
            sweep_x = np.column_stack((time, time))
            sweep_y = np.column_stack((np.full(points, 1.0), np.full(points, 2.0)))
            self.setLoadedData(sweep_x, sweep_y)

    loader = _SweepLoader("unused.abf")
    loader.setSweep(0)

    np.testing.assert_array_equal(loader.get_sweep_y(1), np.full(4, 2.0))
    assert loader.currentSweep == 0
    np.testing.assert_array_equal(loader.sweepY, np.full(4, 1.0))


def test_new_b_analysis(test_data_dir: Path) -> None:
    """Construct a valid analysis through the public API.

    Args:
        test_data_dir: Stable test-only data directory.
    """
    analysis = sanpy.bAnalysis(str(test_data_dir / "19114001.abf"))

    assert not analysis.loadError
