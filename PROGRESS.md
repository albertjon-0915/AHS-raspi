# AHS Heliodon: Progress

Branch: `fix/night-threshold-night-movement`
Pi: `jaekylee@192.168.1.159`, app path `/home/jaekylee/Desktop/heliodon/service`

## Current state

- Code on the Pi matches this branch (`main.py`, `utils/fn.py`, `templates/index.html` checked by SHA-1 on 2026-11-07).
- Flask runs on port 4001. It is started by hand (`nohup python3 main.py`), not by a service.
- Chromium kiosk autostart points at `http://127.0.0.1:4001`. Not confirmed working on screen yet.

## Checklist

- [x] Repo synced to Pi
- [x] Flask serves `index.html` on port 4001
- [x] `/calibrate` returns different sun angles for different places and times
  - Manila 14.6, 120.97 at 08:27: az 121.10, el 33.33
  - NYC 40.71, -74.00 at 12:00: az 185.79, el 32.69
- [ ] Motors physically move to the expected positions (not verified)
- [ ] Repeated Flask restarts do not hit `GPIO busy` (one clean restart passed the test below; repeated restarts not yet tested)
- [ ] Flask runs as a systemd service (starts on boot)
- [ ] Kiosk Chromium shows the page on boot
- [ ] Night behavior: motors go home when sun altitude < -2 (home position confirmed in software; physical motion not yet checked)
- [x] LED off at night, on page load, and at app startup (pin readback verified 2026-11-07; physical LED not yet checked)
- [ ] Physical check: LED on the heliodon matches the pin readback above
- [ ] Motor mapping: confirm the "middle of arc" result is wrong and find the fix (not resolved)

## Known issues

### 1. `GPIO busy` after restarting Flask
- Error: `lgpio.error: 'GPIO busy'` when `fn.py` creates its `OutputDevice`/`ButtonBoard` objects.
- Most likely cause: an old Python process still holds the GPIO lines. Not confirmed.
- Next step: before starting Flask, check which process holds the lines (`sudo lsof /dev/gpiochip0` or `sudo fuser -v /dev/gpiochip0`), and make sure old instances exit.
- Note: an earlier suggestion to change the gpiozero setup was not tested and has been dropped.

### 2. Motors go to the middle of the arc
- Not fixed. `/calibrate` returns only the sun's azimuth and altitude, so motor positions are not visible from the API.
- `calculate_heliodon_angles` gives motor_x 44.32 and motor_y 128.15 for Manila 08:27 (computed from the formula, not measured on the motors).
- Next step: measure the real motor positions on hardware and compare them with the formula.

### 3. Each `/calibrate` call homes first
- `fn.origin()` runs when `data.json` says `pending` or has a non-zero position. Every move therefore starts with a homing run.

### 4. Runtime state in git
- `data.json` is runtime state. It was reset to `idle` on the Pi. Do not commit changes to it unless that is intended.

## Test results

### 2026-11-07: `/calibrate` sequence (Manila 14.6, 120.97), one Flask process

| Time | HTTP | Seconds | Sun az / el | Motor X / Y target (data.json) |
|---|---|---|---|---|
| 08:27 | 200 | 38 | 121.10 / 33.33 | 44.32 / 128.15 |
| 10:27 | 200 | 33 | 149.09 / 54.32 | 72.57 / 121.64 |
| 11:27 | 200 | 34 | 174.05 / 58.99 | 86.94 / 120.87 |
| 03:00 | 200 | 18 | 98.78 / -41.82 | 0 / 0 (night, home) |

- Flask log: 0 `GPIO busy` or traceback errors.
- Motor targets are computed values, not measured. Physical arm movement still needs to be confirmed on the kiosk.
- Y targets for these morning times sit at 120–128, so the middle-of-arc issue is still open.

### 2026-11-07: LED behavior (commit `705b798`, pin 21 read via pigpio)

| Step | LED pin (1 = on) |
|---|---|
| Before restart (old code, LED left on) | 1 |
| After Flask starts (new code) | 0 |
| After loading `/` (kiosk startup) | 0 |
| After night calibrate (03:00) | 0 |
| After daytime calibrate (10:27) | 1 (intended) |

- Flask log: 0 `GPIO busy` or traceback errors.
- Known side effect: reloading the page during the day turns the LED off.

## Session log

### 2026-11-07
- Found `main.py` on the Pi nearly empty. Restored all app files from this repo branch.
- Fixed the stray `n` before a comment in `utils/fn.py` (now fixed on this branch).
- Earlier I suspected a pysolar caching bug. That was not confirmed: after restarting Flask, values varied by place and time as expected. The root cause of the earlier identical results is still unknown.
- pysolar needs timezone-aware datetimes. `get_utc_from_local` in `fn.py` provides them.
- LED was on at night, on page load, and at startup. Cause: `pigpiod` keeps the pin level between client connections, and night calibrate never turned it off. Fixed in `main.py` (`705b798`).
- During debugging, `pkill -9 -f python` was run on the Pi. That may have stopped unrelated Python processes too (for example `wayvnc-control.py`). Check that VNC still works.
