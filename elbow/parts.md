# Elbow actuator

Z = 0 is the rear face of the encoder lid. The axis is Z, pointing toward the forearm. Angles are measured from +X. All dimensions come from `elbow/cad/params.py`; the exact solid is `elbow/cad/actuator.step`; masses are model volume × Bambu data-sheet density (`elbow/cad/mass.txt`, 100% solid, so real prints with infill are lighter); loads, fits and clearances are printed by `elbow/cad/calc.py` into `elbow/cad/calc.txt`. Ordering and print detail stays in `elbow/bom.md`.

## Summary

This is a single-stage cycloid elbow joint, 20:1, driven by a T-Motor MN5008 KV170. The envelope is Ø80 mm at the front flange (Ø69 body) by 78.3 mm long. Modelled parts weigh 386.3 g; the motor adds 128 g, so the actuator is 514 g.

At 24 V the motor runs at 4,080 rpm no-load and the output at 204 rpm (1,224°/s). The rating is 4.93 N·m continuous (5.96 A) and 8.23 N·m proof (9.95 A), the 165 cm stage-2 case in `elbow/research.md` §3. `torque_constant` 0.0486 N·m/A; the ODESC `current_lim` of 10 A caps the output at 8.27 N·m. Output backlash is 21.3 mrad (1.22°) from the profile relief, the output-hole play and the dog play.

Gearbox: 21 steel ring pins Ø5 on Ø60, two 20-lobe discs (e 1.0, λ 0.70, profile relief 0.08) at 180°, six steel output pins Ø5 on Ø40 in Ø7.2 disc holes. The cam is carried by the output cage (6703 in the rear ring, 6701 in the pin plate) and driven by four dog screws in the rotor, so the motor bearings carry no gearbox load. One 61807 carries the output; the arm clevis carries tilt.

Four classes:

- **3D print ASA:** 01, 10, 26, 28.
- **3D print PLA (Bambu PLA Basic):** 14, 16, 24.
- **3D print PET-CF (Bambu PET-CF, hardened 0.6 mm nozzle, annealed):** 18, 20.
- **CNC or hand-made in 6061-T6:** 06, 08.
- **Purchase:** everything else.

The print file is `elbow/cad/actuator_print.zip` (parts 01, 10, 14, 16, 18, 20, 24, 26, 28). All print parts print without supports in the orientation given.

## 01 Encoder lid

3D print, ASA. Quantity 1. Mass 3.7 g. Ø46 × 2 disc with a Ø46 / Ø43.6 skirt to Z 4.1.

Rearmost cover, Z 0 to Z 4.1. Four Ø6 bosses carry four M3 countersunk holes on a Ø37 circle at 107.3° + 90° steps; four Ø5.5 holes on Ø34 at 62.3° + 90° clear the PCB screw heads. An 8 mm slot in the skirt at 220° lets the encoder cable and motor leads out. Print the outer face down.

## 02 Lid screws

Purchase. Quantity 4. Mass 2.2 g for 4. M3 × 8 countersunk, ISO 10642.

Heads flush at Z 0, through the lid into the M3 threads of the clamp ring (06, 2.5 mm thread); the tips end in Ø3.4 clearance holes in the housing wall. Torque 0.3 N·m. No threadlocker.

## 03 Encoder PCB

Purchase. Quantity 1. 30 × 30 × 1.6 mm FR4, four Ø2.7 holes on Ø34. Same board as shoulder P12.

Z 2.5 to Z 4.1, on the rear face of the clamp ring, turned 17.3° so its holes sit at 62.3° + 90°. It carries the AS5047P on its front face, on the motor axis. Keep grease off this board.

## 04 Encoder IC

Purchase. Quantity 1. AS5047P-ATSM, TSSOP-14.

Z 4.1 to Z 5.0. The magnet face is 1.0 mm in front of the package (ams allows 0.5–3.0 mm) [E13].

## 05 PCB screws

Purchase. Quantity 4. Mass 1.8 g for 4. M2.5 × 5 socket head, DIN 912.

Heads in the lid's Ø5.5 holes, through the PCB into the clamp ring's M2.5 threads (2.5 mm); the tips end in Ø2.9 clearance holes in the housing wall. Torque 0.2 N·m. No threadlocker.

## 06 Motor clamp ring

CNC (or drill and tap by hand) from 3 mm 6061-T6 plate, faced to 2.5. Quantity 1. Mass 9.7 g. Ø46 / Ø12 × 2.5.

Z 4.1 to Z 6.6, against the rear face of the housing wall. Four M3 countersinks on Ø25 at 84.8° + 90° for the motor screws; four M2.5 tapped holes on Ø34 (PCB); four M3 tapped holes on Ø37 (lid). It spreads the motor-screw clamp over the ASA wall (2.56 MPa, calc §5) and gives metal threads to the lid and PCB.

## 07 Motor screws

Purchase. Quantity 4. Mass 2.7 g for 4. M3 × 10 countersunk, ISO 10642, 12.9 (10.9 standard is fine).

From the ring face at Z 4.1 through the ring and the 2.2 mm wall into the motor base: 5.3 mm of the base's 7.0 mm thread. Torque 0.5 N·m (slip 9.91 N·m against 0.73 N·m motor torque at 15 A, SF 13.6, calc §5). Loctite 243 placed in the motor-base holes only, not on the screw, so none touches the ASA [E11].

## 08 Magnet cup

Lathe or drill from Ø10 6061-T6 bar. Quantity 1. Mass 0.4 g. Ø10 × 3, magnet pocket Ø6 × 2.5 open to the rear.

Z 6.0 to Z 9.0, bonded with epoxy to the rotating shaft-end retainer on the back of the motor (its front face at Z 9.0). It must be non-magnetic and centre the magnet within 0.5 mm of the motor axis [E13]. Radial clearance to the housing wall bore (Ø11.5) is 0.75 mm.

## 09 Encoder magnet

Purchase. Quantity 1. Mass 0.5 g. Ø6 × 2.5 NdFeB, diametrically magnetised (ams AS5000-MD6H-2).

Bonded in the cup, face at Z 6.0, 1.0 mm from the IC.

## 10 Housing

3D print, ASA. Quantity 1. Mass 76.2 g. Body Ø69 (Z 6.6–53.8), 45° chamfer (Z 53.8–59.3), flange Ø80 (Z 59.3–67.3). Length 60.7.

- Rear wall Z 6.6–8.8 (2.2 thick), Ø11.5 centre bore for the magnet cup.
- Motor pilot collar Ø31 / Ø35 × 2.0 (Z 8.8–10.8) takes the motor base flange.
- Motor bore Ø58.4 (Z 8.8–41.3): 1.4 radial clearance around the rotor can; the closest rotor-to-housing gap anywhere is 0.83 (`cad/gen.log`).
- Disc bore Ø59.94 (Z 41.3–67.3), open to the front face so the discs go in from the front; disc clearance 0.55 radial.
- 21 ring-pin grooves Ø5 on Ø60 at 0° + 17.143° steps, from Z 37.1 (pin seat) to the front face. Between Z 37.1 and 41.3 the bore is Ø58.4, so each groove opening is 4.67 mm, narrower than the pin: the pins cannot fall inward (calc §2).
- Wall holes: 4 × Ø3.4 on Ø25 at 84.8° + 90° (motor screws), 4 × Ø3.4 on Ø37 at 107.3° + 90° (lid screw tips), 4 × Ø2.9 on Ø34 at 62.3° + 90° (PCB screw tips).
- Lead port 8 wide, Z 9.8–15.8, at 220°.
- Front flange: 7 insert holes Ø4.0 × 6.7 deep on Ø71 at 8.57° + 51.43° steps (between pins, wall 2.50 to the OD and 2.85 to the nearest pin groove; Ruthex minimum 1.6 [E5]); 2 dowel holes Ø3 × 6 deep at 25.71° and 180.0°.

Print rear face down. The chamfer removes the flange overhang.

## 11 Motor stator and base

Purchase (with 12). T-Motor MN5008 KV170, 128 g for 11 + 12 [E1]. Geometry from the official T-Motor STEP (`elbow/cad/vendor/tmotor-mn5008.step`).

Base face at Z 8.8; the Ø31 × 3.5 pilot flange sits in the housing collar. Four M3 holes on Ø25 at 84.8° + 90°, 7.0 deep. Phase leads leave at 220°.

## 12 Motor rotor and shaft

Purchase (with 11). Can Ø55.6, Z 17.05 to the top face at Z 35.8 (flat to Ø24). Four M3 holes on Ø12 at 45° + 90° (8.5 deep in the model: **measure on arrival**). Ø4 shaft tip at Z 40.7 inside a Ø5 clearance bore in the cam (no contact).

## 13 Dog screws

Purchase. Quantity 4. Mass 1.8 g for 4. M3 × 8 set screw, flat point, ISO 4026, 45H.

Z 30.8 to Z 38.8: 5.0 mm in the rotor top holes, 3.0 mm protruding into the cam's Ø3.4 pockets (0.2 radial play, 1.0 axial to the pocket floor). They pass torque only, so motor-to-cam misalignment up to 0.2 mm adds no radial load to the motor bearings. At 15 A two dogs bear: 61 N each, 8.1 MPa in the PLA pocket, 79 MPa bending in the screw (calc §4). Set the 3.0 protrusion with a depth gauge. Loctite 243 placed in the bottom third of the rotor holes [E11].

## 14 Cam

3D print, PLA, 100% infill. Quantity 1. Mass 8.7 g. Length 28.5 (Z 36.3–64.8).

| Z | Feature |
|---|---|
| 36.3–41.3 | Ø17 journal for the 6703 (bearing at 37.3–41.3); four Ø3.4 × 3.5 dog pockets on Ø12 at 45° + 90° in the rear face |
| 41.3–41.8 | Collar Ø18 (6703 inner-ring shoulder), trimmed to r 9.8 about the eccentric-A axis so the 6704-A slides over it with 0.2 clearance |
| 41.8–48.3 | Eccentric journal A, Ø20 centred at +1.0 X (6704-A at 44.3–48.3) |
| 48.3–53.8 | Lens: intersection of two Ø22 circles at ±1.0 X (shoulder for both 6704 inner rings) |
| 53.8–57.8 | Eccentric journal B, Ø20 centred at −1.0 X |
| 57.8–60.8 | Collar Ø13.2 (6701 inner-ring shoulder); 6704-B bore clears it by 2.4 |
| 60.8–64.8 | Ø12 journal for the 6701 |

A Ø5 bore from the rear clears the motor shaft tip. Print rear face down; the largest ledge is 2 mm at the start of journal A (not a bearing face).

## 15 Cam rear bearing

Purchase. Quantity 1. Model mass 3.8 g. 6703-2RS, 17 × 23 × 4. C 999 N, C0 657 N (lowest sourced value) [E3].

Z 37.3 to Z 41.3. Outer ring in the rear-ring seat against its Ø20 lip; inner ring on the Ø17 journal against the collar (land 0.30–0.50 mm on the trimmed side). Worst s0 3.66 at proof (need 1.0), 6.10 continuous (need 1.5) (calc §4) [E4].

## 16 Cage rear ring

3D print, PLA, 100% infill. Quantity 1. Mass 9.0 g. Ø50 × 5 (Z 36.3–41.3).

Lip Ø20 (Z 36.3–37.3) behind the 6703 outer ring; seat Ø23 (Z 37.3–41.3). Six Ø5 through holes on Ø40 at 0° + 60° take the rear ends of the output pins (4.5 mm engaged, pin ends 0.5 mm inside the rear face). Pin bearing stress 6.2 MPa at proof. Axial gap to the rotor top 0.5. Print lip face down.

## 17 Disc A bearing

Purchase. Quantity 1. Model mass 5.6 g. 6704-2RS, 20 × 27 × 4. C 1,010 N, C0 722 N (lowest sourced value) [E3].

Z 44.3 to Z 48.3, on eccentric journal A against the lens. s0 3.68 continuous (196 N), 2.20 proof (328 N); L10 at the continuous load 136 Mrev, 529 h at full speed (calc §4) [E4].

## 18 Cycloid disc A

3D print, Bambu PET-CF, 100% infill, then anneal 80 °C for 12 h (the data-sheet test condition) [E7]. Quantity 1. Mass 18.6 g. 9.0 thick (Z 41.8–50.8).

- Outline: 20 lobes, equidistant (relief 0.08) of the epitrochoid for 21 pins Ø5 on R 30, e 1.0 (λ 0.70). Radius in its own frame 26.420–28.420; smallest convex radius 2.24; no self-intersection.
- Six Ø7.2 output holes on Ø40 at 0° + 60° (webs 2.82 outer, 2.90 inner).
- Bearing seat Ø27 from Z 44.3 to the front face; lip Ø25.4 (Z 41.8–44.3) on the rear face.
- In the model it is centred at +1.0 X (cam angle 0).

Sweep over one input turn: ring-pin gap ≥ 0.079, output-pin gap ≥ 0.100; with maximum-size m6 pins 0.073 / 0.094 (calc §2b). Ring-pin contact p0 61.8 MPa continuous (limit 75.7) and 79.8 MPa proof (limit 113.6), with 10 or more pins loaded (calc §3). Print lip face down.

## 19 Disc B bearing

Purchase. Quantity 1. Model mass 5.6 g. 6704-2RS, as 17.

Z 53.8 to Z 57.8, on eccentric journal B against the lens.

## 20 Cycloid disc B

3D print, Bambu PET-CF, as 18. Quantity 1. Mass 18.6 g. Z 51.3 to Z 60.3.

Same outline turned −9° (half a lobe) so that it meshes at 180° to disc A; centred at −1.0 X in the model. Bearing seat Ø27 from the rear face to Z 57.8; lip Ø25.4 (Z 57.8–60.3) on the front face. Print lip face down.

## 21 Ring pins

Purchase. Quantity 21. Mass 96.6 g for 21 (4.6 g each). Ø5 × 30 dowel, ISO 8734 type A, m6 (Ø5.004–5.012), 550–650 HV30 [E6].

On Ø60 at 0° + 17.143° steps, Z 37.1 to Z 67.1. The rear ends sit on the groove floors; the front ends stop 0.2 mm short of the retainer. They drop into the grooves after the motor is in (the rotor, Ø55.6, is larger than the pins' inner edge, Ø55.0).

## 22 Output pins

Purchase. Quantity 6. Mass 27.6 g for 6. Ø5 × 30 dowel, ISO 8734 type A, m6 [E6].

On Ø40 at 0° + 60°, Z 36.8 to Z 66.8. Pressed into the carrier from the rear until they stop on the boss (6.0 mm engaged), then into the rear ring (4.5 mm). Proof: 155 N per pin, 59.4 MPa Hertz in the disc hole, 82 MPa bending (calc §3b).

## 23 Cam front bearing

Purchase. Quantity 1. Model mass 2.9 g. 6701-2RS, 12 × 18 × 4. C 922 N, C0 530 N [E3].

Z 60.8 to Z 64.8. Outer ring in the carrier pocket against its floor; inner ring on the Ø12 journal against the Ø13.2 collar. A Ø15 × 0.5 relief in front of it keeps the pocket floor off the inner ring. Worst s0 2.89 at proof (183 N), 4.82 continuous (calc §4).

## 24 Output carrier

3D print, PLA, 100% infill. Quantity 1. Mass 23.6 g.

- Pin plate Ø51 × 6 (Z 60.8–66.8): six Ø5 holes on Ø40 for the output pins, closed in front by the boss over r 17.5–19; 6701 pocket Ø18 × 4 from the rear face.
- Boss Ø38 (Z 66.8–69.3): shoulder for the 61807 inner ring.
- Hub Ø35 (Z 69.3–75.9): seat for the 61807. Its front face is 0.4 below the inner-ring face, so the forearm plate clamps the inner ring. The forearm plate must stay inside Ø38 to clear the seal.
- Six insert holes Ø4.0 × 6.7 on Ø26 at 0° + 60° (wall 2.50); two dowel holes Ø3 × 5 at 30° and 210° on Ø26.

The hub screws alone slip at 6.18 N·m (SF 0.75 against proof), so the two Ø3 dowels carry the torque: 317 N each, 21.1 MPa bearing in PLA against 31 MPa yield (SF 1.5, calc §5). Print pin-plate face down.

## 25 Hub inserts

Purchase. Quantity 6. Mass 1.6 g for 6. Ruthex RX-M3x5.7 brass heat-set insert, hole Ø4.0 [E5].

Z 70.2 to Z 75.9 in the hub; they take the forearm screws (arm CAD), 0.2 N·m.

## 26 Retainer ring

3D print, ASA. Quantity 1. Mass 7.1 g. Ø80 / Ø44.4 × 2 (Z 67.3–69.3).

Covers the ring-pin front ends and backs the 61807 outer ring (Ø44.4 = outer-ring shoulder; clears the inner ring and seal). Seven Ø3.4 and two Ø3 holes match the housing flange. Print flat.

## 27 Output bearing

Purchase. Quantity 1. Model mass 27.0 g. SKF 61807-2RS1, 35 × 47 × 7. C 4.75 kN, C0 3.2 kN [E2].

Z 69.3 to Z 76.3. Inner ring on the Ø35 hub against the Ø38 boss; outer ring in the cover's Ø47 bore, held between the retainer and the cover lip. Alone (without the clevis sharing tilt), worst s0 7.3 at proof with 4.20 N·m tilt (calc §4).

## 28 Front cover

3D print, ASA. Quantity 1. Mass 18.9 g.

Flange Ø80 / Ø47 × 5 (Z 69.3–74.3), neck Ø52 / Ø47 (Z 74.3–76.3), lip Ø52 / Ø44.4 (Z 76.3–78.3) in front of the 61807 outer ring. Seven Ø3.4 holes; two blind Ø3 dowel holes to Z 73.5. Front face at Z 78.3. Print flange down (the lip is a 1.3 mm inward ledge).

## 29 Housing inserts

Purchase. Quantity 7. Mass 1.9 g for 7. Ruthex RX-M3x5.7 [E5].

Z 61.6 to Z 67.3 in the housing flange.

## 30 Washers

Purchase. Quantity 7. Mass 0.8 g for 7. M3, ISO 7089 (Ø7 / Ø3.2 × 0.5).

Z 74.3 to Z 74.8, under the flange-screw heads (head pressure 13.0 MPa on the ASA).

## 31 Flange screws

Purchase. Quantity 7. Mass 7.9 g for 7. M3 × 12 socket head, DIN 912.

Heads Z 74.8–77.8 (below the front face), through cover and retainer into the housing inserts with 4.5 mm engaged. Torque 0.2 N·m: preload 396 N each, slip 19.69 N·m against 8.64 N·m (SF 2.28), insert pull-out SF 3.5 (calc §5). No threadlocker in inserts [E11].

## 32 Flange dowels

Purchase. Quantity 2. Mass 1.3 g for 2. Ø3 × 12, ISO 8734.

Z 61.3 to Z 73.3: pressed 6 mm into the housing, through the retainer, sliding 4 mm into the cover. Back-up to friction: 122 N each, 6.8 MPa in ASA at proof.

## Assembly

The order is fixed by three facts: the rotor is larger than the pins' inner edge, so the motor goes in before the ring pins; the discs go in from the front; and the cam, discs, rear ring, output pins and carrier form one cage unit.

1. Heat-set the 7 housing inserts (29) and the 6 hub inserts (25).
2. Press 6704-A into disc A from the front (onto the lip); press 6704-B into disc B from the rear. Press the 6703 into the rear ring from the front.
3. Carrier, on the bench:
   1. Drop the retainer (26) over the hub; it clears the Ø38 boss.
   2. Press the 61807 onto the hub with the pin-plate rear face flat on the bench, pushing on the inner ring only, until it seats on the boss. Do this first: later the 6701 and the pins block the rear face. Once the carrier is in the housing nothing holds the cage from behind, and the retainer cannot pass over the bearing afterwards.
   3. Support the carrier on its hub face (a Ø30 tube clears the inner ring). Press the 6701 into the pocket from the rear, then the 6 output pins until they stop on the boss.
4. Cage unit, on the bench:
   1. From the rear of the cam, slide disc A with its bearing onto journal A until the inner ring stops on the lens.
   2. Slide the rear ring with its 6703 onto the Ø17 journal until the inner ring stops on the collar.
   3. From the front, slide disc B with its bearing onto journal B until it stops on the lens.
   4. Turn the cam so that the disc holes line up with the pins. Push the carrier on, pressing on its hub face, until its 6701 seats on the Ø13.2 collar while the pins enter the rear ring.
   5. Check that the rear-ring front face to the pin-plate rear face measures 19.5 mm (Z 41.3 to 60.8).
5. Housing, rear end:
   1. Put the motor in from the front, base flange into the Ø31 collar, with the leads through the port at 220°.
   2. Fit the clamp ring and the four M3 × 10 screws at 0.5 N·m.
   3. Bond the magnet in the cup and the cup onto the rotor retainer through the Ø11.5 wall bore, centred within 0.5 mm.
6. Fit the dog screws: thread them into the rotor top so they protrude 3.0 mm.
7. Press the 2 flange dowels 6 mm into the housing. With the housing front up, drop the 21 ring pins into their grooves.
8. Grease the pins and the disc lobes lightly (Super Lube 21030). Lower the cage unit (with retainer and 61807) in from the front, turning the cam until the dogs enter the pockets and the discs mesh. The retainer lands on the dowels.
9. Fit the cover over the 61807 and the dowels, then the 7 × M3 × 12 screws with washers at 0.2 N·m.
10. Encoder: fit the PCB on the ring (4 × M2.5 at 0.2 N·m), then the lid (4 × M3 at 0.3 N·m).
11. ODESC axis 1: `pole_pairs 14`, `torque_constant 0.0486`, `current_lim 10`. The output turns opposite to the motor, so invert the direction.

Disassembly is the reverse. The cage unit must come out before the ring pins, and the ring pins before the motor.
