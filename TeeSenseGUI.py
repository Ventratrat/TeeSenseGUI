from PyQt5 import QtCore, QtWidgets
from PyQt5.QtWidgets import QFileDialog, QMessageBox, QVBoxLayout, QFrame, QComboBox, QLineEdit, QGroupBox, QPushButton, QFormLayout, QLabel, QHBoxLayout, QWidget, QTableWidget, QSpinBox
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure
from matplotlib.ticker import MultipleLocator
import matplotlib.pyplot as plt
from csvRead import *
import pandas as pd
import numpy as np
import sys
import serial
import serial.tools.list_ports
import traceback
import time
from dataCollect import *


class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(1100, 600)

        self.centralwidget = QtWidgets.QWidget(MainWindow)
        self.main_layout = QtWidgets.QHBoxLayout(self.centralwidget)

        # ======= Plot Frame =======
        self.plotFrame = QFrame(self.centralwidget)
        self.plotLayout = QVBoxLayout(self.plotFrame)
        self.figure = Figure()
        self.canvas = FigureCanvas(self.figure)
        self.toolbar = NavigationToolbar(self.canvas, self.plotFrame)
        self.plotLayout.addWidget(self.toolbar)
        self.plotLayout.addWidget(self.canvas)

        # Add marker controls
        self.markerPanel = QWidget()
        self.markerControls = QHBoxLayout(self.markerPanel)
        self.enable_markers_btn = QPushButton("Placement: OFF")
        self.toggle_marker_orientation_btn = QPushButton("Vertical Marker")
        self.clear_markers_btn = QPushButton("Clear Markers")
        self.marker_info_label = QLabel("")

        self.markerControls.addWidget(self.enable_markers_btn)
        self.markerControls.addWidget(self.toggle_marker_orientation_btn)
        self.markerControls.addWidget(self.clear_markers_btn)
        self.markerControls.addWidget(self.marker_info_label)
        self.markerControls.addStretch()
        self.markerPanel.setFixedWidth(500)

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

        self.marker_manager = MarkerManager(self.canvas, self.figure.gca())
        self.clear_markers_btn.clicked.connect(lambda: self.marker_manager.clear_all_markers())
        self.marker_manager.set_mode_callback(lambda: self.marker_enabled)
        self.marker_manager.set_orientation_callback(lambda: self.marker_orientation)
        self.marker_manager.set_info_callback(lambda text: self.marker_info_label.setText(text))

        self.plotLayout.addWidget(self.markerPanel)
        self.main_layout.addWidget(self.plotFrame, 2)

        # ======= Table and Controls =======
        self.rightLayout = QtWidgets.QVBoxLayout()

        self.tableWidget = QTableWidget(self.centralwidget)
        self.tableWidget.setColumnCount(2)
        self.tableWidget.setHorizontalHeaderLabels(["Parameter", "Analysis"])
        self.tableWidget.horizontalHeader().setStretchLastSection(True)
        self.rightLayout.addWidget(self.tableWidget)

        # ======= Controls =======
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
        
        self.recollect_btn = QPushButton("Recollect Data")
        self.recollect_btn.clicked.connect(self.recollect_data)
        self.controlLayout.addRow(self.recollect_btn)
        self.zero_offset_btn = QPushButton("Zero Offset")
        self.zero_offset_btn.clicked.connect(self.apply_zero_offset)
        self.controlLayout.addRow(self.zero_offset_btn)
        
        self.sample_count_spin = QSpinBox()
        self.sample_count_spin.setRange(10, 10000)  # Reasonable range
        self.sample_count_spin.setValue(200)  # Default value
        self.controlLayout.addRow("Sample Count:", self.sample_count_spin)

        self.rightLayout.addWidget(self.controlGroup)
        self.main_layout.addLayout(self.rightLayout, 1)
        MainWindow.setCentralWidget(self.centralwidget)

        # ======= Menu Bar =======
        self.menubar = QtWidgets.QMenuBar(MainWindow)
        self.menuFile = QtWidgets.QMenu(self.menubar)
        self.actionOpen = QtWidgets.QAction("Open")
        self.actionExportCSV = QtWidgets.QAction("Export Data as CSV")
        self.menuFile.addAction(self.actionOpen)
        self.menuFile.addAction(self.actionExportCSV)
        self.menubar.addMenu(self.menuFile)

        self.menuAnalysis = QtWidgets.QMenu(self.menubar)
        self.actionFilteringWindow = QtWidgets.QAction("Filtering Window")
        self.actionDCBias = QtWidgets.QAction("DC Bias")
        self.menuAnalysis.addAction(self.actionFilteringWindow)
        self.menuAnalysis.addAction(self.actionDCBias)
        self.menubar.addMenu(self.menuAnalysis)

        MainWindow.setMenuBar(self.menubar)

        self.statusbar = QtWidgets.QStatusBar(MainWindow)
        MainWindow.setStatusBar(self.statusbar)

        self.actionOpen.triggered.connect(self.handle_open_action)
        self.actionExportCSV.triggered.connect(self.export_csv)
        self.actionFilteringWindow.triggered.connect(self.handle_filtering_window)
        self.actionDCBias.triggered.connect(self.handle_dc_bias)

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
        self.reference_trigger_time = None

        self.retranslateUi(MainWindow)
        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def apply_axis_settings(self):
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

        self.locked_xlim = None
        self.locked_ylim = None
        self.reference_trigger_time = None

        if self.current_file_path and self.current_file_path.endswith('.csv'):
            self.open_excel_file(self.current_file_path)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "TeeSense Current Pulse Display"))
        self.menuFile.setTitle(_translate("MainWindow", "&File"))
        self.menuAnalysis.setTitle(_translate("MainWindow", "&Analysis"))
        self.actionOpen.setText(_translate("MainWindow", "Open"))
        self.actionExportCSV.setText(_translate("MainWindow", "Export Data as CSV"))
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

        if self.x_min is not None and self.x_max is not None:
            ax.set_xlim(self.x_min, self.x_max)
        if self.y_min is not None and self.y_max is not None:
            ax.set_ylim(self.y_min, self.y_max)

        if self.x_div:
            min_x, max_x = ax.get_xlim()
            ax.set_xticks([min_x + i * self.x_div for i in range(int((max_x - min_x) / self.x_div) + 1)])
        if self.y_div:
            min_y, max_y = ax.get_ylim()
            ax.set_yticks([min_y + i * self.y_div for i in range(int((max_y - min_y) / self.y_div) + 1)])

        self.canvas.draw()

    def open_excel_file(self, file_path):
        try:
            data = pd.read_csv(file_path)
            populate_table(self.tableWidget, data)
            figure = generate_plot(file_path)
            self.display_matplotlib_graph(figure)
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
            self.display_raw_data(aligned_x, raw_y)

            # --- rebind markers to new plot ---
            new_ax = self.figure.axes[0]
            self.marker_manager.ax = new_ax
            self.marker_manager.markers.clear()
            self.marker_manager.marker_counter = 1
            if hasattr(self.marker_manager, 'info_output'):
                self.marker_manager.info_output("")

            self.is_unsaved = True
        except Exception as e:
            QMessageBox.warning(None, "Error", f"Could not load CSV file:\n{e}")

    def display_raw_data(self, x_data, y_data):
        self.figure.clear()
        ax = self.figure.add_subplot(111)
        ax.set_title("Current Pulse Data")

        self.last_x_data = x_data
        self.last_y_data = y_data

        x_scale = self.unit_scale_x.get(self.x_unit, 1)
        y_scale = self.unit_scale_y.get(self.y_unit, 1)
        x = [v * x_scale for v in x_data]
        y = [v * y_scale for v in y_data]

        ax.plot(x, y, label="Pulse", linestyle='-', marker='o')
        ax.set_xlabel(f"Time ({self.x_unit})")
        ax.set_ylabel(f"Current ({self.y_unit})")
        ax.grid(True)
        ax.legend()

        # --- X Axis ---
        final_x_min, final_x_max = self.compute_axis_limits(
            x, self.x_min, self.x_max, self.x_div, "X", is_x_axis=True
        )
        ax.set_xlim(final_x_min, final_x_max)
        self.locked_xlim = (final_x_min, final_x_max)

        if self.x_div and (self.x_min is None or self.x_max is None):
            min_x, max_x = ax.get_xlim()
            start_tick = (min_x // self.x_div) * self.x_div
            end_tick = (max_x // self.x_div + 20) * self.x_div  # extend beyond visible range

            ticks = []
            val = start_tick
            while val <= end_tick:
                ticks.append(val)
                val += self.x_div
            if self.x_div and (self.x_min is None or self.x_max is None):
                ax.xaxis.set_major_locator(MultipleLocator(self.x_div))

        # --- Y Axis ---
        final_y_min, final_y_max = self.compute_axis_limits(
            y, self.y_min, self.y_max, self.y_div, "Y", is_x_axis=False
        )
        ax.set_ylim(final_y_min, final_y_max)
        self.locked_ylim = (final_y_min, final_y_max)

        if self.y_div and (self.y_min is None or self.y_max is None):
            min_y, max_y = ax.get_ylim()
            start_tick = (min_y // self.y_div) * self.y_div
            end_tick = (max_y // self.y_div + 20) * self.y_div  # extend above view

            ticks = []
            val = start_tick
            while val <= end_tick:
                ticks.append(val)
                val += self.y_div
            if self.y_div and (self.y_min is None or self.y_max is None):
                ax.yaxis.set_major_locator(MultipleLocator(self.y_div))

        self.canvas.draw()

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

        print(f"📊 Using {reason} for {label}: {axis_min} to {axis_max}")
        return axis_min, axis_max


    def handle_open_action(self):
        file_path, _ = QFileDialog.getOpenFileName(None, "Open File", "", "CSV Files (*.csv);;JSON Files (*.json)")
        if file_path:
            self.current_file_path = file_path
            if file_path.endswith('.csv'):
                self.open_excel_file(file_path)
            else:
                QMessageBox.warning(None, "Error", "Unsupported file type.")

    def export_csv(self):

        # Get the figure and axis from the plot (assuming it's the first axis in the figure)
        figure = plt.gcf()  # Get current figure
        ax = figure.gca()  # Get the current axis

        # Check if the axis has any lines (plots) and get data from them
        lines = ax.get_lines()
        if not lines:
            QMessageBox.warning(None, "No Data", "No data to export from the plot.")
            return

        # If there are multiple lines, you may want to export the data for each
        # We'll assume you're interested in the data from the first line here
        x_data, y_data = lines[0].get_data()

        # Apply unit scaling if necessary
        x_scale = self.unit_scale_x.get(self.x_unit, 1)
        y_scale = self.unit_scale_y.get(self.y_unit, 1)

        # Prompt the user to choose a file location to save the CSV
        file_path, _ = QFileDialog.getSaveFileName(
            None, "Save CSV", "", "CSV Files (*.csv)"
        )
        if not file_path:
            return

        try:
            # Open the file and write data to it
            with open(file_path, "w", newline="") as f:
                f.write(f"Time ({self.x_unit}),Current ({self.y_unit})\n")  # CSV header
                for x, y in zip(x_data, y_data):
                    f.write(f"{x * x_scale},{y * y_scale}\n")
            
            QMessageBox.information(None, "Success", "CSV file saved successfully.")
        except Exception as e:
            QMessageBox.warning(None, "Error", f"Failed to save CSV:\n{e}")

    def moving_average(self, data, window_size=3):
        if window_size < 1:
            return data
        padded = np.pad(data, (window_size//2, window_size-1-window_size//2), mode='edge')
        return np.convolve(padded, np.ones(window_size)/window_size, mode='valid').tolist()


    def handle_filtering_window(self):
        if not self.figure.axes:
            QMessageBox.warning(None, "Filtering Error", "No data to filter.")
            return

        window_size, ok = QtWidgets.QInputDialog.getInt(None, "Moving Average Filter", "Enter window size:", min=1, value=3)
        if not ok:
            return

        ax = self.figure.axes[0]
        filtered_figure = Figure()
        new_ax = filtered_figure.add_subplot(111)

        for line in ax.lines:
            x_data = line.get_xdata()
            y_data = line.get_ydata()
            filtered_y = self.moving_average(y_data, window_size)

            # Keep x_data same length as y_data
            if len(filtered_y) != len(x_data):
                delta = len(x_data) - len(filtered_y)
                if delta > 0:
                    x_data = x_data[delta//2 : -((delta+1)//2)]
                elif delta < 0:
                    filtered_y = filtered_y[:len(x_data)]

            new_ax.plot(x_data, filtered_y, label=f"{line.get_label()}", linestyle='-', marker='')

        self.display_matplotlib_graph(filtered_figure)

    def handle_dc_bias(self):
        try:
            ax = self.figure.axes[0]

            all_y_values = []

            for line in ax.lines:
                y_data = line.get_ydata()
                all_y_values.extend(y_data)

            if not all_y_values:
                QMessageBox.warning(None, "DC Bias", "No data available to display DC bias.")
                return

            # Calculate average (DC bias level)
            dc_bias_value = sum(all_y_values) / len(all_y_values)


            ax.clear()
            for line in self.figure.axes[0].lines:
                ax.plot(line.get_xdata(), line.get_ydata(), label=line.get_label(), linestyle='--', alpha=0.4)

            # Plot a horizontal line at the DC level
            ax.axhline(dc_bias_value, color='g', linestyle='--', linewidth=2, label=f"DC Bias: {dc_bias_value:.2f} {self.y_unit}")
            ax.set_title("DC Bias Display Mode")
            ax.set_xlabel(f"Time ({self.x_unit})")
            ax.set_ylabel(f"Current ({self.y_unit})")
            ax.grid()
            ax.legend()
            self.canvas.draw()

        except Exception as e:
            QMessageBox.warning(None, "DC Bias Error", f"Error applying DC bias mode:\n{e}")
            
    def recollect_data(self):
        try:
             # Get sample count from UI
             sample_count = self.sample_count_spin.value()
             print(f"Attempting to collect {sample_count} samples")

             # Case 1: Use existing connection if available
             if hasattr(self, 'ser') and self.ser and self.ser.is_open:
                  print(f"Reusing existing connection to {self.serial_port}")

            # Case 2: Try to auto-detect from dataCollect.py (if running)
             elif 'ser' in globals() and hasattr(globals()['ser'], 'is_open') and globals()['ser'].is_open:
                 self.serial_port = globals()['ser'].port
                 self.ser = globals()['ser']
                 print(f"User chosen connection : {self.serial_port}")
        
             # Case 3: Manual port selection
             else:
                ports = self.scan_serial_ports()
                if not ports:
                    raise ValueError("No serial ports detected")
            
                port, ok = QtWidgets.QInputDialog.getItem(
                    None, "Select Port", "Available COM ports:", ports, 0, False
                )
                if not ok:
                    return
            
                self.serial_port = port
                self.ser = serial.Serial(port, 115200, timeout=1)
                print(f"Manually connected to {port}")

             # Verify connection
             if not self.ser.is_open:
                raise ValueError(f"Failed to connect to {self.serial_port}")
        
            # Initialize data collection
             collected_data = []
             start_time = time.time()
        
             # Collect data until we reach sample count
             while len(collected_data) < sample_count:
                if self.ser.in_waiting:
                    line = self.ser.readline().decode('utf-8').strip()
                    if line:  # Only process non-empty lines
                        try:
                            # Assuming data comes as comma-separated values (time, current)
                             time_val, current_val = map(float, line.split(','))
                             collected_data.append((time_val, current_val))
                        
                            # Update status every 10 samples
                             if len(collected_data) % 10 == 0:
                                self.statusbar.showMessage(
                                     f"Collected {len(collected_data)}/{sample_count} samples", 
                                     1000
                                )
                                QtWidgets.QApplication.processEvents()  # Keep UI responsive
                            
                        except ValueError as e:
                             print(f"Error parsing line: {line} - {str(e)}")
        
             # Create DataFrame from collected data
             df = pd.DataFrame(collected_data, columns=['Time', 'Current'])
        
             if df.empty:
                raise ValueError("No valid data was collected")
        
             # Update UI
             populate_table(self.tableWidget, df)
             figure = generate_plot(dataframe=df)
        
             if hasattr(self, 'current_figure'):
                 plt.close(self.current_figure)
        
             self.display_matplotlib_graph(figure)
             self.current_figure = figure
        
             # Show completion message
             elapsed = time.time() - start_time
             msg = f"Collected {len(df)} samples in {elapsed:.2f} seconds"
             self.statusbar.showMessage(msg, 5000)
             QMessageBox.information(None, "Success", msg)

        except ValueError as e:
            QMessageBox.warning(None, "Data Error", str(e))
        except Exception as e:
            QMessageBox.critical(None, "Error", f"Failed to collect data:\n{str(e)}")
            print(f"Error traceback:\n{traceback.format_exc()}")
        finally:
         # Don't close serial connection - keep it open for future use
          pass
      
    def scan_serial_ports(self):
        """Scan for available serial ports"""
        ports = serial.tools.list_ports.comports()
        return [port.device for port in ports]
    
    def apply_zero_offset(self):
        try:
            if not hasattr(self, 'last_y_data') or not self.last_y_data:
                QMessageBox.warning(None, "Zero Offset", "No data available to offset.")
                return

            # Calculate 5th percentile baseline
            baseline_offset = np.percentile(self.last_y_data, 5)
            adjusted_y = [val - baseline_offset for val in self.last_y_data]

            # Update the internal reference
            self.last_y_data = adjusted_y

            # Redraw graph
            self.display_raw_data(self.last_x_data, self.last_y_data)
            self.statusbar.showMessage("Baseline offset applied.", 3000)

        except Exception as e:
            QMessageBox.critical(None, "Error", f"Failed to apply zero offset:\n{e}")


class MarkerManager:
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

    def clear_all_markers(self):
        for marker in self.markers:
            marker.remove()
        self.markers.clear()
        self.marker_counter = 1
        if hasattr(self, 'info_output'):
            self.info_output("")  # clear label
        self.canvas.draw_idle()

    def set_mode_callback(self, fn):
        self.enable_check = fn

    def set_orientation_callback(self, fn):
        self.orientation_check = fn

    def set_info_callback(self, fn):
        self.info_output = fn

    def on_click(self, event):
        if not event.inaxes or not self.enable_check():
            return

        if event.button == 1:
            orientation = self.orientation_check()
            
            if orientation == 'vline':
                position = event.xdata 
            else:
                position = event.ydata 
            marker_label = f"M{self.marker_counter}"
            
            marker = InteractiveMarker(self.ax, orientation, position, label=marker_label)
            self.marker_counter += 1
            self.markers.append(marker)
            
            if hasattr(self, 'info_output'):
                text_lines = []
                for m in self.markers:
                    x_label = self.ax.get_xlabel() if self.ax.get_xlabel() else "Time"
                    y_label = self.ax.get_ylabel() if self.ax.get_ylabel() else "Current"
                    
                    unit = x_label.split()[-1] if m.orientation == 'vline' else y_label.split()[-1]
                    text_lines.append(f"{m.label}: {m.position:.4f} {unit}")

                self.info_output("\n".join(text_lines))

            self.canvas.draw_idle()

        elif event.button == 3:
            for marker in self.markers:
                if marker.line.contains(event)[0]:
                    marker.remove()  
                    self.markers.remove(marker)
                    self.canvas.draw_idle() 
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

            # ✅ Update the label live
            if hasattr(self, 'info_output'):
                text_lines = []
                for m in self.markers:
                    unit = self.ax.get_xlabel().split()[-1] if m.orientation == 'vline' else self.ax.get_ylabel().split()[-1]
                    text_lines.append(f"{m.label}: {m.position:.4f} {unit}")
                self.info_output("\n".join(text_lines))


class InteractiveMarker:
    def __init__(self, ax, orientation, position, label):
        self.ax = ax
        self.orientation = orientation  # 'vline' or 'hline'
        self.position = position
        self.label = label
        self.dragging = False

        if self.orientation == 'vline':
            self.line = ax.axvline(x=position, color='r', linestyle='--', label=self.label, picker=5)
        else:
            self.line = ax.axhline(y=position, color='b', linestyle='--', label=self.label, picker=5)

    def update_position(self, new_pos):
        self.position = new_pos
        if self.orientation == 'vline':
            self.line.set_xdata([new_pos, new_pos])
        else:
            self.line.set_ydata([new_pos, new_pos])

    def remove(self):
        self.line.remove()


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
