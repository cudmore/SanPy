"""
Progress Widget Module for SanPy

This module provides progress tracking widgets for long-running tasks in the SanPy GUI.
It supports both embedded progress bars and modal progress dialogs.

Usage:
    # For embedded progress in existing window
    progress_widget = ProgressWidget(parent=main_window)
    progress_widget.start_task("Processing files...", total_steps=100)
    
    # For modal progress dialog
    progress_dialog = ProgressDialog("Processing files...", total_steps=100, parent=main_window)
    progress_dialog.show()
    
    # Update progress from backend
    progress_widget.update_progress(current_step=50, message="Processing file 50/100")
    
    # Complete task
    progress_widget.complete_task("Processing complete!")
"""

from typing import Optional, Callable, Any
from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QProgressBar, QLabel, 
    QPushButton, QDialog, QDialogButtonBox, QFrame
)
from PyQt5.QtCore import QTimer, pyqtSignal, QThread, QObject, Qt
from PyQt5.QtGui import QFont
import queue
import threading
import time

from sanpy.sanpyLogger import get_logger
logger = get_logger(__name__)


class ProgressSignals(QObject):
    """Signals for progress communication between backend and frontend."""
    progress_updated = pyqtSignal(int, int, str)  # current, total, message
    task_completed = pyqtSignal(str)  # completion message
    task_cancelled = pyqtSignal()
    task_error = pyqtSignal(str)  # error message


class ProgressManager:
    """
    Singleton progress manager for coordinating progress updates across the application.
    
    This class provides a centralized way to manage progress updates from backend
    tasks to frontend widgets without tight coupling.
    """
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        self.signals = ProgressSignals()
        self.active_widgets = []
        self._initialized = True
        
    def register_widget(self, widget):
        """Register a progress widget to receive updates."""
        if widget not in self.active_widgets:
            self.active_widgets.append(widget)
            # Connect signals
            self.signals.progress_updated.connect(widget.update_progress)
            self.signals.task_completed.connect(widget.complete_task)
            self.signals.task_cancelled.connect(widget.cancel_task)
            self.signals.task_error.connect(widget.show_error)
            
    def unregister_widget(self, widget):
        """Unregister a progress widget."""
        if widget in self.active_widgets:
            self.active_widgets.remove(widget)
            # Disconnect signals
            try:
                self.signals.progress_updated.disconnect(widget.update_progress)
                self.signals.task_completed.disconnect(widget.complete_task)
                self.signals.task_cancelled.disconnect(widget.cancel_task)
                self.signals.task_error.disconnect(widget.show_error)
            except:
                pass  # Signals might already be disconnected
                
    def update_progress(self, current: int, total: int, message: str = ""):
        """Update progress for all registered widgets."""
        self.signals.progress_updated.emit(current, total, message)
        
    def complete_task(self, message: str = "Task completed"):
        """Complete task for all registered widgets."""
        self.signals.task_completed.emit(message)
        
    def cancel_task(self):
        """Cancel task for all registered widgets."""
        self.signals.task_cancelled.emit()
        
    def show_error(self, error_message: str):
        """Show error for all registered widgets."""
        self.signals.task_error.emit(error_message)


class ProgressWidget(QFrame):
    """
    Embedded progress widget for showing progress in existing windows.
    
    This widget can be embedded in any existing PyQt window to show
    progress of long-running tasks without blocking the UI.
    """
    
    def __init__(self, parent=None, show_cancel_button: bool = True):
        super().__init__(parent)
        self.show_cancel_button = show_cancel_button
        self.is_active = False
        self.cancelled = False
        
        # Get progress manager
        self.progress_manager = ProgressManager()
        
        self.setup_ui()
        self.hide()  # Hidden by default
        
    def setup_ui(self):
        """Setup the user interface."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)
        
        # Title label
        self.title_label = QLabel("Processing...")
        self.title_label.setFont(QFont("Arial", 10, QFont.Bold))
        layout.addWidget(self.title_label)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)
        
        # Status label
        self.status_label = QLabel("Ready")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)
        
        # Button layout
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        # Cancel button
        if self.show_cancel_button:
            self.cancel_button = QPushButton("Cancel")
            self.cancel_button.clicked.connect(self.cancel_task)
            button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
        
        # Style
        self.setFrameStyle(QFrame.StyledPanel)
        self.setStyleSheet("""
            QFrame {
                background-color: #f0f0f0;
                border: 1px solid #cccccc;
                border-radius: 5px;
            }
            QProgressBar {
                border: 1px solid #cccccc;
                border-radius: 3px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 2px;
            }
        """)
        
    def start_task(self, title: str, total_steps: int, initial_message: str = "Starting..."):
        """Start a new task."""
        self.is_active = True
        self.cancelled = False
        self.total_steps = total_steps
        self.current_step = 0
        
        self.title_label.setText(title)
        self.progress_bar.setMaximum(total_steps)
        self.progress_bar.setValue(0)
        self.status_label.setText(initial_message)
        
        self.show()
        self.progress_manager.register_widget(self)
        
    def update_progress(self, current: int, total: int, message: str = ""):
        """Update progress display."""
        if not self.is_active:
            return
            
        self.current_step = current
        self.progress_bar.setValue(current)
        
        if message:
            self.status_label.setText(message)
        else:
            percentage = int((current / total) * 100) if total > 0 else 0
            self.status_label.setText(f"Progress: {current}/{total} ({percentage}%)")
            
    def complete_task(self, message: str = "Task completed"):
        """Complete the current task."""
        if not self.is_active:
            return
            
        self.is_active = False
        self.progress_bar.setValue(self.total_steps)
        self.status_label.setText(message)
        
        # Auto-hide after a delay
        QTimer.singleShot(2000, self.hide)
        self.progress_manager.unregister_widget(self)
        
    def cancel_task(self):
        """Cancel the current task."""
        if not self.is_active:
            return
            
        self.cancelled = True
        self.status_label.setText("Cancelling...")
        self.progress_manager.cancel_task()
        
    def show_error(self, error_message: str):
        """Show an error message."""
        self.is_active = False
        self.status_label.setText(f"Error: {error_message}")
        self.status_label.setStyleSheet("color: red;")
        
        # Auto-hide after a delay
        QTimer.singleShot(3000, self.hide)
        self.progress_manager.unregister_widget(self)


class ProgressDialog(QDialog):
    """
    Modal progress dialog for critical operations.
    
    This dialog blocks the parent window and shows progress
    for operations that must complete before the user continues.
    """
    
    def __init__(self, title: str, total_steps: int, parent=None, 
                 show_cancel_button: bool = True, auto_close: bool = True):
        super().__init__(parent)
        self.total_steps = total_steps
        self.current_step = 0
        self.show_cancel_button = show_cancel_button
        self.auto_close = auto_close
        self.cancelled = False
        
        # Get progress manager
        self.progress_manager = ProgressManager()
        
        self.setup_ui(title)
        
    def setup_ui(self, title: str):
        """Setup the user interface."""
        self.setWindowTitle(title)
        self.setModal(True)
        self.setFixedSize(400, 150)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(self.total_steps)
        self.progress_bar.setValue(0)
        layout.addWidget(self.progress_bar)
        
        # Status label
        self.status_label = QLabel("Starting...")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)
        
        # Button box
        self.button_box = QDialogButtonBox()
        if self.show_cancel_button:
            self.cancel_button = self.button_box.addButton("Cancel", QDialogButtonBox.RejectRole)
            self.cancel_button.clicked.connect(self.cancel_task)
        else:
            # Add a close button that's initially disabled
            self.close_button = self.button_box.addButton("Close", QDialogButtonBox.AcceptRole)
            self.close_button.setEnabled(False)
            self.close_button.clicked.connect(self.accept)
            
        layout.addWidget(self.button_box)
        
        # Connect signals
        self.progress_manager.register_widget(self)
        
    def update_progress(self, current: int, total: int, message: str = ""):
        """Update progress display."""
        self.current_step = current
        self.progress_bar.setValue(current)
        
        if message:
            self.status_label.setText(message)
        else:
            percentage = int((current / total) * 100) if total > 0 else 0
            self.status_label.setText(f"Progress: {current}/{total} ({percentage}%)")
            
    def complete_task(self, message: str = "Task completed"):
        """Complete the current task."""
        self.progress_bar.setValue(self.total_steps)
        self.status_label.setText(message)
        
        if self.auto_close:
            QTimer.singleShot(1000, self.accept)
        else:
            # Enable close button if it exists
            if hasattr(self, 'close_button'):
                self.close_button.setEnabled(True)
                
        self.progress_manager.unregister_widget(self)
        
    def cancel_task(self):
        """Cancel the current task."""
        self.cancelled = True
        self.status_label.setText("Cancelling...")
        self.progress_manager.cancel_task()
        self.reject()
        
    def show_error(self, error_message: str):
        """Show an error message."""
        self.status_label.setText(f"Error: {error_message}")
        self.status_label.setStyleSheet("color: red;")
        
        if self.auto_close:
            QTimer.singleShot(2000, self.reject)
        else:
            # Enable close button if it exists
            if hasattr(self, 'close_button'):
                self.close_button.setEnabled(True)
                
        self.progress_manager.unregister_widget(self)


# Backend integration helpers
class ProgressCallback:
    """
    Callback class for backend tasks to report progress.
    
    This class provides a simple interface for backend code to
    report progress without needing to know about the UI.
    """
    
    def __init__(self, total_steps: int, title: str = "Processing..."):
        self.total_steps = total_steps
        self.current_step = 0
        self.title = title
        self.progress_manager = ProgressManager()
        
    def update(self, current: int, message: str = ""):
        """Update progress."""
        self.current_step = current
        self.progress_manager.update_progress(current, self.total_steps, message)
        try:
            from PyQt5.QtWidgets import QApplication
            QApplication.processEvents()
        except ImportError:
            pass
        
    def increment(self, message: str = ""):
        """Increment progress by 1."""
        self.current_step += 1
        self.progress_manager.update_progress(self.current_step, self.total_steps, message)
        
    def complete(self, message: str = "Task completed"):
        """Complete the task."""
        self.progress_manager.complete_task(message)
        
    def error(self, error_message: str):
        """Report an error."""
        self.progress_manager.show_error(error_message)


# Example usage functions
def create_embedded_progress(parent_widget, title: str, total_steps: int) -> ProgressWidget:
    """Create an embedded progress widget."""
    progress_widget = ProgressWidget(parent=parent_widget)
    progress_widget.start_task(title, total_steps)
    return progress_widget


def create_modal_progress(parent_widget, title: str, total_steps: int, 
                         show_cancel: bool = True) -> ProgressDialog:
    """Create a modal progress dialog."""
    progress_dialog = ProgressDialog(title, total_steps, parent=parent_widget, 
                                   show_cancel_button=show_cancel)
    return progress_dialog


def get_progress_callback(total_steps: int, title: str = "Processing...") -> ProgressCallback:
    """Get a progress callback for backend tasks."""
    return ProgressCallback(total_steps, title) 