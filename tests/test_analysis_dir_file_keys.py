"""Tests for stable recording identities owned by an analysis directory."""

from pathlib import Path
from unittest.mock import Mock

import pandas as pd
import pytest

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
