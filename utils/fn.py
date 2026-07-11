from gpiozero import OutputDevice, ButtonBoard, LED
from tzfpy import get_tz
from pathlib import Path
from time import sleep
import pytz
import json
import pigpio
import os
from astral import LocationInfo
from astral.sun import sun
import datetime

# BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# DATA_PATH = os.path.join(BASE_DIR, 'data.json')
# .parent is utils/, .parent.parent is service/
DATA_PATH = Path(__file__).resolve().parent.parent / "data.json"

# Pins: [PUL, DIR]
X = [OutputDevice(17), OutputDevice(27)]
Y = [OutputDevice(23), OutputDevice(24)]

# Pins: x=azimuth, y=elevation
# x1, y1 >> LEFT
# x2, y2 >> RIGHT
LIMIT = ButtonBoard(x1=26, x2=16, y1=19, y2=20, pull_up=False)


def get_utc_from_local(lat, lon, naive_dt):
    # Note: tzfpy uses (longitude, latitude) order!
    tz_name = get_tz(lon, lat)
    
    # Convert the "naive" time (14:30) into that local timezone
    local_tz = pytz.timezone(tz_name)
    local_dt = local_tz.localize(naive_dt)
    
    # Convert that local time to UTC
    utc_dt = local_dt.astimezone(pytz.utc)
    return utc_dt


def get_sunrise_sunset_azimuth(lat, lon):
    # Note: tzfpy uses (longitude, latitude) order!
    tz_name = get_tz(lon, lat)
    
    # Convert the "naive" time (14:30) into that local timezone
    local_tz = pytz.timezone(tz_name)
    now = datetime.datetime.now(local_tz)

    city = LocationInfo("Dynamic City", "Region", tz_name, lat, lon)
    s = sun(city.observer, date=now, tzinfo=local_tz)
    sunrise = s['sunrise']
    sunset = s['sunset']
    
    # 3. Calculate Horizontal Position (The X-Axis / Progress)
    total_daylight_seconds = (sunset - sunrise).total_seconds()
    elapsed_seconds = (now - sunrise).total_seconds()

    # Calculate percentage of day completed (0.0 to 1.0)
    # clamp to 0 and 1 so the sun doesn't move off screen at night
    day_progress = max(0.0, min(1.0, elapsed_seconds / total_daylight_seconds))

    # Map to a 180-degree arc for your 2D drawing (Left to Right)
    x_arc_position = day_progress * 180  

    return x_arc_position

def constants(step = 0, ratio = 1):
    # Motor Specs
    SPR = 200            # Standard 1.8 degree motor (360 / 1.8)
    MICROSTEPS = 16      # Driver microstepping settings
    RPM = 60             # Target speed
    TARGET_ANGLE = step  # Change this to whatever angle you want (e.g., 360, 720)
    RATIO = ratio        # Gear ratio for geared motor

    # 1. Calculate how many pulses we need for the desired angle
    # (120 / 1.8) * 16 = 1,066.66 steps * gear ratio
    total_steps = int((TARGET_ANGLE / 1.8) * MICROSTEPS * RATIO)

    # 2. Calculate delay for the speed (RPM)
    # Total pulses for one full 360 degree rev = 3200
    pulses_per_rev = SPR * MICROSTEPS
    step_delay = (60 / RPM) / pulses_per_rev / 2
    return {
        'steps': total_steps,
        'delay': step_delay
    }

def move(axis, steps, delay, isHoming = False):
    motor = X if axis == 'X' else Y

    if steps < 0:
        motor[1].on()
    else:
        motor[1].off()
    

    init_p1 = getattr(LIMIT, f'{axis.lower()}1').is_active

    normalized_steps = abs(steps)
    for i in range(normalized_steps):
        p1 = getattr(LIMIT, f'{axis.lower()}1')
        p2 = getattr(LIMIT, f'{axis.lower()}2')

        if isHoming:
            if p1.is_active:
                light('off')
                print('Homing complete...')
                return i
        else:
            # STOP if moving negative (left/down) and hit home limit
            if steps < 0 and p1.is_active:
                light('off')
                print("Already at home/left-most side...")
                return i
            
            # STOP if moving positive (right/up) and hit far limit
            if steps > 0 and p2.is_active:
                light('off')
                print("Reached the far limit...")
                return i

        motor[0].on()
        sleep(delay)
        motor[0].off()
        sleep(delay)

    return steps


def origin():
    axis = ['Y', 'X']
    # axis = ['Y']
    light('off')

    for plane in axis:
        gear_ratio = 15 if plane == 'X' else 9.8
        attr = constants(360, gear_ratio)
        negative_steps = attr['steps'] * -1
        move(plane, negative_steps, attr['delay'], True)

def check_position():
    pos = 'LEFT'
    axis = ['Y', 'X']
    light('off')


    for plane in axis:
        gear_ratio = 15 if plane == 'X' else 19.6
        attr = constants(10, gear_ratio)
        steps = attr['steps']
        left = move(plane, steps, attr['delay'], True)
        sleep(0.5)
        right = move(plane, steps * -1, attr['delay'], True)

        if int(right) >= int(left):
            pos = 'RIGHT'

    # print(f"{'move towards left' if pos == 'RIGHT' else 'already on the left'}", flush=True)
    # print(f'is in right ?? {pos}', flush=True)
    return pos

def light(state):
    isOn = 1 if state.lower() == 'on' else 0
    pi = pigpio.pi()

    if not pi.connected:
        exit()

    pi.write(21, isOn)
    pi.stop()

def rd_data():
    with open(DATA_PATH, 'r') as f:
        data = json.load(f)
    
    return {
        'status': data.get('status', 'idle'),
        'azimuth': data.get('azimuth', 0.0),
        'elevation': data.get('elevation', 0.0)
    }

def wr_data(data):
    with open(DATA_PATH, 'w') as f:
        json.dump(data, f, indent=4) # indent makes it readable


def set_data(state, config):
    if state == 'PENDING':
        config['status'] = state.lower()
        wr_data(config)

    if state == 'IDLE':
        config['status'] = state.lower()
        wr_data(config)
    