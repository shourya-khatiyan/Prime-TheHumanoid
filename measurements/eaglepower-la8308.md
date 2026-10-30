# EaglePower LA8308 KV90

One motor, used on the shoulder and the elbow. All lengths are millimetres.

Drawing rule: the mounting face is Z = 0. Positive Z goes toward the rotor hub (the arm side). The rear cap and the phase leads are on the negative side of that face.

## Measured

| Item | Value | Status | Where it came from |
|---|---|---|---|
| Outside diameter | 92.0 | MEASURED | Vernier, 2026-10 |
| Mounting face to rotor hub face | 32.5 | MEASURED | Vernier. Includes the gold frame edge on the hub side |
| Front shaft stub | Ø2.9 × 8.9 | MEASURED | Vernier. Sticks out of the hub face. Sun-1 on the first shoulder was drilled for it |
| Rear cap | Black hexagon. Same part as the old "Ø17 cap". Turns with the rotor | MEASURED | 2026-10-31 |
| Rear cap, across flats | 17.2 to 17.4 | MEASURED | Vernier on two flat sides, 2026-10-31 |
| Rear cap, across corners | 19.9 to 20.1 | Derived | Regular hex: flats × 2 / √3. A round hole of 17.4 hits the corners |
| Rear cap standout | 6.7 past the flat mounting face | MEASURED | It does not sit inside the face. The older note that said it did is wrong |
| Magnet cover | Ø10, glued on the hex face, magnet inside | MEASURED | Adds 6.5 past the hex face. From the mounting face the outer face is 6.7 + 6.5 = 13.2 |
| Rear cap centre hole | Covered by that magnet cover | MEASURED | Do not design a pin into it |
| Rotor hub holes | 4 × M2, deeper than 6, opposite holes 38 centre to centre | MEASURED | 38 is the bolt-circle diameter. Seller pages do not list this circle |
| Rear cable | 30 from the axis, cover 11 × 5, can be bent | MEASURED | 2026-10-31. Replaces the earlier “about 13 wide at radius 32”. Angle around the motor is still not taken |
| Stator M4 hole depth | More than 6 | MEASURED | Checked with a screw. Exact depth not taken |
| Stator hole pattern | 4 × M4 | FITTED | The Rev 1.3 rear plate (Ø40 circle, holes at 45°) bolted to this motor. Not re-measured with a caliper |
| Pole pairs | 20 | MEASURED | Counted on the ODESC |
| Phase resistance | 0.0846 Ω | MEASURED | ODESC. Seller 0.186 Ω is line-to-line |
| Phase inductance | 37 µH | MEASURED | ODESC |
| Mass | 336 g | CATALOGUE | Not weighed here |
| KV | 90 | CATALOGUE | Not measured on this motor |

## Used in CAD and not measured

These are in `body parts/shoulder/cad/gen_actuator_3mf.py` and `body parts/arm/cad/arm_params.py`. Do not copy them into a new design.

| Item | CAD value | Status |
|---|---|---|
| Body between the two end faces | Ø86 | ASSUMED |
| Mounting-flange thickness | 3 | ASSUMED |
| Rotor bell inner diameter | Ø89 | ASSUMED |
| Rear cap | Drawn as a Ø17.4 cylinder, 3 long, inside the mounting face, with a Ø3 pin hole | ASSUMED. Wrong. The real cap is a hex, 6.7 proud, and the hole is covered |
| Shaft inside the motor | Ø6 | ASSUMED |
| Rotor bolts | Drawn as M3 on Ø31 and on Ø25 | ASSUMED. Wrong. Real holes are M2 on a 38 circle, deeper than 6 |
| Hub face | Drawn with a recess for a boss | ASSUMED. The real face is flat apart from the stub |
| Lead angle | 180° in the shoulder model, 135° in the arm model | Design choice, not a measurement |

Nothing else sticks out of the rear face except that hex cap, the magnet cover on it, and the flexible wires.

If the 17.2–17.4 reading was flat-to-flat, the corners of a regular hexagon land at 17.4 × 2 / √3 = 20.1. A round hole sized for 17.4 then hits the corners. That is hexagon geometry, not a new measurement.

Seller listings give Ø92 × 28.5 and a Ø6 shaft only. They do not give the bolt circle, the hex, or the 32.5 height ([FindMyChips LA8308](https://findmychips.com/part/eaglepower-la-8308-kv90-motor-06332c), [OL Electronics LA8308](https://www.olelectronics.com/product/eaglepower-la-8308-kv90-brushless-motor/)). The 28.5 height is the number that did not match this motor.

## Still needed

1. Stator hole circle from a caliper. The Rev 1.3 plate (Ø40 circle) did bolt on. That is not a written caliper number. The rear cable is already placed: 30 from the axis, cover 11 × 5.
