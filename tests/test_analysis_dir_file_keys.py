"""Tests for stable recording identities owned by an analysis directory."""

from pathlib import Path
from unittest.mock import Mock

import pandas as pd
import pytest

import sanpy
from sanpy.analysisDir import _normalized_file_key, analysisDir


def test_normalized_file_key_is_relative_and_portable(tmp_path: Path) -> None:
    """Normalize an in-root recording and reject a path outside the root.

    Args:
        tmp_path: Temporary directory supplied by pytest.
    """
    nested = tmp_path / "nested" / "cell.abf"
    nested.parent.mkdir()
    nested.touch()

    assert _normalized_file_key(str(tmp_path), str(nested)) == "nested/cell.abf"
    with pytest.raises(ValueError, match="outside analysis directory"):
        _normalized_file_key(str(tmp_path), str(tmp_path.parent / "other.abf"))


def test_analysis_directory_rejects_duplicate_file_keys(tmp_path: Path) -> None:
    """Fail instead of silently resolving an ambiguous recording key.

    Args:
        tmp_path: Temporary directory supplied by pytest.
    """
    directory = analysisDir.__new__(analysisDir)
    directory.path = str(tmp_path)
    directory._df = pd.DataFrame(
        {"File": ["cell.abf", "cell.abf"], "relPath": ["cell.abf", "cell.abf"]}
    )

    with pytest.raises(ValueError, match="Duplicate analysis file keys"):
        directory._normalize_file_keys()


def test_analysis_directory_recovers_unique_legacy_absolute_path(
    tmp_path: Path,
) -> None:
    """Replace a stale absolute path by matching one current recording name.

    Args:
        tmp_path: Temporary directory supplied by pytest.
    """
    recording = tmp_path / "nested" / "cell.abf"
    recording.parent.mkdir()
    recording.touch()
    directory = analysisDir.__new__(analysisDir)
    directory.path = str(tmp_path)
    directory._df = pd.DataFrame(
        {"File": ["cell.abf"], "relPath": ["C:\\old\\folder\\cell.abf"]}
    )
    directory.getFileList = Mock(return_value=[str(recording)])

    directory._normalize_file_keys()

    assert directory.get_file_key(0) == "nested/cell.abf"


def test_outside_file_key_is_unknown(tmp_path: Path) -> None:
    """Reject an out-of-root lookup without propagating a path error.

    Args:
        tmp_path: Temporary directory supplied by pytest.
    """
    directory = analysisDir.__new__(analysisDir)
    directory.path = str(tmp_path)
    directory._df = pd.DataFrame({"relPath": ["cell.abf"]})

    assert directory.get_row_for_file_key("../outside.abf") is None


def _two_recording_directory(tmp_path: Path, test_data_dir: Path) -> analysisDir:
    """Create an analysis directory containing two local recording copies.

    Args:
        tmp_path: Temporary destination directory.
        test_data_dir: Directory containing stable SanPy test recordings.

    Returns:
        Analysis directory containing two independently addressable recordings.
    """
    source = test_data_dir / "2021_07_20_0010.abf"
    for filename in ("first.abf", "second.abf"):
        (tmp_path / filename).write_bytes(source.read_bytes())
    return analysisDir(str(tmp_path), autoLoad=False, folderDepth=1)


def test_detect_file_keys_uses_full_duration_and_continues_after_bad_key(
    tmp_path: Path,
    test_data_dir: Path,
) -> None:
    """Detect valid keys fully while recording an unknown-key failure.

    Args:
        tmp_path: Temporary destination directory.
        test_data_dir: Directory containing stable SanPy test recordings.
    """
    directory = _two_recording_directory(tmp_path, test_data_dir)
    keys = tuple(directory.get_file_key(row) for row in directory.index)
    analyses = [directory.get_analysis_for_file_key(key) for key in keys]
    for analysis in analyses:
        assert analysis is not None
        analysis.spikeDetect = Mock()
    detection = sanpy.bDetection().getDetectionDict("Fast Neuron")

    detected, failed = directory.detect_file_keys(
        (keys[0], "missing.abf", keys[1]), detection
    )

    assert detected == 2
    assert failed == ("missing.abf",)
    for analysis in analyses:
        assert analysis is not None
        supplied = analysis.spikeDetect.call_args.args[0]
        assert supplied["startSeconds"] == 0
        assert supplied["stopSeconds"] == analysis.fileLoader.recordingDur


def test_detect_file_keys_cancels_before_next_recording(
    tmp_path: Path,
    test_data_dir: Path,
) -> None:
    """Stop batch detection before the second recording when requested.

    Args:
        tmp_path: Temporary destination directory.
        test_data_dir: Directory containing stable SanPy test recordings.
    """
    directory = _two_recording_directory(tmp_path, test_data_dir)
    keys = tuple(directory.get_file_key(row) for row in directory.index)
    analyses = [directory.get_analysis_for_file_key(key) for key in keys]
    for analysis in analyses:
        assert analysis is not None
        analysis.spikeDetect = Mock()
    detection = sanpy.bDetection().getDetectionDict("Fast Neuron")

    def continue_first_only(position: int, total: int, file_key: str) -> bool:
        """Allow only the first recording to begin.

        Args:
            position: One-based batch position.
            total: Total recording count.
            file_key: Recording key about to be processed.

        Returns:
            True only for the first batch position.
        """
        del total, file_key
        return position < 2

    detected, failed = directory.detect_file_keys(
        keys,
        detection,
        should_continue=continue_first_only,
    )

    assert detected == 1
    assert failed == ()
    assert analyses[0] is not None
    assert analyses[1] is not None
    analyses[0].spikeDetect.assert_called_once()
    analyses[1].spikeDetect.assert_not_called()


def test_set_metadata_for_file_keys_cancels_before_next_recording(
    tmp_path: Path,
    test_data_dir: Path,
) -> None:
    """Stop a metadata batch before the second recording when requested.

    Args:
        tmp_path: Temporary destination directory.
        test_data_dir: Directory containing stable SanPy test recordings.
    """
    directory = _two_recording_directory(tmp_path, test_data_dir)
    keys = tuple(directory.get_file_key(row) for row in directory.index)
    analyses = [directory.get_analysis_for_file_key(key) for key in keys]
    assert analyses[0] is not None
    assert analyses[1] is not None
    original = analyses[1].metaData.getMetaData("condition")

    def continue_first_only(position: int, total: int, file_key: str) -> bool:
        """Allow only the first recording to begin.

        Args:
            position: One-based batch position.
            total: Total recording count.
            file_key: Recording key about to be processed.

        Returns:
            True only for the first batch position.
        """
        del total, file_key
        return position < 2

    changed, failed = directory.set_metadata_for_file_keys(
        keys,
        "condition",
        "drug",
        should_continue=continue_first_only,
    )

    assert changed == 1
    assert failed == ()
    assert analyses[0].metaData.getMetaData("condition") == "drug"
    assert analyses[1].metaData.getMetaData("condition") == original


def test_set_metadata_for_file_keys_marks_changed_analyses_dirty(
    tmp_path: Path,
    test_data_dir: Path,
) -> None:
    """Change one field across files without saving either analysis.

    Args:
        tmp_path: Temporary destination directory.
        test_data_dir: Directory containing stable SanPy test recordings.
    """
    directory = _two_recording_directory(tmp_path, test_data_dir)
    keys = tuple(directory.get_file_key(row) for row in directory.index)

    changed, failed = directory.set_metadata_for_file_keys(
        keys, "condition", "drug"
    )

    assert changed == 2
    assert failed == ()
    for key in keys:
        analysis = directory.get_analysis_for_file_key(key)
        assert analysis is not None
        assert analysis.metaData.getMetaData("condition") == "drug"
        assert analysis.isDirty()

    changed_again, failed_again = directory.set_metadata_for_file_keys(
        keys, "condition", "drug"
    )
    assert changed_again == 0
    assert failed_again == ()
