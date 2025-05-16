import csv
import numpy as np
import tkinter as tk
from tkinter import filedialog

baseline_adc_value = 53.248  # Default ADC baseline (same as previously hardcoded)

def process_dc_bias_data(data, return_data=False):
    print("process_dc_bias_data() called")
    from ByteCombine import map_adc_to_current
    avg_currents = []

    for row in data:
        if len(row) >= 5:
            try:
                adc1 = (int(row[1]) << 8) | int(row[2])
                adc2 = (int(row[3]) << 8) | int(row[4])
                avg_adc = (adc1 + adc2) / 2.0
                current = map_adc_to_current(avg_adc)
                avg_currents.append(current)
                # print(f"ADC1: {adc1}, ADC2: {adc2}, Avg: {avg_adc:.2f}, Current: {current:.6f}")
            except Exception as e:
                print(f"Error parsing row {row}: {e}")

    if not avg_currents:
        print("No valid current samples found.")
        return [], []

    dc_bias = sum(avg_currents) / len(avg_currents)
    print(f"Calculated DC Bias: {dc_bias:.6f} A from {len(avg_currents)} samples")

    if return_data:
        times = [row[0] for row in data if len(row) >= 5]
        return times, [dc_bias] * len(times)

    return dc_bias

def map_adc_to_current(adc_avg):
    global baseline_adc_value

    # Check the baseline_adc_value and adc_avg
    print(f"Baseline ADC Value: {baseline_adc_value}")
    print(f"ADC Average: {adc_avg}")

    # Original formula for current (before correction)
    original_current = (((((adc_avg - baseline_adc_value) / 65536.0) * 3.323) / 1.4773))
    print(f"Original Current: {original_current}")

    # Apply the inverse of the regression to get the expected current
    expected_current = (((original_current + 0.0008) / 0.9998) - 0.039) / 0.9944
    print(f"Expected Current: {expected_current}")

    return expected_current 

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

def process_unfiltered_data(data, return_data=False):
    global baseline_adc_value
    unfiltered_data = []
    avg_values = []

    if isinstance(data, str):
        with open(data, 'r') as csvfile:
            reader = csv.reader(csvfile)
            next(reader, None)
            for row in reader:
                if len(row) >= 5 and all(r.isdigit() for r in row[1:5]):
                    elapsed_time_ms = float(row[0])
                    adc1 = (int(row[1]) << 8) | int(row[2])
                    adc2 = (int(row[3]) << 8) | int(row[4])
                    avg = (adc1 + adc2) / 2.0
                    current = map_adc_to_current(avg)
                    avg_values.append(current)
                    unfiltered_data.append([elapsed_time_ms / 1000.0, current])

    else:
        for row in data:
            if len(row) >= 5:
                elapsed_time = float(row[0])
                adc1 = (int(row[1]) << 8) | int(row[2])
                adc2 = (int(row[3]) << 8) | int(row[4])
                avg = (adc1 + adc2) / 2.0
                current = map_adc_to_current(avg)
                avg_values.append(current)
                unfiltered_data.append([elapsed_time, current])

    print(f"avg_values: {len(avg_values)} items")

    # Outlier removal only
    cleaned = detect_and_remove_outliers(avg_values, window=2, threshold=3)
    cleaned_data = [[unfiltered_data[i][0], val] for i, val in enumerate(cleaned)]

    if return_data:
        x_data = [row[0] for row in cleaned_data]
        y_data = [row[1] for row in cleaned_data]
        return x_data, y_data

    save_path = filedialog.asksaveasfilename(
        title="Save Unfiltered Data",
        defaultextension=".csv",
        filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
    )

    if save_path:
        with open(save_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Elapsed Time (s)", "Current (Unfiltered, A)"])
            writer.writerows(cleaned_data)
        print(f"Unfiltered data saved to {save_path}.")
    else:
        print("Save operation canceled.")

def moving_average(data, window_size=3):
    """
    Applies a simple moving average filter to the data.
    
    Parameters:
    - data: List of floats
    - window_size: Number of samples to average overc
    
    Returns:
    - Smoothed list of values
    """
    if window_size < 1:
        return data 
    padded = np.pad(data, (window_size//2, window_size-1-window_size//2), mode='edge')
    return np.convolve(padded, np.ones(window_size)/window_size, mode='valid').tolist()

def process_filtered_data(data, return_data=False):
    global baseline_adc_value
    avg_values = []
    filtered_data = []

    if isinstance(data, str):
        with open(data, 'r') as csvfile:
            reader = csv.reader(csvfile)
            next(reader, None)
            for row in reader:
                if len(row) >= 5 and all(r.isdigit() for r in row[1:5]):
                    elapsed_time_ms = float(row[0])
                    adc1 = (int(row[1]) << 8) | int(row[2])
                    adc2 = (int(row[3]) << 8) | int(row[4])
                    avg = (adc1 + adc2) / 2.0
                    mapped_current = map_adc_to_current(avg)
                    avg_values.append(mapped_current)
                    filtered_data.append([elapsed_time_ms / 1000.0, mapped_current])
                    print(f"ADC1 raw: {adc1}, ADC2 raw: {adc2}, Avg: {avg}")
                    print(f"Mapped current: {mapped_current} A")

    else:
        for row in data:
            if len(row) >= 5:
                try:
                    elapsed_time = float(row[0])  # Already in seconds
                    adc1 = (int(row[1]) << 8) | int(row[2])
                    adc2 = (int(row[3]) << 8) | int(row[4])
                    avg = (adc1 + adc2) / 2.0
                    mapped_current = map_adc_to_current(avg)
                    avg_values.append(mapped_current)
                    filtered_data.append([elapsed_time, mapped_current])
                    print(f"ADC1 raw: {adc1}, ADC2 raw: {adc2}, Avg: {avg}")
                    print(f"Mapped current: {mapped_current} A")
                except Exception as e:
                    print(f"Row caused error: {row} → {e}")

    print(f"avg_values: {len(avg_values)} items")

    # Smoothing and outlier removal
    smoothed = moving_average(avg_values, window_size=3)
    cleaned = detect_and_remove_outliers(smoothed, window=2, threshold=3)
    cleaned_data = [[fd[0], c] for fd, c in zip(filtered_data, cleaned)]

    if return_data:
        x_data = [row[0] for row in cleaned_data]
        y_data = [row[1] for row in cleaned_data]
        return x_data, y_data

    # Save to CSV if not returning
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


        

