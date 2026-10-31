# Shoulder v3 — pitch joint

Folded cycloid. The elbow, the torso shell, and any later yaw or roll joint are not in this folder.

Z = 0 is the torso mounting face. Positive Z is outboard, toward the arm. The motor axis is parallel to Z at x = 96 mm.

## What this is

- One cycloid, 45 lobes and 46 pins, ratio 45:1. Two discs, cranks 180° apart, so the eccentric forces oppose.
- Pin circle radius 38 mm, pin diameter 4 mm. That fit sets the joint barrel at Ø90. A 51:1 set with pins this strong does not fit in Ø80.
- One 1:1 spur pair, 64 teeth, module 1.5, centre distance 96 mm. The pair is this large because the Ø92 motor has to sit clear of the Ø90 barrel.
- The LA8308 is inside a closed tunnel on the housing, inboard of the torso face. The encoder cap closes the back of that tunnel.
- Arm flange: Ø40 pilot, 2 mm deep, 6 × M5 on Ø52.
- Torso interface: 6 × M5 clearance holes on Ø78, on the Z = 0 face. No torso part is modelled. The torso plate needs a hole so the motor tunnel can pass through.

## Size and torque

Outboard of the torso face the joint is Ø90 × 58 mm. The motor and encoder hang inboard of that face, offset 96 mm toward the chest. Overall model envelope is about 198 × 104 × 114 mm.

At the same 12.1 A used for the old 30 N·m planetary (`shoulder/cad/calc.txt`), motor torque is 1.11 N·m. With ratio 45 and an efficiency allowance of 0.85, continuous output is about 42 N·m at about 48 rpm. The 0.85 sits between a measured cycloid peak of 81% and a catalogue single-stage figure of 93%. The short overload at 20 A is about 71 N·m and has not been proven on hardware.

## Gear correction

The first v3 discs used a 0.08 mm pin clearance, the same allowance that left the printed elbow with no gap once a real pin and a small hole were counted. The disc is now the elbow offset curve with 0.12 mm relief. Output holes are the pin radius plus the eccentricity plus 0.20 mm. The earlier holes were about 1.7 mm too large in radius. `cad/calc.py` sweeps the gap the same way as the elbow.

## Tradeoff

The shoulder axle gets much shorter than the 123 mm planetary. The package gets wider toward the chest by the motor. A cycloid is harder to backdrive than the planetary: published no-load start torques are about 10–20% of rated torque, against under 2% for a planetary.
