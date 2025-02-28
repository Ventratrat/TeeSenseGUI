import openpyxl
import struct
import tkinter as tk
from tkinter import filedialog
import csv

def read_excel_and_process(file_path):
    # Load the Excel workbook
    wb = openpyxl.load_workbook(file_path, data_only=True)
    sheet = wb.active  # Get the first sheet
    
    processed_data = []
    
    for row in sheet.iter_rows(values_only=True):
        if row and isinstance(row[0], str):  # Ensure there's data in the row
            bytes_str = row[0].split()
            bytes_str = [b.strip() for b in bytes_str if b.strip().isdigit()]  # Clean and filter valid numbers
            
            if len(bytes_str) == 4:
                adc1 = (int(bytes_str[0]) << 8) | int(bytes_str[1])  # Combine first two bytes
                adc2 = (int(bytes_str[2]) << 8) | int(bytes_str[3])  # Combine second two bytes
                avg = (adc1 + adc2) / 2.0
                processed_data.append([adc1, adc2, avg])
    
    wb.close()
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

        # Save as CSV
        csv_path = save_path.rsplit(".", 1)[0] + ".csv"  # Ensure correct CSV extension
        try:
            with open(csv_path, "w", newline="") as f:
                writer = csv.writer(f)
                writer.writerow(["ADC1", "ADC2", "Average"])  # Header
                for row in data:
                    writer.writerow(row)
            print(f"CSV file saved as: {csv_path}")
        except Exception as e:
            print(f"Error saving CSV file: {e}")


# Example usage:
file_path = filedialog.askopenfilename(title="Select an Excel file", filetypes=[("Excel files", "*.xlsx")])
if file_path:
    processed_data = read_excel_and_process(file_path)
    save_files(processed_data)
