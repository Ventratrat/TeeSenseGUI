import csv
import numpy as np
import tkinter as tk
from tkinter import filedialog

def detect_and_remove_outliers(data, window=2, threshold=3):
    """
    Detects and removes outliers by comparing each point with its neighbors.

    Parameters:
    - data: List of numerical values
    - window: Number of neighboring points to consider on each side (only window=1 supported here)
    - threshold: Absolute deviation threshold to be considered an outlier

    Returns:
    - Cleaned list with outliers replaced by average of neighbors
    """
    if window != 1:
        raise ValueError("This implementation supports only window=1 for averaging two neighbors.")

    data_array = np.array(data)
    cleaned_data = data_array.copy()

    for i in range(window, len(data_array) - window):
        neighbor_avg = (data_array[i - 1] + data_array[i + 1]) / 2.0
        if abs(data_array[i] - neighbor_avg) > threshold:
            cleaned_data[i] = neighbor_avg

    return cleaned_data.tolist()

def process_unfiltered_data(file_path):
    unfiltered_data = []

    with open(file_path, 'r') as csvfile:
        reader = csv.reader(csvfile)
        next(reader, None)  # Skip header
        rows = list(reader)

        if len(rows) < 2:
            print("Not enough data.")
            return

        # First row is the total time in 32-bit value
        t_row = rows[0]
        total_cycles = (int(t_row[1]) << 24) | (int(t_row[2]) << 16) | (int(t_row[3]) << 8) | int(t_row[4])
        total_time_sec = total_cycles / 550_000_000.0
        num_samples = len(rows) - 1
        time_per_sample = total_time_sec / num_samples

        for i, row in enumerate(rows[1:]):
            if len(row) >= 5 and all(cell.isdigit() for cell in row[1:5]):
                elapsed_time = round(i * time_per_sample, 6)
                adc1 = (int(row[1]) << 8) | int(row[2])
                adc2 = (int(row[3]) << 8) | int(row[4])
                avg = (adc1 + adc2) / 2.0
                unfiltered_data.append([elapsed_time, avg])
                

    save_path = filedialog.asksaveasfilename(
        title="Save Unfiltered Data",
        defaultextension=".csv",
        filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
    )

    if save_path:
        with open(save_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Elapsed Time (s)", "Average (Unfiltered)"])
            writer.writerows(unfiltered_data)
        print(f"Unfiltered data saved to {save_path}.")
    else:
        print("Save operation canceled.")


def moving_average(data, window_size=3):
    """
    Applies a simple moving average filter to the data.
    
    Parameters:
    - data: List of floats
    - window_size: Number of samples to average over
    
    Returns:
    - Smoothed list of values
    """
    if window_size < 1:
        return data 
    padded = np.pad(data, (window_size//2, window_size-1-window_size//2), mode='edge')
    return np.convolve(padded, np.ones(window_size)/window_size, mode='valid').tolist()

def process_filtered_data(file_path):
    avg_values = []
    filtered_data = []

    with open(file_path, 'r') as csvfile:
        reader = csv.reader(csvfile)
        next(reader, None)
        rows = list(reader)

        if len(rows) < 2:
            print("Not enough data.")
            return

        t_row = rows[0]
        total_cycles = (int(t_row[1]) << 24) | (int(t_row[2]) << 16) | (int(t_row[3]) << 8) | int(t_row[4])
        total_time_sec = total_cycles / 550_000_000.0
        num_samples = len(rows) - 1
        time_per_sample = total_time_sec / num_samples

        for i, row in enumerate(rows[1:]):
            if len(row) >= 5 and all(cell.isdigit() for cell in row[1:5]):
                elapsed_time = round(i * time_per_sample, 9)
                adc1 = (int(row[1]) << 8) | int(row[2])
                adc2 = (int(row[3]) << 8) | int(row[4])
                avg = (adc1 + adc2) / 2.0
                mapped_current = (((avg - 68) / 65536.0) * 3.323) / 30.0
                avg_values.append(mapped_current)
                filtered_data.append([elapsed_time, mapped_current])

    cleaned_avg_values = detect_and_remove_outliers(avg_values, window=2, threshold=3)
    smoothed_values = moving_average(cleaned_avg_values, window_size=3)

    cleaned_data = [[filtered_data[i][0], smoothed_values[i]] for i in range(len(filtered_data))]

    save_path = filedialog.asksaveasfilename(
        title="Save Filtered Data",
        defaultextension=".csv",
        filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
    )

    if save_path:
        with open(save_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Elapsed Time (s)", "Average (Filtered)"])
            writer.writerows(cleaned_data)
        print(f"Filtered data saved to {save_path}.")
    else:
        print("Save operation canceled.")

        

