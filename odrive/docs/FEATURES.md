# Features

Reference: [MoonLighTingPY/odrive3.6_web_gui](https://github.com/MoonLighTingPY/odrive3.6_web_gui)
(no license, used only as a feature checklist; nothing copied).

## Parity

| reference | here |
|---|---|
| device scan / connect / reconnect | auto connect, native usb then ascii, reconnect by serial after reboot, simulated board |
| 6-step config wizard | commissioning wizard (8 steps, profile driven) + grouped config editor (13 groups) with staged apply |
| pull / apply / save / erase / reboot | same, all confirmed and audited; reboot-aware |
| presets | backups double as presets: save, compare against device, restore, download |
| dashboard | bento dashboard, 10 panels, 3 layout presets, editable |
| inspector tree | full device tree (516 entries on 0.5.1), live values, edit, call functions, favourites, plot any 6 |
| console | odrivetool syntax, tab completion, history, enum names, flag decoding |
| calibration modal | calibration jobs with R/L plausibility checks and pre_calibrated |
| error decoding + troubleshooting | 64-bit safe decoding with firmware docs per flag, first-out alarm |

## Fixed defects of the reference

- NaN/inf (`torque_lim = inf`) no longer breaks reads (msgpack)
- error bits >= 31 decoded (BigInt)
- reconnects after save/reboot
- no "calculated" gains in counts units; turn-based procedure instead
- E-stop-style DISARM ALL, ODrive watchdog fed, setpoints clamped
- localhost-only, session token and origin check (the reference accepts commands from any website)
- batched sampling + canvas charts instead of SVG recharts

## New

- interactive 3D CAD/point-cloud hologram twin (`OdriveHologram`) of the ODESC 3.6 56V + 90KV BLDC actuator + AS5047P SPI encoder with live rotor rotation, 3-phase current particle flow, subsystem fault highlighting, and 6 spatial HUD callouts
- open-loop motor spin mode (`open_loop` job + `OL` panel in Control + `open` button on Dashboard): drives `AXIS_STATE_LOCKIN_SPIN` (state 9) with configurable speed (`turn/s`), phase current (`A`), and target distance (`turns` or timed), automatically bypassing a faulted SPI encoder (`mode -> INCREMENTAL`) and calibrating motor R/L if needed
- concentric dotted polar encoder radar dial (`EncoderCard`) + 24-segment load/torque/thermal envelope meters
- actuator profile with enforced limits and joint-space view (20:1, Kt, joint torque estimate)
- passive health check with saved reports
- encoder hand-turn test
- tuning: step response metrics, gain sweep ranking, sine response
- thermal hold test with exponential fit and auto-abort
- characterization: breakaway/running friction, effective Kt and efficiency, lost motion
- recordings (Parquet + CSV) with replay
- CAN monitor/send with CANSimple decode, USB-side node id / baud setup
- guarded firmware update to official 0.5.6 with elf->hex conversion and vbus verification
- alarms with ack/shelve, events, full audit log
- command palette, keyboard-first operation
- single exe packaging
