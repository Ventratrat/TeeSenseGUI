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
    y = [val - negative_offset for val in y] 

    x_min, x_max = min(x), max(x)
    y_min, y_max = min(y), max(y)

    x_range = x_max - x_min
    y_range = y_max - y_min

    x_step = 10 ** np.floor(np.log10(x_range / 10))  
    y_step = 10 ** np.floor(np.log10(y_range / 10))

    y_min_adjusted = y_min - y_step if y_min - y_step > 0 else 0
    y_max_adjusted = y_max + y_step
    figure, ax = plt.subplots()
    ax.plot(x, y, color='g', linestyle='dashed', marker='o', label="Current")

    ax.set_xlim(0, x_max + x_step)
    ax.set_ylim(y_min_adjusted, y_max_adjusted) 

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

def format_current(value_in_uA):
    """Converts a value in µA to an appropriate unit (µA, mA, A) with formatting."""
    if value_in_uA / 1_000_000 >= 1:
        return f"{value_in_uA / 1_000_000:.4f} A"
    elif value_in_uA / 1_000 >= 1:
        return f"{value_in_uA / 1_000:.4f} mA"
    else:
        return f"{value_in_uA:.4f} µA"


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
    threshold = 0.7 * column_data.max()
    data_for_max = column_data[column_data >= threshold]
    average_max_current = data_for_max.mean() * 1e6  # in µA
    indices_to_exclude = data_for_max.index

    # --- Min Current Analysis ---
    filtered_data_for_min = column_data.drop(indices_to_exclude)
    average_min_current = filtered_data_for_min.rolling(window=5).min().mean() * 1e6  # in µA

    # --- Overshoot ---
    in_pulse = False
    pulse_start_time = None
    pulse_end_index = None

    # Detect first pulse's start and end
    for i in range(1, len(column_data) - 1):
        prev = column_data.iloc[i - 1]
        curr = column_data.iloc[i]
        next_val = column_data.iloc[i + 1]
        current_time = time_data.iloc[i]

        if not in_pulse and curr > prev and curr >= next_val:
            in_pulse = True
            pulse_start_time = current_time

        elif in_pulse and curr < prev and curr <= next_val:
            in_pulse = False
            pulse_end_index = i
            break

    # Estimate settled current from 50 samples after waiting 50 samples past pulse end
    settled_current = 0
    if pulse_end_index is not None and pulse_end_index + 100 < len(column_data):
        settled_region = column_data.iloc[pulse_end_index + 50 : pulse_end_index + 100]
        settled_current = settled_region.mean() * 1e6  # µA

    # Overshoot = peak - settled
    overshoot_peak = column_data.max() * 1e6  # µA
    overshoot = overshoot_peak - settled_current
    OS_percent = (overshoot / settled_current * 100) if settled_current != 0 else 0

    if OS_percent < 0 or OS_percent > 100:
        overshoot = overshoot_peak - average_max_current
        OS_percent = (overshoot/average_max_current * 100)


    # --- Pulse Width (in µs) ---
    peak_current = column_data.max()
    threshold = 0.5 * peak_current

    # Convert to numpy for faster indexing
    current_array = column_data.to_numpy()
    time_array = time_data.to_numpy()

    # Find rising edge
    rising_index = None
    for i in range(1, len(current_array)):
        if current_array[i - 1] < threshold <= current_array[i]:
            rising_index = i
            break

    # Find falling edge
    falling_index = None
    if rising_index is not None:
        for i in range(rising_index + 1, len(current_array)):
            if current_array[i - 1] >= threshold > current_array[i]:
                falling_index = i
                break

    # Pulse Width in µs
    pulse_width = 0
    if rising_index is not None and falling_index is not None:
        pulse_width = (time_array[falling_index] - time_array[rising_index]) * 1e6



    # --- RMS Current ---
    current_rms = np.sqrt(np.mean(column_data**2)) * 1e6  # µA
    
    # --- Settling Time ---
    settling_time_us = 0
    settling_window = 5  # number of samples to average for stability
    tolerance_percent = 0.02

    # Define the band within which the signal is considered "settled"
    settled_target = settled_current / 1e6 
    print(settled_target)
    upper_bound = settled_target * (1 + tolerance_percent)
    lower_bound = settled_target * (1 - tolerance_percent)

    # Use rising_index as pulse start and falling_index as pulse end
    if rising_index is not None and falling_index is not None:
        pulse_start_time = time_array[rising_index]
        pulse_start_index = rising_index

        for i in range(pulse_start_index, len(column_data) - settling_window):
            window = column_data.iloc[i : i + settling_window]
            if window.between(lower_bound, upper_bound).all():
                T2_time = time_data.iloc[i]
                settling_time_us = abs((T2_time - pulse_start_time) * 1e6)  # Convert to µs
                break


    # --- Return results ---
    return {
        "Average Maximum Current": format_current(average_max_current),
        "Average Minimum Current": format_current(average_min_current),
        "Overshoot": f"{format_current(overshoot)} ({OS_percent:.2f} %)",
        "Pulse Width": f"{pulse_width:.4f} µs",
        "Current RMS": format_current(current_rms),
        "Settling Time": f"{settling_time_us:.4f} µs"
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