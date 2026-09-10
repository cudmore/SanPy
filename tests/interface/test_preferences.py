"""Tests for persistent SanPy interface preferences."""

from unittest.mock import Mock

from sanpy.interface import preferences


def test_clear_recent_resets_history_and_saves_once() -> None:
    """Clear file, folder, and most-recent values in one persisted update."""
    options = preferences.__new__(preferences)
    options._configDict = {
        "recentFiles": ["recording.abf"],
        "recentFolders": ["recordings"],
        "mostRecentFile": "recording.abf",
        "mostRecentFolder": "recordings",
    }
    options.save = Mock()

    options.clearRecent()

    assert options.configDict["recentFiles"] == []
    assert options.configDict["recentFolders"] == []
    assert options.configDict["mostRecentFile"] == ""
    assert options.configDict["mostRecentFolder"] == ""
    options.save.assert_called_once_with()
