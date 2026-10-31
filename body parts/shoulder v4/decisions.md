# Shoulder v4 — coaxial cycloid

One module for pitch or yaw. The bolt face is the motor hub face. The motor and the encoder hang behind that face. The cycloid and the arm flange stand in front of it.

## Ratio

45:1. At 24 V the LA8308 no-load speed is 2160 rpm, so the output is 48 rpm (288°/s). A 180°/s shoulder move is 30 rpm, so voltage is not the limit. The same 12.1 A that the old planetary called 30 N·m produces about 42 N·m here, because the ratio is 45 instead of 30 and the efficiency allowance is 0.85. The 20 A short overload is about 71 N·m. Both numbers are current × ratio × 0.85. They are not a bench test.

A lower ratio gives more speed and an easier backdrive, and less output torque at the same current. 45:1 is the high-torque end that still clears 180°/s.

## What sets the length

Behind the bolt face, 51.9 mm. That is the measured motor (32.5 mm hub to mount) plus the measured hex and magnet cover (13.2 mm) plus the encoder stack (6.2 mm). It is not a thick plate.

In front of the bolt face, 62 mm.

- 0.8 mm gap at the hub
- two 12 mm discs, because each disc holds a 6005 bearing (25×47×12) and the proof load on that bearing is about 2.3 kN
- 0.6 mm gaps
- 8 mm pin plate, so a Ø6 output pin has a steel seat
- two 50×65×7 output bearings with 14 mm between centres, then a 6 mm arm flange

The old shoulder used 21 mm between bearing centres for its tilt case. This span is shorter. A heavy arm moment needs that check again before this flange is trusted with the old 65 N·m tilt.

## Fits

The elbow jammed because grooves and holes were drawn at the pin's nominal size, and a printed hole came out smaller than the pin. This model uses the elbow's offset curve. Ring-pin relief is 0.12 mm. After an m6 pin's 0.006 mm radial oversize the swept gap stays about 0.10 mm. Output holes are pin radius + eccentricity + 0.25 mm, which is the pin's orbit, not an enlarged guess.

Housing pin holes in a metal build are reamed H7. They are not left at a nominal that the pin cannot enter.
