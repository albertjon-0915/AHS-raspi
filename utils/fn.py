from gpiozero import OutputDevice, ButtonBoard, LED
from tzfpy import get_tz
from pathlib import Path
from time import sleep
import pytz
import json
import pigpio
import os


# BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# DATA_PATH = os.path.join(BASE_DIR, 'data.json')
# .parent is utils/, .parent.parent is service/
DATA_PATH = Path(__file__).resolve().parent.parent / "data.json"

# Pins: [PUL, DIR]
X = [OutputDevice(17), OutputDevice(27)]
Y = [OutputDevice(23), OutputDevice(24)]

# Pins: x=azimuth, y=elevation
LIMIT = ButtonBoard(x=16, y=20, pull_up=False)

TARGET_ANGLE = 0

def get_utc_from_local(lat, lon, naive_dt):
    # Note: tzfpy uses (longitude, latitude) order!
    tz_name = get_tz(lon, lat)
    
    # Convert the "naive" time (14:30) into that local timezone
    local_tz = pytz.timezone(tz_name)
    local_dt = local_tz.localize(naive_dt)
    
    # Convert that local time to UTC
    utc_dt = local_dt.astimezone(pytz.utc)
    return utc_dt

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

def move(axis, steps, delay, isCalibration = False):
    motor = X if axis == 'X' else Y
    direction = 'negative'

    if steps < 0:
        print('negative steps', flush=True)
        motor[1].on()
        direction = 'negative'
    else:
        motor[1].off()
        direction = 'positive'

        
    steps = abs(steps)
    for i in range(steps):
        point = getattr(LIMIT, axis.lower())

        # isStop = False
        # if not isOrigin:
        #     isStop = point.is_active
        # else:
        #     if i > 500 and point.is_active: 
        #         isStop = True

        # print(isStop, flush=True)
        # if isStop:
        #     light('off')
        #     # print(f"Reached the limit of system's angle...")
        #     break

        if point.is_active:
                light('off')
                print(f"Reached the limit of system's angle...")
                return i

                # if direction == 'negative':
                #     motor[1].off()
                # else:
                #     motor[1].on()

                # while point.is_active:
                #     motor[0].on()
                #     sleep(delay)
                #     motor[0].off()
                #     sleep(delay)
                # return i
            # if not isCalibration:
            #     light('off')
            #     print(f"Reached the limit of system's angle...")
            #     return i
            # elif isCalibration and i >= steps // 2:
            #     light('off')
            #     print(f"Reached the limit of system's angle...")
            #     return i

        # motor[0].on()
        # sleep(delay)
        # motor[0].off()
        # sleep(delay)

    print(f"Moving {TARGET_ANGLE} degrees...")
    return steps


def origin(loaded):
    # axis = ['Y', 'X']
    solar = ['azimuth', 'elevation']
    light('off')

    # for plane in axis:
    #     gear_ratio = 15 if plane == 'X' else 7
    #     attr = constants(360, gear_ratio)
    #     negative_steps = attr['steps'] * -1
    #     # print('negative_steps', flush=True)
    #     # print(negative_steps, flush=True)
    #     move(plane, negative_steps, attr['delay'], True)

    for item in solar:
        axis = 'X' if item == 'azimuth' else 'Y'
        gear_ratio = 15 if item == 'azimuth' else 7
        if loaded[item] > 0:
            attr = constants(loaded[item], gear_ratio)
            print(f'{loaded[item]}', flush=True)
            move(axis, attr['steps']  * -1, attr['delay'], True)
        
        # attr = constants(360, gear_ratio)
        # negative_steps = attr['steps'] * -1
        # # print('negative_steps', flush=True)
        # # print(negative_steps, flush=True)
        # move(plane, negative_steps, attr['delay'], True)

def check_position():
    pos = 'LEFT'
    axis = ['Y', 'X']
    light('off')


    for plane in axis:
        gear_ratio = 15 if plane == 'X' else 7
        attr = constants(10, gear_ratio)
        steps = attr['steps']
        left = move(plane, steps, attr['delay'], True)
        sleep(0.5)
        right = move(plane, steps * -1, attr['delay'], True)

        if int(right) >= int(left):
            pos = 'RIGHT'

    print(f"{'move towards left' if pos == 'RIGHT' else 'already on the left'}", flush=True)
    print(f'is in right ?? {pos}', flush=True)
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
        # print(data, flush=True)
        json.dump(data, f, indent=4) # indent makes it readable


def set_data(state, config):
    if state == 'PENDING':
        config['status'] = state.lower()
        wr_data(config)

    if state == 'IDLE':
        config['status'] = state.lower()
        # print('set to idle logic', flush=True)
        # print(config, flush=True)
        wr_data(config)
    

# NOTE: This is for testing
# for _ in range(10):
#     move_motor('X', total_steps, step_delay)
#     move_motor('Y', total_steps, step_delay)
#     sleep(2)

    