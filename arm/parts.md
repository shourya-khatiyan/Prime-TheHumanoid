# Arm Rev 0 (upper arm, elbow clevis, lattice forearm; no hand in v0)

World frame: origin on the shoulder axis at the shoulder output-flange face. +Y is the shoulder axis pointing outboard, +X forward, +Z up; at 0° the arm hangs along −Z. The elbow axis is parallel to Y at Z −298. Part positions near the elbow are given in the **elbow frame E**: z along the elbow axis (z 0 = elbow lid rear face, world Y = z + 9.5), y downward from the axis (the forearm length s), x forward.

All dimensions come from `arm/cad/arm_params.py`. The exact model is `arm/cad/arm.step` (arm + elbow + shoulder). Checks are in `arm/cad/gen.log` (interference, flexion sweep, bed fit) and `arm/cad/calc.txt` (loads, sections, joints, bearings, stop, encoder). Masses are in `arm/cad/mass.txt`. Ordering and print settings are in `arm/bom.md`.

## Summary

| Item | Value |
|---|---|
| Lengths | Upper arm 298, forearm 234 (elbow axis to wrist face), 160 cm build. The hand (173) is not built in v0; its centre (s 320.5) stays the LC3 / LC4 load point |
| Range | 0–135° in software; hard stops at −5° and 140° (O-ring buffered pin in a slot) |
| Design load | Arm never weaker than the shoulder: 50 N·m shoulder proof (LC2), 50 N·m tilt proof as a 94 N wrist / 114 N future-hand side load (LC3, LC4), 12.35 N·m stop (LC5) |
| Lattice | 45° diamond windows (print without support): upper arm front and back faces, drum, all four faces of the forearm tube; spoked cap; slotted ring; pocketed adapter |
| Mass | 1.327 kg incl. the 0.499 kg elbow actuator (was 1.535 kg with the dummy hand and closed shells). Printed parts at the print estimate (walls solid, 40% infill). Research budget 1.18 kg (+12%) |
| Gravity | Shoulder, arm horizontal: 3.07 N·m, 4.06 N·m with 180°/s in 0.25 s (SF 7.4 against 30 N·m continuous). Elbow, forearm horizontal: 0.16 N·m |
| Lowest margins | Upper-arm window bypass 15.15 MPa of 17.0 at Z −70; X-bar buckling SF 2.3; hub plate friction SF 1.82 (hex key as backup); insert pull-out SF 1.5 (estimated); hard stop needs the firmware rule in "Hard stop" |
| Checks | 0 interferences at 0°; sweep −5…140°: closest moving gaps 0.50 mm (retainer to encoder bracket, slot floor to stop pin) and 0.58 mm (cheek A boss to the 61807 seal); forearm to upper arm and ring ≥ 1.5 mm at every angle; all prints fit the P1S |

The elbow is a **clevis**: cheek A (part of the forearm print) is bolted to the elbow output hub and rides on the elbow's 61807. Cheek B rides on a 61804 on a fixed aluminium pin in the upper arm's rear ear. Bearing span is 89.9 mm, so a side load at the hand becomes a 407 N couple (LC4) instead of a tilt on the 61807. The **absolute output encoder** (AS5047P on the pin, magnet in the cover that turns with the forearm) sits 33.1 mm from the motor encoder magnet (rule ≥ 30). Its stray field there is 0.37 mT against the 35–70 mT working range (calc §8) [A9].

Classes:

- **3D print ASA (Bambu ASA):** 104, 108, 110, 125, 128, 133, 140.
- **CNC / lathe 6061-T6:** 101, 115, 122, 134.
- **Purchase:** everything else.

Allowables: Bambu ASA tensile 37 ± 3 MPa in-layer, 31 ± 4 MPa across layers; modulus across layers 2,120 ± 260 MPa [A1]. The calc uses mean − 1 sd with SF 2.0: 17.0 MPa in-layer, 13.5 MPa across layers, 7.8 MPa interlayer shear. Lattice bars in vertical walls run at 45° to the layers and are checked against the across-layer value; their buckling uses 1,860 MPa with SF 2.0.

**Lattice rules (calc §3, §4).** Windows are 45° diamonds, so the upper edges print without support. Corners are R1.5. The bars between two windows form an X: each carries the face shear (torsion flow + half the direct shear) as V / (2 sin 45°). Every upper-arm window is also checked as if its face were cut through: the torque then passes the window as a couple on the inboard and outboard channels (window bypass). Aluminium is not needed: the worst lattice stress is 15.15 of 17.0 MPa in ASA.

## Shoulder interface

### 101 Adapter plate

CNC from 8 mm 6061-T6, faced to 6. Quantity 1. Mass 64.0 g.

- Hexagon 76 AF, corners R6, world Y 0–6.
- Spigot Ø39.982 (Ø40 g6) × 1.8 into the shoulder flange's Ø40 H7 pilot (0.2 short of the pilot floor).
- Bore Ø28.
- 6 × Ø5.5 on Ø52 at 30° + 60° (shoulder M5).
- 6 × M4 tapped through on Ø68 at 15° + 60° (hub plate).
- 3 × Ø9 × 0.3 reliefs on Ø54 at 60/180/300° over the shoulder's carrier-2 screw heads.
- Lightening on the hub face: annular groove r 15–20 × 3 deep (4.8 mm floor with the spigot), and 6 × Ø7 × 3 pockets on Ø52 at 0° + 60°, clear of the M5 washers and the M4 threads. The hub contact is still 2,837 mm² (3.2 MPa under the 6 M4).

The aluminium plate carries the joint torque from the M5 pattern to a 76 mm hexagon key, so the printed hub sees bearing on six flats instead of six screw holes.

### 102 / 103 Adapter screws and washers

Purchase. 6 × M5 × 12 ISO 4762 12.9 + 6 × M5 ISO 7089. Torque **8.0 N·m**, Loctite 243 (metal to metal; this is shoulder F12). Preload 9,920 N each: slip 232 N·m (SF 4.64), separation 733 N·m against the 50 N·m tilt (calc §5).

### 104 Upper arm, shoulder half

3D print ASA. Quantity 1. Mass 178 g (print estimate 177 g; the part is almost all walls).

- **Drum** Ø100 (the shoulder housing diameter), world Y 1–61, wall 2.5. Rear cable exit Ø14 at Y 34. Four diamond windows 26 × 36 centred at Y 37.5, at flange angles 0° (front), 180° (rear, round the cable exit), 252° and 288° (top). All are clear of the beam root (50–130°) and the cap bosses.
- **Hub plate** Y 1–16:
  - hex pocket 76.3 AF (0.15 clearance per flat), 5 deep;
  - 6 × Ø11 M5-head pockets to Y 12.5;
  - 6 × Ø4.5 M4 clearance;
  - Ø30 centre hole;
  - outside the M4 washers the floor steps down to Y 8 (r 40.5–47.5).
- 4 × Ruthex M3 insert holes on Ø92 at 45° + 90° for the cap.
- **Beam**: octagon shell, wall 2.5, Z −30 to −150. Back face X −32 tapering to −34 by Z −226; front X 32 tapering to 28 by Z −208; Y 1–61; chamfer 15.
- **Beam windows**: 3 diamonds 20 × 20 on the front and on the back face, centred at Y 31 and Z −70 / −100 / −130 (tips Z −60 to −140). The X-bars between them are 7.07 wide. The inboard and outboard faces stay closed.
- **Mid-span collar** Z −150 to −142: 4 × Ø4.5 bolt holes (X −40.2 / 36.3 at Y 7 and 55) and 2 × Ø4 dowel holes at Y 31.

Print the inboard face (Y 1) on the bed. The beam layers then run along the arm, so bending stress is in-layer.

### 105 / 106 Hub screws and washers

Purchase. 6 × M4 × 16 ISO 4762 12.9 + 6 × M4 DIN 9021 (Ø12 / Ø4.3 × 1) [A13]. Through the hub plate into the adapter's threads (6 mm, 9 pitches). Torque **1.0 N·m**, Loctite 243 placed in the adapter threads only, kept off the ASA [A10].

- Preload 1,490 N; 15.1 MPa under the washers (limit 17.0).
- Friction slip 91.2 N·m against 50 N·m (SF 1.82); separation 98.2 N·m against 50 N·m (SF 2.0).
- If the ASA relaxes, the hex key is the backup: 677 N per flat, 14.6 MPa peak in the best case (calc §5).
- **Re-torque after 24 h** (ASA creep under clamp).

### 107 / 108 / 109 Cap

Cap: 3D print ASA, Ø100 × 2.5, 12.4 g. Spoked diaphragm: four windows r 13–37 between 8 mm spokes on the screw diagonals (R2 corners); the hub screws can be reached through them. Decorative groove r 40–41.2 × 0.6. Fixed with 4 Ruthex RX-M3x5.7 (107) and 4 × M3 × 8 ISO 10642 (109) at 0.4 N·m. Print the outer face down.

## Mid-span joint

### 110 Upper arm, elbow half

3D print ASA. Quantity 1. Mass 199 g solid, 156 g print estimate.

- **Collar** Z −160 to −150: 4 Ruthex RX-M4x8.1 insert holes (Ø5.6 × 9.1) and 2 × Ø4 dowel holes.
- **Beam** Z −150 to −196, then flares to the **crown** (Y up to 85.3) by Z −226. The front narrows to X 12 by Z −236. One 20 × 20 diamond window on the front and one on the back face at Z −178.
- **Crown pocket**: octagon pocket 3 inset from the skin, Y 44–72. **Cable channel** X −24…4, Y 6–40, from the beam cavity down to 25 above the elbow axis.
- **Saddle** R41.5 round the elbow actuator. **Ring pocket** 1.5 deep: the front ring is let into the crown face as a shear key. 4 RX-M4x8.1 holes for the ring.
- **Rear ear** (world Y 1–9, R24 round the axis, plus a 42 wide web up into the crown):
  - Ø16 bore for the pin spigot;
  - 3 RX-M3x5.7 holes on Ø30 at 90/210/330° (E frame);
  - 6 × 3 encoder-wire groove on its inner face.

Print the inboard face (Y 1) on the bed.

Stresses (calc §3, §6):

- Beam (both halves): worst LC2 + LC4 von Mises 11.29 MPa at the Z −70 window (closed section at Z −50: 9.56); Bredt shear ≤ 2.43 MPa (limit 7.8).
- Windows: X-bars 9.39 MPa (limit 13.5), buckling SF 2.3; window bypass at most 3.98 MPa on top of the beam stress, 15.15 MPa total at Z −70 (limit 17.0).
- Crown: ≤ 3.25 MPa.
- Ear: 10.8 MPa von Mises under the LC4 couple.

### 111–114 Joint hardware

4 × RX-M4x8.1 in 110 (111), 4 × M4 × 16 ISO 4762 (112) from 104 with DIN 9021 washers (113), 2 × Ø4 × 16 ISO 8734 dowels (114), 8 mm in each half. Torque **1.0 N·m**, no threadlocker (inserts) [A10].

- Worst bolt load 374 N (LC3) against 1,490 N preload: no separation (SF 4.0).
- Torsion LC4 36.6 N·m against 80.8 N·m friction (SF 2.2). The dowels are the backup (15.0 MPa bearing).

## Elbow clevis

### 115 Front ring

CNC from 4 mm 6061-T6. Quantity 1. Mass 44.2 g.

- Ø88 disc (E z 74.3–78.3, on the elbow cover flange) plus a tab up the crown: X −31…9, 69 above the axis, R4 corners.
- Ø52.2 bore pilots on the elbow cover neck (Ø52).
- 7 × Ø3.4 on Ø71 at the elbow flange angles + 36°.
- 4 × M4 countersinks at (−24, −52), (2, −52), (−24, −63), (2, −63) (E frame).
- **Stop boss** Ø10 × 3 on the front face at r 35.5, ψ −32.57° (between two flange screws), with a Ø5 press hole through ring and boss (7 mm).
- **4 kidney slots** 11.5 wide on r 35.25, ±7.5° about the screw-gap centres at ψ 18.9°, 70.3°, 121.7° and 173.1°: below the tab and away from the stop pin, 2.0 mm clear of the washers. Net band 25.6 mm²: even with the LC5 stop and the 61807 proof load all through one band, the stress is 33 MPa (limit 138).

The ring clamps the actuator cover to the housing and holds the actuator in the crown. Friction to the crown is 107 N·m against 21.0 N·m (stop + housing reaction, SF 5.1), plus the 1.5 mm pocket key.

### 116 / 117 Flange screws (replace elbow parts 30 and 31)

Purchase. 7 × M3 × 16 DIN 912 + 7 × M3 ISO 7089. Through the ring and the elbow cover into the elbow housing inserts. Engagement 4.5 of 5.7, with the tip 2.2 above the hole floor. Torque **0.2 N·m**, as the elbow. **Do not fit the elbow's own M3 × 12 screws and washers**: the ring sits under these heads.

### 118 / 119 Ring screws

4 × RX-M4x8.1 in the crown (118) + 4 × M4 × 12 ISO 10642 (119), flush in the ring. Torque **1.0 N·m**.

### 120 / 121 Hard stop

Stop pin Ø5 × 14 ISO 8734 (120), pressed 7 mm through ring and boss, with 3 × O-ring 4.5 × 1.5 NBR 70 (121) on its free end. It runs in an 8.6 wide, 6 deep arc slot in cheek A. The O-rings touch the slot ends only at −5° and 140° (`gen.log` sweep: 0.30 mm clear at 0° and 135°).

| Case | Stop torque | Pin bending | Ring + boss bearing | Slot (ASA) |
|---|---|---|---|---|
| Stall at the 10 A limit | 8.23 N·m | 90 MPa | 34 MPa | 6.4 MPa |
| LC5 | 12.35 N·m | 135 MPa | 50 MPa | 9.7 MPa |
| Capacity (slot-limited) | 17.3 N·m | — | — | 13.5 MPa |

**Impact (calc §7).** At 180°/s the joint carries 0.202 J (load inertia 0.025 + reflected rotor 0.016 kg·m²). The O-rings absorb about F·d/3 up to 25% squeeze, the top of Parker's 15–25% static range [A8]. 39% of the stop torque passes through the gearbox, because that is the rotor's share of the inertia. **Firmware rules:**

1. Cut motor current to 0 beyond the soft limits (0° and 135°).
2. Limit the approach speed to ≤ 90°/s within the last few degrees before a soft limit. With the current cut, the stop absorbs 0.061 J, which is safe up to 98.6°/s.
3. With the motor still at the 10 A limit, any impact overloads the gearbox past its 8.23 N·m proof.

### 122 Passive pin

Lathe, 6061-T6. Quantity 1. Mass 16.2 g. E z −20.4 to −2.5.

| E z | Feature |
|---|---|
| −8.5…−2.5 | Spigot Ø16 in the ear bore (4.2 MPa bearing at LC4) |
| −11.5…−8.5 | Flange Ø38, 3 × M3 countersunk on Ø30 at 90/210/330° into the ear inserts |
| −13.6…−11.5 | Shoulder Ø23 (61804 inner-ring abutment, SKF da 22–23.6 [A3]) |
| −20.4…−13.6 | Journal Ø20 j6 for the 61804; 3 × M2.5 tapped 6 deep on Ø15 at 90/210/330° in the end face |
| through | Ø10 bore for the encoder wires |

Bending at the shoulder 2.0 MPa.

### 123 / 124 Pin screws

3 × RX-M3x5.7 in the ear (123) + 3 × M3 × 8 ISO 10642 (124). Torque **0.4 N·m**: the worst screw sees 156 N of the LC4 moment against 793 N preload (SF 5.1).

## Forearm

### 125 Forearm + cheek A

3D print ASA, one piece. Quantity 1. Mass 159 g solid, 155 g print estimate.

- **Cheek A**: plate E z 82.8–90.8 (8 thick), R44 round the axis, flanks tangent to the disc to (30, 80).
  - Boss Ø37.5 × 0.5 clamps the 61807 inner ring (middle of SKF da 37–38 [A4]), then a teardrop to Ø43 inside the cover lip.
  - 6 × Ø3.4 with Ø6.2 × 3.4 counterbores on Ø26 at 36° + 60° (hub screws).
  - 2 × Ø3 × 11 dowel holes at 66° and 246°.
  - Stop slot r 35.5 × 8.6 wide × 6 deep (2.0 floor).
  - Decorative groove r 24–25.2 × 0.6.
- **Clevis root**: R47 cut-out round the cradle. Full clevis width (E z −12.5…90.8) down to s 80, with an open anterior trough from s 30 to 80.
- **Y-yoke neck** s 80–120: the section blends from the full clevis width to 44 × 44 along a cosine curve (zero slope at both ends; lofted every 4 mm). The cheek-side wall tapers 8 → 2.5 by s 100. A 2.5 mm centre web and a 14 mm inner roof chamfer keep every roof bridge under 33 mm.
- **Lattice tube** s 120–226: straight 44 × 44 octagon (chamfer 8), wall 2.5. 4 diamond windows 22 × 22 on each of the four faces, centred at s 133 / 159.7 / 186.3 / 213. The chamfered corners are the longerons, and the X-bars between windows are 3.30 wide. From s 126 the inner roof chamfer equals the others, so the windowed roof bridges 25.9 mm.
- **Wrist block** s 226–234:
  - Ø19.98 (Ø20 h7) × 1.8 spigot;
  - 4 RX-M3x5.7 holes on Ø30 at 45° + 90°;
  - Ø10 wire bore.
- 4 RX-M4x8.1 holes for cheek B at (−15, 52), (−15, 70), (8, 60), (14, 72) (E frame).

Print the posterior face (x −22) on the bed. Stresses (calc §4):

- Neck: ≤ 5.00 MPa von Mises.
- Window sections (corners only, 165 mm²): ≤ 11.90 MPa at s 133 (limit 17.0).
- X-bars: 7.69 MPa posterior / anterior (in layer, limit 17.0) and 3.89 MPa inboard / outboard (vertical, limit 13.5); buckling SF ≥ 3.2.

### 126 / 127 Hub screws and dowels

6 × M3 × 16 DIN 912 (126) into the elbow hub inserts. Engagement 4.5 of 5.7, tip 2.2 above the hole floor. Torque **0.2 N·m**, as the elbow.

Friction alone slips at 6.2 N·m (SF 0.75 at proof, as in the elbow calc), so the two **Ø3 × 16 ISO 8734 dowels** (127) carry the torque: 5 mm in the elbow hub, 11 mm in the ASA. 317 N each, 9.6 MPa bearing in the ASA (SF 2.8 on the across-layer strength).

### 128 Cheek B

3D print ASA. Quantity 1. Mass 43 g solid, 32.5 g print estimate. E z −21 to −12.5, R34, flanks to (27, 80).

- Ø32 slip bore for the 61804 outer ring, with a Ø29 lip at z −13.25. The outer ring floats 0.40 / 0.35 mm axially; the load is a point load on the outer ring, so a slip fit is correct.
- 4 × Ø4.8 holes: 0.4 radial float, so cheek B aligns to the pin before tightening.
- 3 RX-M3x5.7 holes on Ø53 at 0/120/240° for the cover.

Print the lip face on the bed.

### 129–131 Cheek B screws

4 × RX-M4x8.1 in the forearm (129), 4 × M4 × 16 ISO 4762 (130), DIN 9021 washers (131). Torque **1.0 N·m**: friction 1,788 N against the 407 N LC4 bearing force (SF 4.4).

### 132 Passive bearing

Purchase. SKF 61804-2RS1, 20 × 32 × 7, C 4.03 kN, C0 2.32 kN [A3]. Inner ring on the pin with Loctite 641 [A11], outer ring floating in cheek B. LC4: Fr 407 N, s0 5.7 (need 1.0) [A5].

The elbow's 61807 takes the other 407 N plus 94 N of its own at proof, and 114 N axial: s0 6.4 [A4].

### 133 Bearing retainer

3D print ASA. Ø60 / Ø29 × 1 washer on the cover side of the 61804 outer ring, with 3 × Ø3.4 holes, under the cover bosses. Print flat.

## Output encoder

### 134 Encoder bracket

Lathe, 6061-T6. Quantity 1. Mass 10.4 g.

- Boss Ø22 (z −22.5…−20.6) clamps the 61804 inner ring against the pin shoulder.
- Plate Ø40 × 3 (z −25.5…−22.5).
- Ø10 bore.
- 3 × M2.5 countersunk on Ø15 into the pin.
- 4 × M2.5 tapped on Ø34 at 45° + 90° for the PCB.
- 6 × 13 × 1.5 wire groove under the PCB.

### 135–139 Encoder parts

- 3 × M2.5 × 10 ISO 10642 (135, bracket to pin).
- Encoder PCB 30 × 30 × 1.6, shoulder P12 board (136), with the AS5047P (137) facing outboard.
- 4 × M2.5 × 4 DIN 912 (138).
- Magnet Ø6 × 2.5 diametric, ams AS5000-MD6H-2 (139), bonded in the cover boss. Gap to the IC is 1.0 mm (0.5–3.0 allowed) [A9].

The IC is on the stationary pin and the magnet turns with the forearm, so the reading is the true output angle.

### 140–142 Encoder cover

Cover (140): 3D print ASA, Ø50 cup to z −33.5, magnet boss Ø10, 3 bosses Ø7 on Ø53, 7.0 g. 3 × M3 × 12 DIN 912 (142) with heads in Ø6.2 counterbores at z −28.5, into RX-M3x5.7 inserts in cheek B (141), 4.5 mm engaged. Torque 0.4 N·m. Print the end face down.

## Wrist interface

### 143 Wrist inserts

4 × RX-M3x5.7 in the forearm wrist face, on Ø30 at 45° + 90°, with the Ø20 h7 spigot. This is the interface for the future wrist or hand (it needs a Ø20 H8 recess). There is no hand in v0. Fitting the inserts now (1.2 g) means the forearm does not have to be reprinted later.

## Assembly

1. Heat-set all inserts: 4 cap, 4 + 4 in 110 (collar, crown), 3 ear, 4 + 4 in 125 (cheek B, wrist), 3 in 128.
2. Bolt the adapter (101) to the shoulder flange: 6 × M5 at 8.0 N·m, Loctite 243.
3. Fit 104 over the adapter hex, then 6 × M4 + DIN 9021 at 1.0 N·m.
4. Join 104 and 110: dowels into 110 first, then 4 × M4 at 1.0 N·m.
5. Elbow:
   1. Put the elbow actuator in the saddle with the lead port up (actuator turned 36°, port at 256°). Run the leads into the crown channel.
   2. Fit the front ring with the stop pin and O-rings already in it.
   3. Fit 7 × M3 × 16 + washers at 0.2 N·m, then 4 × M4 × 12 into the crown at 1.0 N·m.
6. Bolt the passive pin (122) into the ear: 3 × M3 × 8 at 0.4 N·m. Pass the encoder wires through the pin bore and the ear groove.
7. Press the 2 hub dowels 5 mm into the elbow hub. Slide the forearm (125) on from outboard, so the dowels enter the cheek A holes and the stop pin enters the slot. Fit 6 × M3 × 16 at 0.2 N·m.
8. Fit cheek B (128) over the pin journal and 4 × M4 + washers, finger-tight.
9. Fit the 61804:
   1. Apply Loctite 641 to the pin journal (activator SF 7649 on aluminium) [A11].
   2. Press the 61804 onto the pin and into cheek B, pushing on the **inner ring only**.
   3. Tighten the 4 cheek B screws to 1.0 N·m; the float holes let cheek B centre on the bearing.
10. Fit the retainer (133), the bracket (134, 3 × M2.5), the PCB (4 × M2.5), and the cover with its magnet (3 × M3 at 0.4 N·m).
11. Re-torque the hub-plate M4s after 24 h.

## Open items

| Item | Status |
|---|---|
| Mass 1.327 kg vs 1.18 kg budget | The elbow actuator is 0.499 kg of it. Shoulder SF 7.4 (calc §1). Heaviest printed items: upper halves 177 + 156 g, forearm 155 g. The beam walls are minimum gauge (2.5) and strength-limited, so more windows would not pay off |
| Future hand / wrist | Not built. Its mass will raise the shoulder and elbow gravity torques (calc §1); the LC3 / LC4 load point already assumes it |
| Insert pull-out (M4 ~2,785 N, M3 ~1,400 N) | M4 is scaled from the M3 value by hole area: **pull-test one insert** in a printed ASA coupon |
| Hub plate friction SF 1.82 | Hex key backup at 14.6 MPa (best-case contact). Re-torque after 24 h |
| Stop impact | Firmware rules above. O-ring stiffness to be measured |
| Clevis width | World Y −24 (cover) to 100 (forearm cheek A) |

## References

- [A1] Bambu ASA data sheet (tensile X-Y 37 ± 3, Z 31 ± 4 MPa; E 2,450 / 2,120 MPa; 1.05 g/cm³): https://wiki.bambulab.com/filament-acc/abs-asa-pc/6eaf4c432d1d4014a1975e55a55ed00b.pdf, https://eshop.3dmanufaktura.sk/user/documents/upload/Bambu%20lab/ASA/Bambu_ASA_Technical_Data_Sheet.pdf
- [A3] SKF 61804-2RS1 (C 4.03 kN, C0 2.32 kN, d1 23.85, da 22–23.6): https://www.skf.com/group/products/rolling-bearings/ball-bearings/deep-groove-ball-bearings/productid-61804-2RS1, https://www.coolenbearings.com/skf/ball-bearings/deep-groove/61804-2rs1, https://www.rhia.de/datasheet/en/61804-2rs
- [A4] SKF 61807-2RS1 (C 4.75 kN, C0 3.2 kN, da 37–38): https://www.skf.com/group/products/rolling-bearings/ball-bearings/deep-groove-ball-bearings/productid-61807-2RS1, https://www.coolenbearings.com/skf/ball-bearings/deep-groove/61807-2rs1
- [A5] SKF static safety factor s0 = C0 / P0: https://www.skf.com/group/products/rolling-bearings/principles-of-rolling-bearing-selection/bearing-selection-process/bearing-size/size-selection-based-on-static-load, https://www.skf.com/us/products/rolling-bearings/principles-of-rolling-bearing-selection/bearing-selection-process/bearing-size/size-selection-based-on-static-load
- [A6] Ruthex RX series (RX-M3x5.7 hole Ø4.0; RX-M4x8.1 hole Ø5.6; depth ≥ L + 1): https://www.igo3d.com/mediafiles/Sonstiges/Ruthex/ruthex_Datenblatt_RX-Serie.pdf, https://machinistcalcs.com/guides/heat-set-insert-holes/
- [A7] ISO 8734 dowels: https://www.fasteners.eu/standards/ISO/8734/, https://www.opac.net/en/producto-166-iso-8734
- [A8] Parker O-Ring Handbook ORD 5700 (static squeeze about 15–25%; compression force charts): https://www.pneu-draulics.com/wp-content/uploads/ord-5700.pdf, https://discover.parker.com/Parker-ORing-Handbook-ORD-5700
- [A9] AS5047P (magnet Ø6 × 2.5 diametric, gap 0.5–3 mm, 35–70 mT): https://media.digikey.com/pdf/Data%20Sheets/Austriamicrosystems%20PDFs/AS5047P-TS_EK_AB.pdf, https://www.infineon.com/assets/row/public/documents/24/49/infineon-as5047p-datasheet-en.pdf
- [A10] Loctite 243 (not on thermoplastics): https://datasheets.tdx.henkel.com/LOCTITE-243-en_GL.pdf, https://docs.rs-online.com/22f6/0900766b80076c5f.pdf
- [A11] Loctite 641 (bearing retaining, medium strength, gap ≤ 0.15, activator for slow substrates): https://www.farnell.com/datasheets/306464.pdf, https://loctiteadhesive.com/wp-content/uploads/2025/10/LOCTITE-641.pdf
- [A12] VDI 2230 preload basis: `shoulder/cad/calc.py` (same table used for the shoulder and elbow).
- [A13] DIN 9021 M4 washer 4.3 / 12 × 1.0: https://www.aspenfasteners.com/content/pdf/Metric_DIN_9021_spec.pdf, https://www.aramfix.com/content/files/9021hv0zp/datasheet%20din%209021.pdf
