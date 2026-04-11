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

    # The Global Compass Convention (also known as the Navigation Convention)
    # is the worldwide standard for defining direction.
    # It treats the horizon as a 360° circle where every number
    # corresponds to a specific cardinal direction.

    if lat >= 0: 
        # NORTHERN HEMISPHERE (e.g., Philippines, USA)
        # Sun path: 90 (E) -> 180 (S) -> 270 (W)
        # We want:  0 (E)  -> 90 (S)  -> 180 (W)
        normalize_az = azimuth - 90
        normalize_el = 180 - altitude

    else: 
        # SOUTHERN HEMISPHERE (e.g., Cape Town)
        # Sun path: 90 (E) -> 0 (N)  -> 270 (W)
        # We want:  0 (E)  -> 90 (N) -> 180 (W)
        normalize_az = (90 - azimuth) % 360
        normalize_el = altitude

    data = {
        "azimuth":  normalize_az,
        "elevation": normalize_el,
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
        gear_ratio = 15 if key == 'azimuth' else 19.6
        deg_in_step = (value -  10) if key == 'azimuth' else value

        attr = fn.constants(deg_in_step, gear_ratio) 

        # attr = fn.constants(-20, gear_ratio) >> test
        fn.move(axis, attr['steps'], attr['delay'])

        results.append({"axis": axis, "angle": value, "status": "Moved"})
        results.append(attr)

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