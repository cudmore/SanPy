from types import SimpleNamespace

import pytest
from qtpy import QtWidgets

import sanpy.interface.sanpy_window as sanpy_window_module
from sanpy.interface.openFirstWidget import openFirstWidget
from sanpy.interface.sanpy_app import SanPyApp
from sanpy.interface.sanpy_window import SanPyWindow


class _FakeCloseEvent:
    def __init__(self):
        self.accepted = False
        self.ignored = False

    def accept(self):
        self.accepted = True

    def ignore(self):
        self.ignored = True


class _FakeAnalysisWindow:
    def __init__(self, may_close=True):
        self.may_close = may_close
        self.prepare_calls = 0
        self.close_calls = 0

    def prepareToClose(self):
        self.prepare_calls += 1
        return self.may_close

    def close(self):
        self.close_calls += 1


class _FakeLauncher:
    def __init__(self):
        self.close_calls = 0

    def close(self):
        self.close_calls += 1


class _FakeApp:
    requestQuit = SanPyApp.requestQuit

    def __init__(self, windows):
        self._windowList = windows
        self._openFirstWidget = _FakeLauncher()
        self._quitInProgress = False
        self.quit_calls = 0

    def quit(self):
        self.quit_calls += 1


def test_request_quit_preflights_before_closing_any_windows():
    first = _FakeAnalysisWindow(may_close=True)
    second = _FakeAnalysisWindow(may_close=False)
    app = _FakeApp([first, second])

    assert app.requestQuit() is False
    assert first.prepare_calls == 1
    assert second.prepare_calls == 1
    assert first.close_calls == 0
    assert second.close_calls == 0
    assert app._openFirstWidget.close_calls == 0
    assert app.quit_calls == 0
    assert app._quitInProgress is False


def test_request_quit_closes_everything_after_all_windows_approve():
    first = _FakeAnalysisWindow()
    second = _FakeAnalysisWindow()
    app = _FakeApp([first, second])

    assert app.requestQuit() is True
    assert first.close_calls == 1
    assert second.close_calls == 1
    assert app._openFirstWidget.close_calls == 1
    assert app.quit_calls == 1
    assert app._quitInProgress is True


class _FakeAnalysisDir:
    def __init__(self, table_dirty=True, analysis_dirty=False):
        self.isDirty = table_dirty
        self._analysis_dirty = analysis_dirty

    def hasDirty(self):
        return self._analysis_dirty


class _PrepareWindow:
    _hasUnsavedAnalysis = SanPyWindow._hasUnsavedAnalysis
    prepareToClose = SanPyWindow.prepareToClose

    def __init__(self, save_error=None):
        self.path = "/data/example.abf"
        self.myAnalysisDir = _FakeAnalysisDir()
        self.save_calls = 0
        self.save_error = save_error

    def saveFilesTable(self):
        self.save_calls += 1
        if self.save_error is not None:
            raise self.save_error


@pytest.mark.parametrize(
    ("response", "expected", "save_calls"),
    [
        (QtWidgets.QMessageBox.No, True, 0),
        (QtWidgets.QMessageBox.Cancel, False, 0),
        (QtWidgets.QMessageBox.Yes, True, 1),
    ],
)
def test_prepare_to_close_respects_user_choice(
    monkeypatch, response, expected, save_calls
):
    monkeypatch.setattr(
        sanpy_window_module.sanpy.interface.bDialog,
        "yesNoCancelDialog",
        lambda message: response,
    )
    window = _PrepareWindow()

    assert window.prepareToClose() is expected
    assert window.save_calls == save_calls


def test_prepare_to_close_handles_only_expected_save_failures(monkeypatch):
    monkeypatch.setattr(
        sanpy_window_module.sanpy.interface.bDialog,
        "yesNoCancelDialog",
        lambda message: QtWidgets.QMessageBox.Yes,
    )
    critical_calls = []
    monkeypatch.setattr(
        sanpy_window_module.QtWidgets.QMessageBox,
        "critical",
        lambda *args: critical_calls.append(args),
    )
    window = _PrepareWindow(save_error=OSError("disk full"))

    assert window.prepareToClose() is False
    assert len(critical_calls) == 1


def test_prepare_to_close_does_not_hide_unexpected_exceptions(monkeypatch):
    monkeypatch.setattr(
        sanpy_window_module.sanpy.interface.bDialog,
        "yesNoCancelDialog",
        lambda message: QtWidgets.QMessageBox.Yes,
    )
    window = _PrepareWindow(save_error=RuntimeError("programming defect"))

    with pytest.raises(RuntimeError, match="programming defect"):
        window.prepareToClose()


def test_close_plugin_windows_uses_snapshot():
    closed = []
    owner = SimpleNamespace(_openPluginSet=set())

    class Plugin:
        def getWidget(self):
            return self

        def close(self):
            closed.append(self)
            owner._openPluginSet.remove(self)

    owner._openPluginSet.update([Plugin(), Plugin()])

    SanPyWindow._closePluginWindows(owner)

    assert len(closed) == 2
    assert owner._openPluginSet == set()


def test_final_analysis_close_closes_plugins_and_restores_launcher():
    calls = []
    app = SimpleNamespace(
        quitInProgress=False,
        isLastAnalysisWindow=lambda window: True,
        showOpenFirstWidget=lambda: calls.append("show launcher"),
        closeSanPyWindow=lambda window: calls.append("unregister analysis"),
    )
    window = SimpleNamespace(
        getSanPyApp=lambda: app,
        prepareToClose=lambda: True,
        _closePluginWindows=lambda: calls.append("close plugins"),
    )
    event = _FakeCloseEvent()

    SanPyWindow.closeEvent(window, event)

    assert calls == ["close plugins", "show launcher", "unregister analysis"]
    assert event.accepted is True


def test_cancelled_analysis_close_keeps_plugins_and_window_open():
    calls = []
    app = SimpleNamespace(quitInProgress=False)
    window = SimpleNamespace(
        getSanPyApp=lambda: app,
        prepareToClose=lambda: False,
        _closePluginWindows=lambda: calls.append("close plugins"),
    )
    event = _FakeCloseEvent()

    SanPyWindow.closeEvent(window, event)

    assert calls == []
    assert event.ignored is True
    assert event.accepted is False


def test_application_quit_does_not_restore_launcher_or_prompt_again():
    calls = []
    app = SimpleNamespace(
        quitInProgress=True,
        closeSanPyWindow=lambda window: calls.append("unregister analysis"),
    )
    window = SimpleNamespace(
        getSanPyApp=lambda: app,
        prepareToClose=lambda: calls.append("prompt again"),
        _closePluginWindows=lambda: calls.append("close plugins"),
    )
    event = _FakeCloseEvent()

    SanPyWindow.closeEvent(window, event)

    assert calls == ["close plugins", "unregister analysis"]
    assert event.accepted is True


def test_launcher_hides_instead_of_quitting_while_analysis_is_open():
    app = SimpleNamespace(
        hasAnalysisWindows=lambda: True,
        quitInProgress=False,
    )
    launcher = SimpleNamespace(
        getSanPyApp=lambda: app,
        hide=lambda: setattr(launcher, "hidden", True),
        hidden=False,
    )
    event = _FakeCloseEvent()

    openFirstWidget.closeEvent(launcher, event)

    assert launcher.hidden is True
    assert event.ignored is True
    assert event.accepted is False


def test_launcher_close_is_accepted_when_no_analysis_is_open():
    app = SimpleNamespace(
        hasAnalysisWindows=lambda: False,
        quitInProgress=False,
    )
    launcher = SimpleNamespace(getSanPyApp=lambda: app)
    event = _FakeCloseEvent()

    openFirstWidget.closeEvent(launcher, event)

    assert event.accepted is True
    assert event.ignored is False
