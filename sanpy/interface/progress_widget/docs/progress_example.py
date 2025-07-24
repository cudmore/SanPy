"""
Example script demonstrating how to use the progress widgets in SanPy.

This script shows different ways to integrate progress tracking into your PyQt application.
"""

import sys
import time
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QLabel
from PyQt5.QtCore import QThread, pyqtSignal

from sanpy.interface.progress_widget.progress_widget import (
    ProgressWidget, 
    ProgressDialog, 
    get_progress_callback,
    create_embedded_progress,
    create_modal_progress
)


class SimulatedTask(QThread):
    """Simulate a long-running task with progress updates."""
    
    progress_updated = pyqtSignal(int, int, str)
    task_completed = pyqtSignal(str)
    
    def __init__(self, total_steps: int, task_name: str):
        super().__init__()
        self.total_steps = total_steps
        self.task_name = task_name
        self.cancelled = False
        
    def run(self):
        """Run the simulated task."""
        for i in range(self.total_steps):
            if self.cancelled:
                break
                
            # Simulate work
            time.sleep(0.1)
            
            # Update progress
            message = f"Processing step {i + 1}/{self.total_steps}"
            self.progress_updated.emit(i + 1, self.total_steps, message)
            
        if not self.cancelled:
            self.task_completed.emit(f"{self.task_name} completed successfully!")
        else:
            self.task_completed.emit(f"{self.task_name} was cancelled.")


class ExampleWindow(QMainWindow):
    """Example window demonstrating different progress tracking approaches."""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Progress Widget Examples")
        self.setGeometry(100, 100, 600, 400)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Create layout
        layout = QVBoxLayout(central_widget)
        
        # Add title
        title = QLabel("Progress Widget Examples")
        title.setStyleSheet("font-size: 16px; font-weight: bold; margin: 10px;")
        layout.addWidget(title)
        
        # Add embedded progress widget
        self.progress_widget = ProgressWidget(parent=self)
        layout.addWidget(self.progress_widget)
        
        # Add buttons
        self.create_buttons(layout)
        
        # Add status label
        self.status_label = QLabel("Ready")
        layout.addWidget(self.status_label)
        
        # Initialize task thread
        self.task_thread = None
        
    def create_buttons(self, layout):
        """Create example buttons."""
        
        # Embedded progress example
        embedded_btn = QPushButton("Start Embedded Progress (Non-blocking)")
        embedded_btn.clicked.connect(self.start_embedded_progress)
        layout.addWidget(embedded_btn)
        
        # Modal progress example
        modal_btn = QPushButton("Start Modal Progress (Blocking)")
        modal_btn.clicked.connect(self.start_modal_progress)
        layout.addWidget(modal_btn)
        
        # TiffPool simulation example
        tiffpool_btn = QPushButton("Simulate TiffPool Analysis")
        tiffpool_btn.clicked.connect(self.simulate_tiffpool_analysis)
        layout.addWidget(tiffpool_btn)
        
    def start_embedded_progress(self):
        """Start embedded progress example."""
        self.status_label.setText("Starting embedded progress...")
        
        # Start progress widget
        self.progress_widget.start_task(
            title="Processing Files",
            total_steps=50,
            initial_message="Starting file processing..."
        )
        
        # Create and start task thread
        self.task_thread = SimulatedTask(50, "File Processing")
        self.task_thread.progress_updated.connect(self.progress_widget.update_progress)
        self.task_thread.task_completed.connect(self.progress_widget.complete_task)
        self.task_thread.task_completed.connect(self.on_task_completed)
        self.task_thread.start()
        
    def start_modal_progress(self):
        """Start modal progress example."""
        self.status_label.setText("Starting modal progress...")
        
        # Create modal progress dialog
        progress_dialog = ProgressDialog(
            title="Critical Operation",
            total_steps=30,
            parent=self,
            show_cancel_button=True
        )
        
        # Create and start task thread
        self.task_thread = SimulatedTask(30, "Critical Operation")
        self.task_thread.progress_updated.connect(progress_dialog.update_progress)
        self.task_thread.task_completed.connect(progress_dialog.complete_task)
        self.task_thread.task_completed.connect(self.on_task_completed)
        
        # Show dialog and start task
        progress_dialog.show()
        self.task_thread.start()
        
    def simulate_tiffpool_analysis(self):
        """Simulate TiffPool analysis with progress tracking."""
        self.status_label.setText("Starting TiffPool analysis simulation...")
        
        # Simulate finding files
        total_files = 25
        
        # Start progress widget
        self.progress_widget.start_task(
            title="TiffPool Analysis",
            total_steps=total_files,
            initial_message=f"Found {total_files} files to analyze..."
        )
        
        # Create progress callback (like what TiffPool would use)
        progress_callback = get_progress_callback(
            total_steps=total_files,
            title="TiffPool Analysis"
        )
        
        # Simulate the analysis process
        self.simulate_tiffpool_process(progress_callback)
        
    def simulate_tiffpool_process(self, progress_callback):
        """Simulate the TiffPool analysis process."""
        import threading
        
        def run_analysis():
            total_files = progress_callback.total_steps
            
            for i in range(total_files):
                # Simulate processing each file
                time.sleep(0.2)
                
                # Update progress (like TiffPool.pool_all_analysis would do)
                filename = f"file_{i+1:03d}.tif"
                progress_callback.update(
                    current=i + 1,
                    message=f"Processing file {i + 1}/{total_files}: {filename}"
                )
                
            # Complete the task
            progress_callback.complete("TiffPool analysis completed successfully!")
            
        # Run in background thread
        thread = threading.Thread(target=run_analysis)
        thread.daemon = True
        thread.start()
        
    def on_task_completed(self, message):
        """Handle task completion."""
        self.status_label.setText(message)
        if self.task_thread:
            self.task_thread.wait()
            self.task_thread = None


def main():
    """Run the example application."""
    app = QApplication(sys.argv)
    
    window = ExampleWindow()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main() 