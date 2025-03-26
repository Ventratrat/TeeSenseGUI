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

    x_min, x_max = min(x), max(x)
    y_min, y_max = min(y), max(y)

    x_margin = (x_max - x_min) * 0.1 
    y_margin = (y_max - y_min) * 0.1 
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

    column_data = numeric_cols.iloc[:, 1]  
    
    max = column_data.max()
    threshold = 0.8 * column_data.max()
    data_for_max = column_data[column_data >= threshold]
    
    average_max_current = data_for_max.mean() 

    indices_to_exclude = data_for_max.index

    #Filter out data points from max current
    filtered_data_for_min = column_data.drop(indices_to_exclude)
    average_min_current = filtered_data_for_min.rolling(window=5).min().mean() 

    overshoot = column_data.max() - average_max_current
    pulse_width = (column_data > (average_max_current * 0.9)).sum() 
    current_rms = np.sqrt(np.mean(column_data**2))
    settling_time = (column_data > (average_max_current * 0.98)).sum() 

    return {
        "Average Maximum Current": average_max_current,
        "Average Minimum Current": average_min_current,
        "Overshoot": overshoot,
        "Pulse Width": pulse_width,
        "Current RMS": current_rms,
        "Settling Time": settling_time
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
        tableWidget.setItem(row, 1, QtWidgets.QTableWidgetItem(f"{value:.4f}"))  

    tableWidget.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)