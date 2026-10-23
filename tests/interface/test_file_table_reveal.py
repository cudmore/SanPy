"""Tests for revealing a file-table recording in the platform file manager."""

import importlib
import shutil
import subprocess
from pathlib import Path

import pytest

import sanpy

# The package exports bTableView as the view class, which hides this module.
file_table_module = importlib.import_module("sanpy.interface.bTableView")

_RECORDING = Path(__file__).resolve().parents[1] / "data" / "2021_07_20_0010.abf"


def test_reveal_label_names_the_platform_file_manager(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Use the file-manager name for the current platform.

    Args:
        monkeypatch: Pytest fixture used to select a platform name.
    """
    monkeypatch.setattr(file_table_module.platform, "system", lambda: "Darwin")
    assert file_table_module.file_manager_reveal_label() == "Reveal in Finder"

    monkeypatch.setattr(file_table_module.platform, "system", lambda: "Windows")
    assert file_table_module.file_manager_reveal_label() == "Show in Explorer"

    monkeypatch.setattr(file_table_module.platform, "system", lambda: "Linux")
    assert file_table_module.file_manager_reveal_label() == "Show in File Manager"


def test_recording_path_follows_the_visible_row(tmp_path: Path) -> None:
    """Map a visible row through the table index to its recording path.

    Args:
        tmp_path: Temporary directory supplied by pytest.
    """
    shutil.copy2(_RECORDING, tmp_path / "a.abf")
    shutil.copy2(_RECORDING, tmp_path / "b.abf")
    table = sanpy.analysisDir(path=str(tmp_path), autoLoad=False, folderDepth=1)
    table._df = table._df.iloc[::-1]

    visible_file = table.loc[table.index[0], "File"]
    recording_path = file_table_module.recording_path_for_visual_row(table, 0)

    assert recording_path is not None
    assert Path(recording_path).name == visible_file
    assert file_table_module.recording_path_for_visual_row(table, -1) is None
    assert file_table_module.recording_path_for_visual_row(table, len(table.index)) is None

    table._df.at[table.index[0], "relPath"] = ""
    assert file_table_module.recording_path_for_visual_row(table, 0) is None


def test_reveal_missing_file_does_not_launch(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Return False without running a command when the file is absent.

    Args:
        monkeypatch: Pytest fixture used to reject an unexpected launch.
        tmp_path: Temporary directory supplied by pytest.
    """

    def fail_run(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        """Reject a command launched for a missing file.

        Args:
            _args: Unused command arguments.
            _kwargs: Unused command options.

        Returns:
            This function always raises.
        """
        raise AssertionError("subprocess should not run")

    monkeypatch.setattr(file_table_module.subprocess, "run", fail_run)

    assert file_table_module.reveal_in_file_manager(str(tmp_path / "missing.abf")) is False


def test_reveal_on_macos_selects_the_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Ask Finder to select the resolved recording.

    Args:
        monkeypatch: Pytest fixture used to isolate the platform command.
        tmp_path: Temporary directory supplied by pytest.
    """
    recording = tmp_path / "recording.abf"
    recording.write_bytes(b"")
    commands: list[list[str] | str] = []

    def fake_run(
        command: list[str] | str,
        **_kwargs: object,
    ) -> subprocess.CompletedProcess[list[str] | str]:
        """Record the Finder command.

        Args:
            command: Command passed to subprocess.
            _kwargs: Unused command options.

        Returns:
            A successful completed process.
        """
        commands.append(command)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(file_table_module.platform, "system", lambda: "Darwin")
    monkeypatch.setattr(file_table_module.subprocess, "run", fake_run)

    assert file_table_module.reveal_in_file_manager(str(recording)) is True
    assert commands == [["open", "-R", str(recording.resolve())]]


def test_reveal_on_windows_ignores_explorer_exit_code(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Treat Explorer's handoff exit code as success.

    Args:
        monkeypatch: Pytest fixture used to isolate the platform command.
        tmp_path: Temporary directory supplied by pytest.
    """
    recording = tmp_path / "recording.abf"
    recording.write_bytes(b"")
    commands: list[list[str] | str] = []

    def fake_run(
        command: list[str] | str,
        **_kwargs: object,
    ) -> subprocess.CompletedProcess[list[str] | str]:
        """Record the Explorer command and return its usual exit code.

        Args:
            command: Command passed to subprocess.
            _kwargs: Unused command options.

        Returns:
            A completed process with Explorer's successful exit code.
        """
        commands.append(command)
        return subprocess.CompletedProcess(command, 1)

    monkeypatch.setattr(file_table_module.platform, "system", lambda: "Windows")
    monkeypatch.setattr(file_table_module.subprocess, "run", fake_run)

    assert file_table_module.reveal_in_file_manager(str(recording)) is True
    resolved = recording.resolve()
    assert commands == [f'explorer.exe /select,"{resolved}"']


def test_reveal_on_linux_selects_then_falls_back(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Select the file with the file manager, then open the parent folder.

    Args:
        monkeypatch: Pytest fixture used to isolate the platform commands.
        tmp_path: Temporary directory supplied by pytest.
    """
    recording = tmp_path / "recording.abf"
    recording.write_bytes(b"")
    resolved = recording.resolve()
    commands: list[list[str] | str] = []

    def fake_run(
        command: list[str] | str,
        **_kwargs: object,
    ) -> subprocess.CompletedProcess[list[str] | str]:
        """Succeed for the file-manager call.

        Args:
            command: Command passed to subprocess.
            _kwargs: Unused command options.

        Returns:
            A successful completed process.
        """
        commands.append(command)
        return subprocess.CompletedProcess(command, 0)

    monkeypatch.setattr(file_table_module.platform, "system", lambda: "Linux")
    monkeypatch.setattr(file_table_module.subprocess, "run", fake_run)

    assert file_table_module.reveal_in_file_manager(str(recording)) is True
    assert commands[0][0] == "dbus-send"
    assert f'array:string:"{resolved.as_uri()}"' in commands[0]
    assert len(commands) == 1

    commands.clear()

    def fallback_run(
        command: list[str] | str,
        **_kwargs: object,
    ) -> subprocess.CompletedProcess[list[str] | str]:
        """Fail the file-manager call and accept the folder fallback.

        Args:
            command: Command passed to subprocess.
            _kwargs: Unused command options.

        Returns:
            A failed file-manager process or a successful folder process.
        """
        commands.append(command)
        exit_code = 1 if command[0] == "dbus-send" else 0
        return subprocess.CompletedProcess(command, exit_code)

    monkeypatch.setattr(file_table_module.subprocess, "run", fallback_run)

    assert file_table_module.reveal_in_file_manager(str(recording)) is True
    assert commands[1] == ["xdg-open", str(resolved.parent)]


def test_reveal_on_linux_returns_false_when_both_commands_fail(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Return False when the file manager and folder fallback both fail.

    Args:
        monkeypatch: Pytest fixture used to isolate the platform commands.
        tmp_path: Temporary directory supplied by pytest.
    """
    recording = tmp_path / "recording.abf"
    recording.write_bytes(b"")

    def fake_run(
        command: list[str] | str,
        **kwargs: object,
    ) -> subprocess.CompletedProcess[list[str] | str]:
        """Fail the file-manager call, then fail the folder fallback.

        Args:
            command: Command passed to subprocess.
            kwargs: Command options, including the timeout.

        Returns:
            A failed completed process, or raises when the call times out.
        """
        if command[0] == "dbus-send":
            raise subprocess.TimeoutExpired(command, kwargs["timeout"])
        return subprocess.CompletedProcess(command, 1)

    monkeypatch.setattr(file_table_module.platform, "system", lambda: "Linux")
    monkeypatch.setattr(file_table_module.subprocess, "run", fake_run)

    assert file_table_module.reveal_in_file_manager(str(recording)) is False


def test_reveal_unknown_platform_returns_false(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """Return False for a platform without a reveal command.

    Args:
        monkeypatch: Pytest fixture used to isolate the platform name.
        tmp_path: Temporary directory supplied by pytest.
    """
    recording = tmp_path / "recording.abf"
    recording.write_bytes(b"")

    def fail_run(*_args: object, **_kwargs: object) -> subprocess.CompletedProcess[str]:
        """Reject a command launched for an unsupported platform.

        Args:
            _args: Unused command arguments.
            _kwargs: Unused command options.

        Returns:
            This function always raises.
        """
        raise AssertionError("subprocess should not run")

    monkeypatch.setattr(file_table_module.platform, "system", lambda: "FreeBSD")
    monkeypatch.setattr(file_table_module.subprocess, "run", fail_run)

    assert file_table_module.reveal_in_file_manager(str(recording)) is False
