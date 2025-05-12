import serial
import time
import csv
import threading
import subprocess
import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter import StringVar, IntVar
from PIL import Image, ImageTk
from ttkbootstrap import Style
from ttkbootstrap.constants import *
from ttkbootstrap.widgets import Frame, LabelFrame, Button, Label, Combobox

from ByteCombine import process_filtered_data, process_unfiltered_data


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


def on_select_port():
    port = port_combobox.get()
    if port:
        global ser
        try:
            ser = serial.Serial(port, 115200, parity=serial.PARITY_NONE,
                                bytesize=serial.EIGHTBITS, timeout=1)
            ser.flushInput()
            update_status(f"Connected to {port}", "success")
            show_reading_buttons()
        except serial.SerialException:
            update_status(f"Connection failed: {port}", "danger")
            messagebox.showerror("Connection Error", f"Could not connect to {port}")
    else:
        messagebox.showwarning("Port Missing", "Please select a port.")


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


def stop_reading():
    global stop_thread
    stop_thread = True
    update_status("Reading stopped", "danger")


def read_from_serial():
    global data
    data = []
    buffer = b""
    start_time = None

    try:
        while not stop_thread:
            if ser.in_waiting > 0:
                # Read all available bytes at once
                buffer += ser.read(ser.in_waiting)

                # Split lines
                while b'\n' in buffer:
                    line, buffer = buffer.split(b'\n', 1)
                    
                    if start_time is None:
                        start_time = time.time()

                    try:
                        decoded = line.decode('utf-8').strip()
                        values = list(map(int, decoded.split()))
                        elapsed_ms = round((time.time() - start_time), 2)
                        data.append([elapsed_ms] + values)
                        print(f"Received: {values} (Elapsed: {elapsed_ms} s)")
                    except ValueError:
                        print(f"Parse error: {line}")

                    if len(data) >= sample_count:
                        break
                    stop_reading()
    except serial.SerialException as e:
        print(f"Serial error: {e}")
    except KeyboardInterrupt:
        print("Stopped by user.")

    if data:
        ask_for_save_location(data)


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


def ask_for_save_location(data):
    response = messagebox.askyesnocancel(
        "Save Data",
        "Would you like to save the filtered data?\n\n"
        "Yes = Save filtered\n"
        "No = Save raw\n"
        "Cancel = Don't save"
    )

    if response is None:
        update_status("User cancelled saving", "info")
        return

    save_path = filedialog.asksaveasfilename(
        title="Save Data As",
        defaultextension=".csv",
        filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
    )

    if save_path:
        write_data_to_csv(data, save_path)
        if response:
            process_filtered_data(save_path)
        else:
            process_unfiltered_data(save_path)
    else:
        update_status("Save path cancelled", "warning")


def update_status(message, status_type="info"):
    status_label.config(text=message)
    status_label.config(bootstyle=status_type)


def show_reading_buttons():
    start_button.pack(side="left", padx=10, pady=10)
    stop_button.pack(side="right", padx=10, pady=10)


def create_gui():
    root = tk.Tk()
    style = Style("flatly")  # Light theme
    root.title("TeeSense USB Data Logger")
    root.geometry("800x500")  # Or wider if needed
    root.resizable(False, False)
    root.columnconfigure(1, weight=1)
    start_main_application(root)
    root.mainloop()


def start_main_application(root):
    global port_combobox, start_button, stop_button, status_label, sample_entry, time_estimate_label, num_samples

    num_samples = IntVar(value=200)
    est_time = StringVar(value="~0.000 s")

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

    port_combobox = Combobox(port_frame, values=get_available_ports(), width=15, state="readonly")
    port_combobox.grid(row=0, column=1, padx=(0, 5), pady=5, sticky="w")

    refresh_btn = Button(port_frame, text="Refresh", command=refresh_ports, bootstyle="info-outline")
    refresh_btn.grid(row=0, column=2, padx=(0, 5), pady=5, sticky="w")

    connect_btn = Button(port_frame, text="Connect", command=on_select_port, bootstyle="primary")
    connect_btn.grid(row=0, column=3, padx=(0, 5), pady=5, sticky="w")

    # --- Status Frame ---
    status_label = Label(
        port_frame,
        text="Not Connected",
        bootstyle="danger",
        font=("Segoe UI", 9, "bold")
    )
    status_label.grid(row=0, column=4, padx=(10, 0), pady=5, sticky="w")

    # --- Sample Entry Frame ---
    sample_frame = LabelFrame(root, text="Acquisition Settings", padding=15)
    sample_frame.grid(row=3, column=0, columnspan=2, padx=20, pady=10, sticky="ew")
    sample_frame.columnconfigure(0, weight=0)
    sample_frame.columnconfigure(1, weight=1)
    sample_frame.columnconfigure(2, weight=1)
    sample_frame.columnconfigure(3, weight=1)

    sample_frame.columnconfigure(0, weight=0)
    sample_frame.columnconfigure(1, weight=0)
    sample_frame.columnconfigure(2, weight=1)

    Label(sample_frame, text="Number of Samples:").grid(row=0, column=0, padx=5, pady=5, sticky="e")
    sample_entry = tk.Entry(sample_frame, width=12, textvariable=num_samples)
    sample_entry.grid(row=0, column=1, padx=(0, 5), pady=5, sticky="w")
    time_estimate_label = Label(sample_frame, textvariable=est_time, bootstyle="info")
    time_estimate_label.grid(row=0, column=2, padx=(0, 5), pady=5, sticky="w")


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

    # --- Control Frame ---
    control_frame = LabelFrame(root, text="Data Control", padding=15)
    control_frame.grid(row=4, column=0, columnspan=2, padx=20, pady=10, sticky="ew")
    control_frame.columnconfigure(0, weight=1)
    control_frame.columnconfigure(1, weight=1)

    start_button = Button(control_frame, text="Start Reading", command=start_reading, bootstyle="success-outline")
    stop_button = Button(control_frame, text="Stop", command=stop_reading, bootstyle="danger-outline")


if __name__ == "__main__":
    create_gui()
