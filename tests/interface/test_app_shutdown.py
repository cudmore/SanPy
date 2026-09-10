import gc
from types import SimpleNamespace
from typing import Any
from unittest.mock import Mock

import pytest
import pyqtgraph as pg
from qtpy import QtCore, QtGui, QtWidgets

import sanpy.interface.sanpy_window as sanpy_window_module
from sanpy.interface.openFirstWidget import openFirstWidget
from sanpy.interface.sanpy_app import SanPyApp
from sanpy.interface.sanpy_window import SanPyWindow
from sanpy.interface.plugins.setMetaData import SetMetaData


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


def test_window_registry_removes_window_only_after_qt_destroys_it(
    qtbot: Any,
) -> None:
    """Keep a strong window reference until Qt completes deferred deletion.

    Args:
        qtbot: Pytest-Qt widget lifecycle helper.
    """
    app = _FakeApp([])
    app._on_sanpy_window_destroyed = (
        SanPyApp._on_sanpy_window_destroyed.__get__(app)
    )
    window = QtWidgets.QMainWindow()
    window.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
    qtbot.addWidget(window)

    SanPyApp._register_sanpy_window(app, window)
    assert app._windowList == [window]

    window.show()
    window.close()
    assert app._windowList == [window]

    # Deliver Qt's deferred-delete event before Python can collect the wrapper.
    QtCore.QCoreApplication.sendPostedEvents(None, QtCore.QEvent.DeferredDelete)
    assert app._windowList == []


def test_sanpy_window_enables_qt_managed_deletion(
    monkeypatch: pytest.MonkeyPatch, qtbot: Any
) -> None:
    """Apply the analysis-window lifetime policy during construction.

    Args:
        monkeypatch: Pytest fixture used to isolate expensive window setup.
        qtbot: Pytest-Qt widget lifecycle helper.
    """
    geometry = {"x": 0, "y": 0, "width": 800, "height": 600}
    app = SimpleNamespace(newWindowGeometry=lambda: geometry, quitInProgress=True)
    monkeypatch.setattr(SanPyWindow, "_buildUI", lambda _window: None)
    monkeypatch.setattr(SanPyWindow, "_buildMenus", lambda _window: None)
    monkeypatch.setattr(SanPyWindow, "_load", lambda _window: None)
    monkeypatch.setattr(SanPyWindow, "slot_updateStatus", lambda _window, _text: None)

    window = SanPyWindow(app, None)
    qtbot.addWidget(window)

    assert window.testAttribute(QtCore.Qt.WA_DeleteOnClose)


def test_qt_managed_plot_windows_survive_repeated_garbage_collection(
    qtbot: Any,
) -> None:
    """Destroy plot windows through Qt before forcing Python collection.

    Args:
        qtbot: Pytest-Qt helper that provides the running Qt application.
    """
    app = _FakeApp([])
    app._on_sanpy_window_destroyed = (
        SanPyApp._on_sanpy_window_destroyed.__get__(app)
    )

    for _index in range(10):
        window = QtWidgets.QMainWindow()
        window.setAttribute(QtCore.Qt.WA_DeleteOnClose, True)
        plot_widget = pg.PlotWidget(window)
        plot_widget.plot([0, 1, 2], [0, 1, 0])
        window.setCentralWidget(plot_widget)
        SanPyApp._register_sanpy_window(app, window)

        window.show()
        window.close()
        # Complete C++ graphics destruction before collecting Python cycles.
        QtCore.QCoreApplication.sendPostedEvents(None, QtCore.QEvent.DeferredDelete)
        gc.collect()

    assert app._windowList == []


def test_file_menu_exposes_folder_save_action(qtbot):
    """The analysis-window save action appears in File and invokes its slot."""
    main_window = QtWidgets.QMainWindow()
    qtbot.addWidget(main_window)

    class _MenuApp(QtCore.QObject):
        """Minimal QObject owner for exercising the shared menu builder."""

        _buildMenus = SanPyApp._buildMenus
        _close_active_menu_window = SanPyApp._close_active_menu_window

        def __init__(self) -> None:
            """Provide the callbacks consumed while building menus."""
            super().__init__()
            self.configDict = SimpleNamespace(save=lambda: None)
            self.loadFile = lambda: None
            self.loadFolder = lambda: None
            self._refreshOpenRecent = lambda: None
            self.requestQuit = lambda: None
            self._onHelpMenuAction = lambda name: None
            self._onAboutMenuAction = lambda: None
            self._onPreferencesMenuAction = lambda: None

    app = _MenuApp()

    save_calls = []
    save_action = QtWidgets.QAction("Save Folder Analysis", main_window)
    save_action.setShortcut(QtGui.QKeySequence.Save)
    save_action.triggered.connect(lambda: save_calls.append(True))

    app._buildMenus(
        main_window.menuBar(),
        saveFolderAnalysisAction=save_action,
    )

    file_menu = main_window.menuBar().actions()[0].menu()
    assert save_action in file_menu.actions()
    assert save_action.shortcut() == QtGui.QKeySequence(QtGui.QKeySequence.Save)

    save_action.trigger()
    assert save_calls == [True]


def test_file_menu_exposes_platform_close_window_shortcut(qtbot: Any) -> None:
    """Close only the owning window through Qt's platform-standard shortcut.

    Args:
        qtbot: Pytest-Qt widget lifecycle helper.
    """
    main_window = QtWidgets.QMainWindow()
    qtbot.addWidget(main_window)

    class _MenuApp(QtCore.QObject):
        """Minimal application callbacks required by the shared menu builder."""

        _buildMenus = SanPyApp._buildMenus
        _close_active_menu_window = SanPyApp._close_active_menu_window

        def __init__(self) -> None:
            """Initialize callback state used by the menu test."""
            super().__init__()
            self.configDict = SimpleNamespace(save=lambda: None)
            self.loadFile = lambda: None
            self.loadFolder = lambda: None
            self._refreshOpenRecent = lambda: None
            self.requestQuit = lambda: None
            self._onHelpMenuAction = lambda _name: None
            self._onAboutMenuAction = lambda: None
            self._onPreferencesMenuAction = lambda: None

    app = _MenuApp()
    app._buildMenus(main_window.menuBar())
    file_menu = main_window.menuBar().actions()[0].menu()
    close_action = next(
        action for action in file_menu.actions() if action.text() == "Close Window"
    )

    assert close_action.shortcut() == QtGui.QKeySequence(QtGui.QKeySequence.Close)
    assert close_action.shortcutContext() == QtCore.Qt.WindowShortcut

    main_window.show()
    main_window.activateWindow()
    qtbot.waitUntil(lambda: QtWidgets.QApplication.activeWindow() is main_window)
    close_action.trigger()
    assert main_window.isVisible() is False


def test_parent_close_action_ignores_frontmost_plugin(qtbot: Any) -> None:
    """Keep the parent open when its child plugin window is frontmost.

    Args:
        qtbot: Pytest-Qt widget lifecycle helper.
    """
    parent_window = QtWidgets.QMainWindow()
    plugin_window = QtWidgets.QWidget(parent_window, QtCore.Qt.Window)
    qtbot.addWidget(parent_window)
    qtbot.addWidget(plugin_window)

    class _MenuApp(QtCore.QObject):
        """Minimal shared-menu owner for active-window testing."""

        _buildMenus = SanPyApp._buildMenus
        _close_active_menu_window = SanPyApp._close_active_menu_window

        def __init__(self) -> None:
            """Initialize callbacks required by the shared menu builder."""
            super().__init__()
            self.configDict = SimpleNamespace(save=lambda: None)
            self.loadFile = lambda: None
            self.loadFolder = lambda: None
            self._refreshOpenRecent = lambda: None
            self.requestQuit = lambda: None
            self._onHelpMenuAction = lambda _name: None
            self._onAboutMenuAction = lambda: None
            self._onPreferencesMenuAction = lambda: None

    app = _MenuApp()
    app._buildMenus(parent_window.menuBar())
    file_menu = parent_window.menuBar().actions()[0].menu()
    close_action = next(
        action for action in file_menu.actions() if action.text() == "Close Window"
    )

    parent_window.show()
    plugin_window.show()
    plugin_window.activateWindow()
    qtbot.waitUntil(lambda: QtWidgets.QApplication.activeWindow() is plugin_window)

    close_action.trigger()

    assert parent_window.isVisible() is True
    assert plugin_window.isVisible() is True


def test_view_menu_omits_metadata_panel_action(qtbot: Any) -> None:
    """Hide the metadata panel action while preserving its plugin.

    Args:
        qtbot: Pytest-Qt widget lifecycle helper.
    """
    window = QtWidgets.QMainWindow()
    qtbot.addWidget(window)
    window.viewMenu = QtWidgets.QMenu(window)
    window.configDict = {
        "filePanels": {"File Panel": True},
        "detectionPanels": {
            "Detection Panel": True,
            "Detection": True,
            "Display": True,
            "Set Spikes": False,
            "Set Meta Data": False,
            "Plot Options": False,
        },
        "rawDataPanels": {
            "Full Recording": False,
            "Derivative": True,
            "DAC": False,
        },
    }
    window._viewMenuAction = lambda *args: None
    window.pluginDock1 = QtWidgets.QDockWidget(window)
    window.useDarkStyle = False

    SanPyWindow._refreshViewMenu(window)

    action_names = [action.text() for action in window.viewMenu.actions()]
    assert "Set Meta Data" not in action_names
    assert "Set Spikes" in action_names
    assert "Plot Options" in action_names
    assert SetMetaData.myHumanName == "Set Meta Data"
    assert SetMetaData.showInMenu


def test_failed_file_selection_is_not_broadcast() -> None:
    """Report a failed recording load without emitting a file-switch event."""
    statuses = []
    emitted = []
    window = SimpleNamespace(
        startSec=None,
        stopSec=None,
        myAnalysisDir=SimpleNamespace(getAnalysis=lambda row: None),
        signalSwitchFile=SimpleNamespace(
            emit=lambda *args: emitted.append(args)
        ),
        slot_updateStatus=lambda message: statuses.append(message),
    )
    row = {
        "File": "invalid.sanpy",
        "Start(s)": float("nan"),
        "Stop(s)": float("nan"),
    }

    SanPyWindow.slot_fileTableClicked(window, 4, row, False)

    assert emitted == []
    assert statuses[-1] == (
        'Unable to load "invalid.sanpy"; see the SanPy log for details.'
    )


def test_only_standalone_plugins_are_registered() -> None:
    """Keep embedded plugin tabs out of the standalone Windows menu set."""
    widget = SimpleNamespace(
        show=lambda: None,
        hide=lambda: None,
        setVisible=lambda visible: None,
    )
    plugin = Mock()
    plugin.getInitError.return_value = False
    plugin.getWidget.return_value = widget
    constructor = Mock(return_value=plugin)
    constructor.myHumanName = "Example"
    plugin_info = {
        "Example": {
            "constructor": constructor,
        }
    }
    app = SimpleNamespace(
        getPlugins=lambda: SimpleNamespace(pluginDict=plugin_info)
    )
    window = SimpleNamespace(
        startSec=None,
        stopSec=None,
        _openPluginSet=set(),
        getSanPyApp=lambda: app,
    )

    SanPyWindow.runPlugin(window, "Example", None, show=False)
    assert window._openPluginSet == set()

    SanPyWindow.runPlugin(window, "Example", None, show=True)
    assert window._openPluginSet == {plugin}


def test_closing_embedded_tab_closes_and_deletes_plugin() -> None:
    """Closing a tab must end the embedded plugin widget lifecycle."""
    calls = []
    plugin = SimpleNamespace(
        close=lambda: calls.append("close"),
        deleteLater=lambda: calls.append("delete"),
    )
    tabs = SimpleNamespace(
        widget=lambda index: plugin,
        removeTab=lambda index: calls.append(("remove", index)),
    )

    SanPyWindow.slot_closeTab(SimpleNamespace(), 2, tabs)

    assert calls == [("remove", 2), "close", "delete"]


def test_plugin_close_is_safe_when_plugin_was_not_registered() -> None:
    """Disconnect embedded plugins without requiring Windows-menu ownership."""
    calls = []
    plugin = Mock()
    plugin.getHumanName.return_value = "Example"
    plugin._disconnectSignalSlot.side_effect = lambda: calls.append("disconnect")
    window = SimpleNamespace(_openPluginSet=set())

    SanPyWindow.slot_closeWindow(window, plugin)

    assert calls == ["disconnect"]
    assert window._openPluginSet == set()


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


def test_final_analysis_close_closes_plugins_and_restores_launcher() -> None:
    """Close plugins and restore the launcher without early deregistration."""
    calls = []
    app = SimpleNamespace(
        quitInProgress=False,
        isLastAnalysisWindow=lambda window: True,
        showOpenFirstWidget=lambda: calls.append("show launcher"),
    )
    window = SimpleNamespace(
        getSanPyApp=lambda: app,
        prepareToClose=lambda: True,
        _closePluginWindows=lambda: calls.append("close plugins"),
    )
    event = _FakeCloseEvent()

    SanPyWindow.closeEvent(window, event)

    assert calls == ["close plugins", "show launcher"]
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


def test_application_quit_does_not_restore_launcher_or_prompt_again() -> None:
    """Accept app-driven closure without restoring or prompting again."""
    calls = []
    app = SimpleNamespace(quitInProgress=True)
    window = SimpleNamespace(
        getSanPyApp=lambda: app,
        prepareToClose=lambda: calls.append("prompt again"),
        _closePluginWindows=lambda: calls.append("close plugins"),
    )
    event = _FakeCloseEvent()

    SanPyWindow.closeEvent(window, event)

    assert calls == ["close plugins"]
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
