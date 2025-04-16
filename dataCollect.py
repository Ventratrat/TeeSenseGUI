import serial
import time
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import threading
import csv
import subprocess
from ByteCombine import process_unfiltered_data, process_filtered_data

# Global variables
sample_count = 200  # Default sample count


def get_available_ports():
    """Return a list of available serial ports."""
    ports = []
    for i in range(1, 256):
        port = f'COM{i}'
        try:
            ser_test = serial.Serial(port)
            ser_test.close()
            ports.append(port)
        except serial.SerialException:
            continue
    return ports


def on_select_port():
    """Connect to the selected serial port and display options."""
    port = port_combobox.get()
    if port:
        global ser
        try:
            ser = serial.Serial(port, 115200, parity=serial.PARITY_NONE, bytesize=serial.EIGHTBITS, timeout=1)
            ser.flushInput()
            status_label.config(text=f"Connected to {port}", foreground="green")
            show_reading_controls()
        except serial.SerialException:
            messagebox.showerror("Connection Error", f"Could not connect to {port}")
    else:
        messagebox.showwarning("No Port Selected", "Please select a USB port.")


def show_reading_controls():
    """Show sample input, Start and Stop buttons after successful connection."""
    sample_label.grid(row=2, column=0, padx=10, pady=10)
    sample_entry.grid(row=2, column=1, padx=10, pady=10)

    start_button.grid(row=3, column=0, padx=20, pady=20)
    stop_button.grid(row=4, column=0, columnspan=2, padx=20, pady=20)


def stop_reading():
    """Stop reading from the serial port."""
    global stop_thread
    stop_thread = True
    status_label.config(text="Reading Stopped", foreground="red")
    print("Reading stopped.")


def start_reading():
    """Start a new thread for reading from the serial port."""
    global stop_thread, sample_count
    stop_thread = False
    try:
        sample_count = int(sample_entry.get())
        if sample_count <= 0:
            raise ValueError
    except ValueError:
        messagebox.showerror("Invalid Input", "Please enter a valid number of samples (> 0).")
        return

    ser.write(b'RESET\n')
    time.sleep(0.5)
    reading_thread = threading.Thread(target=read_from_serial, daemon=True)
    reading_thread.start()


def read_from_serial():
    """Read ASCII data from the serial port and convert it to numbers."""
    global data
    data = []
    byte_buffer = b""
    start_time = None

    try:
        while not stop_thread:
            if ser.in_waiting > 0:
                byte = ser.read(1)

                if byte == b'\n':
                    if start_time is None:
                        start_time = time.time()
                    try:
                        decoded_string = byte_buffer.decode('utf-8').strip()
                        values = list(map(int, decoded_string.split()))
                        elapsed_time_ms = round((time.time() - start_time), 2)
                        data.append([elapsed_time_ms] + values)
                        print(f"Received: {values} (Elapsed Time: {elapsed_time_ms} s)")
                    except ValueError:
                        print("Error: Unable to parse data:", byte_buffer)

                    byte_buffer = b""

                    if len(data) >= sample_count:
                        break
                else:
                    byte_buffer += byte
    except serial.SerialException:
        print("Error reading from USB port.")
    except KeyboardInterrupt:
        print("Reading stopped by user.")

    if data:
        ask_for_save_location(data)


def write_data_to_csv(data, filename):
    """Write the collected data to a CSV file."""
    try:
        with open(filename, mode="a", newline="") as file:
            writer = csv.writer(file)
            if file.tell() == 0:
                writer.writerow(["Time", "Byte1", "Byte2", "Byte3", "Byte4"])
            writer.writerows(data)
            print(f"Written {len(data)} rows to {filename}.")
    except Exception as e:
        print(f"Error writing to CSV: {e}")


def ask_for_save_location(data):
    """Ask the user if they want to save raw data or filtered data."""
    response = messagebox.askyesnocancel(
        "Save Data",
        "Do you want to save the filtered data?\n\n"
        "Yes - Save filtered data\n"
        "No - Save raw data\n"
        "Cancel - Do not save"
    )

    if response is None:
        messagebox.showwarning("No File Selected", "Data was not saved.")
        return

    save_path = filedialog.asksaveasfilename(
        title="Save Processed Data",
        defaultextension=".csv",
        filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
    )

    if save_path:
        write_data_to_csv(data, save_path)

        if response:
            process_filtered_data(save_path)
        else:
            process_unfiltered_data(save_path)

        subprocess.run(["python", "TeeSenseGUI.py", save_path])
    else:
        messagebox.showwarning("No File Selected", "No file was selected. Data was not saved.")


def create_gui():
    """Create the GUI window and start the main loop."""
    root = tk.Tk()
    root.title("USB Port Communication")
    start_main_application(root)
    root.mainloop()


def start_main_application(root):
    """Start the main application."""
    global port_combobox, start_button, stop_button, status_label
    global sample_entry, sample_label

    port_label = ttk.Label(root, text="Select Port:")
    port_label.grid(row=0, column=0, padx=10, pady=10)

    available_ports = get_available_ports()
    port_combobox = ttk.Combobox(root, values=available_ports)
    port_combobox.grid(row=0, column=1, padx=10, pady=10)

    connect_button = ttk.Button(root, text="Connect", command=on_select_port)
    connect_button.grid(row=0, column=2, padx=10, pady=10)

    status_label = ttk.Label(root, text="Not connected", font=("Arial", 12))
    status_label.grid(row=1, column=0, columnspan=3)

    # Create sample input field (hidden initially)
    sample_label = ttk.Label(root, text="Number of Samples:")
    sample_entry = ttk.Entry(root)
    sample_entry.insert(0, "200")

    # Create buttons (also hidden initially)
    start_button = ttk.Button(root, text="Start Reading", command=start_reading)
    stop_button = ttk.Button(root, text="Stop", command=stop_reading)


create_gui()
