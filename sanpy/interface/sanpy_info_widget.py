"""SanPy description, contact, and build information widget.

Used by the About SanPy dialog and the detection view's SanPy Info panel.
"""

from qtpy import QtCore, QtGui, QtWidgets

from sanpy import build_info
from sanpy.sanpyPaths import SanPyPaths
from sanpy.sanpyLogger import getLoggerText, get_logger

logger = get_logger(__name__)


def _getSanPyInfoForClipboard() -> str:
    """Return complete build metadata followed by all retained log text."""
    logText = getLoggerText()

    return f'{build_info.get_build_info_json()}\n\n=== log file ===\n{logText}'


def _openSanPyUserFilesFolder(
    parent: QtWidgets.QWidget | None = None,
    sanpy_paths: SanPyPaths | None = None,
) -> bool:
    """Open the SanPy user-files folder in the platform file browser.

    Args:
        parent: Parent widget for an error dialog.
        sanpy_paths: Optional application path manager.

    Returns:
        True when Qt accepts the request to open the folder, otherwise False.
    """
    user_folder = (sanpy_paths or SanPyPaths()).user_files_dir
    if not user_folder.is_dir():
        message = f'SanPy-User-Files folder was not found:\n{user_folder}'
        logger.warning(message)
        QtWidgets.QMessageBox.warning(parent, 'SanPy-User-Files', message)
        return False

    folder_url = QtCore.QUrl.fromLocalFile(str(user_folder))
    if not QtGui.QDesktopServices.openUrl(folder_url):
        message = f'Could not open SanPy-User-Files folder:\n{user_folder}'
        logger.warning(message)
        QtWidgets.QMessageBox.warning(parent, 'SanPy-User-Files', message)
        return False
    return True


class SanPyInfoWidget(QtWidgets.QWidget):
    """Show the SanPy description, contact links, and build summary.

    The About dialog and the detection view's SanPy Info panel both use this
    widget. The dialog adds its own Close button.
    """

    def __init__(
        self,
        sanpy_paths: SanPyPaths | None = None,
        parent: QtWidgets.QWidget | None = None,
    ) -> None:
        """Build the shared SanPy information controls.

        Args:
            sanpy_paths: Application path manager used to open the user-files folder.
            parent: Optional owning Qt widget.
        """
        super().__init__(parent)
        self._sanpy_paths = sanpy_paths

        layout = QtWidgets.QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        description = QtWidgets.QLabel(
            'SanPy is designed for whole-cell current clamp analysis. '
            'We are always open to comments and suggestions on how to improve, '
            'extend, and fix SanPy. '
            'Reach out to Robert Cudmore with any ideas, questions, or bug fixes.'
        )
        description.setWordWrap(True)
        layout.addWidget(description)

        contact = QtWidgets.QLabel(
            'Contact: Robert Cudmore '
            '(<a href="mailto:robert.cudmore@gmail.com">'
            'robert.cudmore@gmail.com</a>)<br>'
            'Website: <a href="https://mapmanager.net/">'
            'https://mapmanager.net/</a><br>'
            'SanPy Documentation: '
            '<a href="https://cudmore.github.io/SanPy/">'
            'https://cudmore.github.io/SanPy/</a>'
        )
        contact.setTextFormat(QtCore.Qt.RichText)
        contact.setTextInteractionFlags(QtCore.Qt.TextBrowserInteraction)
        contact.setOpenExternalLinks(True)
        contact.setWordWrap(True)
        layout.addWidget(contact)

        divider = QtWidgets.QFrame()
        divider.setFrameShape(QtWidgets.QFrame.HLine)
        divider.setFrameShadow(QtWidgets.QFrame.Sunken)
        layout.addWidget(divider)

        for label, value in build_info.get_build_summary_rows():
            layout.addWidget(QtWidgets.QLabel(f'{label}: {value}'))

        button_layout = QtWidgets.QHBoxLayout()
        copy_button = QtWidgets.QPushButton('Copy SanPy Info')
        copy_button.clicked.connect(self._copy_sanpy_info)
        button_layout.addWidget(copy_button)

        user_files_button = QtWidgets.QPushButton('SanPy-User-Files')
        user_files_button.clicked.connect(self._open_user_files)
        button_layout.addWidget(user_files_button)
        layout.addLayout(button_layout)
        layout.addStretch(1)

    def _copy_sanpy_info(self, _checked: bool = False) -> None:
        """Copy build metadata and the retained log to the clipboard.

        Args:
            _checked: Unused checked state emitted by ``QPushButton.clicked``.
        """
        QtWidgets.QApplication.clipboard().setText(_getSanPyInfoForClipboard())

    def _open_user_files(self, _checked: bool = False) -> None:
        """Open the SanPy user-files folder in the platform file browser.

        Args:
            _checked: Unused checked state emitted by ``QPushButton.clicked``.
        """
        _openSanPyUserFilesFolder(self, self._sanpy_paths)
