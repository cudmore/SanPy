"""Tests for persistent SanPy interface preferences."""

import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

from sanpy.interface import preferences
from sanpy.interface.bTableView import DEFAULT_HIDDEN_FILE_COLUMNS
from sanpy.sanpy_paths import SanPyPaths


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
    assert saved_preferences["fileList"]["hiddenColumns"] == list(
        DEFAULT_HIDDEN_FILE_COLUMNS
    )


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


def _load_preferences(tmp_path: Path, file_list: dict) -> tuple[preferences, Path, dict]:
    """Load one preferences file without treating the launch as a first run.

    Args:
        tmp_path: Temporary Documents directory supplied by pytest.
        file_list: ``fileList`` object to store in the preferences JSON.

    Returns:
        Loaded preferences, the preferences path, and the JSON that was written.
    """
    sanpy_paths = SanPyPaths(documents_dir=tmp_path)
    sanpy_paths.preferences_dir.mkdir(parents=True)
    preferences_file = sanpy_paths.preferences_dir / "sanpy_preferences.json"
    stored = {"version": 1.9, "fileList": file_list}
    preferences_file.write_text(json.dumps(stored), encoding="utf-8")
    app = SimpleNamespace(sanpy_paths=sanpy_paths)
    return preferences(app, first_time_running=False), preferences_file, stored


def test_load_drops_unknown_hidden_file_columns(tmp_path: Path) -> None:
    """Ignore unknown, required, and non-string hidden columns while loading.

    Args:
        tmp_path: Temporary Documents directory supplied by pytest.
    """
    options, preferences_file, stored = _load_preferences(
        tmp_path,
        {
            "Folder Depth": 3,
            "hiddenColumns": ["species", "not_a_column", "File", 3, "age"],
        },
    )

    assert options.configDict["fileList"]["hiddenColumns"] == ["species", "age"]
    assert json.loads(preferences_file.read_text(encoding="utf-8")) == stored

    options.save()
    saved = json.loads(preferences_file.read_text(encoding="utf-8"))
    assert saved["fileList"]["hiddenColumns"] == ["species", "age"]


def test_load_uses_default_hidden_columns_when_the_key_is_missing(
    tmp_path: Path,
) -> None:
    """Use the default hidden columns when an existing file has no saved list.

    Args:
        tmp_path: Temporary Documents directory supplied by pytest.
    """
    options, preferences_file, stored = _load_preferences(
        tmp_path,
        {"Folder Depth": 2},
    )

    assert options.configDict["fileList"]["Folder Depth"] == 2
    assert options.configDict["fileList"]["hiddenColumns"] == list(
        DEFAULT_HIDDEN_FILE_COLUMNS
    )
    assert json.loads(preferences_file.read_text(encoding="utf-8")) == stored


def test_load_keeps_an_empty_hidden_column_list(tmp_path: Path) -> None:
    """Treat an empty hidden-column list as show every optional column.

    Args:
        tmp_path: Temporary Documents directory supplied by pytest.
    """
    options, _preferences_file, _stored = _load_preferences(
        tmp_path,
        {"hiddenColumns": []},
    )

    assert options.configDict["fileList"]["hiddenColumns"] == []


def test_load_replaces_a_non_list_hidden_column_value(tmp_path: Path) -> None:
    """Use the default hidden columns when the saved value is not a list.

    Args:
        tmp_path: Temporary Documents directory supplied by pytest.
    """
    options, _preferences_file, _stored = _load_preferences(
        tmp_path,
        {"hiddenColumns": "age"},
    )

    assert options.configDict["fileList"]["hiddenColumns"] == list(
        DEFAULT_HIDDEN_FILE_COLUMNS
    )
