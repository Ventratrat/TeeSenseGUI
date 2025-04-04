import csv
import numpy as np
import tkinter as tk
from tkinter import filedialog

def detect_and_remove_outliers(data, window=2, threshold=3):
    """
    Detects and removes outliers by comparing each point with its neighbors.
    
    Parameters:
    - data: List of numerical values
    - window: Number of neighboring points to consider on each side
    - threshold: Factor by which a point must deviate to be considered an outlier
    
    Returns:
    - Cleaned list with outliers replaced by median of neighbors
    """
    data_array = np.array(data)
    cleaned_data = data_array.copy()
    
    for i in range(window, len(data_array) - window):
        local_median = np.median(data_array[i - window : i + window + 1])
        if abs(data_array[i] - local_median) > threshold:
            cleaned_data[i] = local_median  # Replace outlier with median of neighbors
    
    return cleaned_data.tolist()

def process_unfiltered_data(file_path):
    """
    Processes the ADC byte data and computes unfiltered average values.
    - Ignores the first column.
    - Combines columns 2-3 and 4-5 as big-endian values.
    - Averages the two combined values.
    - Saves the unfiltered data with elapsed time and average.
    """
    unfiltered_data = []

    with open(file_path, 'r') as csvfile:
        reader = csv.reader(csvfile)
        next(reader, None)  # Skip header if present
        for row in reader:
            if len(row) >= 5 and row[1].isdigit() and row[2].isdigit() and row[3].isdigit() and row[4].isdigit():
                elapsed_time_ms = float(row[0])  # Get the elapsed time
                adc1 = (int(row[1]) << 8) | int(row[2])  # Combine columns 2 and 3
                adc2 = (int(row[3]) << 8) | int(row[4])  # Combine columns 4 and 5
                avg = (adc1 + adc2) / 2.0  # Calculate average
                unfiltered_data.append([elapsed_time_ms, avg])
                
                # Stop if more than 200 rows are collected
                if len(unfiltered_data) >= 200:
                    break

    # Ask user for save location and file name
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
    """
    Processes the ADC byte data, computes averages, and removes outliers.
    - Ignores the first column.
    - Combines columns 2-3 and 4-5 as big-endian values.
    - Averages the two combined values.
    - Removes outliers and writes the cleaned values to a new CSV.
    """
    avg_values = []
    filtered_data = []

    with open(file_path, 'r') as csvfile:
        reader = csv.reader(csvfile)
        next(reader, None) 
        for row in reader:
            if len(row) >= 5 and row[1].isdigit() and row[2].isdigit() and row[3].isdigit() and row[4].isdigit():
                elapsed_time_ms = float(row[0])  
                adc1 = (int(row[1]) << 8) | int(row[2])  
                adc2 = (int(row[3]) << 8) | int(row[4]) 
                avg = (adc1 + adc2) / 2.0
                
                mapped_current = (((avg - 68) / 65536.0) * 3.323) / 30.0
                avg_values.append(mapped_current)
                filtered_data.append([elapsed_time_ms, mapped_current])
                
                if len(filtered_data) >= 200:
                    break

    smoothed_values = moving_average(avg_values, window_size=3)

    # Outlier removal
    cleaned_avg_values = detect_and_remove_outliers(smoothed_values, window=2, threshold=3)


    cleaned_data = []
    for i in range(len(filtered_data)):
        cleaned_data.append([filtered_data[i][0], cleaned_avg_values[i]])

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

        

