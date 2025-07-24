# Progress Widgets for SanPy

This module provides progress tracking widgets for long-running tasks in the SanPy GUI. It supports both embedded progress bars and modal progress dialogs.

## Overview

The progress widget system consists of:

1. **ProgressWidget** - Embedded progress bar for non-blocking operations
2. **ProgressDialog** - Modal progress dialog for critical operations
3. **ProgressManager** - Singleton manager for coordinating progress updates
4. **ProgressCallback** - Simple interface for backend tasks to report progress

## Quick Start

### Basic Usage

```python
from sanpy.interface.progress_widget import ProgressWidget, get_progress_callback

# Create embedded progress widget
progress_widget = ProgressWidget(parent=main_window)
progress_widget.start_task("Processing files...", total_steps=100)

# Create progress callback for backend
progress_callback = get_progress_callback(100, "Processing files...")

# Update progress from backend
progress_callback.update(50, "Processing file 50/100")

# Complete task
progress_callback.complete("Processing complete!")
```

### Modal Progress Dialog

```python
from sanpy.interface.progress_widget import ProgressDialog

# Create modal progress dialog
progress_dialog = ProgressDialog(
    title="Critical Operation",
    total_steps=50,
    parent=main_window,
    show_cancel_button=True
)
progress_dialog.show()

# Update progress
progress_dialog.update_progress(25, 50, "Halfway done...")
```

## Integration with Backend Tasks

### Modifying Backend Functions

To add progress tracking to your backend functions, modify them to accept a `progress_callback` parameter:

```python
def your_long_running_function(self, progress_callback=None):
    """Your function with progress tracking."""
    total_steps = len(self.items)
    
    if progress_callback:
        progress_callback.update(0, "Starting processing...")
    
    for i, item in enumerate(self.items):
        # Do work...
        
        # Update progress
        if progress_callback:
            progress_callback.update(
                i + 1, 
                f"Processing item {i + 1}/{total_steps}: {item.name}"
            )
    
    # Complete
    if progress_callback:
        progress_callback.complete("Processing completed successfully!")
```

### Example: TiffPool Integration

The `TiffPool.pool_all_analysis()` method has been modified to support progress tracking:

```python
# In your PyQt widget
from sanpy.interface.progress_widget import get_progress_callback

# Get total files
total_files = len(self.backend.df)

# Create progress callback
progress_callback = get_progress_callback(
    total_steps=total_files,
    title="TiffPool Analysis"
)

# Start progress widget
self.progress_widget.start_task(
    title="TiffPool Analysis",
    total_steps=total_files,
    initial_message=f"Found {total_files} files to analyze..."
)

# Run analysis with progress tracking
tiff_pool.pool_all_analysis(progress_callback=progress_callback)
```

## UI Design Options

### 1. Embedded Progress Widget

**Best for:** Non-blocking operations, better UX
- User can continue working while task runs
- Progress bar appears in existing window
- Auto-hides when complete

```python
# Add to existing window layout
self.progress_widget = ProgressWidget(parent=self)
layout.addWidget(self.progress_widget)

# Start task
self.progress_widget.start_task("Processing...", total_steps=100)
```

### 2. Modal Progress Dialog

**Best for:** Critical operations that should block the UI
- User must wait for completion
- Prevents interaction with parent window
- Good for operations that must complete before continuing

```python
# Create and show modal dialog
progress_dialog = ProgressDialog(
    title="Critical Operation",
    total_steps=50,
    parent=self,
    show_cancel_button=True
)
progress_dialog.show()
```

### 3. Hybrid Approach

You can use both approaches depending on the operation:

```python
def process_files(self, critical=False):
    """Process files with appropriate progress UI."""
    total_files = len(self.files)
    
    if critical:
        # Use modal dialog for critical operations
        progress_dialog = ProgressDialog(
            title="Critical File Processing",
            total_steps=total_files,
            parent=self,
            show_cancel_button=False  # No cancel for critical ops
        )
        progress_dialog.show()
        progress_callback = get_progress_callback(total_files, "Critical Processing")
    else:
        # Use embedded widget for non-critical operations
        self.progress_widget.start_task("File Processing", total_files)
        progress_callback = get_progress_callback(total_files, "File Processing")
    
    # Run processing
    self.run_processing(progress_callback)
```

## Advanced Features

### Cancellation Support

Progress widgets support cancellation:

```python
# In your backend function
def process_with_cancellation(self, progress_callback):
    for i, item in enumerate(self.items):
        # Check if cancelled
        if progress_callback.cancelled:
            break
            
        # Do work...
        progress_callback.update(i + 1, f"Processing {item.name}")
```

### Error Handling

Report errors through the progress system:

```python
try:
    # Do work...
    progress_callback.complete("Success!")
except Exception as e:
    progress_callback.error(f"Error: {str(e)}")
```

### Multiple Progress Widgets

The ProgressManager can handle multiple widgets simultaneously:

```python
# Multiple widgets can receive the same progress updates
progress_widget1 = ProgressWidget(parent=window1)
progress_widget2 = ProgressWidget(parent=window2)

# Both will receive updates from the same progress_callback
progress_callback = get_progress_callback(100, "Processing")
```

## Best Practices

### 1. Choose the Right UI Type

- **Embedded**: For background tasks, user can continue working
- **Modal**: For critical operations, user must wait
- **Hybrid**: Start embedded, switch to modal if operation becomes critical

### 2. Provide Meaningful Messages

```python
# Good
progress_callback.update(i + 1, f"Processing file {i + 1}/{total}: {filename}")

# Bad
progress_callback.update(i + 1, "Processing...")
```

### 3. Handle Edge Cases

```python
def process_files(self, progress_callback=None):
    if len(self.files) == 0:
        if progress_callback:
            progress_callback.complete("No files to process")
        return
    
    # Process files...
```

### 4. Use Appropriate Threading

For long-running tasks, use QThread or threading:

```python
from PyQt5.QtCore import QThread, pyqtSignal

class ProcessingThread(QThread):
    progress_updated = pyqtSignal(int, int, str)
    task_completed = pyqtSignal(str)
    
    def run(self):
        # Do work and emit signals
        self.progress_updated.emit(current, total, message)
        self.task_completed.emit("Done!")
```

## Example Integration

See `progress_example.py` for a complete working example that demonstrates:

- Embedded progress widgets
- Modal progress dialogs
- Backend integration with TiffPool simulation
- Threading with progress updates
- Error handling

Run the example:

```bash
python sanpy/interface/progress_example.py
```

## Troubleshooting

### Progress Not Updating

1. Ensure you're calling `progress_callback.update()` in your backend
2. Check that the progress widget is visible (`show()` called)
3. Verify signals are properly connected

### Widget Not Appearing

1. Make sure the widget is added to a layout
2. Check that `start_task()` was called
3. Verify the parent widget is visible

### Cancellation Not Working

1. Check that `show_cancel_button=True` was set
2. Ensure your backend checks `progress_callback.cancelled`
3. Connect the cancel signal to your backend logic 