from flask import Flask,render_template, request, jsonify
import subprocess
from datetime import datetime, timezone
from pysolar.solar import get_azimuth, get_altitude
from utils import fn
# import Rpi.GPIO as GPIO

app = Flask(__name__)
# Tell Flask to look in 'my_pages' instead of 'templates'
# app = Flask(__name__, template_folder='folder path')

# This route serves your HTML page
@app.route('/')
def WEBSERVE():
    return render_template('index.html')

@app.route("/calibrate", methods=['GET', 'POST'])
def SLR():
    lat = float(request.values.get('lat', 0.0))
    lon = float(request.values.get('lon', 0.0))
    dt = request.values.get('datetime') # format >> "2026-02-07T14:30"

    if dt:
        clean_date = datetime.strptime(dt, '%Y-%m-%dT%H:%M')
    else:
        clean_date = datetime.now()
    date = clean_date.replace(tzinfo=timezone.utc) # format >> should be utc aware for pysolar to accept

    azimuth = get_azimuth(lat, lon, date)
    altitude = get_altitude(lat, lon, date)

    data = {
        "azimuth":  azimuth,
        "elevation": altitude,
    }

    results = []

    config = fn.rd_data()
    if config['status'] == 'pending' or config['azimuth'] > 0 or config['elevation'] > 0:
        fn.origin()
    
    for key, value in data.items():
        axis = 'X' if key == 'azimuth' else 'Y'

        if key == 'elevation':
            fn.light('on')

        # NOTE: change gear ratio base on the actual ratio of ark/planetary gear
        # NOTE: change this base on gear ratio of the x and y motor
        gear_ratio = 1 if key == 'elevation' else 15

        attr = fn.constants(value, gear_ratio) 
        fn.move(axis, attr['steps'], attr['delay'])

        results.append({"axis": axis, "angle": value, "status": "Moved"})

    return jsonify(data)

@app.route("/shutdown", methods=['GET', 'POST'])
def SHTDWN():
    subprocess.run(['sudo', 'shutdown', '-h', 'now'])
    return "Shutting down..."

@app.route("/reset", methods=['GET', 'POST'])
def RST():
    subprocess.run(['sudo', 'reboot'])
    return "Rebooting..."

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=4001)