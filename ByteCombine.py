import csv
import numpy as np
import tkinter as tk
from tkinter import filedialog

def process_unfiltered_data(file_path):
    avg_values = []
    unfiltered_data = []

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
                unfiltered_data.append([elapsed_time, mapped_current])
                

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
    filtered_data = []
    mapped_values = []

    with open(file_path, 'r') as csvfile:
        reader = csv.reader(csvfile)
        next(reader, None)
        rows = list(reader)

        if len(rows) < 4:
            print("Not enough data.")
            return

        t_row = rows[0]
        total_cycles = (int(t_row[1]) << 24) | (int(t_row[2]) << 16) | (int(t_row[3]) << 8) | int(t_row[4])
        total_time_sec = total_cycles / 550_000_000.0
        num_samples = len(rows) - 1
        time_per_sample = total_time_sec / num_samples

        adc_pairs = []
        time_stamps = []

        for i, row in enumerate(rows[1:]):
            if len(row) >= 5 and all(cell.isdigit() for cell in row[1:5]):
                elapsed_time = round(i * time_per_sample, 9)
                adc1 = (int(row[1]) << 8) | int(row[2])
                adc2 = (int(row[3]) << 8) | int(row[4])
                adc_pairs.append((adc1, adc2))
                time_stamps.append(elapsed_time)

        for i in range(1, len(adc_pairs) - 1):
            adc1, adc2 = adc_pairs[i]
            prev_avg = sum(adc_pairs[i - 1]) / 2
            next_avg = sum(adc_pairs[i + 1]) / 2
            current_time = time_stamps[i]

            # Check if there's a large mismatch between adc1 and adc2
            if max(adc1, adc2) == 0:
                chosen_adc = (prev_avg + next_avg) / 2  # fallback to neighbors' average
            elif min(adc1, adc2) / max(adc1, adc2) < 0.5:
                if adc1 > adc2:
                    chosen_adc = adc1 if (prev_avg + next_avg) / 2 > adc1 else adc2
                else:
                    chosen_adc = adc2 if (prev_avg + next_avg) / 2 > adc2 else adc1
            else:
                chosen_adc = (adc1 + adc2) / 2.0


            mapped_current = (((chosen_adc - 68) / 65536.0) * 3.323) / 30.0
            mapped_values.append(mapped_current)
            filtered_data.append([current_time, mapped_current])

    # Smooth the values
    cleaned_values = moving_average(mapped_values, window_size=3)

    cleaned_data = [[filtered_data[i][0], cleaned_values[i]] for i in range(len(filtered_data))]

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
