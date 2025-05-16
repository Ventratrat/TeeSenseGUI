import csv
import matplotlib.pyplot as plt
import numpy as np
from matplotlib.ticker import FuncFormatter
from PyQt5 import QtWidgets

def generate_plot(csv_file, return_raw=False):
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

    if return_raw:
        return x, y

    return figure

def format_current(value_in_uA):
    """Converts a value in uA to an appropriate unit (uA, mA, A) with formatting."""
    if value_in_uA / 1_000_000 >= 1:
        return f"{value_in_uA / 1_000_000:.4f} A"
    elif value_in_uA / 1_000 >= 1:
        return f"{value_in_uA / 1_000:.4f} mA"
    else:
        return f"{value_in_uA:.4f} uA"


def calculate_parameters(data):
    """Calculates key electrical parameters from a numerical signal dataset."""
    if data.empty:
        return None

    numeric_cols = data.select_dtypes(include=['number'])
    if numeric_cols.shape[1] < 2:
        return None

    # Sort by time
    data = data.sort_values(by=data.columns[0]).reset_index(drop=True)
    time_data = numeric_cols.iloc[:, 0]  # time in seconds
    column_data = numeric_cols.iloc[:, 1]  # current

    # Remove negative offset
    negative_offset = column_data[column_data < 0].mean() if column_data[column_data < 0].any() else 0
    column_data = column_data - negative_offset

    # --- Peak and Threshold Calculations ---
    peak_current = column_data.max()
    peak_current_time = time_data[column_data.idxmax()]  # Time at which peak current occurs

    # Print the results
    print(f"Peak Current: {peak_current:.6f} A at Time: {peak_current_time:.6f} s")

    threshold_10 = 0.1 * peak_current
    threshold_50 = 0.5 * peak_current
    threshold_70 = 0.7 * peak_current
    threshold_90 = 0.9 * peak_current

    # Max current estimate
    data_for_max = column_data[column_data >= threshold_70]
    average_max_current = data_for_max.mean() * 1e6  # uA
    indices_to_exclude = data_for_max.index

    # Min current estimate
    filtered_data_for_min = column_data.drop(indices_to_exclude)
    average_min_current = filtered_data_for_min.rolling(window=5).min().mean() * 1e6  # uA

    # --- Rising and Falling Edge Detection (first full pulse only) ---
    current_array = column_data.to_numpy()
    time_array = time_data.to_numpy()
    rising_index = None
    falling_index = None

    for i in range(1, len(current_array) - 1):
        prev, curr, next_val = current_array[i - 1], current_array[i], current_array[i + 1]

        # Rising edge
        if rising_index is None and prev < threshold_50 <= curr:
            rising_index = i
            continue

        # Falling edge (after rising edge)
        if rising_index is not None and curr >= threshold_50 > next_val:
            falling_index = i
            break

    # --- Print the Falling Index and Time ---
    if falling_index is not None:
        falling_time = time_data[falling_index]  # Time at which falling edge occurs
        print(f"Falling Index: {falling_index}, Time: {falling_time:.6f} s")
    else:
        print("No falling edge detected.")

    # --- Pulse Width ---
    pulse_width = 0
    if rising_index is not None and falling_index is not None:
        pulse_width = (time_array[falling_index] - time_array[rising_index]) * 1e6  # us

    # --- RMS Current ---
    current_rms = np.sqrt(np.mean(column_data**2)) * 1e6  # uA

    # --- Settling Time (rising edge → last out-of-band before flat-top starts) ---
    settling_time_us = 0
    tolerance_percent = 0.03
    N = 3

    overshoot = 0
    OS_percent = 0

    if falling_index is not None and rising_index is not None:
        flat_top_region = column_data.iloc[rising_index:falling_index + 1]
        diffs = flat_top_region.diff().abs()
        flat_threshold = 0.001 * peak_current
        flat_samples = flat_top_region[diffs < flat_threshold]
        last_flat = flat_samples.tail(N)

        # --- Overshoot Calculation ---
        settled_target = last_flat.mean() if not last_flat.empty else average_max_current / 1e6  # fallback in A
        overshoot = (peak_current - settled_target) * 1e6  # convert to uA
        OS_percent = (overshoot / (settled_target * 1e6)) * 100 if settled_target > 0 else 0
     
        print(f"Using {len(last_flat)} flat-top samples for averaging:")
        print(last_flat.values)

        if not last_flat.empty:
            settled_target = last_flat.mean()
            upper_bound = settled_target * (1 + tolerance_percent)
            lower_bound = settled_target * (1 - tolerance_percent)

            print(f"Settled target: {settled_target:.6f} A")
            print(f"±{tolerance_percent*100:.1f}% bounds: {lower_bound:.6f} A to {upper_bound:.6f} A")
            print(f"Rising index: {rising_index}, Time: {time_array[rising_index]*1e6:.2f} µs")

            # Get index of first flat-top sample (start of the average window)
            flat_start_index = last_flat.index[0]

            # Walk backward from flat-top average start → rising edge
            last_out_of_band_index = rising_index
            for i in range(flat_start_index, rising_index - 1, -1):
                val = column_data.iloc[i]
                if val < lower_bound or val > upper_bound:
                    last_out_of_band_index = i
                    print(f"Last out-of-band value: {val:.6f} A at index {i}, Time: {time_array[i]*1e6:.2f} µs")
                    break

        if 'last_out_of_band_index' in locals():
            settling_time_us = (time_array[last_out_of_band_index] - time_array[rising_index]) * 1e6
        else:
            settling_time_us = 0.0  # fallback if no out-of-band point was found
        print(f"✔ Settling time: {settling_time_us:.4f} µs")

    # --- Return Results ---
    return {
        "Average Maximum Current": format_current(average_max_current),
        "Average Minimum Current": format_current(average_min_current),
        "Overshoot": f"{format_current(overshoot)} ({OS_percent:.2f} %)",
        "Pulse Width": f"{pulse_width:.4f} us",
        "Current RMS": format_current(current_rms),
        "Settling Time": f"{settling_time_us:.4f} us"
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

    # Set the width of the first column (Parameter column)
    tableWidget.setColumnWidth(0, 300)  # Adjust 200 to the width you need

    # Set the width of the second column (Value column)
    tableWidget.setColumnWidth(1, 200)  # Adjust 300 to the width you need

    for row, (param, value) in enumerate(stats.items()):
        tableWidget.setItem(row, 0, QtWidgets.QTableWidgetItem(param))  
        tableWidget.setItem(row, 1, QtWidgets.QTableWidgetItem(value))

    tableWidget.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)