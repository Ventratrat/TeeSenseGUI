from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import QFileDialog, QMessageBox, QVBoxLayout, QFrame, QComboBox, QLineEdit, QGroupBox, QPushButton, QFormLayout, QLabel, QHBoxLayout, QWidget, QTableWidget, QMainWindow, QPushButton
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from matplotlib.backend_bases import MouseEvent
from matplotlib.ticker import MultipleLocator
from csvRead import generate_plot, populate_table
import pandas as pd
import json
import sys
import time
import tkinter as tk
import threading
from tkinter import messagebox
import importlib

import subprocess

def start_data_collect_window():
    root = tk.Tk()
    root.title("Data Collection Window")

    tk.Label(root, text="Data Collection Window", font=('Arial', 14)).pack(pady=10)

    def start_data_collection():
        messagebox.showinfo("Data Collection", "Data collection has started!")
        print("Data collection has started...")

    collect_button = tk.Button(root, text="Start Data Collection", command=start_data_collection)
    collect_button.pack(pady=10)

    close_button = tk.Button(root, text="Close DataCollect", command=root.quit)
    close_button.pack(pady=10)

    root.mainloop()

# Function to start the Tkinter window (dataCollect)
def start_tkinter_window():
    global root
    root = tk.Tk()
    root.title("DataCollect")
    tk.Label(root, text="This is the DataCollect window").pack()

    tk.Button(root, text="Close DataCollect", command=root.quit).pack()

    root.mainloop()  # Start the Tkinter event loop

class MyMainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('PyQt5 Window')
        self.setGeometry(100, 100, 300, 200)
        self.setStyleSheet("background-color: lightgray;")
        
    def closeEvent(self, event):
        """Override close event to ensure the entire program exits when 'X' is clicked."""
        ui = Ui_MainWindow()
        ui.MainWindow = self  # Passing reference of the main window to the Ui_MainWindow instance
        ui.closeEvent(event)

class Ui_MainWindow(object):

    def closeEvent(self, event):
        """Handle the close event for the PyQt window."""
        # Show a confirmation dialog when the user tries to close the window
        reply = QMessageBox.question(self.MainWindow, 'Quit', 'Are you sure you want to quit?',
                                     QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            print("PyQt5 window closed, exiting program...")

            # Close the Tkinter window if it's open
            if root:
                root.quit()  # End the Tkinter event loop
                root.destroy()  # Destroy the Tkinter window

            event.accept()  # Allow the window to close
            QApplication.quit()  # Exit the PyQt application
        else:
            event.ignore()  # Ignore the close event and keep the window open

    def open_data_collect_window(self):
        # Ensure we are closing the MainWindow correctly
        self.MainWindow.close()  # Close the current window

        # Run the dataCollect program as a subprocess
        subprocess.Popen([sys.executable, 'dataCollect.py'])  # Assuming 'data_collect.py' is in the same directory

    def retake_measurement(self):
        if not hasattr(self, 'retake_settings'):
            QMessageBox.warning(None, "Missing Settings", "No previous measurement settings found.")
            return

        settings = self.retake_settings
        port = settings.get("port")
        samples = settings.get("samples")
        filter_mode = settings.get("filter_mode")

        if not port:
            QMessageBox.warning(None, "Invalid Settings", "Measurement settings are incomplete.")
            return

        try:
            import serial
            ser = serial.Serial(port, 115200, timeout=1)
            ser.flushInput()
        except Exception as e:
            QMessageBox.critical(None, "Serial Error", f"Failed to open port {port}: {e}")
            return

        ser.write(b'RESET\n')
        time.sleep(0.5)
        ser.reset_input_buffer()

        if filter_mode == "DC Bias":
            # DC Bias specific logic
            try:
                print("Retaking DC Bias")
                samples = []
                skip_first = True
                start_time = time.time()
                timeout = 60

                while time.time() - start_time < timeout:
                    if ser.in_waiting:
                        line = ser.readline().decode('utf-8').strip()
                        try:
                            parts = list(map(int, line.split()))
                            if skip_first:
                                print(f"Skipping first timing line: {parts}")
                                skip_first = False
                                continue
                            if len(parts) == 4:
                                samples.append(parts)
                        except:
                            continue
                    else:
                        time.sleep(0.001)

                ser.close()

                if not samples:
                    QMessageBox.warning(None, "Error", "No data collected during DC Bias retake.")
                    return

                sample_interval = 1 / 1_220_000
                formatted = [[i * sample_interval] + row for i, row in enumerate(samples)]

                from ByteCombine import process_dc_bias_data
                x_data, y_data = process_dc_bias_data(formatted, return_data=True)
                self.retake_button.setEnabled(True)
                self.load_direct_data(x_data, y_data, filtered=False, retake_settings=settings)


            except Exception as e:
                QMessageBox.critical(None, "Retake Error", f"DC Bias retake failed:\n{e}")
            return

        # For filtered/unfiltered modes
        data = []
        sample_interval = 1 / 1_220_000
        sample_index = 0
        skip_first = True
        start_time = time.time()
        timeout = 5

        while len(data) < samples and (time.time() - start_time < timeout):
            if ser.in_waiting:
                line = ser.readline().decode('utf-8').strip()
                try:
                    parts = list(map(int, line.split()))
                    if skip_first:
                        print(f"⚠️ Skipping first timing line: {parts}")
                        skip_first = False
                        continue
                    if len(parts) == 4:
                        data.append([sample_index * sample_interval] + parts)
                        sample_index += 1
                except:
                    continue
            else:
                time.sleep(0.001)

        ser.close()

        from ByteCombine import process_filtered_data, process_unfiltered_data
        if filter_mode == "Filtered":
            x_data, y_data = process_filtered_data(data, return_data=True)
        else:
            x_data, y_data = process_unfiltered_data(data, return_data=True)

        self.load_direct_data(x_data, y_data, filtered=(filter_mode == "Filtered"), retake_settings=settings)
        self.retake_button.setEnabled(True)

    def on_pick(self, event):
        for marker in self.markers:
            if marker.line == event.artist:
                self.dragging_marker = marker
                marker.dragging = True
                break

    def on_motion(self, event):
        if self.dragging_marker and event.inaxes:
            new_pos = event.xdata if self.dragging_marker.orientation == 'vline' else event.ydata
            self.dragging_marker.update_position(new_pos)
            self.update_marker_labels()
            self.canvas.draw_idle()

    def on_release(self, event):
        if self.dragging_marker:
            self.dragging_marker.dragging = False
            self.dragging_marker = None

    def enable_check(self):
        return self.marker_placement_enabled

    def orientation_check(self):
        return self.current_marker_orientation

    def clear_all_markers(self):
        for marker in self.markers:
            marker.remove()
        self.markers.clear()
        self.marker_counter = 1
        self.marker_info_label.setText("")
        self.canvas.draw_idle()

    def toggle_marker_placement(self):
        self.marker_placement_enabled = not self.marker_placement_enabled
        status = "ON" if self.marker_placement_enabled else "OFF"
        self.enable_markers_btn.setText(f"Placement: {status}")

    def toggle_marker_orientation(self):
        if self.current_marker_orientation == "vline":
            self.current_marker_orientation = "hline"
            self.toggle_marker_orientation_btn.setText("Horizontal Marker")
        else:
            self.current_marker_orientation = "vline"
            self.toggle_marker_orientation_btn.setText("Vertical Marker")

    def update_marker_labels(self):
        if hasattr(self, 'info_output') and hasattr(self, 'markers'):
            x_unit = self.extract_unit(self.ax.get_xlabel())
            y_unit = self.extract_unit(self.ax.get_ylabel())
            lines = []
            for m in self.markers:
                unit = x_unit if m.orientation == 'vline' else y_unit
                lines.append(f"{m.label}: {m.position:.4f} {unit}")
            self.info_output("\n".join(lines))

    def on_click(self, event):
        if not hasattr(self, 'markers') or not hasattr(self, 'canvas'):
            return

        if not event.inaxes or not self.enable_check():
            return

        if event.button == 1:  # Left-click → Add marker
            orientation = self.orientation_check()
            position = event.xdata if orientation == 'vline' else event.ydata
            label = f"M{self.marker_counter}"
            marker = InteractiveMarker(self.ax, orientation, position, label=label)
            self.markers.append(marker)
            self.marker_counter += 1
            self.update_marker_labels()

        elif event.button == 3:  # Right-click → Delete nearest marker
            for marker in self.markers:
                if marker.line.contains(event)[0]:
                    marker.remove()
                    self.markers.remove(marker)
                    break

        # Update marker labels if info_output is available
        self.update_marker_labels()

        self.canvas.draw_idle()

        # Update marker info if available
        if hasattr(self, 'info_output'):
            x_unit = self.extract_unit(self.ax.get_xlabel())
            y_unit = self.extract_unit(self.ax.get_ylabel())
            lines = []
            for m in self.markers:
                unit = x_unit if m.orientation == 'vline' else y_unit
                lines.append(f"{m.label}: {m.position:.4f} {unit}")
            self.info_output("\n".join(lines))

        self.canvas.draw_idle()

    def on_motion(self, event):
        if not self.dragging_marker or not event.inaxes:
            return

        new_pos = event.xdata if self.dragging_marker.orientation == 'vline' else event.ydata
        self.dragging_marker.update_position(new_pos)
        self.update_marker_labels()
        self.canvas.draw_idle()

    def on_release(self, event):
        self.dragging_marker = None
        self.dragging_event = None

    def orientation_check(self):
        return getattr(self, 'current_marker_orientation', 'vline')

    def enable_check(self):
        return getattr(self, 'marker_placement_enabled', True)

    def extract_unit(self, label_text):
        # From "Current (mA)" → "mA"
        if "(" in label_text and ")" in label_text:
            return label_text.split("(")[-1].split(")")[0]

    def prepare_and_display_data(self, x_data, y_data):
        """
        Applies current unit settings, axis controls, and calls display.
        """
        self.y_unit = self.unit_selector_y.currentText()
        self.x_unit = self.unit_selector_x.currentText()

        # Apply axis input settings
        try: self.x_div = float(self.input_x_div.text())
        except: self.x_div = None
        try: self.y_div = float(self.input_y_div.text())
        except: self.y_div = None
        try: self.x_min = float(self.input_x_min.text().strip())
        except: self.x_min = None
        try: self.x_max = float(self.input_x_max.text().strip())
        except: self.x_max = None
        try: self.y_min = float(self.input_y_min.text().strip())
        except: self.y_min = None
        try: self.y_max = float(self.input_y_max.text().strip())
        except: self.y_max = None

        self.locked_xlim = None
        self.locked_ylim = None
        self.reference_trigger_time = None

        self.display_raw_data(x_data, y_data)

        self.last_x_data = x_data
        self.last_y_data = y_data
        self.current_file_path = None  # to signal in-memory mode

    def load_direct_data(self, x_data, y_data, filtered=False, retake_settings=None):
        self.reference_trigger_time = None
        self.x_unit = self.unit_selector_x.currentText()
        self.y_unit = self.unit_selector_y.currentText()

        if retake_settings is not None:
            self.retake_settings = retake_settings

        self.last_x_data = x_data
        self.last_y_data = y_data
        self.current_file_path = None

        populate_table(self.tableWidget, pd.DataFrame({
            "Time": x_data,
            "Current": y_data
        }))

        # Auto-detect trigger threshold if needed
        threshold = None
        try:
            threshold = float(self.trigger_threshold.text())
        except:
            pass

        trigger_index = 0
        if threshold is not None:
            for i in range(1, len(y_data)):
                if y_data[i - 1] < threshold <= y_data[i]:
                    trigger_index = i
                    break

        trigger_time = x_data[trigger_index]
        aligned_x = [x - trigger_time for x in x_data]

        print(f"Trigger threshold: {threshold}")
        print(f"Trigger index: {trigger_index}")
        print(f"Trigger time: {trigger_time}")
        print(f"First aligned x: {aligned_x[0]:.6f}, Last: {aligned_x[-1]:.6f}")

        self.prepare_and_display_data(aligned_x, y_data)
        self.is_unsaved = True

         # Store settings if provided
        if retake_settings:
            self.retake_settings = retake_settings
            print("Retake settings received:", self.retake_settings)
        else:
            # Only disable if not previously set
            if not hasattr(self, 'retake_settings'):
                self.retake_settings = None

        # Enable or disable the button based on whether settings exist
        self.retake_button.setEnabled(self.retake_settings is not None)
    
    def setupUi(self, MainWindow):

        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(1200, 700)
        self.MainWindow = MainWindow  # Store reference to the MainWindow
        self.markers = []
        self.marker_counter = 1
        self.marker_placement_enabled = False
        self.current_marker_orientation = 'vline'  # or 'hline'
        self.dragging_marker = None
        self.dragging_event = None
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        self.ax = self.figure.add_subplot(111)  # Initialize to prevent None
        # After plot area and right controls
        self.marker_info_label = QtWidgets.QLabel("Markers will appear here")
        self.marker_info_label.setWordWrap(True)
        self.marker_info_label.setMinimumHeight(40)

        self.last_x_data = None
        self.last_y_data = None
        self.current_file_path = None  # already exists

        self.reference_trigger_time = None

        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.main_layout = QtWidgets.QHBoxLayout(self.centralwidget)

        # ========== Plot Area ==========
        self.plotFrame = QFrame(self.centralwidget)
        self.plotOuterLayout = QHBoxLayout(self.plotFrame)
        self.plotOuterLayout.setContentsMargins(0, 0, 0, 0)
        self.plotOuterLayout.setSpacing(0)

        # ----- Plot and Toolbar -----
        self.plotLayout = QVBoxLayout()
        self.plotLayout.setContentsMargins(0, 0, 0, 0)
        self.plotLayout.setSpacing(0)

        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self.plotFrame)

        self.plotLayout.addWidget(self.toolbar)
        self.plotLayout.addWidget(self.canvas)

        # ----- Marker Controls Panel -----
        self.markerControls = QVBoxLayout()

        self.enable_markers_btn = QPushButton("Placement: OFF")
        self.toggle_marker_orientation_btn = QPushButton("Vertical Marker")
        self.marker_info_label = QLabel("")
        self.clear_markers_btn = QPushButton("Clear Markers")

        self.markerControls.addWidget(self.clear_markers_btn)
        self.markerControls.addWidget(self.enable_markers_btn)
        self.markerControls.addWidget(self.toggle_marker_orientation_btn)
        self.markerControls.addWidget(self.marker_info_label)
        self.markerControls.addStretch()

        self.markerPanel = QWidget()
        self.markerPanel.setLayout(self.markerControls)
        self.markerPanel.setFixedWidth(160)

        # Replace MarkerManager logic
        self.clear_markers_btn.clicked.connect(self.clear_all_markers)
        self.enable_markers_btn.clicked.connect(self.toggle_marker_placement)
        self.toggle_marker_orientation_btn.clicked.connect(self.toggle_marker_orientation)
        self.info_output = lambda text: self.marker_info_label.setText(text)

        self.canvas.mpl_connect("pick_event", self.on_pick)
        self.canvas.mpl_connect("motion_notify_event", self.on_motion)
        self.canvas.mpl_connect("button_release_event", self.on_release)

        # Set default marker state
        self.marker_enabled = False
        self.marker_orientation = 'vline'
        self.markers = []
        self.marker_counter = 1

        # Add plot and marker panel side by side
        self.plotOuterLayout.addLayout(self.plotLayout, stretch=1)
        self.plotOuterLayout.addWidget(self.markerPanel)

        # Add to main layout
        self.main_layout.addWidget(self.plotFrame, stretch=2)

        # ========== Right Side: Table + Graph Controls ==========
        self.rightLayout = QVBoxLayout()

        self.tableWidget = QTableWidget()
        self.tableWidget.setColumnCount(2)
        self.tableWidget.setHorizontalHeaderLabels(["Parameter", "Analysis"])
        self.tableWidget.horizontalHeader().setStretchLastSection(True)
        self.rightLayout.addWidget(self.tableWidget)

        # --- Graph Controls ---
        self.controlGroup = QGroupBox("Graph Controls")
        self.controlLayout = QFormLayout(self.controlGroup)

        self.unit_selector_y = QComboBox()
        self.unit_selector_y.addItems(["uA", "mA", "A"])

        self.unit_selector_x = QComboBox()
        self.unit_selector_x.addItems(["us", "ms", "s"])

        self.input_x_div = QLineEdit(); self.input_x_div.setPlaceholderText("e.g. 100")
        self.input_y_div = QLineEdit(); self.input_y_div.setPlaceholderText("e.g. 50")

        self.input_x_min = QLineEdit(); self.input_x_max = QLineEdit()
        self.input_y_min = QLineEdit(); self.input_y_max = QLineEdit()
        for line in [self.input_x_min, self.input_x_max, self.input_y_min, self.input_y_max]:
            line.setPlaceholderText("Optional")

        self.trigger_threshold = QLineEdit()
        self.trigger_threshold.setPlaceholderText("e.g. 0.01 A")

        self.apply_btn = QPushButton("Apply")
        self.apply_btn.clicked.connect(self.apply_axis_settings)

        # --- Retake Button ---
        self.retake_button = QPushButton("Retake Measurement")
        self.retake_button.setEnabled(False)  # Initially disabled until settings exist
        self.retake_button.clicked.connect(self.retake_measurement)
        self.rightLayout.addWidget(self.retake_button)

        # --- Open Data Collect Window Button ---
        self.open_button = QPushButton("Open Data Collect Window", self.centralwidget)
        self.open_button.clicked.connect(self.open_data_collect_window)
        self.rightLayout.addWidget(self.open_button)  # Add the button to the layout below the Retake button

        # Setup the layout for the controls
        self.controlLayout.addRow("Y-axis unit:", self.unit_selector_y)
        self.controlLayout.addRow("X-axis unit:", self.unit_selector_x)
        self.controlLayout.addRow("X units/div:", self.input_x_div)
        self.controlLayout.addRow("Y units/div:", self.input_y_div)
        self.controlLayout.addRow("X min:", self.input_x_min)
        self.controlLayout.addRow("X max:", self.input_x_max)
        self.controlLayout.addRow("Y min:", self.input_y_min)
        self.controlLayout.addRow("Y max:", self.input_y_max)
        self.controlLayout.addRow("Trigger Threshold:", self.trigger_threshold)
        self.controlLayout.addRow(self.apply_btn)

        self.rightLayout.addWidget(self.controlGroup)
        self.main_layout.addLayout(self.rightLayout, stretch=1)

        MainWindow.setCentralWidget(self.centralwidget)

        # ========== Menu Bar ==========
        self.menubar = QtWidgets.QMenuBar(MainWindow)
        self.menuFile = QtWidgets.QMenu(self.menubar)
        self.actionOpen = QtWidgets.QAction("Open")
        self.actionOpen.triggered.connect(self.handle_open_action)
        self.menuFile.addAction(self.actionOpen)
        self.menubar.addMenu(self.menuFile)
        MainWindow.setMenuBar(self.menubar)

        # ========== Status Bar ==========
        self.statusbar = QtWidgets.QStatusBar(MainWindow)
        MainWindow.setStatusBar(self.statusbar)

        self.markers = []  # 🔧 store all InteractiveMarker instances here
        self.marker_counter = 1  # optional: for labeling M1, M2, etc.
        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

        # === Marker State Variables ===
        self.marker_enabled = False
        self.marker_orientation = 'vline'

        def toggle_placement():
            self.marker_enabled = not self.marker_enabled
            self.enable_markers_btn.setText(f"Placement: {'ON' if self.marker_enabled else 'OFF'}")

        def toggle_orientation():
            if self.marker_orientation == 'vline':
                self.marker_orientation = 'hline'
                self.toggle_marker_orientation_btn.setText("Horizontal Marker")
            else:
                self.marker_orientation = 'vline'
                self.toggle_marker_orientation_btn.setText("Vertical Marker")

        self.enable_markers_btn.clicked.connect(toggle_placement)
        self.toggle_marker_orientation_btn.clicked.connect(toggle_orientation)

        # === Internal State Initialization ===
        self.current_file_path = None
        self.is_unsaved = False

        self.y_unit = "mA"
        self.x_unit = "us"

        # Unit scales (for display conversions)
        self.unit_scale_y = {"uA": 1e6, "mA": 1e3, "A": 1}
        self.unit_scale_x = {"us": 1e6, "ms": 1e3, "s": 1}

        # User axis settings
        self.x_div = None
        self.y_div = None
        self.x_min = None
        self.x_max = None
        self.y_min = None
        self.y_max = None

        # Triggering and axis control
        self.reference_trigger_time = None
        self.locked_xlim = None


    def export_csv(self):
        if not hasattr(self, "last_x_data") or not hasattr(self, "last_y_data"):
            QMessageBox.warning(None, "No Data", "No data to export. Please load a file first.")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            None, "Save CSV", "", "CSV Files (*.csv)"
        )
        if not file_path:
            return

        x_scale = self.unit_scale_x.get(self.x_unit, 1)
        y_scale = self.unit_scale_y.get(self.y_unit, 1)

        try:
            with open(file_path, "w", newline="") as f:
                f.write(f"Time ({self.x_unit}),Current ({self.y_unit})\n")
                for x, y in zip(self.last_x_data, self.last_y_data):
                    f.write(f"{x * x_scale},{y * y_scale}\n")
            QMessageBox.information(None, "Success", "CSV file saved successfully.")
        except Exception as e:
            QMessageBox.warning(None, "Error", f"Failed to save CSV:\n{e}")

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "TeeSense Current Pulse Display"))
        self.menuFile.setTitle(_translate("MainWindow", "&File"))
        self.actionOpen.setText(_translate("MainWindow", "Open"))
        self.actionExportCSV = QtWidgets.QAction("Export Data as CSV")
        self.menuFile.addAction(self.actionExportCSV)
        self.actionExportCSV.triggered.connect(self.export_csv)

    def apply_axis_settings(self):
        print("apply_axis_settings called")

        self.y_unit = self.unit_selector_y.currentText()
        self.x_unit = self.unit_selector_x.currentText()

        try: self.x_div = float(self.input_x_div.text())
        except: self.x_div = None

        try: self.y_div = float(self.input_y_div.text())
        except: self.y_div = None

        try: self.x_min = float(self.input_x_min.text().strip())
        except: self.x_min = None

        try: self.x_max = float(self.input_x_max.text().strip())
        except: self.x_max = None

        try: self.y_min = float(self.input_y_min.text().strip())
        except: self.y_min = None

        try: self.y_max = float(self.input_y_max.text().strip())
        except: self.y_max = None

        print(f"🧪 Parsed X min/max: {self.x_min}, {self.x_max}")
        print(f"🧪 Parsed Y min/max: {self.y_min}, {self.y_max}")

        self.locked_xlim = None
        self.locked_ylim = None
        self.reference_trigger_time = None

        # Prioritize .csv file if loaded
        if self.current_file_path:
            if self.current_file_path.endswith('.csv'):
                print("Re-opening .csv file...")
                self.open_excel_file(self.current_file_path)
            else:
                print("current_file_path is set but not a .csv — skipping.")
        elif self.last_x_data is not None and self.last_y_data is not None:
            print("Re-triggering and redrawing direct-loaded data...")
            self.load_direct_data(self.last_x_data, self.last_y_data, )
        else:
            print("No data source available — nothing to update.")

        self.canvas.draw_idle() 

    def handle_open_action(self):
        file_path, _ = QFileDialog.getOpenFileName(None, "Open File", "", "CSV Files (*.csv);;JSON Files (*.json)")
        if file_path:
            self.current_file_path = file_path
            if file_path.endswith('.csv'):
                self.open_excel_file(file_path)
            else:
                QMessageBox.warning(None, "Error", "Unsupported file type.")

    def open_excel_file(self, file_path):
        try:
            self.x_unit = self.unit_selector_x.currentText()
            self.y_unit = self.unit_selector_y.currentText()
            data = pd.read_csv(file_path)
            populate_table(self.tableWidget, data)
            
            self.locked_ylim = None 
           
            raw_x, raw_y = generate_plot(file_path, return_raw=True)

         
            try:
                threshold = float(self.trigger_threshold.text())
            except:
                threshold = None

            
            trigger_index = 0
            if threshold is not None:
                for i in range(1, len(raw_y)):
                    if raw_y[i - 1] < threshold <= raw_y[i]:
                        trigger_index = i
                        break

            trigger_time = raw_x[trigger_index]

            
            if self.reference_trigger_time is None:
                self.reference_trigger_time = 0

            
            aligned_x = [x - trigger_time for x in raw_x]
            
            print(f"x_unit: {self.x_unit}")
            print(f"x_scale: {self.unit_scale_x.get(self.x_unit, 1)}")
            print(f"x range (raw): {min(raw_x)} to {max(raw_x)}")
            print(f"x range (scaled): {[min(raw_x)*self.unit_scale_x.get(self.x_unit,1), max(raw_x)*self.unit_scale_x.get(self.x_unit,1)]}")
            self.display_raw_data(aligned_x, raw_y)
            self.is_unsaved = True

        except Exception as e:
            QMessageBox.warning(None, "Error", f"Could not load CSV file:\n{e}")


    def display_raw_data(self, x_data, y_data):
        self.figure.clear()
        self.ax = self.figure.add_subplot(111)
        self.ax.set_title("Current Pulse Data")

        self.last_x_data = x_data
        self.last_y_data = y_data

        x_scale = self.unit_scale_x.get(self.x_unit, 1)
        y_scale = self.unit_scale_y.get(self.y_unit, 1)
        x = [v * x_scale for v in x_data]
        y = [v * y_scale for v in y_data]

        self.ax.plot(x, y, label="Pulse", linestyle='-', marker='o')
        self.ax.set_xlabel(f"Time ({self.x_unit})")
        self.ax.set_ylabel(f"Current ({self.y_unit})")
        self.ax.grid(True)
        self.ax.legend()

        # --- X Axis ---
        final_x_min, final_x_max = self.compute_axis_limits(
            x, self.x_min, self.x_max, self.x_div, "X", is_x_axis=True
        )
        self.ax.set_xlim(final_x_min, final_x_max)
        self.locked_xlim = (final_x_min, final_x_max)

        if self.x_div and (self.x_min is None or self.x_max is None):
            min_x, max_x = self.ax.get_xlim()
            start_tick = (min_x // self.x_div) * self.x_div
            end_tick = (max_x // self.x_div + 20) * self.x_div
            ticks = []
            val = start_tick
            while val <= end_tick:
                ticks.append(val)
                val += self.x_div
            self.ax.set_xticks(ticks)

        # --- Y Axis ---
        final_y_min, final_y_max = self.compute_axis_limits(
            y, self.y_min, self.y_max, self.y_div, "Y", is_x_axis=False
        )
        self.ax.set_ylim(final_y_min, final_y_max)
        self.locked_ylim = (final_y_min, final_y_max)

        if self.y_div and (self.y_min is None or self.y_max is None):
            min_y, max_y = self.ax.get_ylim()
            start_tick = (min_y // self.y_div) * self.y_div
            end_tick = (max_y // self.y_div + 20) * self.y_div
            ticks = []
            val = start_tick
            while val <= end_tick:
                ticks.append(val)
                val += self.y_div
            self.ax.set_yticks(ticks)

        # --- Redraw Markers on Fresh Axes ---
        new_markers = []
        for old_marker in self.markers:
            m = InteractiveMarker(self.ax, old_marker.orientation, old_marker.position, old_marker.label)
            new_markers.append(m)
        self.markers = new_markers

        # Reconnect click handler to new canvas/axes
        self.canvas.mpl_disconnect(getattr(self, '_marker_click_cid', None))
        self._marker_click_cid = self.canvas.mpl_connect("button_press_event", self.on_click)
        self.canvas.mpl_disconnect(getattr(self, "_click_cid", None))
        self.canvas.mpl_disconnect(getattr(self, "_release_cid", None))
        self.canvas.mpl_disconnect(getattr(self, "_motion_cid", None))

        self._click_cid = self.canvas.mpl_connect("button_press_event", self.on_click)
        self._release_cid = self.canvas.mpl_connect("button_release_event", self.on_release)
        self._motion_cid = self.canvas.mpl_connect("motion_notify_event", self.on_motion)

        self.canvas.draw_idle() 
        

    def compute_axis_limits(self, data, min_val, max_val, units_per_div, label, is_x_axis=True):
        NUM_DIVS = 10
        data_min, data_max = min(data), max(data)
        center = (data_min + data_max) / 2

        if min_val is not None and max_val is not None:
            axis_min = min_val
            axis_max = max_val
            reason = "manual min/max"
        elif units_per_div is not None:
            half_range = (units_per_div * NUM_DIVS) / 2
            axis_min = center - half_range
            axis_max = center + half_range
            reason = f"{units_per_div} units/div"
        else:
            span = data_max - data_min
            pad = span * 0.05
            axis_min = data_min - pad
            axis_max = data_max + pad
            reason = "auto"

        print(f"Using {reason} for {label}: {axis_min} to {axis_max}")
        return axis_min, axis_max

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

class InteractiveMarker:
    def __init__(self, ax, orientation, position, label="M", color='r'):
        self.ax = ax
        self.orientation = orientation
        self.position = position
        self.label = label
        self.color = color

        if orientation == 'vline':
            self.line = ax.axvline(position, color=color, linestyle='-', linewidth=1.5, picker=True)
            self.text = ax.text(position, ax.get_ylim()[1], label, color=color, fontsize=9,
                                ha='left', va='top', backgroundcolor='white')
        else:
            self.line = ax.axhline(position, color='b', linestyle='-', linewidth=1.5, picker=True)
            self.text = ax.text(ax.get_xlim()[1], position, label, color='b', fontsize=9,
                                ha='right', va='bottom', backgroundcolor='white')

        self.dragging = False

    def update_position(self, new_pos):
        self.position = new_pos
        if self.orientation == 'vline':
            self.line.set_xdata([new_pos, new_pos])
            self.text.set_position((new_pos, self.ax.get_ylim()[1]))
        else:
            self.line.set_ydata([new_pos, new_pos])
            self.text.set_position((self.ax.get_xlim()[1], new_pos))

    def remove(self):
        self.line.remove()
        self.text.remove()

class MarkerManager:
    def reconnect(self):
        self.canvas.mpl_disconnect(self.cid_click)
        self.canvas.mpl_disconnect(self.cid_release)
        self.canvas.mpl_disconnect(self.cid_motion)
        self.canvas.mpl_disconnect(self.cid_pick)

        self.cid_click = self.canvas.mpl_connect('button_press_event', self.on_click)
        self.cid_release = self.canvas.mpl_connect('button_release_event', self.on_release)
        self.cid_motion = self.canvas.mpl_connect('motion_notify_event', self.on_motion)
        self.cid_pick = self.canvas.mpl_connect('pick_event', self.on_pick)
    
    def __init__(self, canvas, ax):
        self.marker_counter = 1
        self.canvas = canvas
        self.ax = ax
        self.markers = []
        self.active_marker = None
        self.cid_click = self.canvas.mpl_connect('button_press_event', self.on_click)
        self.cid_release = self.canvas.mpl_connect('button_release_event', self.on_release)
        self.cid_motion = self.canvas.mpl_connect('motion_notify_event', self.on_motion)
        self.cid_pick = self.canvas.mpl_connect('pick_event', self.on_pick)

    def extract_unit(self, label: str) -> str:
        """Extracts unit from axis label like 'Time (us)' → 'us'"""
        if '(' in label and ')' in label:
            return label.split('(')[-1].split(')')[0]
        return ''

    def clear_all_markers(self):
        for marker in self.markers:
            marker.remove()
        self.markers.clear()
        self.marker_counter = 1
        self.update_marker_labels()
        self.canvas.draw_idle()

    def set_mode_callback(self, fn):
        self.enable_check = fn

    def set_orientation_callback(self, fn):
        self.orientation_check = fn

    def set_info_callback(self, fn):
        self.info_output = fn

    def on_click(self, event: MouseEvent):
        print(f"Click at ({event.xdata}, {event.ydata})")  # Debug
        if not event.inaxes or not self.enable_check():
            return

        if event.button == 1:  # Left click → add marker
            orientation = self.orientation_check()
            position = event.xdata if orientation == 'vline' else event.ydata
            marker_label = f"M{self.marker_counter}"
            marker = InteractiveMarker(self.ax, orientation, position, label=marker_label)
            print(f"Added {orientation} marker at {position}")
            print(f"Axes title: {self.ax.get_title()}")
            print(f"Line object: {marker.line}")
            self.marker_counter += 1
            self.markers.append(marker)

            # Update marker labels
            self.update_marker_labels()

            self.canvas.draw_idle()

        elif event.button == 3:
            for marker in self.markers:
                if marker.line.contains(event)[0]:
                    marker.remove()
                    self.markers.remove(marker)
                    self.active_marker = None  # Ensure drag state is cleared
                    self.canvas.draw_idle()
                    self.update_marker_labels()
                    break

    def on_pick(self, event):
        for marker in self.markers:
            if marker.line == event.artist:
                marker.dragging = True
                self.active_marker = marker
                break

    def on_release(self, event):
        if self.active_marker:
            self.active_marker.dragging = False
            self.active_marker = None

    def on_motion(self, event):
        if self.active_marker and event.inaxes:
            new_pos = event.xdata if self.active_marker.orientation == 'vline' else event.ydata
            self.active_marker.update_position(new_pos)
            self.canvas.draw_idle()

            # Update the label live
            self.update_marker_labels()

    def update_marker_labels(self):
        if not hasattr(self, 'info_output'):
            return

        x_unit = self.extract_unit(self.ax.get_xlabel())
        y_unit = self.extract_unit(self.ax.get_ylabel())

        text_lines = []
        for m in self.markers:
            unit = x_unit if m.orientation == 'vline' else y_unit
            text_lines.append(f"{m.label}: {m.position:.4f} {unit}")
        self.info_output("\n".join(text_lines))

if __name__ == "__main__":
    app = QtWidgets.QApplication(sys.argv)
    MainWindow = QtWidgets.QMainWindow()
    ui = Ui_MainWindow()
    ui.setupUi(MainWindow)
    MainWindow.setWindowTitle("TeeSense Current Pulse Display")
    MainWindow.show()
    sys.exit(app.exec_())
