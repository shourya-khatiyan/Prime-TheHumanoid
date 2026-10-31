# Shoulder v4 — coaxial cycloid

One module for pitch or yaw. The bolt face is the motor hub face. The motor and the encoder hang behind that face. The cycloid and the arm flange stand in front of it.

## Ratio

45:1. At 24 V the LA8308 no-load speed is 2160 rpm, so the output is 48 rpm (288°/s). A 180°/s shoulder move is 30 rpm, so voltage is not the limit. The same 12.1 A that the old planetary called 30 N·m produces about 42 N·m here, because the ratio is 45 instead of 30 and the efficiency allowance is 0.85. The 20 A short overload is about 71 N·m. Both numbers are current × ratio × 0.85. They are not a bench test.

A lower ratio gives more speed and an easier backdrive, and less output torque at the same current. 45:1 is the high-torque end that still clears 180°/s.

## What sets the length

The motor body is 27.5 mm flat to flat. Behind the hub face is 46.9 mm: 27.5 plus the hex and cover (13.2) plus the encoder (6.2). In front of the hub face is 51.4 mm. Overall 98.3 mm, against 100.5 mm for the two-stage planetary. The gearbox after the hub is 51 mm. On the planetary it was 57 mm. The motor and the encoder are the same length in both.

The discs are 7 mm because the eccentric bearing is a 61805, 25×37×7, static rating 2.6 kN ([SKF 61805](https://www.skf.com/group/products/rolling-bearings/ball-bearings/deep-groove-ball-bearings/productid-61805)). The proof load on one disc bearing is about 2.1 kN, so the static factor is about 1.2. Tooth contact at that thickness is a few hundred MPa, not the 1500 MPa steel limit, so the disc is not made thicker than the bearing.

The output bearings are 61906, 30×47×9, static rating 4.55 kN. They sit on the two ends of the disc stack, so the span is about 27 mm and there is no empty spacer. The arm flange is 6 mm, which is the M5 thread. The housing stops at the front bearing. A 2 mm cover holds that bearing and is the part you remove to put the discs in.

The rear of the housing is open at Ø94. The motor slides in until the hub face hits the lip. The rear cup goes on after the motor. The elbow failed this way: the bore was closed and the parts had to be hammered. This one does not.

## Fits

The elbow jammed because grooves and holes were drawn at the pin's nominal size, and a printed hole came out smaller than the pin. This model uses the elbow's offset curve. Ring-pin relief is 0.12 mm. After an m6 pin's 0.006 mm radial oversize the swept gap stays about 0.10 mm. Output holes are pin radius + eccentricity + 0.25 mm, which is the pin's orbit, not an enlarged guess.

The housing pin holes are drawn 0.05 mm larger in radius than the 4 mm pin, so the pin enters. The elbow holes were drawn at the pin's nominal size.
