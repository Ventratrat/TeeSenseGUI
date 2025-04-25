import csv
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import FuncFormatter
from PyQt5 import QtWidgets

def generate_plot(csv_file):
    x = []
    y = []

    with open(csv_file, 'r', encoding='utf-8-sig') as csvfile: 
        reader = csv.reader(csvfile, delimiter=',')
        next(reader, None) 
        for row in reader: 
            try:
                x_val = float(row[0])
                y_val = float(row[1])
                x.append(x_val)
                y.append(y_val)
            except ValueError:
                print(f"Skipping invalid row: {row}")

    if len(x) == 0 or len(y) == 0:
        raise ValueError("No valid data found in the CSV file.")

    # --- Correcting for negative offset --- 
    negative_offset = np.mean([val for val in y if val < 0]) if any(val < 0 for val in y) else 0
    y = [val - negative_offset for val in y]  # Shift all data by the negative offset

    x_min, x_max = min(x), max(x)
    y_min, y_max = min(y), max(y)

    x_margin = (x_max - x_min) * 0.1 
    x_range = x_max - x_min
    y_range = y_max - y_min

    x_step = 10 ** np.floor(np.log10(x_range / 10))  
    y_step = 10 ** np.floor(np.log10(y_range / 10))

    y_min_adjusted = y_min - y_step if y_min - y_step > 0 else 0
    y_max_adjusted = y_max + y_step
    figure, ax = plt.subplots()
    ax.plot(x, y, color='g', linestyle='dashed', marker='o', label="Current")

    ax.set_xlim(x_min - x_margin, x_max + x_margin)
    ax.set_ylim(y_min_adjusted, y_max_adjusted) 
    ax.set_xticks(np.arange(0, x_max + x_margin, step=x_step))
    ax.set_yticks(np.arange(y_min_adjusted, y_max_adjusted, step=y_step))

    ax.set_xlabel('Input') 
    ax.set_ylabel('Output') 
    ax.set_title('Current Pulse Data', fontsize=20) 
    ax.grid() 
    ax.legend()

    def scientific_formatter(value, tick_position):
        if value > 1000 or value < 0.01:
            return f'{value:.1e}'
        else:
            return f'{value:.2f}'

    ax.xaxis.set_major_formatter(FuncFormatter(scientific_formatter))
    ax.yaxis.set_major_formatter(FuncFormatter(scientific_formatter))

    return figure


def calculate_parameters(data):
    """Calculates key electrical parameters from a numerical signal dataset."""
    if data.empty:
        return None

    numeric_cols = data.select_dtypes(include=['number'])
    if numeric_cols.shape[1] < 2: 
        return None

    # Sort the data by time to avoid negative durations
    data = data.sort_values(by=data.columns[0]).reset_index(drop=True)
    numeric_cols = data.select_dtypes(include=['number'])

    time_data = numeric_cols.iloc[:, 0]  # time in seconds
    column_data = numeric_cols.iloc[:, 1]  # current

    negative_offset = column_data[column_data < 0].mean() if column_data[column_data < 0].any() else 0
    column_data = column_data - negative_offset  # Shift all data by the negative offset

    # --- Max Current Analysis ---
    threshold = 0.8 * column_data.max()
    data_for_max = column_data[column_data >= threshold]
    average_max_current = data_for_max.mean() * 1e6  # in µA
    indices_to_exclude = data_for_max.index

    # --- Min Current Analysis ---
    filtered_data_for_min = column_data.drop(indices_to_exclude)
    average_min_current = filtered_data_for_min.rolling(window=5).min().mean() * 1e6  # in µA

    # --- Overshoot ---
    overshoot = (column_data.max() * 1e6) - average_max_current

    # --- Pulse Width (in µs) ---
    pulse_durations = []
    in_pulse = False
    pulse_start_time = None

    for i in range(1, len(column_data) - 1):
        prev = column_data.iloc[i - 1]
        curr = column_data.iloc[i]
        next_val = column_data.iloc[i + 1]
        current_time = time_data.iloc[i]

        # Detect rising edge start
        if not in_pulse and curr > prev and curr >= next_val:
            in_pulse = True
            pulse_start_time = current_time

        # Detect falling edge end
        elif in_pulse and curr < prev and curr <= next_val:
            in_pulse = False
            pulse_end_time = current_time
            duration_us = (pulse_end_time - pulse_start_time) * 1e7
            if duration_us > 0:
                pulse_durations.append(duration_us)

    pulse_width = np.mean(pulse_durations) if pulse_durations else 0



    # --- RMS Current ---
    current_rms = np.sqrt(np.mean(column_data**2)) * 1e6  # µA

    # --- Settling Time ---
    settling_threshold = 0.02 * (average_max_current / 1e6)  # 2% in original units
    final_value = average_max_current / 1e6  # convert to original unit
    lower_bound = final_value - settling_threshold
    upper_bound = final_value + settling_threshold

    settling_time = 0
    in_settling = False

    for i in range(len(column_data)):
        if in_settling:
            if lower_bound <= column_data.iloc[i] <= upper_bound:
                settling_time = time_data.iloc[i] - pulse_start_time
                break
        elif i > 0 and column_data.iloc[i] > column_data.iloc[i - 1]:
            # Detect rising edge (start of pulse)
            pulse_start_time = time_data.iloc[i]
            in_settling = True

    settling_time_us = settling_time * 1e6 if settling_time else 0  # Convert to µs

    # --- Return results ---
    return {
        "Average Maximum Current": f"{average_max_current:.4f} µA",
        "Average Minimum Current": f"{average_min_current:.4f} µA",
        "Overshoot": f"{overshoot:.4f} µA",
        "Pulse Width": f"{pulse_width:.4f} µs",
        "Current RMS": f"{current_rms:.4f} µA",
        "Settling Time": f"{settling_time:.4f} µs"
    }


def populate_table(tableWidget, data):
    """Populates a QTableWidget with predefined current parameters."""
    stats = calculate_parameters(data)
    if not stats:
        QtWidgets.QMessageBox.warning(None, "Error", "No numerical data found in the file.")
        return

    tableWidget.setRowCount(len(stats))
    tableWidget.setColumnCount(2)
    tableWidget.setHorizontalHeaderLabels(["Parameter", "Value"])

    for row, (param, value) in enumerate(stats.items()):
        tableWidget.setItem(row, 0, QtWidgets.QTableWidgetItem(param))  
        tableWidget.setItem(row, 1, QtWidgets.QTableWidgetItem(value))

    tableWidget.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)