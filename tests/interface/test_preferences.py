"""Tests for persistent SanPy interface preferences."""

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from sanpy.interface import preferences
from sanpy.sanpyPaths import SanPyPaths


def test_example_data_is_seeded_only_for_first_run() -> None:
    """Seed recent-folder preferences only when the user tree was created."""
    example_data_dir = Path("/documents/SanPy-User-Files/example-data")
    app = SimpleNamespace(
        sanpy_paths=SimpleNamespace(example_data_dir=example_data_dir)
    )
    options = preferences.__new__(preferences)
    options._sanpyApp = app
    options._version = 1.9

    options._first_time_running = True
    first_run_defaults = options.getDefaults()
    assert first_run_defaults["recentFolders"] == [str(example_data_dir)]
    assert first_run_defaults["mostRecentFolder"] == str(example_data_dir)

    options._first_time_running = False
    later_defaults = options.getDefaults()
    assert later_defaults["recentFolders"] == []
    assert later_defaults["mostRecentFolder"] == ""


def test_first_run_preferences_are_persisted(tmp_path: Path) -> None:
    """Write the seeded example-data path to the first-run preferences file.

    Args:
        tmp_path: Temporary Documents directory supplied by pytest.
    """
    sanpy_paths = SanPyPaths(documents_dir=tmp_path)
    sanpy_paths.preferences_dir.mkdir(parents=True)
    app = SimpleNamespace(sanpy_paths=sanpy_paths)

    preferences(app, first_time_running=True)

    preferences_file = sanpy_paths.preferences_dir / "sanpy_preferences.json"
    saved_preferences = json.loads(preferences_file.read_text(encoding="utf-8"))
    expected_path = str(sanpy_paths.example_data_dir)
    assert saved_preferences["recentFolders"] == [expected_path]
    assert saved_preferences["mostRecentFolder"] == expected_path


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
