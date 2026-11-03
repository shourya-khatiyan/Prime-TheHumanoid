# Shoulder v4 — bought parts

Screws, bearings, and pins for one actuator. The motor and the encoder are not on this list. Printed and machined parts are in `cad/actuator_print.zip`.

Sizes match `cad/gen_actuator_3mf.py`. The 61906 static rating 4.55 kN and the K 20×24×10 static rating 12.9 kN are the SKF catalog values used in `decisions.md`.

## Bearings

| Qty | Part | Size | Where it goes |
|---|---|---|---|
| 2 | Needle roller and cage, no inner ring. SKF K 20×24×10 | 20 × 24 × 10 mm | One on each crank journal. The Ø20 journal is the inner race and must be hardened and ground. The disc bore is the outer race, Ø24. |
| 2 | Deep groove ball bearing. SKF 61906 | 30 × 47 × 9 mm | Rear hub, and front hub. Static rating 4.55 kN. |

## Pins

The eight Ø6 output pins are part of the rear carrier. They are not bought separately.

| Qty | Part | Size | Where it goes |
|---|---|---|---|
| 46 | Ring pin, hardened steel, slip fit | Ø4 × 37 mm | Through the cycloid. Rear end in the housing lip, front end in the cover. Holes are Ø4.1. |
| 1 | Cross pin, hardened steel, slip fit | Ø4 × 36 mm | Through the arm flange and the hub nose. Holes are Ø4.1. |

## Screws

| Qty | Part | Size | Where it goes |
|---|---|---|---|
| 4 | Socket head cap screw, ISO 4762 | M2 × 8 | Crank flange to the rotor face. Circle diameter 38 mm. Heads sit in the Ø4.4 counterbore. |
| 8 | Countersunk screw, ISO 10642 | M3 × 4 | Front plate to the output pin ends. Heads stay inside the plate. |
| 8 | Socket head cap screw, ISO 4762 | M3 × 25 | Rear plate to the housing. Circle diameter 99 mm. The plate is 19.4 mm thick and the tap in the housing is 8 mm deep, so a 25 mm screw leaves about 6 mm of thread. |
| 8 | Socket head cap screw, ISO 4762 | M3 × 12 | Front cover to the housing. Same 99 mm circle. The cover grip is 6 mm and the housing tap is 8 mm deep. |
| 6 | Socket head cap screw, ISO 4762 | M5, length set by the arm | Arm to the flange. Circle diameter 52 mm. This flange has 6 mm of thread. |

Use one grade for the steel screws, 12.9. The M2 screws go into the rotor, so use the torque the motor maker allows.
