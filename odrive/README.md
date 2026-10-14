# VAYN ODRV - ODrive v3.6 bench GUI

Commissioning, control and test tool for the ODESC 3.6 56V (ODrive v3.6 clone) that drives the
VAYN shoulder actuator. Terminal-style UI, live telemetry, guided bring-up, health checks, tuning,
thermal and characterization tests, recordings, CAN tools and a guarded firmware update.

It is a bench tool, not the robot runtime: in VAYN the RT Motion Core talks to the ODrive over CAN.

## Run

```powershell
# first time
cd odrive\backend ; uv sync            # python 3.11 venv + odrive 0.5.1 tools
cd ..\frontend ; npm install

# windows only, once per pc: lets libusb open the ODrive native usb interface (admin prompt)
powershell -ExecutionPolicy Bypass -File odrive\tools\fix_winusb_guid.ps1

# start (from odrive/)
.\dev.ps1           # real board: native usb, falls back to ascii over the COM port
.\dev.ps1 mock      # simulated board, no hardware needed
# open http://localhost:5173
```

Production build: `.\build.ps1` makes `backend\dist\vayn-odrv.exe` (serves the UI on
http://127.0.0.1:8765 and opens the browser). Firmware flashing needs the source install.

Env: `ODRV_MODE=auto|usb|ascii|mock`, `ODRV_PORT` (8765), `ODRV_NO_BROWSER=1`.

## Tests

```powershell
cd backend ; .venv\Scripts\python -m pytest     # end-to-end over the websocket, simulated board
cd frontend ; npm test                          # decoding, downsampling, formatting
```

## Docs

- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) - processes, transports, protocol, folders
- [docs/SAFETY.md](docs/SAFETY.md) - what the safety layer enforces and what it cannot
- [docs/COMMISSIONING.md](docs/COMMISSIONING.md) - first bring-up of the actuator, encoder modes
- [docs/HEALTH_CHECKS.md](docs/HEALTH_CHECKS.md) - every self-test signal and how to read it
- [docs/DESIGN.md](docs/DESIGN.md) - visual system and the rules that keep it readable
- [docs/FEATURES.md](docs/FEATURES.md) - feature list vs the reference GUI
