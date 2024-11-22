import csv
import matplotlib.pyplot as plt
import numpy as np

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

    num_x_intervals = 10
    num_y_intervals = 20

    x_step = x_max / num_x_intervals
    y_step = y_max / num_y_intervals

    figure, ax = plt.subplots()
    ax.plot(x, y, color='g', linestyle='dashed', marker='o', label="Current")

    ax.set_xlim(x_min - x_margin, x_max + x_margin)
    ax.set_ylim(y_min - y_margin, y_max + y_margin)
    ax.set_xticks(np.arange(0, x_max + x_margin, step=x_step))
    ax.set_yticks(np.arange(0, y_max + y_margin, step=y_step))

    ax.set_xlabel('Input') 
    ax.set_ylabel('Output') 
    ax.set_title('Current Pulse Data', fontsize=20) 
    ax.grid() 
    ax.legend() 

    return figure
