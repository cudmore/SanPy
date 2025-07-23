import sys
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar

import seaborn as sns

from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget

# TODO: use this to plot one of seaborn plots


class KymRoiMainWindow(QMainWindow):
    def __init__(self, figure, ax):
        super().__init__()
        self.setWindowTitle("Matplotlib in PyQt")

        # Create a Matplotlib figure and axes
        # self.figure, self.ax = plt.subplots()
        self.figure = figure
        self.ax = ax
        self.canvas = FigureCanvas(self.figure)

        self.toolbar = NavigationToolbar(self.canvas, self)

        # Create a layout and add the canvas
        layout = QVBoxLayout()
        layout.addWidget(self.canvas)
        layout.addWidget(self.toolbar)

        # Create a central widget and set the layout
        central_widget = QWidget()
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

        # Plot some data
        # self.ax = sns.scatterplot(x=[1,2,3], y=[3,10,2])
        # self.ax = sns.lineplot(x=[1,2,3], y=[3,10,2])
        # self.ax = ax
        # self.ax.plot([0, 1, 2, 3, 4], [10, 1, 20, 3, 40])

        # self.figure = figure
        # Redraw the canvas
        self.canvas.draw()


if __name__ == '__main__':
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec_())
