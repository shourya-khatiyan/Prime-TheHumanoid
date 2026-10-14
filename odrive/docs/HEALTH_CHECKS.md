# Health checks

Health check screen (or commissioning step 5). Passive: reads only, never energizes. Takes ~3 s,
samples a 2 s standstill window, saves a report (`data/reports/*.json|md`, downloadable).

| check | signal | pass | when it fails |
|---|---|---|---|
| device link | transport, achieved sample rate | connected | usb driver / cable |
| hardware variant | `hw_version_*` | 3.6-56V | firmware built for another board: vbus scaling will be wrong |
| firmware | `fw_version_*` | 0.5.6 | warn only: 0.5.1 works, 0.5.6 fixes CAN |
| bus voltage | `vbus_voltage` mean | inside profile window | supply, wrong board variant (compare with a multimeter) |
| bus noise | `vbus_voltage` std | < 150 mV | weak supply, long leads |
| control loop rate | device clock delta / time | ~8000 Hz | firmware overloaded or wrong clock |
| error registers | axis, motor, encoder, controller (+ system on 0.5.6) | none | decoded flags tell the cause; clear, fix, rerun |
| gate driver | `last_drv_fault` / `gate_driver.drv_fault` | no fault | DRV8301 over-current, over-temp or supply faults |
| current sensor offset | `current_meas_phB/C` at idle | < 0.3 A | damaged shunt amp / offset calibration |
| FET thermistor | `fet_thermistor.temperature` | 5-60 C idle | sensor open/short, board already hot |
| motor thermistor | `motor_thermistor.config.enabled` | enabled | warn: fit an NTC before thermal tests |
| encoder config | mode, cpr, CS pin vs profile | match | apply profile, save + reboot |
| encoder SPI link | `spi_error_rate` max | < 0.01 | CS pin, 3.3 V, SCK/MISO wiring, magnet |
| encoder data line | `pos_abs` | changing | stuck 16383 = floating MISO/CS; stuck 0 = MISO low / unpowered / mode not active |
| encoder noise | std of `pos_abs` at standstill | < 3 counts | magnet gap/centering, cable near motor phases |
| pole pairs | `motor.config.pole_pairs` | profile (20) | apply profile |
| phase R / L | calibration results | R within profile tolerance, L 2-4000 uH | loose phase lead, wrong calibration current |
| over-voltage trip | `config.dc_bus_overvoltage_trip_level` | <= profile (28 V) | apply profile power settings |
| current / velocity limit | `current_lim`, `vel_limit` | <= profile | apply profile |
| brake resistor | `brake_resistance`, `brake_resistor_armed` | matches profile, armed | warn always: verify the resistor with a multimeter |
| CAN baud | `can.config.baud_rate` | 1 Mbit | warn: needed for the RT core bus |

Other tests that complete the picture:
- **encoder hand-turn** (commissioning step 2): travel ~1 turn, no jumps > cpr/8, no SPI errors
- **motor calibration** checks R/L plausibility and `UNBALANCED_PHASES`
- **thermal hold** gives the real continuous current
