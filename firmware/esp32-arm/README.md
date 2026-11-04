# ESP32 + ReadyToSky ESC bench firmware

One ESP32 talks to both ESCs and both AS5047P boards. It can spin a motor. It cannot hold a joint. A drone ESC has no standstill commutation, so goals 3 and 4 (hold, then a real arm path) need a FOC board.

## What this is for

1. Read the shoulder encoder.
2. Arm one ESC and spin the shoulder actuator at a capped throttle.
3. Spin elbow the same way, then both at once from the same clock.
4. Stop. Do not try to pose the arm on these ESCs.

## Wiring (ESP32 DevKitC defaults)

Power the ESP32 from USB. Do not take 5 V from an OPTO ESC unless you have measured a BEC. Join **signal ground** of each ESC to ESP32 GND.

| Signal | ESP32 | Other end |
|---|---|---|
| Shoulder ESC PWM | GPIO 25 | ESC white/yellow signal |
| Elbow ESC PWM | GPIO 26 | ESC white/yellow signal |
| ESC grounds | GND | ESC signal black |
| Encoder 3V3 | 3V3 | Meukron 3.3V (not 5 V) |
| Encoder GND | GND | Meukron GND |
| SCK | GPIO 18 | CLK |
| MISO | GPIO 19 | MISO |
| MOSI | GPIO 23 | MOSI |
| Shoulder CS | GPIO 4 | CS. unplugged for now |
| Elbow CS | GPIO 5 | CS |
| Kill button | GPIO 27 to GND | optional. held = cut |

OPTO means the ESC does not power the ESP32. If your unit is 2–4S and really has a 5 V BEC, you may use that 5 V on VIN, still with a common signal ground. If the print says 2–6S or 2–24S and **OPTO / no BEC**, USB only.

**Voltage check before you connect the pack.** ReadyToSky 40 A listings are almost all **2–4S or 2–6S**, not 2–24S. A 6S-max ESC on a 24 V (or higher) pack dies. Read the silk on the board.

Phase wires: three from ESC to motor. Swap any two to reverse. Unidirectional ESCs only go one way.

## Flash

Arduino IDE: board **ESP32 Dev Module**, 115200 baud, open `esp32-arm.ino`.

Or:

```
pio run -e esp32dev -t upload -t monitor
```

Edit `config.h` if your pins differ.

## Both motors on this ESP32

Shoulder ESC signal is GPIO 25. Elbow ESC signal is GPIO 26. Each ESC signal ground goes to ESP32 GND. Motor power stays on the 12 V supply.

The shoulder has no encoder connected, so it moves by time: `time 8` runs GPIO 25 at 12% for 8 seconds, then stops. The elbow still moves by degrees on GPIO 26 (`loops`). The elbow encoder chip-select is GPIO 5. The shoulder encoder chip-select is GPIO 4 when that encoder is plugged in.

```
arm
time 8
loops
pattern
```

`pattern` leaves the saved elbow profile alone. It runs 40 slower elbow turns between 30° and 130°, with the light brake near the top and a stronger brake toward 30°. The shoulder repeats 3 seconds on and 3 seconds off for that whole run. This ESC cannot drive the shoulder backward, so the off half is released, not a powered reverse.

## First motion (if `move` is too much)

```
enc
arm
spin s 6
```

`x` or GPIO 27 to GND cuts. Serial silence of 400 ms while spinning also cuts.

## Commands

| Command | Meaning |
|---|---|
| `help` | list |
| `enc` | one encoder sample |
| `arm` | min throttle for 2.5 s |
| `spin s 6` | shoulder 6 % |
| `spin e 6` | elbow 6 % |
| `spin both 6` | both, same tick |
| `stop` | zero throttle, stay armed |
| `disarm` / `x` | cut and idle |
| `goto ...` | refused. needs FOC |

## After this

Replace both ESCs with FOC servo drives that take the AS5047P (another ODESC, two ODESC V4.2, VESC, or MKS XDrive Mini). Keep **one** trajectory clock. `trajectory.h` already interpolates two joint angles on one timer. The drives track those angles. Two ESP32s do not help sync.
