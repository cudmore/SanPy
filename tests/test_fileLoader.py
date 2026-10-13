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


def test_file_loader_abf_reads_metadata_without_raw_arrays(
    test_data_dir: Path,
) -> None:
    """Read ABF table metadata without materializing recording arrays.

    Args:
        test_data_dir: Stable test-only data directory.
    """
    loader = fileLoader_abf(
        str(test_data_dir / "2021_07_20_0010.abf"),
        loadData=False,
    )

    assert not loader.getLoadError()
    assert loader.recordingDur == 0.16
    assert loader.numChannels == 2
    assert loader.numSweeps == 18
    assert loader.numEpochs == 5
    assert loader.recordingFrequency == 10.0
    assert loader.recordingMode.value == "I-Clamp"
    assert loader._sweepX is None
    assert loader._sweepY is None
    assert loader._sweepC is None


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
    np.testing.assert_array_equal(loader.get_sweep_c(1), np.zeros(4))


def test_get_sweep_c_ignores_current_sweep() -> None:
    """Return an explicit command sweep while the property follows currentSweep."""

    class _CommandSweepLoader(fileLoader_base):
        """Load two synthetic recording and command sweeps."""

        def loadFile(self) -> None:
            """Store two-column recording and command arrays."""
            points = 4
            time = np.arange(points) / 1000
            sweep_x = np.column_stack((time, time))
            sweep_y = np.column_stack((np.full(points, 1.0), np.full(points, 2.0)))
            sweep_c = np.column_stack(
                (np.full(points, 10.0), np.full(points, 20.0))
            )
            self.setLoadedData(sweep_x, sweep_y, sweepC=sweep_c)

    loader = _CommandSweepLoader("unused.abf")
    loader.setSweep(0)

    np.testing.assert_array_equal(loader.get_sweep_c(1), np.full(4, 20.0))
    assert loader.currentSweep == 0
    np.testing.assert_array_equal(loader.sweepC, np.full(4, 10.0))


def test_new_b_analysis(test_data_dir: Path) -> None:
    """Construct a valid analysis through the public API.

    Args:
        test_data_dir: Stable test-only data directory.
    """
    analysis = sanpy.bAnalysis(str(test_data_dir / "19114001.abf"))

    assert not analysis.loadError


def test_b_analysis_retains_header_only_loader(test_data_dir: Path) -> None:
    """Retain file metadata while deferring raw ABF arrays.

    Args:
        test_data_dir: Stable test-only data directory.
    """
    analysis = sanpy.bAnalysis(
        str(test_data_dir / "19114001.abf"),
        loadData=False,
    )

    assert not analysis.loadError
    assert analysis.fileLoader is not None
    assert analysis.fileLoader.recordingDur == 60.0
    assert analysis.fileLoader._sweepY is None


def test_b_analysis_header_only_keeps_sweep_conditions(test_data_dir: Path) -> None:
    """Accept saved sweep conditions when raw arrays are not loaded.

    Args:
        test_data_dir: Stable test-only data directory.
    """
    analysis = sanpy.bAnalysis(
        str(test_data_dir / "19114001.abf"),
        loadData=False,
    )
    sweep = analysis.fileLoader.sweepList[0]

    assert analysis.getSweepCondition(sweep) == ""
    analysis.setSweepCondition(sweep, "drug")
    assert analysis.getSweepCondition(sweep) == "drug"
