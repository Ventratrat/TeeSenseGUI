import openpyxl
import struct
import tkinter as tk
from tkinter import filedialog
import csv

def read_excel_and_combine_bytes(file_path):
    # Load the Excel workbook
    wb = openpyxl.load_workbook(file_path, data_only=True)
    sheet = wb.active  # Get the first sheet
    
    byte_list = []
    for row in sheet.iter_rows(values_only=True):
        for cell in row:
            if isinstance(cell, int):  # Assuming integer byte values (0-255)
                byte_list.append(cell & 0xFF)  # Ensure it's a single byte
    
    wb.close()
    
    # Combine bytes into 2-byte values
    combined_values = []
    for i in range(0, len(byte_list) - 1, 2):
        combined_value = (byte_list[i] << 8) | byte_list[i + 1]  # Combine two bytes
        combined_values.append(combined_value)
    
    return combined_values

def select_file():
    root = tk.Tk()
    root.withdraw()  # Hide the root window
    file_path = filedialog.askopenfilename(title="Select an Excel file", filetypes=[("Excel files", "*.xlsx")])
    return file_path

def save_to_csv(data):
    root = tk.Tk()
    root.withdraw()
    save_path = filedialog.asksaveasfilename(title="Save Combined Bytes", defaultextension=".csv", filetypes=[("CSV files", "*.csv"), ("All files", "*.*")])
    if save_path:
        with open(save_path, "w", newline="") as f:
            writer = csv.writer(f)
            writer.writerow(["Combined Bytes"])  # Header
            for value in data:
                writer.writerow([value])

def save_to_excel(data):
    root = tk.Tk()
    root.withdraw()
    save_path = filedialog.asksaveasfilename(title="Save Combined Bytes", defaultextension=".xlsx", filetypes=[("Excel files", "*.xlsx"), ("All files", "*.*")])
    if save_path:
        wb = openpyxl.Workbook()
        sheet = wb.active
        sheet.title = "Combined Bytes"
        sheet.append(["Combined Bytes"])  # Header
        for value in data:
            sheet.append([value])
        wb.save(save_path)

# Example usage:
file_path = select_file()
if file_path:
    combined_data = read_excel_and_combine_bytes(file_path)
    save_to_csv(combined_data)  # Save as CSV
    save_to_excel(combined_data)  # Save as Excel
