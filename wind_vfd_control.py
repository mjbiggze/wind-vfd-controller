# ... [imports and setup remain unchanged]
import time
import threading
from tkinter import *
from datetime import datetime
import board
import busio
import adafruit_ads1x15.ads1115 as ADS
from adafruit_ads1x15.analog_in import AnalogIn
import minimalmodbus
import smtplib
from email.mime.text import MIMEText
from flask import Flask, request, render_template_string, redirect

# Initialize ADS1115 and Modbus VFD (same as before)
# ... [unchanged setup]

# --- Flask setup and global variables remain unchanged ---

# GUI Setup
root = Tk()
root.title("Wind VFD Controller")
root.geometry("550x720")

# Create scrollable canvas
canvas = Canvas(root)
scroll_y = Scrollbar(root, orient="vertical", command=canvas.yview)
scroll_frame = Frame(canvas)

scroll_frame.bind(
    "<Configure>",
    lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
)

canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
canvas.configure(yscrollcommand=scroll_y.set)
canvas.pack(fill=BOTH, expand=True, side=LEFT)
scroll_y.pack(fill=Y, side=RIGHT)

# Mode toggle
mode_var = StringVar(value="Auto")
def set_mode():
    global mode
    mode = mode_var.get()

Radiobutton(scroll_frame, text="Auto", variable=mode_var, value="Auto", command=set_mode).pack()
Radiobutton(scroll_frame, text="Manual", variable=mode_var, value="Manual", command=set_mode).pack()

# Slider mapping side-by-side layout
slider_vars = []
for i, (mph, hz) in enumerate(slider_map):
    row = Frame(scroll_frame)
    mph_var = IntVar(value=mph)
    hz_var = IntVar(value=hz)
    slider_vars.append((mph_var, hz_var))

    Scale(row, from_=0, to=100, variable=mph_var, label=f"MPH {i+1}", orient=VERTICAL).pack(side=LEFT, padx=10)
    Scale(row, from_=0, to=60, variable=hz_var, label=f"Hz {i+1}", orient=VERTICAL).pack(side=LEFT, padx=10)

    row.pack(pady=5)

def update_sliders():
    global slider_map
    slider_map = [(mph.get(), hz.get()) for mph, hz in slider_vars]

Button(scroll_frame, text="Apply Slider Settings", command=update_sliders).pack(pady=5)

# Manual slider
manual_slider = Scale(scroll_frame, from_=0, to=60, label="Manual Hz", orient=HORIZONTAL)
manual_slider.set(30)
manual_slider.config(command=lambda val: update_manual_hz(val))
manual_slider.pack(pady=5)

def update_manual_hz(val):
    global manual_hz
    manual_hz = int(val)

# Displays
wind_label = Label(scroll_frame, text="0 MPH", font=("Arial", 24))
wind_label.pack(pady=5)

hz_label = Label(scroll_frame, text="0 Hz", font=("Arial", 24))
hz_label.pack(pady=5)

valve_label = Label(scroll_frame, text="Valve OFF", font=("Arial", 18))
valve_label.pack(pady=5)

clock_label = Label(scroll_frame, font=("Arial", 18))
clock_label.pack(pady=5)

# Email settings
Label(scroll_frame, text="Gmail Address").pack()
gmail_entry = Entry(scroll_frame, width=40)
gmail_entry.pack()

Label(scroll_frame, text="Gmail App Password").pack()
gmail_pass_entry = Entry(scroll_frame, width=40, show="*")
gmail_pass_entry.pack()

Label(scroll_frame, text="Recipient Email").pack()
recipient_entry = Entry(scroll_frame, width=40)
recipient_entry.pack()

email_time_slider = Scale(scroll_frame, from_=10, to=600, label="Seconds before alert", orient=HORIZONTAL)
email_time_slider.set(60)
email_time_slider.pack()
slider_map = [(10, 30), (20, 20), (30, 10)]

def update_email_settings():
    global gmail_user, gmail_pass, recipient_email, email_timer
    gmail_user = gmail_entry.get()
    gmail_pass = gmail_pass_entry.get()
    recipient_email = recipient_entry.get()
    email_timer = email_time_slider.get()

Button(scroll_frame, text="Apply Email Settings", command=update_email_settings).pack(pady=5)

# Web login route
@app.route("/", methods=["GET", "POST"])
def login():
    global logged_in
    if request.method == "POST":
        if request.form.get("user") == USERNAME and request.form.get("pass") == PASSWORD:
            logged_in = True
            return redirect("/status")
    return render_template_string("""
    <form method="post">
        <h3>Login</h3>
        Username: <input name="user"><br>
        Password: <input name="pass" type="password"><br>
        <input type="submit">
    </form>
    """)

@app.route("/status")
def status():
    if not logged_in:
        return redirect("/")
    return f"<h2>Wind: {wind_speed:.2f} MPH<br>VFD: {vfd_output_hz:.1f} Hz<br>Valve: {status_text}</h2>"

# Function definitions for logic remain unchanged...
# read_wind_mph(), is_valve_on(), send_email_alert(), update_vfd(), etc.

# Start GUI and Flask web server
def gui_loop():
    global wind_speed, vfd_output_hz, status_text

    mph = read_wind_mph()
    wind_speed = mph

    if mode == "Auto":
        for threshold, hz in reversed(sorted(slider_map)):
            if mph >= threshold:
                vfd_output_hz = hz
                break
        else:
            vfd_output_hz = 60
    else:
        vfd_output_hz = manual_hz

    threading.Timer(15, lambda: update_vfd(vfd_output_hz)).start()

    if is_valve_on():
        status_text = "Valve ON"
        if not hasattr(gui_loop, 'on_time'):
            gui_loop.on_time = time.time()
        elif time.time() - gui_loop.on_time > email_timer:
            send_email_alert()
            gui_loop.on_time = time.time() + 3600
    else:
        status_text = "Valve OFF"
        if hasattr(gui_loop, 'on_time'):
            del gui_loop.on_time

    root.after(1000, update_gui_labels)

def update_gui_labels():
    wind_label.config(text=f"{wind_speed:.2f} MPH")
    hz_label.config(text=f"{vfd_output_hz:.1f} Hz")
    valve_label.config(text=status_text)
    clock_label.config(text=datetime.now().strftime("%H:%M:%S"))
    root.after(1000, gui_loop)

def start_web():
    app.run(host="0.0.0.0", port=5000)

threading.Thread(target=start_web, daemon=True).start()
root.after(1000, gui_loop)
root.mainloop()
