# Shoulder actuator

Z = 0 is the rear face. The axis is Z, pointing toward the arm. Masses of machined parts are from the model (`shoulder/cad/mass.txt`). Bought bearings use the catalogue mass. The exact solid is `shoulder/cad/actuator.step`. Loads and fits are from `shoulder/cad/calc.txt`. Ordering detail stays in `shoulder/bom.md`.

## Summary

This is a two-stage planetary shoulder joint, 30:1 overall (6:1 then 5:1). The body is Ø100 mm and 100.5 mm long. At the torso end it has a Ø112 mm rear flange, 16 mm deep, which is where it bolts to the torso. Modelled parts weigh 2,514 g. The motor adds 336 g, so the actuator is about 2.85 kg.

At 24 V the motor runs at 2,160 rpm, the first carrier at 360 rpm, and the output at 72 rpm. Continuous output is 30 N·m. Proof torque is 50 N·m, including a 50 N·m tilt case. The motor torque constant used in the calc is 0.0919 N·m/A, so 30 N·m needs about 12.1 A and 50 N·m needs about 20.2 A.

The real actuator is metal. Aluminium is used for the lid, the magnet holder, the rear plate, the housing, and the front cover. The gears, the rings, the carriers, and the planet pins stay steel: the stage-2 sun sees about 1,350 MPa contact stress at 30 N·m, which case-hardened 16MnCr5 can carry and aluminium cannot. The fit check is a 3D print of those same metal parts. Bought parts (motor, bearings, pins, screws, dowels, spring, washers, shims, magnets, electronics) are not printed.

Three classes:

- **3D print, then CNC in aluminium:** 01, 06, 08, 15, 45. The print file is `shoulder/cad/actuator_print.zip`.
- **3D print, then CNC in steel:** 16, 18, 21, 22, 24, 32, 33, 36, 42. Same zip.
- **Purchase:** everything else. Shop links are given only for the bearings and the wave spring.

### Rev 1.4: motor fit (from the first build)

The LA8308 was measured with a vernier: Ø92.0 mm, 32.5 mm from the mounting face to the rotor hub face, a Ø2.9 × 3.9 mm shaft stub on the front, and a rotating Ø17.4 mm cap on the rear that stays inside the mounting face. The phase leads leave the rear face at a radius of 32 mm, about 12 mm wide. Rev 1.3 had three faults against this motor:

1. **The motor could not go in.** The rear lip was Ø88 mm and the front was closed by the partition, so a Ø92 motor could not pass either end. Rev 1.4 opens the rear: the Ø94.5 bore runs through the rear face, and a Ø112 flange carries the plate screws.
2. **Sun-1 hit carrier-1 and the partition.** Rev 1.3 used the catalogue height of 28.5 mm and gave the 3.9 mm front stub only a 2 mm recess in sun-1. Rev 1.4 uses the measured 32.5 mm, moves the gearbox forward 5.0 mm, drills sun-1 Ø3.5 × 5.5 for the stub, and recesses carrier-1. Every axial gap is now 1.5 mm at the nominal shim. A shim pack (part 48) sets the axial position of the motor.
3. **The rear plate hole was smaller than the Ø17.4 cap.** That cap rotates, so it cannot centre anything. Rev 1.4 gives it a Ø19.5 relief, 1.05 mm radial clearance. The magnet holder now plugs into the cap's centre hole, so the magnet centres on the rotor axis.

The gearbox, bearings, and gears are unchanged. They sit 5.0 mm further forward.

## 01 Encoder lid

3D print for the fit check, then CNC from 6061-T6. Quantity 1. Mass 14.2 g. Size Ø59.8 mm × 2 mm.

It is the rearmost cover, from Z 0 to Z 2. Four M2 countersunk screws on a Ø54 mm circle clamp it to the rear plate. A slot at 0° lets the encoder cable out. A notch at 180° clears the phase-lead slot. Clear anodize. The screws are a light joint at 0.3 N·m.

## 02 Lid screws

Purchase. Quantity 4. Mass 0.13 g each. M2 × 4 countersunk, ISO 7046 or ISO 14581. Grade 8.8 or A2 is enough.

They sit in the lid, heads at Z 0, threaded into the rear plate. Torque 0.3 N·m. No threadlocker.

## 03 Encoder PCB

Purchase. Quantity 1. The model assigns no mass. Size 30 × 30 × 1.6 mm FR4, four Ø2.7 mm holes on a Ø34 mm circle.

It sits in the rear-plate pocket, rotated 45°, from Z 2.5 to Z 4.1, on the motor axis. It carries the AS5047P. The holes are the ISO 273 fine clearance for M2.5, so the board is centred within ±0.1 mm by its screws. A shielded SPI cable leaves through the plate groove. Keep grease off this board.

## 04 Encoder IC

Purchase. Quantity 1. The model assigns no mass. Package TSSOP-14, part AS5047P-ATSM.

It is soldered on the PCB, centred on the axis, from Z 4.1 to Z 5. The gap from the magnet to the IC is 1.25 mm with the nominal 1.0 mm shim pack, and 0.75–1.75 mm across the shim range (0.5–3.0 mm allowed). The die wants 35–70 mT. The centring budget is 0.55 mm worst case and 0.22 mm RSS, against 0.5 mm allowed (calc §9). The largest single items are the motor's own stator-hole accuracy, the countersunk stator screws, the PCB holes, and IC placement, each 0.1 mm.

## 05 PCB screws

Purchase. Quantity 4. Mass 0.46 g each. M2.5 × 5 pan head, ISO 7045 or ISO 14583.

They clamp the PCB to four bosses in the rear plate. Torque 0.4 N·m. No threadlocker.

## 06 Magnet holder

3D print for the fit check, then CNC from 6061-T6. Quantity 1. Mass 0.85 g. Body Ø10 mm × 4.75 mm with a Ø6 × 2.5 mm magnet pocket in the rear face. A Ø2.8 × 2 mm pin is on the front face.

It sits on the motor's rotating rear cap, from Z 6.25 to Z 11. The pin goes into the cap's centre hole, and that pin is what centres the magnet on the rotor axis. Turn the pin to the measured hole, 0–0.02 mm clearance. Glue the face and the pin with structural epoxy. If the hole turns out to be threaded, make the pin a matching threaded stub. The holder must be non-magnetic. Concentricity of pin to pocket within 0.03 mm TIR. No anodize required.

## 07 Encoder magnet

Purchase. Quantity 1. Mass 0.53 g in the model. Size Ø6 × 2.5 mm NdFeB, diametrically magnetised. The ams kit magnet is AS5000-MD6H-2.

It sits in the holder, from Z 6.25 to Z 8.75. Glue it with structural epoxy. Keep it below about 80 °C.

## 08 Rear mount plate

3D print for the fit check, then CNC from 7075-T651. Quantity 1. Mass 197.2 g. Size Ø112 mm × 10 mm.

It is the part that bolts to the torso, from Z 0 to Z 10. The housing flange lands on its front face at Z 10. It carries:

- the stator screws, 4 × M4 countersunk on a Ø40 mm circle at 45°;
- six M4 wire-thread inserts on a Ø76 mm circle for the torso, and two Ø4 torso dowels;
- six M3 counterbored holes on a Ø104 mm circle for the housing flange, and two Ø3 dowels on the same circle at 120° and 300°;
- the encoder pocket, and the encoder cable groove at 0°;
- the phase-lead slot at 180°: through the plate at a radius of 26–38 mm, 14 mm wide, continuing as a 5 mm deep groove in the rear face out to the rim.

A Ø19.5 × 1.5 mm relief in the front face clears the rotating Ø17.4 mm motor cap by 1.05 mm radially. The plate does not pilot the motor. The countersunk stator screws centre it. The stator hole pattern and the torso holes are unchanged from Rev 1.3, where they fitted the real motor. Clear anodize, type II, with the M3 counterbores masked.

## 09 Plate screws

Purchase. Quantity 6. Mass 1.12 g each. M3 × 12 socket head, ISO 4762, grade 12.9.

They clamp the rear plate to the housing flange on a Ø104 mm circle. Heads sit in the plate. Thread engagement in the flange is 6 mm, which gives a strip safety factor of 5.9. Torque 1.2 N·m with Loctite 243. At the proof load the slip safety factor is 2.2 and the separation safety factor is 5.3.

## 10 Plate dowels

Purchase. Quantity 2. Mass 0.33 g each. ISO 8734 Ø3 × 6 mm, hardened, m6.

They locate the rear plate on the housing flange at 120° and 300°, on a Ø104 mm circle, from Z 7 to Z 13. They are a backup. The six screws carry the torque.

## 11 Stator screws

Purchase. Quantity 4. Mass 1.24 g each. M4 × 10 countersunk, ISO 10642.

They clamp the motor stator to the rear plate on a Ø40 mm circle, heads toward the encoder, through the shim pack. Thread engagement in the motor is 6.0 mm minus the shim pack: 5.5, 5.0 or 4.5 mm. The motor's M4 holes must be at least 6 mm deep, so measure them. At 4.5 mm engagement and 2.0 N·m, the strip safety factor is 2.9. Use the motor maker's torque, not more than 2.0 N·m into an aluminium base. Loctite 243.

## 12 Motor stator

Purchase. Quantity 1. EaglePower LA8308, KV90, measured Ø92.0 × 32.5 mm (mounting face to rotor hub face), 336 g for the whole motor. The model is an envelope only and assigns this part no mass.

It sits in the open Ø94.5 housing bore with 1.25 mm radial clearance. The mounting face is at Z 11, on the 1.0 mm shim pack. The phase leads leave the rear face at a radius of 32 mm, 12 mm wide, at 180°, and pass through the plate slot. The model shows the lead exit block 2.5 mm proud of the mounting face. Measure the real protrusion.

## 13 Motor rotor

Purchase. Quantity 1. Part of the same LA8308. The model is an envelope and assigns no mass.

The bell runs from Z 14.5 to Z 43.5 around the stator, 1.25 mm radially inside the housing bore. Sun-1 bolts to the rotor hub face at Z 43.5, which is 1.5 mm behind the partition. The Ø2.9 × 3.9 mm front shaft stub sits in sun-1's Ø3.5 bore with 1.6 mm to spare. The Ø17.4 mm rear cap rotates inside the mounting face and carries the magnet holder. Sun-1 is drilled with 4 × M3 on a Ø31 mm circle and on a Ø25 mm circle. These four screws use whichever circle the real rotor has.

## 14 Motor shaft

Purchase. Quantity 1. It is part of the motor. The model shows a Ø6 mm rod from Z 14 to Z 41.5 and gives that rod a mass of 6.0 g. That is not the motor weight.

The rear end is under the rear cap. The front end comes out as the Ø2.9 stub.

## 15 Housing

3D print for the fit check, then CNC from 7075-T651 or T6511 bar. Quantity 1. Mass 370.8 g. Body Ø100 mm, rear flange Ø112 × 6 mm, 79 mm long.

It is the structural tube from Z 10 to Z 89. The rear is open: the Ø94.5 motor bore runs through the rear face, so the motor, already screwed to the plate, slides in from behind. The flange (Z 10–16) carries six M3 tapped through on a Ø104 mm circle and two Ø3 dowel holes.

Inside, from back to front:

- the motor bore, to Z 45;
- a 2.5 mm partition (Z 45–47.5) with the Ø41.0 mm H8 labyrinth;
- the Ø85 mm K6 bore for ring-1;
- the Ø89 mm G7 bore for the cartridge.

Twelve cooling slots, 3 mm × 20 mm at Z 19–39, pierce the motor-bore wall. Two radial slots in the front face of the partition, 3.02–3.04 mm wide and 1.5 mm deep, let the ring-1 dowels slide as the aluminium grows. The thinnest section is the 2.75 mm wall at the motor bore. At 50 N·m it sees 1.4 MPa in torsion, and 3.7 MPa in bending at the 65 N·m tilt case, so the section is set by stiffness, not by strength. Clear anodize, type II, with every fit and thread masked.

## 16 Ring-1

3D print for the fit check, then CNC from 42CrMo4 (EN19), quenched and tempered to 28–34 HRC. Quantity 1. Mass 190.8 g. Size Ø85 mm h5 × 15.35 mm. Internal gear, 90 teeth, module 0.8.

It is fixed in the housing from Z 47.5 to Z 62.85 and is the reaction ring of the first stage. The OD is a light interference at room temperature and becomes a clearance of about 44–81 µm at 80 °C, which is why the dowels, not the fit, keep it from spinning when hot. Teeth are wire-EDM, then gas or plasma nitrided, with 0.03–0.04 mm growth allowed and no grind afterwards. Inspection: dimension between Ø1.2 mm pins, Mi = 70.813 mm, plus 0.015 / minus 0. Two Ø3 mm H7 holes, 7 mm deep from the rear face, on a Ø79.5 mm circle, take the dowels.

## 17 Ring-1 dowels

Purchase. Quantity 2. Mass 0.44 g each. ISO 8734 Ø3 × 8 mm, hardened, m6.

They are pressed into ring-1 and slide in the housing slots. Axis at radius 39.75 mm, angles 45° and 225°, from Z 46 to Z 54. At the proof load each pin sees about 110 N, 16 MPa shear. A Ø4 pin pressed into both the steel ring and the aluminium housing would bind as they grow differently, so these stay Ø3 in a slot.

## 18 Sun-1

3D print for the fit check, then CNC from 16MnCr5, carburized. Quantity 1. Mass 42.8 g. Flange Ø40 mm × 3 mm, teeth Ø16 mm × 10.4 mm face, overall length 18.2 mm. 18 teeth, module 0.8.

The flange bolts to the rotor hub face at Z 43.5–46.5. The teeth run from Z 51.3 to Z 61.7 and drive the three planet-1 gears. The rear face has a Ø3.5 × 5.5 mm bore for the motor's 3.9 mm shaft stub, and a Ø18 × 0.5 mm relief that clears the hub centre. The flange is drilled for both rotor patterns: 4 × M3 countersunk on Ø31 mm, and 4 × M3 countersunk on Ø25 mm at 45°. Use the pattern that matches the motor. Carburize to a case depth of 0.12–0.18 mm, 58–62 HRC on the teeth, core 30–40 HRC, then hard-finish the teeth to ISO 1328 grade 6–7. Span over 3 teeth, W3 = 6.082 mm, minus 0.015 / plus 0.

The labyrinth between this flange (Ø40 h8) and the partition bore (Ø41.0 H8) is 1.00–1.08 mm on the diameter at 20 °C. The flange front face is 1.5 mm from carrier-1, and the tooth tips are 1.5 mm from the carrier-1 front plate.

## 19 Sun-1 screws

Purchase. Quantity 4. Mass 0.38 g each. M3 × 5 countersunk, ISO 10642, grade 12.9.

They clamp sun-1 to the rotor, heads toward the gears. Only about 2 mm of thread enters the rotor, so the torque is 0.8 N·m, not 1.2. On the smaller Ø25 mm circle the slip safety factor at the 50 N·m proof is 6.4. Loctite 243. Fit the four screws to the pattern the rotor actually has.

## 20 Carrier-1 rear washer

Purchase. Quantity 1. Mass 1.0 g. Size Ø48 mm / Ø42 mm × 0.3 mm. Hardened spring steel, or a stack of shims if the standard ring is the wrong size.

It is the thrust face between the stationary housing partition and the back of carrier-1, from Z 47.5 to Z 47.8. Flatness within 0.02 mm.

## 21 Carrier-1 rear

3D print for the fit check, then CNC from EN24T (34CrNiMo6), already quenched and tempered. Quantity 1. Mass 76.0 g. Envelope Ø60 mm × 14 mm, with three posts.

The plate is from Z 48 to Z 51. Three posts run forward to Z 62 on a Ø44 mm circle and are tapped M3. Three Ø8 mm R7 holes on a Ø43.2 mm circle hold planet pins 1. No further heat treatment. The R7 fit on an h6 pin is 4–28 µm interference, so the pin cannot walk.

## 22 Carrier-1 front and sun-2

3D print for the fit check, then CNC from 16MnCr5, carburized. Quantity 1. Mass 92.0 g. Plate Ø60 mm, sun-2 teeth Ø20 mm × 10 mm face, overall about 24 mm. Sun-2 is 18 teeth, module 1.0.

The plate is from Z 62 to Z 65 and closes carrier-1. A Ø19 × 1.2 mm recess in its rear face gives the sun-1 tooth tips 1.5 mm of axial clearance. Sun-2 teeth run from Z 76 to Z 86 and drive the second stage. Three M3 countersunk holes on a Ø44 mm circle bolt it to the posts. Carburize the sun to a case depth of 0.15–0.20 mm, 58–62 HRC, and mask the plate so it does not carburize. Span over 3 teeth, W3 = 7.609 mm, minus 0.015 / plus 0. Three Ø8 mm R7 holes take the front of planet pins 1.

## 23 Carrier-1 screws

Purchase. Quantity 3. Mass 0.66 g each. M3 × 10 countersunk, ISO 10642, grade 12.9.

They clamp the carrier-1 front plate to the posts, from the front face at Z 65. Torque 1.2 N·m with Loctite 243.

## 24 Planet-1

3D print for the fit check, then CNC from 16MnCr5, carburized. Quantity 3. Mass 41.6 g each. Size Ø30.4 mm × 10 mm face, bore Ø12 mm. 36 teeth, module 0.8.

They orbit at radius 21.6 mm, teeth from Z 51.5 to Z 61.5, between sun-1 and ring-1. Space them at 0°, 120°, and 240°. Carburize to 0.12–0.18 mm case, 58–62 HRC, and grind the bore after hardening. Bore Ø12 N6, roundness IT5/2, Ra at or below 0.8 µm. Span over 5 teeth, W5 = 11.008 mm, minus 0.015 / plus 0. Tooth grade ISO 1328 grade 6–7. Sun-1's 10.4 mm face covers at least 9.7 mm of the planet face across the shim range.

## 25 Planet-1 needle bearings

Purchase. Quantity 3, plus 2 spares. Catalogue mass about 3.1 g each. The model envelope weighs 4.9 g and is only a stand-in. Drawn-cup needle roller bearing HK0810, 8 × 12 × 10 mm, open ends.

One sits in each planet-1 bore, from Z 51.5 to Z 61.5, on the Ø8 mm pin. Press it into the Ø12 N6 bore with a stepped mandrel on the stamped end. Design to the lower catalogue rating, dynamic capacity 3.69 kN.

Buy: [INA HK0810](https://www.noksbearings.com/brand/ina/hk0810/needle-roller-bearings-ina), [SKF HK 0810 data sheet](https://documents.klium.nl/9ad58f0c-40d4-47fb-ab4e-48a1f5b26eee/en/technical-data-sheet-skf-hk-0810-hk-0810-en.pdf).

## 26 Planet pins 1

Purchase. Quantity 3. Mass 6.6 g each. Size Ø8 mm × 17 mm, 52100 (EN31) bearing steel.

Each pin is the inner race of a planet-1 needle bearing. It runs from Z 48 to Z 65, through both carrier-1 plates, 6 mm of press in each. Through-harden to 58–64 HRC, grind h6, Ra at or below 0.2 µm. The holes are Ø8 R7 (4–28 µm interference). Do not use a g6 shaft or an m6 dowel: the needle clearance would be wrong. No threads in the pin.

## 27 Planet-1 rear washers

Purchase. Quantity 3. Mass 0.24 g each. Size Ø14 mm / Ø8.2 mm × 0.3 mm. A DIN 988 ring, 8 × 14 × 0.3, is the standard candidate. Its bore is 8.04–8.19 mm, so check that one sample spins free on the Ø8 h6 pin before buying the set.

They sit behind each planet-1, from Z 51.2 to Z 51.5, so the gear does not rub the carrier.

## 28 Planet-1 front washers

Purchase. Quantity 3. Mass 0.24 g each. Same ring as 27.

They sit in front of each planet-1, from Z 61.5 to Z 61.8.

## 29 Wave spring

Purchase. Quantity 1, plus 1 spare. Mass 8.6 g in the model. Smalley SSB-0335, carbon steel. Bore clears 71.4 mm, outside fits inside 85 mm, free height 5.59 mm, thickness 0.76 mm, rate 83 N/mm, 231 N at the 2.77 mm catalogue work height.

It sits on the front face of ring-1, around Z 62.85, and pushes the rear 61813 outer ring forward. At the real stack the work height is about 2.65–3.07 mm and the force stays about 186–252 N, which is enough to keep the front bearing loaded. It acts on the floating outer ring only. A stainless option is SSB-0335-S17. Lispring LB-0335 is the drop-in alternate.

Buy: [Smalley SSB-0335](https://www.smalley.com/wave-spring/ssb-0335).

## 30 Carrier-1 front washer

Purchase. Quantity 1. Mass 1.9 g. Size Ø40 mm / Ø24 mm × 0.3 mm. Same hardened strip as the other thrust washers.

It is the thrust face between carrier-1 and carrier-2, from Z 65.2 to Z 65.5. The two carriers turn at different speeds, so this washer is what they rub on.

## 31 Rear output bearing

Purchase. Quantity 1, plus 1 spare. Catalogue mass about 130 g. The model splits it into rings, balls, and shields and under-weighs that split. 61813-2Z/C3, 65 × 85 × 10 mm, metal shields.

It is the rear output bearing, from Z 65.5 to Z 75.5. The outer ring must slide in the cartridge so the wave spring can preload the pair. The inner ring is on the Ø65 mm j5 seat of carrier-2. Order C3. A normal-clearance bearing would be preloaded by about 13 µm after the press fit and the temperature difference. C3 keeps about 2 µm of clearance. Dynamic capacity 11.9 kN, static 11.5 kN. The spare is so the cartridge bore can be matched to the measured outer diameter, 3–10 µm larger than that measurement.

Buy: [61813-2Z listing](https://en.tradebearings.com/61813_2Z-80293.html). Confirm C3 is printed on the box. The SKF shielded part is 61813-2Z/C3.

## 32 Carrier-2 rear

3D print for the fit check, then CNC from EN24T, already quenched and tempered. Quantity 1. Mass 232.3 g. Hub Ø65 mm × 10 mm, three posts, envelope about Ø67 mm × 21 mm.

The hub is the rear inner-ring seat, from Z 65.5 to Z 75.5, Ø65 mm j5. The posts run forward to Z 86.5 on a Ø54 mm circle and are tapped M4. The post faces are the shoulder for the rear inner ring. Three Ø8 mm R7 pin holes on a Ø45 mm circle are 6 mm deep from the front and stop on a 1.0 mm shoulder. A Ø3 mm hole through that shoulder vents the press and lets a punch drive the pin out. The rear lightening groove is Ø42–Ø59 mm and 3 mm deep, and it does not break the pin shoulder. No heat treatment unless a later endurance test shows fretting on the hub.

## 33 Bearing cartridge and ring-2

3D print for the fit check, then CNC from 42CrMo4, quenched and tempered to 28–34 HRC. Quantity 1. Mass 351.0 g. Flange Ø100 mm × 7.5 mm, spigot Ø89 mm, overall length 31.5 mm. Ring-2 is 72 teeth, module 1.0, cut in the same piece.

It is the front structure, from Z 65 to Z 96.5. The spigot is Ø89 mm h6 in the housing's G7 bore. The Ø85 mm bore holds both 61813 outer rings. Machine that bore after measuring the bearings: 3–10 µm larger than the measured OD, and the rear ring must still slide under the spring. Ring-2 teeth run from Z 75.8 to Z 86.2. Wire-EDM the teeth, tap the eight M2.5 cover holes before nitriding, then nitride. Finish Ø89 and Ø85 after nitriding, or mask them. Eight M3 counterbored holes on a Ø93 mm circle bolt the flange to the housing. Inspection of ring-2: dimension between Ø1.5 mm pins, Mi = 70.499 mm, plus 0.015 / minus 0.

## 34 Cartridge screws

Purchase. Quantity 8. Mass 1.01 g each. M3 × 10 socket head, ISO 4762, grade 12.9.

They clamp the cartridge flange to the housing. Heads at the front of the flange. Torque 1.2 N·m with Loctite 243. Slip safety factor at the proof load is 3.4. Thread engagement in the housing is 6 mm, strip safety factor 5.9.

## 35 Cartridge dowels

Purchase. Quantity 2. Mass 0.78 g each. ISO 8734 Ø4 × 8 mm, hardened, m6.

They stop the cartridge rotating in the housing, on a Ø94 mm circle, from Z 85 to Z 93. They are a backup. The eight screws carry the torque. At the proof load each pin sees about 420 N.

## 36 Planet-2

3D print for the fit check, then CNC from 16MnCr5, carburized. Quantity 3. Mass 35.2 g each. Size Ø29 mm × 10 mm face, bore Ø12 mm. 27 teeth, module 1.0.

They orbit at radius 22.5 mm, teeth from Z 76 to Z 86, between sun-2 and ring-2. Same spacing as planet-1. Carburize to 0.15–0.20 mm case, 58–62 HRC, and grind the bore. Bore Ø12 N6. Span over 4 teeth, W4 = 10.687 mm, minus 0.015 / plus 0. This is the high-load mesh: at 30 N·m the sun contact stress is about 1,350 MPa.

## 37 Planet-2 needle bearings

Purchase. Quantity 3, plus the same 2 spares as part 25. Same HK0810, 8 × 12 × 10 mm, catalogue mass about 3.1 g.

One sits in each planet-2, from Z 76 to Z 86. Same press and same capacity as part 25.

Buy: [INA HK0810](https://www.noksbearings.com/brand/ina/hk0810/needle-roller-bearings-ina), [SKF HK 0810 data sheet](https://documents.klium.nl/9ad58f0c-40d4-47fb-ab4e-48a1f5b26eee/en/technical-data-sheet-skf-hk-0810-hk-0810-en.pdf).

## 38 Planet pins 2

Purchase. Quantity 3. Mass 9.0 g each. Size Ø8 mm × 23 mm, 52100, same specification as part 26.

Each pin runs from Z 69.5 to Z 92.5. The rear 6 mm is pressed into carrier-2 rear and stops on the 1.0 mm shoulder. The front 6 mm is pressed into a blind R7 hole in carrier-2 front, with 0.3 mm of empty hole beyond the pin so the two carrier halves clamp on their faces. Grind a 0.2 mm vent flat on the front 6 mm only, clear of the needle track, so the blind hole can vent. Through-harden 58–64 HRC, grind h6, Ra at or below 0.2 µm.

## 39 Planet-2 rear washers

Purchase. Quantity 3. Mass 0.24 g each. Same Ø14 / Ø8.2 × 0.3 mm ring as part 27.

They sit behind each planet-2, from Z 75.7 to Z 76.0.

## 40 Planet-2 front washers

Purchase. Quantity 3. Mass 0.24 g each. Same ring.

They sit in front of each planet-2, from Z 86.0 to Z 86.3.

## 41 Front output bearing

Purchase. Quantity 1, plus 1 spare. Catalogue mass about 131 g. 61813-2RS1/C3, 65 × 85 × 10 mm, contact rubber seals.

It is the front output bearing, from Z 86.5 to Z 96.5, and the seals are the gearbox seal. The outer ring is located in the cartridge. The inner ring is on the Ø65 mm j5 seat of carrier-2 front. Order C3, for the same clearance reason as part 31. Dynamic capacity 11.9 kN. Use the lower static capacity, 9.65 kN. At 30 N·m and 72 rpm the calculated life of this bearing is about 209,000 hours.

Buy: [SKF 61813-2RS1](https://www.skf.com/uk/products/rolling-bearings/ball-bearings/deep-groove-ball-bearings/productid-61813-2RS1). Order the C3 clearance variant, 61813-2RS1/C3.

## 42 Carrier-2 front

3D print for the fit check, then CNC from EN24T, already quenched and tempered. Quantity 1. Mass 313.9 g. Flange Ø78 mm, hub Ø65 mm, overall length 14 mm.

This is the arm flange. The hub is from Z 86.5 to Z 97 and is the front inner-ring seat, Ø65 mm j5. The flange runs out to Z 100.5. Six M5 holes on a Ø52 mm circle, tapped 8 mm deep in the steel, take the arm screws. A Ø40 mm H7 pilot, 2 mm deep, centres the arm. Runout within 0.02 mm TIR, face flatness within 0.03 mm. Three Ø8 mm R7 holes, blind 6.3 mm deep, take planet pins 2. Three M4 counterbores on a Ø54 mm circle clamp this half to the rear half. A Ø3 mm radial hole in the rim at Z 98.75 holds the homing magnet.

## 43 Carrier-2 screws

Purchase. Quantity 3. Mass 2.65 g each. M4 × 16 socket head, ISO 4762, grade 12.9.

They clamp the two carrier-2 halves. Heads in the front flange. Torque 4.0 N·m exactly, with a torque driver and Loctite 243. The slip safety factor is 1.4, which is the lowest joint in the actuator, so this torque is not a suggestion.

## 44 Homing magnet

Purchase. Quantity 1, plus 2 spares. Mass 0.10 g. Size Ø3 × 2 mm NdFeB N52, axially magnetised.

It is glued in the rim of the output flange at radius 36.8 mm, Z 98.75, pole facing outward. At the 1.2–2.0 mm gaps used here the field is 97–201 mT, far above the hall sensor's 6.8 mT maximum operate point. Glue with structural epoxy.

## 45 Front cover

3D print for the fit check, then CNC from 7075-T651. Quantity 1. Mass 23.2 g. Size Ø100 mm outside, Ø80 mm inside, 3 mm thick.

It is the bearing retainer, from Z 96.5 to Z 99.5. The lip touches only the front outer ring. Eight M2.5 countersunk screws on a Ø93.2 mm circle bolt it to the cartridge. A pocket at 270° holds the hall sensor, with a wire slot to the outside edge. Clear anodize.

## 46 Hall sensor

Purchase. Quantity 1, plus 2 spares. The model assigns no mass. TI DRV5033FAQDBZR, SOT-23, omnipolar, open drain. Bandwidth 20–30 kHz. Operate point ±3.5 mT typical, ±6.8 mT maximum. Supply 2.5–38 V.

It sits in the cover pocket at 270°, from Z 97.6 to Z 99.2, facing the homing magnet across about 1.2–2.0 mm. A 10 kΩ pull-up to 3.3 V is required. The older DRV5032FB samples at 5 Hz and would miss the magnet, which is in view for about 14 ms, so do not fit that part. DRV5033AJ is an acceptable, less sensitive, alternate.

## 47 Cover screws

Purchase. Quantity 8. Mass 0.29 g each. M2.5 × 6 countersunk, ISO 7046 or ISO 14581.

They clamp the cover to the cartridge. The cartridge threads are M2.5 and must be tapped before the cartridge is nitrided. Torque 0.8 N·m with Loctite 222, so they can be removed without damaging the small threads.

## 48 Motor shims

Purchase, or laser-cut from shim stock. Quantity: a set of 0.25 mm and 0.5 mm shims, enough to stack 0.5–1.5 mm. The nominal pack is 2 × 0.5 mm, 12.5 g in the model. Size Ø50 / Ø19.5 mm, four Ø4.5 mm holes on a Ø40 mm circle at 45°. Stainless or spring-steel shim stock.

They sit between the rear plate (Z 10) and the motor mounting face, and set where the motor and sun-1 sit axially without moving the gearbox. To choose the pack: screw the motor to the plate on the nominal 1.0 mm pack and measure from the plate front face to the rotor hub face. The pack is 1.0 + (33.5 − reading) mm, rounded to 0.25 mm. Across 0.5–1.5 mm every axial gap (rotor to partition, sun-1 to both carrier-1 plates) stays between 1.0 and 2.0 mm. The magnet gap stays between 0.75 and 1.75 mm (calc §9).
