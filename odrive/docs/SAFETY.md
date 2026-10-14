# Safety

The GUI is a commissioning tool. It reduces mistakes; it is **not** a safety device.
A latching hardware e-stop that cuts DC bus power is required on the bench. An on-screen button is
not an e-stop (NFPA 79 / ISO 13850 do not allow graphical e-stops).

## What the backend enforces

Every write and call from the UI, the console and jobs goes through `app/safety.py`.

| rule | detail |
|---|---|
| actuator profile | `profiles/vayn_shoulder.yaml` (edit in Configuration > actuator profile). Limits below come from it |
| limit writes | `current_lim`, `calibration_current`, `torque_lim`, `vel_limit`, trap `vel_limit`, `dc_bus_overvoltage_trip_level`, `dc_max_positive_current`, `resistance_calib_max_voltage` (<= vbus/2) are rejected above the profile. Raising any of them needs confirmation |
| setpoints | `input_pos/vel/torque` are clamped to the profile envelope; only accepted while this GUI activated the axis |
| energizing | any `requested_state` other than IDLE needs a hold-to-confirm, and a preflight: bus voltage in window, current/velocity limits and over-voltage trip within the profile |
| dangerous calls | save, erase, reboot, DFU, anticogging, CAN baud need confirmation; save/erase/reboot are refused while an axis is active |
| CAN frames | motion/config frames need confirmation (CAN bypasses the USB-side checks) |
| tokens | one-shot, action-bound, 20 s lifetime, issued only after the user holds the confirm button |
| audit | every write/call/safety event with old and new value in `data/audit.db` (Alarms > audit log) |

## Runtime monitor (every telemetry sample)

An active axis is disarmed (both axes to IDLE) when:
- bus voltage leaves `power.bus_min_v .. bus_max_v`
- FET temperature exceeds `thermal.fet_abort_c` (warning alarm at `fet_warn_c`)
- motor thermistor (if enabled) exceeds `thermal.motor_abort_c`
- |Iq| exceeds 1.15 x `motor.current_peak_a`
- in closed loop: |vel| > 1.25 x `limits.vel_max_turns_s` or position outside the limits (+5 % margin)
- no GUI heartbeat for 1.5 s (browser closed, tab frozen, network gone)

## Watchdog

When the GUI puts an axis into a non-idle state it sets `watchdog_timeout` (profile, 0.5 s),
feeds it, enables it, and keeps feeding at 20 Hz. If the backend dies, the ODrive itself disarms
the axis. The watchdog is switched off again once the axis is back in IDLE.

## DISARM ALL

Status bar button and `Esc` anywhere. No confirmation, aborts running jobs, writes IDLE to both
axes before any other queued operation. Deliberately not styled red-on-yellow (that look is
reserved for certified e-stop devices).

## Jobs

Energizing jobs need confirmation to start, and always end with both axes in IDLE (done, failed
or aborted). Inner steps still pass the limit checks.

## Known limits

- v3.6 has no enable/error pins; the hardware safe state needs a contactor/brake designed separately
  (see the VAYN Phase 1 safety state table).
- The brake resistor cannot be measured by the board; confirm it with a multimeter.
- Losing the drive drops the arm; use a guarded, tethered rig for early tests.
