# Shoulder v4 — coaxial cycloid

One module for pitch or yaw. The bolt face is the motor hub face. The motor and the encoder hang behind that face. The cycloid and the arm flange stand in front of it.

## Ratio

45:1. At 24 V the LA8308 no-load speed is 2160 rpm, so the output is 48 rpm (288°/s). A 180°/s shoulder move is 30 rpm, so voltage is not the limit. The same 12.1 A that the old planetary called 30 N·m produces about 42 N·m here, because the ratio is 45 instead of 30 and the efficiency allowance is 0.85. The 20 A short overload is about 71 N·m. Both numbers are current × ratio × 0.85. They are not a bench test.

A lower ratio gives more speed and an easier backdrive, and less output torque at the same current. 45:1 is the high-torque end that still clears 180°/s.

## What sets the length

The motor body is 27.5 mm flat to flat. Behind the hub face is 46.9 mm: 27.5 plus the hex and cover (13.2) plus the encoder (6.2). In front of the hub face is 53 mm. Overall 99.9 mm.

The discs stay 7 mm. The crank bearing is no longer a 61805. That ball bearing is rated 2.6 kN static, and the proof load on one disc was about 2.1 kN, a margin of about 1.2. The replacement is a SKF K 20×24×10 needle cage, catalog static rating 12.9 kN over its full 10 mm. The disc covers 7 mm of that, so the working rating is about 9 kN and the proof margin is about 4. The needle is 10 mm wide and the disc is 7 mm, so 1.5 mm of the cage stands out of each face. The two cages are 1.2 mm apart. The journal is Ø20 and has to be hardened, because this cage has no inner ring. The 0.05 mm gaps drawn around the needle and the bearing bores are only so the model solids do not fuse. Machine the disc bore as the catalog race, Ø24, and the hub as Ø30 for the 61906.

He, Li and Zhang, Tehnički vjesnik 30 (2023), show that a large profile relief drops teeth out of contact and raises the force on the teeth that remain. The old 0.12 mm relief was 23% of the 0.53 mm crank offset. It is now 0.08 mm. An m6 pin is only 0.006 mm over size, and the swept gap after that is still about 0.06 mm. The check prints the one-tooth, two-tooth and three-tooth cases, which is the set used by Blagojević in Journal of Mechanical Design 133 (2011). With 45 lobes the one-tooth case is the extreme, not the working case. The pin circle stays 44 mm and the pins stay Ø4: a fatter pin would meet the housing bore.

The output is one piece. Eight Ø6 pins run from a 2.7 mm rear plate to a 2.8 mm front plate, and both plates join the hub. The rear hub sits in the rear 61906. The front hub sits in the front 61906 and carries the arm flange. The pins are a beam on two supports, not a cantilever. The bearing centres are about 33 mm apart.

The 46 ring pins are Ø4. The housing lip holds the rear end for 4 mm. The front cover holds the other end. The pin is a beam on those two supports. The cover is the part you remove to put the discs in, then the pins, then the cover. Eight M3 screws on a 99 mm circle clamp the cover, tapped into the housing. Eight more M3 screws on that circle clamp the rear plate.

The crank flange is Ø44, so the four M2 holes on the measured 38 mm circle are in the flange and line up with the holes in the rotor face.

The rear plate is the planetary one: a 2 mm encoder lid, a 30 mm board pocket on the measured Meukron rhombus, a cable groove at 0°, and a 15 mm phase-lead slot at 180° with a groove out to the rim. The elbow failed because the bore was closed. This bore stays open until the cover goes on.

## Fits

The elbow jammed because grooves and holes were drawn at the pin's nominal size, and a printed hole came out smaller than the pin. This model uses the elbow's offset curve. Ring-pin relief is 0.08 mm. After an m6 pin's 0.006 mm radial oversize the swept gap stays positive. Output holes are pin radius + eccentricity + 0.25 mm, which is the pin's orbit, not an enlarged guess. A Journal of Mechanical Design paper on the clearance-fit output (2017, DOI 10.1115/1.4035541) treats that clearance as part of the load path, so it is kept and not opened further.

The housing pin holes and the cover pin holes are drawn 0.05 mm larger in radius than the 4 mm pin, so the pin enters both ends. The elbow holes were drawn at the pin's nominal size.
