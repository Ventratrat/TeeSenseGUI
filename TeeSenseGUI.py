from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QFileDialog, QMessageBox, QVBoxLayout, QFrame
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from csvRead import generate_plot, populate_table
import pandas as pd
import json
import os

class Ui_MainWindow(object):

    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(900, 600)

        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")

        self.main_layout = QtWidgets.QHBoxLayout(self.centralwidget)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        # Left side: Matplotlib plot container
        self.plotFrame = QFrame(self.centralwidget)
        self.plotLayout = QVBoxLayout(self.plotFrame)
        self.plotLayout.setContentsMargins(0, 0, 0, 0)

        # Matplotlib Figure and Canvas
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self.plotFrame)

        self.plotLayout.addWidget(self.toolbar)
        self.plotLayout.addWidget(self.canvas)
        self.main_layout.addWidget(self.plotFrame, 2)

        self.tableWidget = QtWidgets.QTableWidget(self.centralwidget)
        self.tableWidget.setObjectName("tableWidget")
        self.tableWidget.setColumnCount(2)
        self.tableWidget.setHorizontalHeaderLabels(["Parameter", "Analysis"])
        self.tableWidget.horizontalHeader().setStretchLastSection(True)

        self.main_layout.addWidget(self.tableWidget, 1)

        MainWindow.setCentralWidget(self.centralwidget)

        # Menu Bar
        self.menubar = QtWidgets.QMenuBar(MainWindow)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 900, 21))
        self.menuFile = QtWidgets.QMenu(self.menubar)
        self.menuEdit = QtWidgets.QMenu(self.menubar)
        MainWindow.setMenuBar(self.menubar)

        # Status Bar
        self.statusbar = QtWidgets.QStatusBar(MainWindow)
        MainWindow.setStatusBar(self.statusbar)

        # Actions
        self.actionOpen = QtWidgets.QAction(MainWindow, text="Open")
        self.actionSave = QtWidgets.QAction(MainWindow, text="Save")

        self.menuFile.addAction(self.actionOpen)
        self.menuFile.addAction(self.actionSave)
        self.menubar.addAction(self.menuFile.menuAction())

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

        # Connect Actions
        self.actionOpen.triggered.connect(self.handle_open_action)
        self.actionSave.triggered.connect(self.save_file)

        self.current_file_path = None
        self.is_unsaved = False

    def display_matplotlib_graph(self, figure):
        """Embeds a Matplotlib figure into the PyQt5 GUI."""
        self.figure.clear()
        new_ax = self.figure.add_subplot(111)
        new_ax.set_title("Current Pulse Data")
        
        for ax in figure.axes:
            for line in ax.lines:
                new_ax.plot(line.get_xdata(), line.get_ydata(), label=line.get_label(), linestyle='dashed', marker='o')

            new_ax.set_xlim(ax.get_xlim())
            new_ax.set_ylim(ax.get_ylim())
            new_ax.set_xticks(ax.get_xticks())
            new_ax.set_yticks(ax.get_yticks())
            new_ax.grid()

        self.figure.legend()
        self.canvas.draw()

    def open_excel_file(self, file_path):
        """Loads a CSV file and plots the data."""
        if file_path.endswith('.csv'):
            try:
                data = pd.read_csv(file_path)
                populate_table(self.tableWidget, data)  
                figure = generate_plot(file_path)
                self.display_matplotlib_graph(figure)
                self.is_unsaved = True
            except Exception as e:
                QMessageBox.warning(None, "Error", f"Could not load CSV file:\n{e}")
        else:
            QMessageBox.information(None, "File Opened", f"Opened: {file_path}")

    def save_workspace(self, file_path):
        """Saves the workspace as a JSON file."""
        workspace_data = {
            "current_file_path": self.current_file_path,
            "is_unsaved": self.is_unsaved,
            "text_display": self.textDisplay.toPlainText(),
        }

        try:
            with open(file_path, 'w') as json_file:
                json.dump(workspace_data, json_file, indent=4)
            QMessageBox.information(None, "Save Successful", "Workspace saved successfully.")
        except Exception as e:
            QMessageBox.warning(None, "Save Failed", f"Could not save workspace:\n{e}")

    def retranslateUi(self, MainWindow):
        """Sets the text for the UI components."""
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "TeeSense Current Pulse Display"))
        self.menuFile.setTitle(_translate("MainWindow", "&File"))
        self.menuEdit.setTitle(_translate("MainWindow", "&Edit"))
        self.actionOpen.setShortcut(_translate("MainWindow", "Ctrl+O"))
        self.actionSave.setShortcut(_translate("MainWindow", "Ctrl+S"))

    def handle_open_action(self):
        """Handles opening a new file."""
        file_path, _ = QFileDialog.getOpenFileName(None, "Open File", "", "CSV Files (*.csv);;JSON Files (*.json)")
        if file_path:
            self.current_file_path = file_path

            if file_path.endswith('.json'):
                self.open_json_file(file_path)
            elif file_path.endswith('.csv'):
                self.open_excel_file(file_path)
            else:
                QMessageBox.warning(None, "Error", "Unsupported file type.")

    def save_file(self):
        """Saves the current workspace."""
        if self.current_file_path:
            self.save_workspace(self.current_file_path)
        else:
            self.save_as_file()

    def save_as_file(self):
        """Saves the workspace as a new file."""
        file_path, _ = QFileDialog.getSaveFileName(None, "Save Workspace As", "", "JSON Files (*.json)")
        if file_path:
            self.current_file_path = file_path
            self.save_workspace(file_path)


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    MainWindow = QtWidgets.QMainWindow()
    ui = Ui_MainWindow()
    ui.setupUi(MainWindow)

    MainWindow.show()
    sys.exit(app.exec_())
