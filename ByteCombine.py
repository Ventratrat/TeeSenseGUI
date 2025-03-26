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

def read_csv_and_process(file_path):
    """
    Reads a CSV file, processes the ADC byte data, computes averages,
    and removes outliers before writing the results to a new CSV.
    
    - Ignores the first column.
    - Combines columns 2-3 and 4-5 as big-endian values.
    - Averages the two combined values.
    - Runs outlier detection and writes the cleaned average to the 4th column.
    """
    processed_data = []
    avg_values = []

    with open(file_path, 'r') as csvfile:
        reader = csv.reader(csvfile)
        for row in reader:
            if len(row) >= 5 and row[1].isdigit() and row[2].isdigit() and row[3].isdigit() and row[4].isdigit():
                # Combine columns 2 and 3 into a big-endian integer
                adc1 = (int(row[1]) << 8) | int(row[2])
                # Combine columns 4 and 5 into a big-endian integer
                adc2 = (int(row[3]) << 8) | int(row[4])
                # Calculate average of adc1 and adc2
                avg = (adc1 + adc2) / 2.0
                
                # Store the processed data
                processed_data.append([adc1, adc2, avg])
                avg_values.append(avg)

    # Detect and remove outliers in the avg_values
    cleaned_avg_values = detect_and_remove_outliers(avg_values, window=2, threshold=3)
    
    # Add the cleaned data to the 4th column
    for i in range(len(processed_data)):
        processed_data[i].append(cleaned_avg_values[i])
    
    return processed_data

def save_csv_file(data):
    """
    Prompts the user to save the processed data as a CSV file.
    """
    root = tk.Tk()
    root.withdraw()
    save_path = filedialog.asksaveasfilename(
        title="Save Processed Data",
        defaultextension=".csv",
        filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
    )

    if save_path:
        try:
            with open(save_path, "w", newline="") as f:
                writer = csv.writer(f)
                header = ["ADC1", "ADC2", "Average", "Average (Filtered)"]
                writer.writerow(header)
                for row in data:
                    writer.writerow(row)
            print(f"CSV file saved as: {save_path}")
        except Exception as e:
            print(f"Error saving CSV file: {e}")

# Open file dialog to select a CSV file
file_path = filedialog.askopenfilename(title="Select a CSV file", filetypes=[("CSV files", "*.csv")])
if file_path:
    processed_data = read_csv_and_process(file_path)
    save_csv_file(processed_data)
