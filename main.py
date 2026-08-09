from flask import Flask,render_template, request, jsonify
import subprocess
from datetime import datetime, timezone
from pysolar.solar import get_azimuth, get_altitude
from utils import fn

app = Flask(__name__)

# This route serves your HTML page
@app.route('/')
def WEBSERVE():
    return render_template('index.html')

@app.route("/calibrate", methods=['GET', 'POST'])
def SLR():
    json_data = request.get_json(silent=True) or {}

    lat = float(json_data.get('latitude') or request.values.get('latitude', 0.0))
    lon = float(json_data.get('longitude') or request.values.get('longitude', 0.0))
    dt = json_data.get('datetime') or request.values.get('datetime')
    
    if dt:
        clean_date = datetime.strptime(dt, '%Y-%m-%dT%H:%M')
    else:
        clean_date = datetime.now()
    
    date = fn.get_utc_from_local(lat, lon, clean_date)

    azimuth = get_azimuth(lat, lon, date)
    altitude = get_altitude(lat, lon, date)

    # Sole source of truth for both motors: projects 3D solar azimuth/altitude
    # onto the 2D heliodon's 0-180 (X) / 0-90 (Y) physical arcs.
    motor_angles = fn.calculate_heliodon_angles(azimuth, altitude)

    data = {
        "azimuth": motor_angles['motor_x'],
        "elevation": motor_angles['motor_y'],
    }
    results = []
    config = fn.rd_data()
    def idle():
        config['status'] = 'idle'
        config['azimuth'] = 0.0
        config['elevation'] = 0.0
        fn.set_data('IDLE', config)
    
    # fn.check_position()
    if config['status'] == 'pending' or config['azimuth'] > 0 or config['elevation'] > 0:
        fn.origin()
        idle()
    
    config['status'] = 'pending'
    config['azimuth'] = data['azimuth']
    config['elevation'] = data['elevation']
    fn.set_data('PENDING', config)

    for key, value in data.items():
        axis = 'X' if key == 'azimuth' else 'Y'
        if key == 'elevation':
            fn.light('on')
        # Gear ratio of the x and y motor
        gear_ratio = fn.AZIMUTH_GEAR_RATIO if key == 'azimuth' else fn.ELEVATION_GEAR_RATIO
        deg_in_step = (value - fn.AZIMUTH_ARC_TRIM_DEG) if key == 'azimuth' else value
        attr = fn.constants(deg_in_step, gear_ratio)
        # attr = fn.constants(-20, gear_ratio) >> test
        # fn.move(axis, attr['steps'], attr['delay'])
        # results.append({"axis": axis, "angle": value, "status": "Moved"})
        # results.append(attr)
    return jsonify({'azimuth': azimuth, 'elevation': altitude })

@app.route("/shutdown", methods=['GET', 'POST'])
def SHTDWN():
    fn.origin()
    subprocess.run(['sudo', 'shutdown', '-h', 'now'])
    return "Shutting down..."

@app.route("/reset", methods=['GET', 'POST'])
def RST():
    fn.origin()
    subprocess.run(['sudo', 'reboot'])
    return "Rebooting..."

@app.route("/reinit", methods=['GET', 'POST'])
def REINIT():
    fn.origin()
    return "Re-initializing..."

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=4001)