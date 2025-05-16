import serial
import time
import csv
import threading
import subprocess
import tkinter as tk
from PyQt5.QtCore import QTimer, pyqtSignal, QObject
from PyQt5.QtWidgets import QApplication, QMainWindow
import TeeSenseGUI
import numpy as np
from tkinter import filedialog, messagebox
from tkinter import StringVar, IntVar
from PIL import Image, ImageTk
from ttkbootstrap import Style
from ttkbootstrap.constants import *
from ttkbootstrap.widgets import Frame, LabelFrame, Button, Label, Combobox

from ByteCombine import process_filtered_data, process_unfiltered_data
from csvRead import calculate_parameters, populate_table
from TeeSenseGUI import start_tkinter_window
import ByteCombine

root = None

def generate_fake_pulse_data(filtered=True):
    t = np.linspace(0, 0.001, 1000)  # 1 ms total, 1000 samples
    pulse = np.zeros_like(t)

    # Create a 100 µs-wide pulse at 200 µs
    pulse_start = int(0.0002 / (t[1] - t[0]))
    pulse_width = int(0.0001 / (t[1] - t[0]))
    pulse[pulse_start:pulse_start + pulse_width] = 0.1  # 100 mA pulse

    if filtered:
        pulse = np.convolve(pulse, np.ones(5)/5, mode='same')  # smooth

    # Convert to same format as real ADC rows: [time, byte1, byte2, byte3, byte4]
    fake_data = []
    for time_s, amp in zip(t, pulse):
        # simulate a 16-bit ADC reading (reverse from mapping equation)
        raw_val = int((amp * 30.0 / 3.323) * 65536.0 + 68)
        adc1 = (raw_val >> 8) & 0xFF
        adc2 = raw_val & 0xFF
        fake_data.append([time_s, adc1, adc2, adc1, adc2])  # reuse for both ADCs

    return fake_data

def show_about_window():
    about = tk.Toplevel()
    about.title("About TeeSense Logger")
    about.geometry("480x340")
    about.resizable(False, False)

    description = (
        "TeeSense USB Data Logger\n"
        "\n"
        "This application reads data from a high-speed ADC over a USB serial connection.\n"
        "The data is sampled at ~1.22 MHz and stored in memory for further analysis.\n\n"
        "- Real-time serial connection\n"
        "- Adjustable sample size\n"
        "- Estimated time duration display\n"
        "- Filtered or raw data saving\n"
        "- Clean, modern interface with theme support\n\n"
        "Developed for lab and field testing of pulsed current signals generated in the DC ports of RF bias tees."
        "\n\n"
        "The document below contains instructions on how to use this software:"
    )

    Label(about, text=description, wraplength=440, justify="left", padding=20).pack()
    Button(about, text="Close", command=about.destroy, bootstyle="secondary").pack(pady=10)

def get_available_ports():
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


def refresh_ports():
    ports = get_available_ports()
    port_combobox["values"] = ports
    port_combobox.set("")
    update_status("Ports refreshed", "info")


def read_from_serial():
        global data
        data = []
        buffer = b""
        first_line_skipped = False
        sample_index = 0

        print(f"[Reading] Starting, data = {data[:5]}")

        SAMPLE_RATE = 1_220_000  # Hz
        SAMPLE_PERIOD = 1 / SAMPLE_RATE  # ~819.67 ns

        try:
            while not stop_thread:
                if ser.in_waiting > 0:
                    buffer += ser.read(ser.in_waiting)

                    while b'\n' in buffer:
                        line, buffer = buffer.split(b'\n', 1)

                        decoded = line.decode('utf-8').strip()
                        parts = list(map(int, decoded.split()))

                        if not first_line_skipped:
                            print(f"Skipping first timing line: {parts}")
                            first_line_skipped = True
                            continue

                        if len(parts) != 4:
                            print(f"Skipping malformed line: {parts}")
                            continue

                        # Use fixed time step based on sample index
                        timestamp_s = sample_index * SAMPLE_PERIOD
                        data.append([timestamp_s] + parts)
                        sample_index += 1

                        retake_settings = {
                            "port": ser.port,
                            "samples": sample_count,
                            "filter_mode": filter_var.get()
                        }

                        if len(data) >= sample_count:
                            print("Sample count reached, launching GUI")
                            ser.close()

                            # First, call the Qt-based GUI
                            try:
                                print("Calling process_and_launch_gui()...")
                                process_and_launch_gui(data, retake_settings)
                                print("Returned from process_and_launch_gui()")
                            except Exception as e:
                                print(f"Error in process_and_launch_gui: {e}")

                            return  # End the function to continue the program
        except Exception as e:
            print(f"Error during serial read: {e}")
 

def write_data_to_csv(data, filename):
    try:
        with open(filename, mode="a", newline="") as file:
            writer = csv.writer(file)
            if file.tell() == 0:
                writer.writerow(["Time", "Byte1", "Byte2", "Byte3", "Byte4"])
            writer.writerows(data)
            print(f"Saved {len(data)} entries to {filename}.")
    except Exception as e:
        print(f"CSV write error: {e}")

def process_and_launch_gui(data, retake_settings=None):

    root.withdraw()

    selected_filter = filter_var.get()
    print(f"Selected filter: '{selected_filter}'")  # <-- Add this

    if selected_filter == "Filtered":
        print(f"process_filtered_data called")
        x_data, y_data = process_filtered_data(data, return_data=True)
    elif selected_filter == "Unfiltered":
        x_data, y_data = process_unfiltered_data(data, return_data=True)
    elif selected_filter == "DC Bias":
        from ByteCombine import process_dc_bias_data
        print(f"baseline_adc_value before DC bias calc: {ByteCombine.baseline_adc_value}")
        x_data, y_data = process_dc_bias_data(data, return_data=True)
    else:
        raise ValueError("Unknown filter option selected")

    from PyQt5.QtWidgets import QApplication, QMainWindow
    from TeeSenseGUI import Ui_MainWindow

    app = QApplication([])
    MainWindow = QMainWindow()
    ui = Ui_MainWindow()
    ui.setupUi(MainWindow)
    ui.load_direct_data(x_data, y_data, filtered=(selected_filter == "Filtered"), retake_settings=retake_settings)
    MainWindow.show()
    app.exec_()

def update_status(message, status_type="info"):
    status_label.config(text=message)
    status_label.config(bootstyle=status_type)


def show_reading_buttons():
    start_button.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
    zero_button.grid(row=0, column=1, padx=10, pady=10, sticky="ew")
    stop_button.grid(row=0, column=2, padx=10, pady=10, sticky="ew")

def on_close_tkinter():
    """Close the entire program when the Tkinter window is closed."""
    print("Tkinter window closed, exiting program...")
    root.quit()
    root.destroy()

def create_tkinter_gui():
    global root
    root = tk.Tk()
    style = Style("flatly")  # Light theme
    root.title("TeeSense USB Data Logger")
    root.geometry("800x500")  # Or wider if needed
    root.resizable(False, False)
    root.columnconfigure(1, weight=1)

    # Add the close event handler
    root.protocol("WM_DELETE_WINDOW", on_close_tkinter)

    start_main_application(root)
    root.mainloop()


def start_main_application(root):
    global port_combobox, start_button, stop_button, zero_button, status_label, sample_entry, time_estimate_label, num_samples

    def disconnect_port():
        try:
            if ser.is_open:
                ser.close()
                update_status("Disconnected", "danger")
                connect_btn.config(state="normal")  # Enable Connect button
                refresh_btn.config(state="normal")  # Enable Refresh button
                disconnect_btn.grid_forget()  # Hide Disconnect button after disconnection
            else:
                update_status("Already disconnected", "warning")
        except Exception as e:
            update_status(f"Error disconnecting: {str(e)}", "danger")

    num_samples = StringVar(value=200)
    est_time = StringVar(value="~0.000 s")

    global filter_var
    filter_var = StringVar(value="Filtered")

    # --- Root column config ---
    root.columnconfigure(0, weight=1)
    root.columnconfigure(1, weight=1)

    # --- Header Frame ---
    # --- Header Frame ---
    header = Frame(root, padding=(20, 10))
    header.grid(row=0, column=0, columnspan=2, sticky="ew")
    header.columnconfigure(0, weight=0)  # Logo
    header.columnconfigure(1, weight=1)  # Title (expandable)
    header.columnconfigure(2, weight=0)  # Info button
    header.columnconfigure(3, weight=0)  # info button

    # Logo
    try:
        logo_img = Image.open("assets/logo.png")
        logo_img = logo_img.resize((300, 93), Image.LANCZOS)
        logo = ImageTk.PhotoImage(logo_img)
        logo_label = Label(header, image=logo)
        logo_label.image = logo
        logo_label.grid(row=0, column=0, sticky="w", padx=(0, 10))
    except Exception as e:
        print(f"Logo load error: {e}")

    # Title (column 1)
    title = Label(header, text="TeeSense Current Capture", font=("Roboto", 25, "bold"))
    title.grid(row=0, column=1, sticky="w", pady=(10, 0))

    # Spacer (column 2) – just an empty space to push the button over
    info_button = Button(
        root,
        text="ℹ️",
        bootstyle="info-outline",
        command=show_about_window,
        width=1  # smaller text width
    )
    info_button.grid(
        row=0,
        column=1,
        sticky="ne",
        padx=10,
        pady=10,
        ipadx=2,
        ipady=1
    )

    # --- Port Frame ---
    port_frame = LabelFrame(root, text="USB Connection", padding=15)
    port_frame.grid(row=2, column=0, columnspan=2, padx=20, pady=10, sticky="ew")
    port_frame.columnconfigure(0, weight=0)
    port_frame.columnconfigure(1, weight=0)
    port_frame.columnconfigure(2, weight=0)
    port_frame.columnconfigure(3, weight=0)
    port_frame.columnconfigure(4, weight=1)  # status label can stretch if needed

    Label(port_frame, text="Select Port:").grid(row=0, column=0, padx=(0, 5), pady=5, sticky="e")

    def on_select_port():
        port = port_combobox.get()
        if port:
            global ser
            try:
                # Open the COM port connection
                ser = serial.Serial(port, 115200, parity=serial.PARITY_NONE,
                                    bytesize=serial.EIGHTBITS, timeout=1)
                ser.flushInput()
            
                # Update the UI status
                update_status(f"Connected: {port}", "success")
            
                # Show the Disconnect button
                disconnect_btn.grid(row=0, column=4, padx=(0, 5), pady=5, sticky="w")
                connect_btn.config(state="disabled")  # Disable Connect button
                refresh_btn.config(state="disabled")  # Disable Refresh button
            
                # Show the reading buttons (if needed)
                show_reading_buttons()
            except serial.SerialException:
                # Show error if connection fails
                update_status(f"Connection failed: {port}", "danger")
                messagebox.showerror("Connection Error", f"Could not connect to {port}")
        else:
            # Show warning if no port is selected
            messagebox.showwarning("Port Missing", "Please select a port.")

    port_combobox = Combobox(port_frame, values=get_available_ports(), width=15, state="readonly")
    port_combobox.grid(row=0, column=1, padx=(0, 5), pady=5, sticky="w")

    refresh_btn = Button(port_frame, text="Refresh", command=refresh_ports, bootstyle="info-outline")
    refresh_btn.grid(row=0, column=2, padx=(0, 5), pady=5, sticky="w")

    connect_btn = Button(port_frame, text="Connect", command=on_select_port, bootstyle="primary")
    connect_btn.grid(row=0, column=3, padx=(0, 5), pady=5, sticky="w")

    # --- Disconnect Button ---
    disconnect_btn = Button(port_frame, text="Disconnect", command=disconnect_port, bootstyle="danger-outline")
    disconnect_btn.grid(row=0, column=4, padx=(0, 5), pady=5, sticky="w")
    disconnect_btn.grid_forget()  # Initially hide the disconnect button

    # --- Status Frame ---
    status_label = Label(
        port_frame,
        text="Not Connected",
        bootstyle="danger",
        font=("Segoe UI", 9, "bold")
    )
    status_label.grid(row=0, column=4, padx=(10, 0), pady=5, sticky="e")

    # --- Sample Entry Frame Layout Adjustment ---
    sample_frame = LabelFrame(root, text="Acquisition Settings", padding=15)
    sample_frame.grid(row=3, column=0, columnspan=3, padx=20, pady=10, sticky="ew")
    sample_frame.columnconfigure(0, weight=0)  # 'Number of Samples' column
    sample_frame.columnconfigure(1, weight=1)  # 'Sample Entry' column
    sample_frame.columnconfigure(2, weight=0)  # 'Time Estimate' column
    sample_frame.columnconfigure(3, weight=0)  # 'DC Bias Message' column

    def update_sample_count(*args):
        # Get the value from num_samples (which is a StringVar)
        samples = num_samples.get()  # This will be a string from the user input

        # If the string is empty, set it to the default value (e.g., 10000)
        if not samples:  # If it's an empty string or None
            samples = 10000  # Default to 10000
        else:
            try:
                # Try converting the value to an integer
                samples = int(samples)  # Convert the string to an integer
            except ValueError:
                # If conversion fails (invalid number), set it to default value (10000)
                samples = 10000

        # Ensure the value doesn't exceed 10000, and it's not below 0
        if samples > 10000:
            samples = 10000
        elif samples < 0:
            samples = 0  # You can choose to set a lower limit, like 0

        # Set the updated value back to num_samples (StringVar) as a string
        num_samples.set(str(samples))  # Convert the integer back to a string

        # Now update the time estimate with the new sample value
        update_time_estimate()

    # Label and Entry field for samples
    Label(sample_frame, text="Number of Samples:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
    sample_entry = tk.Entry(sample_frame, width=12, textvariable=num_samples)
    sample_entry.grid(row=0, column=1, padx=(0, 5), pady=5, sticky="w")
    time_estimate_label = Label(sample_frame, textvariable=est_time, bootstyle="info")
    time_estimate_label.grid(row=0, column=2, padx=(0, 5), pady=5, sticky="w")

    Label(sample_frame, text="Filter Type:").grid(row=1, column=0, padx=5, pady=5, sticky="e")

    filter_var = StringVar(value="Filtered")  # default
    filter_dropdown = Combobox(sample_frame, textvariable=filter_var,
        values=["Filtered", "Unfiltered", "DC Bias"],
        state="readonly", width=15)
    filter_dropdown.grid(row=1, column=1, padx=(0, 5), pady=5, sticky="w")

    from tkinter import messagebox

    # --- Filter Mode Change Handler ---
    def filter_mode_changed(*args):
        dc_bias_message_label = Label(sample_frame, text="Warning: DC biasing plot takes ~50 seconds to load", foreground="red")
        # Show or hide the message when "DC Bias" is selected
        if filter_var.get() == "DC Bias":
            messagebox.showinfo("DC Bias Selected", "Warning: DC biasing plot takes ~50 seconds to load")
        else:
            dc_bias_message_label.grid_forget()  # Hide the message

    # Bind the dropdown selection change to the filter_mode_changed function
    filter_dropdown.bind("<<ComboboxSelected>>", filter_mode_changed)

    baseline_offset = 0.0  # Global offset

    def start_zeroing():
        global baseline_offset, ser

        if not ser or not ser.is_open:
            messagebox.showerror("Connection Error", "Serial port not open.")
            return

        update_status("Zeroing in progress...", "warning")
        zero_data = []  # ← Use a separate list, not `data`
        ser.reset_input_buffer()
        ser.write(b'ZERO\n')  # Signal to MCU
        time.sleep(0.5)
        ser.reset_input_buffer()    

        start_time = time.time()
        timeout = 10  # seconds
        skip_first = True
        while len(zero_data) < 100 and (time.time() - start_time) < timeout:
            if ser.in_waiting > 0:
                line = ser.readline().decode('utf-8').strip()
                try:
                    parts = list(map(int, line.split()))
                    if len(parts) >= 4:
                        if skip_first:
                            print(f"Skipping first timing line: {parts}")
                            skip_first = False
                            continue
                        adc1 = (parts[0] << 8) | parts[1]
                        adc2 = (parts[2] << 8) | parts[3]
                        avg_adc = (adc1 + adc2) / 2.0
                        zero_data.append(avg_adc)
                except:
                    continue

        ser.reset_input_buffer()  # Flush after zeroing!

        if zero_data:
            ByteCombine.baseline_adc_value = sum(zero_data) / len(zero_data)
            update_status(f"Zeroing complete. Baseline ADC: {ByteCombine.baseline_adc_value:.2f}", "success")
            ser.reset_input_buffer()
        else:
            update_status("Zeroing failed: No data received.", "danger")

    def update_time_estimate(*args):
        try:
            samples = int(num_samples.get())
            seconds = samples / 1_220_000
            milliseconds = seconds * 1000
            microseconds = seconds * 1_000_000
            est_time.set(f"~{seconds:.3f} s / {milliseconds:.1f} ms / {microseconds:.0f} us")
        except:
            est_time.set("~-- s / -- ms / -- us")

    num_samples.trace_add("write", update_time_estimate)
    update_time_estimate()

    def disable_buttons():
        """Disable all buttons except for Stop."""
        start_button.config(state="disabled")
        zero_button.config(state="disabled")
        connect_btn.config(state="disabled")
        refresh_btn.config(state="disabled")
        # Disable other buttons as needed

    def enable_buttons():
        """Enable all buttons except for Stop."""
        start_button.config(state="normal")
        zero_button.config(state="normal")
        connect_btn.config(state="normal")
        refresh_btn.config(state="normal")
        # Enable other buttons as needed

    def start_reading():
        """Start a new thread for reading from the serial port."""
        global data
        data = []  #Clear any previous data (zeroing or partial runs)
        buffer = b""
        global stop_thread, sample_count
        stop_thread = False
        selected_mode = filter_var.get()
        disable_buttons()

        if selected_mode == "DC Bias":
            try:
                ser.write(b'RESET\n')
                time.sleep(0.5)
                ser.reset_input_buffer()

                print("Starting DC Bias read")
                samples = []
                skip_first = True
                start_time = time.time()
                timeout = 60  # seconds

                while time.time() - start_time < timeout:
                    if ser.in_waiting:
                        line = ser.readline().decode('utf-8').strip()
                        try:
                            parts = list(map(int, line.split()))
                            if skip_first:
                                print(f"Skipping first timing line: {parts}")
                                skip_first = False
                                continue
                            if len(parts) == 4:
                                samples.append(parts)
                        except:
                            continue
                    else:
                        time.sleep(0.001)

                ser.close()

                if not samples:
                    messagebox.showerror("Error", "No data collected in DC Bias mode.")
                    return

                # Pre-format the data as expected: [time, byte1, byte2, byte3, byte4]
                sample_interval = 1 / 1_220_000
                formatted = [[i * sample_interval] + row for i, row in enumerate(samples)]

                retake_settings = {
                    "port": ser.port,  # Get from open serial object
                    "filter_mode": filter_var.get()  # From dropdown
                }

                # Call existing GUI launcher (this will use process_dc_bias_data internally)
                process_and_launch_gui(formatted, retake_settings)
            except Exception as e:
                messagebox.showerror("Error", f"DC Bias mode failed:\n{e}")
            return

        try:
            sample_count = int(sample_entry.get())
            if sample_count <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid Input", "Please enter a valid number of samples (> 0).")
            return

        ser.write(b'RESET\n')
        time.sleep(0.5)  # Ensure MCU has time to start waveform
        ser.reset_input_buffer()  # Final clean start
        reading_thread = threading.Thread(target=read_from_serial, daemon=True)
        reading_thread.start()
        enable_buttons()

    def stop_reading():
        global stop_thread
        stop_thread = True
        update_status("Reading stopped", "danger")
        if ser and ser.is_open:
            ser.close()
        

    # --- Control Frame ---
    control_frame = LabelFrame(root, text="Data Control", padding=15)
    control_frame.grid(row=4, column=0, columnspan=2, padx=20, pady=10, sticky="ew")
    control_frame.columnconfigure(0, weight=1)
    control_frame.columnconfigure(1, weight=1)
    control_frame.columnconfigure(2, weight=1)

    start_button = Button(control_frame, text="Start Reading", command=start_reading, bootstyle="success-outline")
    zero_button = Button(control_frame, text="Zero Current", command=start_zeroing, bootstyle="warning-outline")
    stop_button = Button(control_frame, text="Stop", command=stop_reading, bootstyle="danger-outline")


if __name__ == "__main__":
    create_tkinter_gui()

