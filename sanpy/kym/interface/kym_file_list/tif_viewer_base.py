import sys
from functools import partial
from PyQt5.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QToolBar,
    QPushButton,
    QCheckBox,
    QSplitter,
    QLabel,
    QMainWindow,
    QAction,
    QMenu,
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPalette


class CustomWidget(QWidget):
    """Main widget with toolbar and three resizable sections"""

    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle('Custom Layout Widget')
        self.setGeometry(100, 100, 800, 600)

        # Create main layout
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        # Create toolbar
        self.create_toolbar()
        main_layout.addWidget(self.toolbar)

        # Create splitter for the widgets
        self.splitter = QSplitter(Qt.Vertical)

        # Initialize empty widgets dictionary - widgets will be added by subclasses
        self.widgets = {}

        # Add splitter to main layout
        main_layout.addWidget(self.splitter)

        self.setLayout(main_layout)

        # Enable context menu
        self.setContextMenuPolicy(Qt.CustomContextMenu)
        self.customContextMenuRequested.connect(self.show_context_menu)

    def create_toolbar(self):
        """Create the top toolbar with fixed height"""
        self.toolbar = QToolBar()
        self.toolbar.setFixedHeight(40)
        self.toolbar.setMovable(False)

        # Store toolbar widgets in dictionary using meaningful names
        from PyQt5.QtWidgets import QLineEdit, QLabel

        self.toolbar_widgets = {"Status Label": QLabel("Status: Ready")}

        # Add widgets to toolbar in desired order
        self.toolbar.addWidget(self.toolbar_widgets["Status Label"])

    def create_colored_widget(self, text, color):
        """Create a widget with colored background for debugging"""
        widget = QWidget()
        layout = QVBoxLayout()

        # Create label to show which widget this is
        label = QLabel(text)
        label.setAlignment(Qt.AlignCenter)
        layout.addWidget(label)

        widget.setLayout(layout)

        # Set background color
        widget.setStyleSheet(f"background-color: {color}; border: 1px solid #CCCCCC;")

        return widget

    def show_context_menu(self, position):
        """Show context menu to toggle toolbar and widget visibility"""
        context_menu = QMenu(self)

        # Create toggle toolbar action
        toggle_toolbar_action = QAction("Toggle Toolbar", self)
        toggle_toolbar_action.setCheckable(True)
        toggle_toolbar_action.setChecked(self.toolbar.isVisible())
        toggle_toolbar_action.triggered.connect(self.toggle_toolbar)

        context_menu.addAction(toggle_toolbar_action)
        context_menu.addSeparator()

        # Create toggle actions for each widget using partial
        for widget_name in self.widgets:
            toggle_action = QAction(f"Toggle {widget_name}", self)
            toggle_action.setCheckable(True)
            toggle_action.setChecked(self.widgets[widget_name].isVisible())
            toggle_action.triggered.connect(partial(self.toggle_widget, widget_name))
            context_menu.addAction(toggle_action)

        context_menu.exec_(self.mapToGlobal(position))

    def toggle_toolbar(self):
        """Toggle toolbar visibility"""
        self.toolbar.setVisible(not self.toolbar.isVisible())

    def toggle_widget(self, name):
        """Toggle widget visibility by name"""
        if name in self.widgets:
            widget = self.widgets[name]
            widget.setVisible(not widget.isVisible())
        else:
            print(f"Warning: Widget '{name}' not found")

    def on_toolbar_action(self, widget_name):
        """Handle toolbar button clicks"""
        print(f"Toolbar {widget_name} clicked")

    def on_toolbar_state_changed(self, widget_name, state):
        """Handle toolbar checkbox state changes"""
        is_checked = state == 2  # Qt.Checked
        print(f"Toolbar {widget_name}: {is_checked}")

    def on_toolbar_text_changed(self, widget_name, text):
        """Handle toolbar text input changes"""
        print(f"Toolbar {widget_name}: {text}")

    def get_toolbar_widget(self, name):
        """Get a specific toolbar widget by name"""
        return self.toolbar_widgets.get(name)

    def get_toolbar_widgets(self):
        """Get all toolbar widgets dictionary"""
        return self.toolbar_widgets

    def add_toolbar_widget(self, name, widget, position=None):
        """Add a new toolbar widget with uniqueness check"""
        if name in self.toolbar_widgets:
            print(
                f"Warning: Toolbar widget '{name}' already exists. Use a unique name."
            )
            return False

        self.toolbar_widgets[name] = widget

        if position is None:
            self.toolbar.addWidget(widget)
        else:
            # Insert at specific position (advanced usage)
            actions = self.toolbar.actions()
            if position < len(actions):
                self.toolbar.insertWidget(actions[position], widget)
            else:
                self.toolbar.addWidget(widget)
        return True

    def remove_toolbar_widget(self, name):
        """Remove a toolbar widget"""
        if name not in self.toolbar_widgets:
            print(f"Warning: Toolbar widget '{name}' not found")
            return False

        widget = self.toolbar_widgets[name]
        self.toolbar.removeAction(widget)
        widget.setParent(None)
        del self.toolbar_widgets[name]
        return True

    def set_toolbar_value(self, name, value):
        """Set value for a toolbar widget"""
        widget = self.toolbar_widgets.get(name)
        if not widget:
            print(f"Warning: Toolbar widget '{name}' not found")
            return False

        # Handle different widget types
        if hasattr(widget, 'setChecked'):  # QCheckBox
            widget.setChecked(value)
        elif hasattr(widget, 'setText'):  # QLabel, QLineEdit, QPushButton
            widget.setText(str(value))
        else:
            print(
                f"Warning: Don't know how to set value for widget type {type(widget)}"
            )
            return False
        return True

    def get_toolbar_value(self, name):
        """Get value from a toolbar widget"""
        widget = self.toolbar_widgets.get(name)
        if not widget:
            print(f"Warning: Toolbar widget '{name}' not found")
            return None

        # Handle different widget types
        if hasattr(widget, 'isChecked'):  # QCheckBox
            return widget.isChecked()
        elif hasattr(widget, 'text'):  # QLabel, QLineEdit, QPushButton
            return widget.text()
        else:
            print(
                f"Warning: Don't know how to get value for widget type {type(widget)}"
            )
            return None

    def get_widgets(self):
        """Return the widgets dictionary for external modification"""
        return self.widgets

    def get_widget(self, name):
        """Return a specific widget by name"""
        return self.widgets.get(name)

    def add_widget(self, name, widget, background_color="#F0F0F0"):
        """Add a new widget to the layout with uniqueness check"""
        if name in self.widgets:
            print(f"Warning: Widget '{name}' already exists. Use a unique name.")
            return False

        # Set background color for debugging
        widget.setStyleSheet(
            f"background-color: {background_color}; border: 1px solid #CCCCCC;"
        )

        self.widgets[name] = widget
        self.splitter.addWidget(widget)
        return True

    def remove_widget(self, name):
        """Remove a widget from the layout"""
        if name not in self.widgets:
            print(f"Warning: Widget '{name}' not found")
            return False

        widget = self.widgets[name]
        self.splitter.removeWidget(widget)
        widget.setParent(None)  # Remove from parent
        del self.widgets[name]
        return True


class MainWindow(QMainWindow):
    """Main window to contain the custom widget"""

    def __init__(self):
        super().__init__()
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle('PyQt5 Custom Layout Demo')
        self.setGeometry(100, 100, 800, 600)

        # Create and set the custom widget as central widget
        self.custom_widget = CustomWidget()
        self.setCentralWidget(self.custom_widget)


def main():
    app = QApplication(sys.argv)

    # Create and show the main window
    window = MainWindow()
    window.show()

    # Example of how to access the widgets for customization
    widgets_dict = window.custom_widget.get_widgets()
    toolbar_widgets = window.custom_widget.get_toolbar_widgets()

    print("Available widgets:", list(widgets_dict.keys()))
    print("Available toolbar widgets:", list(toolbar_widgets.keys()))
    print("You can now add your own widgets to each section")

    # Example: Access individual widgets using meaningful names
    widget1 = window.custom_widget.get_widget("Widget 1")
    option1_checkbox = window.custom_widget.get_toolbar_widget("Option 1")

    # Example: Programmatic control of toolbar widgets using meaningful names
    window.custom_widget.set_toolbar_value("Option 1", True)
    window.custom_widget.set_toolbar_value("Status Label", "Status: Connected")
    window.custom_widget.set_toolbar_value("Text Input", "Hello World")

    print("Option 1 checked:", window.custom_widget.get_toolbar_value("Option 1"))
    print("Text Input value:", window.custom_widget.get_toolbar_value("Text Input"))

    # Example: Adding new widgets dynamically (with uniqueness check)
    from PyQt5.QtWidgets import QCheckBox, QLabel

    # This will work
    new_checkbox = QCheckBox("Enable Debug")
    success = window.custom_widget.add_toolbar_widget("Enable Debug", new_checkbox)
    print(f"Added 'Enable Debug' checkbox: {success}")

    # This will fail due to duplicate name
    duplicate_checkbox = QCheckBox("Enable Debug")
    success = window.custom_widget.add_toolbar_widget(
        "Enable Debug", duplicate_checkbox
    )
    print(f"Added duplicate 'Enable Debug' checkbox: {success}")

    sys.exit(app.exec_())


if __name__ == '__main__':
    main()
