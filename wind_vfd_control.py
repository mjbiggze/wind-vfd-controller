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

# Initialize ADS1115
i2c = busio.I2C(board.SCL, board.SDA)
ads = ADS.ADS1115(i2c)
wind_channel = AnalogIn(ads, ADS.P0)
current_channel = AnalogIn(ads, ADS.P1)

# VFD setup (adjust port & settings if needed)
vfd = minimalmodbus.Instrument('/dev/ttyUSB0', 1)
vfd.serial.baudrate = 9600
vfd.serial.timeout = 1

# Flask app for web login
app = Flask(__name__)
USERNAME = "Mckwind"
PASSWORD = "18281828"
logged_in = False

# Global GUI state
mode = "Auto"
wind_speed = 0
vfd_output_hz = 0
manual_hz = 30
status_text = "Valve OFF"
email_timer = 60
max_wind = 30
recipient_email = ""
gmail_user = ""
gmail_pass = ""
slider_map = [(10, 30), (20, 20), (30, 10)]

# GUI update function
def update_vfd(hz):
    try:
        vfd.write_register(1, int(hz * 10))
    except Exception as e:
        print("VFD Error:", e)

def read_wind_mph():
    millivolts = wind_channel.voltage * 1000
    return round(0.01342 * millivolts, 2)

def is_valve_on():
    current_mv = current_channel.voltage * 1000
    return current_mv > 200

def send_email_alert():
    try:
        msg = MIMEText("Valve has been ON too long.")
        msg['Subject'] = "VFD Alert"
        msg['From'] = gmail_user
        msg['To'] = recipient_email

        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(gmail_user, gmail_pass)
        server.send_message(msg)
        server.quit()
        print("Alert email sent")
    except Exception as e:
        print("Email failed:", e)

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

# Build GUI
root = Tk()
root.title("Wind VFD Controller")
root.geometry("500x700")

# Mode toggle
mode_var = StringVar(value="Auto")
def set_mode():
    global mode
    mode = mode_var.get()

Radiobutton(root, text="Auto", variable=mode_var, value="Auto", command=set_mode).pack()
Radiobutton(root, text="Manual", variable=mode_var, value="Manual", command=set_mode).pack()

# Slider mapping
slider_vars = []
for i, (mph, hz) in enumerate(slider_map):
    Label(root, text=f"MPH > {mph}: Set to {hz} Hz").pack()
    mph_var = IntVar(value=mph)
    hz_var = IntVar(value=hz)
    slider_vars.append((mph_var, hz_var))
    Scale(root, from_=0, to=100, variable=mph_var, label=f"MPH {i+1}").pack()
    Scale(root, from_=0, to=60, variable=hz_var, label=f"Hz {i+1}").pack()

def update_sliders():
    global slider_map
    slider_map = [(mph.get(), hz.get()) for mph, hz in slider_vars]

Button(root, text="Apply Slider Settings", command=update_sliders).pack()

# Manual slider
manual_slider = Scale(root, from_=0, to=60, label="Manual Hz", orient=HORIZONTAL)
manual_slider.set(30)
manual_slider.pack()
def update_manual_hz(val):
    global manual_hz
    manual_hz = int(val)
manual_slider.config(command=update_manual_hz)

# Live display
wind_label = Label(root, text="0 MPH", font=("Arial", 24))
wind_label.pack()

hz_label = Label(root, text="0 Hz", font=("Arial", 24))
hz_label.pack()

valve_label = Label(root, text="Valve OFF", font=("Arial", 18))
valve_label.pack()

clock_label = Label(root, font=("Arial", 18))
clock_label.pack()

# Email settings
Entry(root, width=40, justify=LEFT, textvariable=StringVar(value="Gmail Address")).pack()
gmail_entry = Entry(root, width=40)
gmail_entry.pack()

Entry(root, width=40, justify=LEFT, textvariable=StringVar(value="Gmail App Password")).pack()
gmail_pass_entry = Entry(root, width=40, show="*")
gmail_pass_entry.pack()

Entry(root, width=40, justify=LEFT, textvariable=StringVar(value="Recipient Email")).pack()
recipient_entry = Entry(root, width=40)
recipient_entry.pack()

email_time_slider = Scale(root, from_=10, to=600, label="Seconds before alert", orient=HORIZONTAL)
email_time_slider.set(60)
email_time_slider.pack()

def update_email_settings():
    global gmail_user, gmail_pass, recipient_email, email_timer
    gmail_user = gmail_entry.get()
    gmail_pass = gmail_pass_entry.get()
    recipient_email = recipient_entry.get()
    email_timer = email_time_slider.get()
Button(root, text="Apply Email Settings", command=update_email_settings).pack()

# Web login interface
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

# Run GUI and web server
def start_web():
    app.run(host="0.0.0.0", port=5000)

threading.Thread(target=start_web, daemon=True).start()
root.after(1000, gui_loop)
root.mainloop()



