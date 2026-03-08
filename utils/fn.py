from gpiozero import OutputDevice, ButtonBoard, LED
from time import sleep
import json

# Pins: [PUL, DIR]
X = [OutputDevice(17), OutputDevice(27)]
Y = [OutputDevice(23), OutputDevice(24)]

# NOTE: change variables into actual pins, checking the raspi for pinouts
# Pins: x=azimuth, y=elevation
LIMIT = ButtonBoard(x=12, y=26)
#Pins: LED
LIGHT = LED(16)

TARGET_ANGLE = 0

def constants(step = 0, ratio = 1):
    # Motor Specs
    SPR = 200            # Standard 1.8 degree motor (360 / 1.8)
    MICROSTEPS = 16      # Driver microstepping settings
    RPM = 90             # Target speed
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

def move(axis, steps, delay):
    motor = X if axis == 'X' else Y

    if steps < 0:
        motor[1].on()
    else:
        motor[1].off()
        
    point = getattr(LIMIT, axis.lower())
    steps = abs(steps)

    for _ in range(steps):
        if point.is_active: 
            LIGHT.off()
            print(f"Reached the limit of system's angle...")
            break

        motor[0].on()
        sleep(delay)
        motor[0].off()
        sleep(delay)

    print(f"Moving {TARGET_ANGLE} degrees...")
    return f'DONE {axis}'


def origin():
    axis = ['Y', 'X']
    LIGHT.off()

    for plane in axis:
        attr = constants(360, 1)
        negative_steps = attr['steps'] * -1
        move(plane, negative_steps, attr['delay'])

def light(state):
    if state.lower() == 'on':
        LIGHT.on()
    elif state.lower() == 'off':
        LIGHT.off()

def rd_data():
    with open('data.json', 'r') as f:
        data = json.load(f)
    
    return {
        'status': data.get('status', 'idle'),
        'azimuth': data.get('azimuth', 0.0),
        'elevation': data.get('elevation', 0.0)
    }

def wr_data(data):
    with open('data.json', 'w') as f:
        json.dump(data, f, indent=4) # indent makes it readable


def set_data(state, config):
    if state == 'PENDING':
        config['status'] = state.lower()
        wr_data(config)

    if state == 'IDLE':
        config['status'] = state.lower()
        wr_data(config)
    
    
# NOTE: This is for testing
# for _ in range(10):
#     move_motor('X', total_steps, step_delay)
#     move_motor('Y', total_steps, step_delay)
#     sleep(2)

    