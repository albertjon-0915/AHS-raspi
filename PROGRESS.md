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
- [ ] Repeated Flask restarts do not hit `GPIO busy`
- [ ] Flask runs as a systemd service (starts on boot)
- [ ] Kiosk Chromium shows the page on boot
- [ ] Night behavior: motors go home when sun altitude < -2 (code exists, not tested on hardware)
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

## Session log

### 2026-11-07
- Found `main.py` on the Pi nearly empty. Restored all app files from this repo branch.
- Fixed the stray `n` before a comment in `utils/fn.py` (now fixed on this branch).
- Earlier I suspected a pysolar caching bug. That was not confirmed: after restarting Flask, values varied by place and time as expected. The root cause of the earlier identical results is still unknown.
- pysolar needs timezone-aware datetimes. `get_utc_from_local` in `fn.py` provides them.
- During debugging, `pkill -9 -f python` was run on the Pi. That may have stopped unrelated Python processes too (for example `wayvnc-control.py`). Check that VNC still works.
