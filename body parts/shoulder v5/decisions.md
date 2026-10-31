# Shoulder v5 — two-stage cycloid

One module for pitch or yaw. Z = 0 is the motor hub face. The motor and the encoder hang behind that face. The cycloid and the arm flange stand in front of it.

The solid is `cad/actuator.step`. The numbers are printed by `cad/calc.py`.

## Where it comes from

Blagojević, Marjanović, Đorđević, Stojanović and Dišić, Journal of Mechanical Design, vol. 133, 085001 (2011), built a two-stage cycloid with one disc per stage instead of the usual four. Both discs sit on one crank, 180° apart. A plate of rollers passes through both discs. The first ring of pins is fixed. The second ring is the output, and it turns the same way as the motor. Their test box was 11 × 11 = 121:1. That ratio is too slow for this shoulder: 2,160 rpm at the motor is only about 107°/s at the arm.

The same formula with 11 lobes and then 9 lobes is 55:1. At the measured motor resistance that is still about 200°/s at 20 A, which clears a 180°/s move. He, Li and Zhang, Tehnički vjesnik 30 (2023), and the 2024 JAMDSM load study, both show that a larger pin circle and a thicker disc cut the contact pressure, and that the small profile relief has to stay small or teeth drop out of contact. The pin circle here is 42 mm. Each disc is 10 mm, which is the width of the needle that carries it. The profile relief stays one equidistant cut of 0.12 mm. A trial that split that 0.12 mm into a radial shift plus a smaller equidistant cut did not change the swept gap, so the profile stays the single cut.

## Ratio and torque

55:1. The first disc has 11 lobes and 12 pins. The second has 9 lobes and 10 pins. Both crank offsets are 1.75 mm.

At 12.1 A the output is about 44 to 50 N·m. The low number is two meshes at 85% each. The high number is two meshes at 90% each. The 2011 paper sets losses to zero, so it does not pick a point inside that band. The 20 A case scales by 1.67, to about 73 to 83 N·m. These are current × ratio × efficiency. They are not a bench test.

v4 at the same current is 42.5 N·m on one 45:1 mesh at 85%.

## What carries the load

The crank needles are SKF K 20×24×10, static rating 12.9 kN. The heavier disc puts about 6.5 kN on its needle at the proof current, so the static margin is about 2. A 61805 ball bearing does not have that rating, which is why v4 was tight and this crank is a needle on a hardened 20 mm journal.

The middle plate was the highest-stressed part in the 2011 computer model. It is 20MnCr5, with six Ø7 rollers on a 24 mm circle. Its own needle is SKF K 16×20×10, static rating 10 kN. The plate is sized as if it passes the full output torque.

The arm bearings are two SKF 61906, 30×47×9, static rating 4.55 kN each. Their centres are 16 mm apart. A 50 N·m tilt puts about 3.1 kN on one of them, static margin about 1.5. Both bearings sit in the front cover. The housing bore stays open, so the discs slide in from the front and the motor slides in from the back.

Contact pressure on a flat-flank check, 10 mm face, at the high torque:

- many teeth sharing: 962 MPa on the 10-pin stage, about 1,240 MPa at proof current
- three teeth sharing: the case the 2011 paper treats as a real clearance case
- three teeth sharing: about 1,030 MPa on the 10-pin stage
- one tooth sharing: about 1,560 MPa on that stage, just over the 1,500 MPa line

`calc.py` prints the three cases. The working target is the three-tooth case. One tooth is the extreme the 2011 paper checked, and on this smaller disc it is the overload that marks the surface.

## Size

Ø104 mm. From the encoder lid to the arm face is about 120 mm. v4 is 98 mm. The extra length is the 10 mm needles, the middle plate, and the pair of output bearings in front of the discs.

The arm face is unchanged: Ø40 pilot, 2 mm deep, six M5 on a 52 mm circle. The rear plate is the measured one: hex bore Ø21.1, cover bore Ø11, Meukron rhombus, cable groove at 0°, phase slot at 180°.

## Build order

1. Press the twelve Ø9 pins into the housing lip. The holes are 0.05 mm larger in radius than the pin.
2. Bolt the crank to the rotor with four M2 on the 38 mm circle. The stub hole is Ø3.2 for the measured Ø2.9 stub.
3. Slide the motor in from the back.
4. Slide the 11-lobe disc and its needle onto the first journal, from the front.
5. Slide the middle plate and its six rollers on. The rollers enter the first disc.
6. Slide the 9-lobe disc onto the second journal and onto those rollers.
7. Bring the output ring in from the front. Its ten Ø10 pins enter only the second disc.
8. Bolt the cover on. The two 61906 bearings load from opposite ends of the cover. The arm flange is the end of that output part.
