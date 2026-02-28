from gpiozero import OutputDevice, ButtonBoard, LED
from time import sleep

# Pins: [PUL, DIR]
X = [OutputDevice(17), OutputDevice(27)]
Y = [OutputDevice(23), OutputDevice(24)]
# Pins: x=azimuth, y=elevation
LIMIT = ButtonBoard(x=x, y=y)
#Pins: LED
LIGHT = LED(led)

TARGET_ANGLE = 0

def constants(step = 0):
    # Motor Specs
    SPR = 200            # Standard 1.8 degree motor (360 / 1.8)
    MICROSTEPS = 16      # Driver microstepping settings
    RPM = 90             # Target speed
    TARGET_ANGLE = step  # Change this to whatever angle you want (e.g., 360, 720)

    # 1. Calculate how many pulses we need for the desired angle
    # (120 / 1.8) * 16 = 1,066.66 steps
    total_steps = int((TARGET_ANGLE / 1.8) * MICROSTEPS)

    # 2. Calculate delay for the speed (RPM)
    # Total pulses for one full 360 degree rev = 3200
    pulses_per_rev = SPR * MICROSTEPS
    step_delay = (60 / RPM) / pulses_per_rev / 2
    return {
        'steps': total_steps,
        'delay': step_delay
    }

def move(axis, steps, delay):
    config = rd_data()
    config['status'] = 'pending'
    wr_data(config)

    # motor[1].on() # Toggle this for direction
    motor = X if axis == 'X' else Y
    if steps < 0:
        motor[1].on()
        steps = abs(steps)


    for _ in range(steps):
        if LIMIT.y.is_active: 
            print(f"Reached the limit of system's angle...")
            break

        motor[0].on()
        sleep(delay)
        motor[0].off()
        sleep(delay)

    config['status'] = 'idle'
    wr_data(config)

    print(f"Moving {TARGET_ANGLE} degrees...")
    return f'DONE {axis}'


def origin():
    axis = ['y', 'x']
    light.off()
    config = rd_data()
    config['status'] = 'pending'
    wr_data(config)

    for plane in axis:
        return_cycle = True
        print(f'Reset for origin point {plane}...')
            
        while return_cycle:
            point = getattr(LIMIT, plane)
            move(-360)
            if point.is_active:
                print(f'Axis reached origin point {plane}...')
                return_cycle = False
            sleep(0.001)

    config['status'] = 'idle'
    wr_data(config)

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
        json.dump(data, f, indent=4) # indent makes it pretty/readable


# def light(state):
#     match state:
#         case 'ON':
#             LIGHT.on()
#         case 'OFF':
#             LIGHT.off()
#         case 'CHECK':
#             if LIMIT.y.is_active:
#                 LIGHT.off()
#             else:
#                 LIGHT.on()
#         case _:
#             LIGHT.off()


# for _ in range(10):
#     move_motor('X', total_steps, step_delay)
#     move_motor('Y', total_steps, step_delay)
#     sleep(2)

    