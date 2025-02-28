import openpyxl
import struct
import tkinter as tk
from tkinter import filedialog
import csv
import numpy as np

def detect_and_remove_outliers(data, window=1, threshold=2.5):
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

def read_excel_and_process(file_path):
   
    wb = openpyxl.load_workbook(file_path, data_only=True)
    sheet = wb.active  
    
    processed_data = []
    avg_values = []
    
    for row in sheet.iter_rows(values_only=True):
        if row and isinstance(row[0], str):  # Ensure there's data in the row
            bytes_str = row[0].split()
            bytes_str = [b.strip() for b in bytes_str if b.strip().isdigit()]  # Clean and filter valid numbers
            
            if len(bytes_str) == 4:
                adc1 = (int(bytes_str[0]) << 8) | int(bytes_str[1])  # First two bytes
                adc2 = (int(bytes_str[2]) << 8) | int(bytes_str[3])  # Second two bytes
                avg = (adc1 + adc2) / 2.0
                processed_data.append([adc1, adc2, avg])
                avg_values.append(avg)
            if len(bytes_str) == 1:
                single_value = int(bytes_str[0])
                processed_data.append([single_value])
                avg_values.append(single_value)
        elif row and isinstance(row[0], (int, float)):
                processed_data.append([row[0]])
                avg_values.append(row[0])
    wb.close()
    
    cleaned_avg_values = detect_and_remove_outliers(avg_values, window=2, threshold=3) # Outlier Removal
    
    # Update the processed data with cleaned average values
    for i in range(len(processed_data)):
        if len(processed_data[i]) == 3:  # Case with two-byte data (adc1, adc2, avg)
            processed_data[i][2] = cleaned_avg_values[i]
        elif len(processed_data[i]) == 1:  # Case with single-byte data (only avg)
            processed_data[i][0] = cleaned_avg_values[i]
    
    return processed_data

def save_files(data):
    root = tk.Tk()
    root.withdraw()
    save_path = filedialog.asksaveasfilename(
        title="Save Processed Data",
        defaultextension=".xlsx",
        filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")]
    )

    if save_path:
        csv_path = save_path.rsplit(".", 1)[0] + ".csv"
        try:
            with open(csv_path, "w", newline="") as f:
                writer = csv.writer(f)
                header = ["ADC1", "ADC2", "Average (Filtered)"] if any(len(row) == 3 for row in data) else ["Byte Value (Filtered)"]
                writer.writerow(header)
                for row in data:
                    writer.writerow(row)
            print(f"CSV file saved as: {csv_path}")
        except Exception as e:
            print(f"Error saving CSV file: {e}")

file_path = filedialog.askopenfilename(title="Select an Excel file", filetypes=[("Excel files", "*.xlsx")])
if file_path:
    processed_data = read_excel_and_process(file_path)
    save_files(processed_data)
