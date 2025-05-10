from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import QFileDialog, QMessageBox, QVBoxLayout, QFrame, QComboBox, QLineEdit, QGroupBox, QPushButton, QFormLayout
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from csvRead import generate_plot, populate_table
import pandas as pd
import json
import sys


class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(1100, 600)

        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.main_layout = QtWidgets.QHBoxLayout(self.centralwidget)

        # ======= Left side: Plot Frame =======
        self.plotFrame = QFrame(self.centralwidget)
        self.plotLayout = QVBoxLayout(self.plotFrame)
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self.plotFrame)
        self.plotLayout.addWidget(self.toolbar)
        self.plotLayout.addWidget(self.canvas)
        self.main_layout.addWidget(self.plotFrame, 2)

        # ======= Right side: Table and Controls =======
        self.rightLayout = QtWidgets.QVBoxLayout()

        # Table widget
        self.tableWidget = QtWidgets.QTableWidget(self.centralwidget)
        self.tableWidget.setColumnCount(2)
        self.tableWidget.setHorizontalHeaderLabels(["Parameter", "Analysis"])
        self.tableWidget.horizontalHeader().setStretchLastSection(True)
        self.rightLayout.addWidget(self.tableWidget)

        # ======= Controls =======
        self.controlGroup = QGroupBox("Graph Controls")
        self.controlLayout = QFormLayout(self.controlGroup)

        # Unit selectors
        self.unit_selector_y = QComboBox()
        self.unit_selector_y.addItems(["uA", "mA", "A"])

        self.unit_selector_x = QComboBox()
        self.unit_selector_x.addItems(["us", "ms", "s"])

        # Units per division
        self.input_x_div = QLineEdit()
        self.input_x_div.setPlaceholderText("e.g. 100")

        self.input_y_div = QLineEdit()
        self.input_y_div.setPlaceholderText("e.g. 50")

        # Axis limits
        self.input_x_min = QLineEdit()
        self.input_x_max = QLineEdit()
        self.input_y_min = QLineEdit()
        self.input_y_max = QLineEdit()

        for line in [self.input_x_min, self.input_x_max, self.input_y_min, self.input_y_max]:
            line.setPlaceholderText("Optional")

        # Apply button
        self.apply_btn = QPushButton("Apply")
        self.apply_btn.clicked.connect(self.apply_axis_settings)

        # Add controls to layout
        self.controlLayout.addRow("Y-axis unit:", self.unit_selector_y)
        self.controlLayout.addRow("X-axis unit:", self.unit_selector_x)
        self.controlLayout.addRow("X units/div:", self.input_x_div)
        self.controlLayout.addRow("Y units/div:", self.input_y_div)
        self.controlLayout.addRow("X min:", self.input_x_min)
        self.controlLayout.addRow("X max:", self.input_x_max)
        self.controlLayout.addRow("Y min:", self.input_y_min)
        self.controlLayout.addRow("Y max:", self.input_y_max)
        self.controlLayout.addRow(self.apply_btn)

        self.rightLayout.addWidget(self.controlGroup)
        self.main_layout.addLayout(self.rightLayout, 1)
        MainWindow.setCentralWidget(self.centralwidget)

        # ======= Menu Bar =======
        self.menubar = QtWidgets.QMenuBar(MainWindow)

        # File menu
        self.menuFile = QtWidgets.QMenu(self.menubar)
        self.actionOpen = QtWidgets.QAction("Open")
        self.actionSave = QtWidgets.QAction("Save")
        self.menuFile.addAction(self.actionOpen)
        self.menuFile.addAction(self.actionSave)
        self.menubar.addMenu(self.menuFile)

        # Analysis menu
        self.menuAnalysis = QtWidgets.QMenu(self.menubar)
        self.actionFilteringWindow = QtWidgets.QAction("Filtering Window")
        self.actionDCBias = QtWidgets.QAction("DC Bias")
        self.menuAnalysis.addAction(self.actionFilteringWindow)
        self.menuAnalysis.addAction(self.actionDCBias)
        self.menubar.addMenu(self.menuAnalysis)

        MainWindow.setMenuBar(self.menubar)

        self.statusbar = QtWidgets.QStatusBar(MainWindow)
        MainWindow.setStatusBar(self.statusbar)

        # Connections
        self.actionOpen.triggered.connect(self.handle_open_action)
        self.actionSave.triggered.connect(self.save_file)
        self.actionFilteringWindow.triggered.connect(self.handle_filtering_window)
        self.actionDCBias.triggered.connect(self.handle_dc_bias)

        # Internal state
        self.current_file_path = None
        self.is_unsaved = False
        self.y_unit = "A"
        self.x_unit = "s"
        self.unit_scale_y = {"uA": 1e6, "mA": 1e3, "A": 1}
        self.unit_scale_x = {"us": 1e6, "ms": 1e3, "s": 1}
        self.x_div = None
        self.y_div = None
        self.x_min = 0
        self.x_max = None
        self.y_min = None
        self.y_max = None

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def apply_axis_settings(self):
        """Applies all user-defined settings."""
        self.y_unit = self.unit_selector_y.currentText()
        self.x_unit = self.unit_selector_x.currentText()

        try: self.x_div = float(self.input_x_div.text())
        except: self.x_div = None

        try: self.y_div = float(self.input_y_div.text())
        except: self.y_div = None

        try: self.x_min = float(self.input_x_min.text())
        except: self.x_min = None

        try: self.x_max = float(self.input_x_max.text())
        except: self.x_max = None

        try: self.y_min = float(self.input_y_min.text())
        except: self.y_min = None

        try: self.y_max = float(self.input_y_max.text())
        except: self.y_max = None

        if self.current_file_path and self.current_file_path.endswith('.csv'):
            self.open_excel_file(self.current_file_path)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "TeeSense Current Pulse Display"))
        self.menuFile.setTitle(_translate("MainWindow", "&File"))
        self.menuAnalysis.setTitle(_translate("MainWindow", "&Analysis"))
        self.actionOpen.setText(_translate("MainWindow", "Open"))
        self.actionSave.setText(_translate("MainWindow", "Save"))
        self.actionFilteringWindow.setText(_translate("MainWindow", "Filtering Window"))
        self.actionDCBias.setText(_translate("MainWindow", "DC Bias"))

    def display_matplotlib_graph(self, figure):
        """Displays the matplotlib graph with scaling, ticks, and axis limits."""
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        ax.set_title("Current Pulse Data")

        y_scale = self.unit_scale_y.get(self.y_unit, 1)
        x_scale = self.unit_scale_x.get(self.x_unit, 1)

        for fig_ax in figure.axes:
            for line in fig_ax.lines:
                x = [v * x_scale for v in line.get_xdata()]
                y = [v * y_scale for v in line.get_ydata()]
                ax.plot(x, y, label=line.get_label(), linestyle='dashed', marker='o')

        ax.set_xlabel(f"Time ({self.x_unit})")
        ax.set_ylabel(f"Current ({self.y_unit})")
        ax.grid(True)
        ax.legend()

        # Apply user-defined limits
        if self.x_min is not None and self.x_max is not None:
            ax.set_xlim(self.x_min, self.x_max)
        if self.y_min is not None and self.y_max is not None:
            ax.set_ylim(self.y_min, self.y_max)

        # Apply ticks
        if self.x_div:
            min_x, max_x = ax.get_xlim()
            ax.set_xticks([min_x + i * self.x_div for i in range(int((max_x - min_x) / self.x_div) + 1)])
        if self.y_div:
            min_y, max_y = ax.get_ylim()
            ax.set_yticks([min_y + i * self.y_div for i in range(int((max_y - min_y) / self.y_div) + 1)])

        self.canvas.draw()

    def open_excel_file(self, file_path):
        """Loads CSV and plots it."""
        try:
            data = pd.read_csv(file_path)
            populate_table(self.tableWidget, data)
            figure = generate_plot(file_path)
            self.display_matplotlib_graph(figure)
            self.is_unsaved = True
        except Exception as e:
            QMessageBox.warning(None, "Error", f"Could not load CSV file:\n{e}")

    def save_file(self):
        if self.current_file_path:
            self.save_workspace(self.current_file_path)
        else:
            file_path, _ = QFileDialog.getSaveFileName(None, "Save Workspace As", "", "JSON Files (*.json)")
            if file_path:
                self.current_file_path = file_path
                self.save_workspace(file_path)

    def save_workspace(self, file_path):
        workspace_data = {
            "current_file_path": self.current_file_path,
            "is_unsaved": self.is_unsaved,
        }
        try:
            with open(file_path, 'w') as json_file:
                json.dump(workspace_data, json_file, indent=4)
            QMessageBox.information(None, "Save Successful", "Workspace saved successfully.")
        except Exception as e:
            QMessageBox.warning(None, "Save Failed", f"Could not save workspace:\n{e}")

    def handle_open_action(self):
        file_path, _ = QFileDialog.getOpenFileName(None, "Open File", "", "CSV Files (*.csv);;JSON Files (*.json)")
        if file_path:
            self.current_file_path = file_path
            if file_path.endswith('.csv'):
                self.open_excel_file(file_path)
            else:
                QMessageBox.warning(None, "Error", "Unsupported file type.")

    def handle_filtering_window(self):
        QMessageBox.information(None, "Filtering Window", "Filtering window analysis not implemented yet.")

    def handle_dc_bias(self):
        try:
            ax = self.figure.axes[0]
            all_y_values = []

            # Collect all y-data from lines
            for line in ax.lines:
                y_data = line.get_ydata()
                all_y_values.extend(y_data)

            if not all_y_values:
                QMessageBox.warning(None, "DC Bias", "No data found to calculate DC bias.")
                return

            dc_bias = sum(all_y_values) / len(all_y_values)

            # Add horizontal line to the plot
            ax.axhline(dc_bias, color='g', linestyle='--', linewidth=1.5, label=f"DC Bias")
            ax.legend()
            self.canvas.draw()

        except Exception as e:
            QMessageBox.warning(None, "DC Bias Error", f"Error calculating DC bias:\n{e}")



if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    MainWindow = QtWidgets.QMainWindow()
    ui = Ui_MainWindow()
    ui.setupUi(MainWindow)

    if len(sys.argv) > 1 and sys.argv[1].endswith(".csv"):
        csv_path = sys.argv[1]
        ui.current_file_path = csv_path
        ui.open_excel_file(csv_path)

    MainWindow.setWindowTitle("TeeSense Current Pulse Display")
    MainWindow.show()
    sys.exit(app.exec_())
