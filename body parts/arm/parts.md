# Arm, Rev 2 (twin plates, direct-drive elbow)

World frame: origin on the shoulder axis at the shoulder output-flange face, +Y outboard along the shoulder axis, +X forward, +Z up; the arm hangs along −Z and the elbow axis is parallel to Y at Z −298. Arm-plane coordinates (u, v): u = X, v = height above the elbow axis. All dimensions come from `arm/cad/arm_params.py`; the exact solid is `arm/cad/arm.step`; masses are in `arm/cad/mass.txt`; loads, fits and settings are printed by `arm/cad/calc.py` into `arm/cad/calc.txt`; interference, sweep and bed checks are in `arm/cad/gen.log`. Ordering, print settings and assembly: [`arm_bom.md`](arm_bom.md). Elbow decisions and research: [`../elbow/research.md`](../elbow/research.md).

## Summary

- Two DoF: shoulder pitch (existing Ø100 actuator, [`../shoulder/parts.md`](../shoulder/parts.md)) and elbow pitch driven directly by an EaglePower LA8308 KV90 (no gearbox).
- Upper arm: two shaped PETG plates (inner 7 mm, outer 5 mm), facing surfaces 43.2 mm apart, joined by 11 spacer sleeves. Each plate is printed in two pieces joined by a glued, screwed half-lap; the inner plate splits at v 120, the outer at v 155, so the link is never cut at one height on both sides.
- Elbow: the motor sits between the plates on four 5 mm standoffs. Its rotor drives a printed hub. A sleeve in the outer plate holds a 19.5 × 26.5 bearing on the hub journal, and the hub end flange stands 8.5 mm proud of that plate and bolts to the forearm outer plate. The forearm inner plate pivots on a printed stub through a 6804Z in a slip bore. The sleeve and the pivot bore are both slip fits, so the motor bearings still set the axis.
- Forearm: two 4 mm PETG truss plates outside the upper plates, 7 spacer sleeves, wrist block with the Ø20 spigot and 4 × M3 for the future hand.
- Stops: rubber-sleeved forearm spacers. Extension at −5° against a 3 mm rubber pad on the heel tab; flexion at 140° against the upper-plate front edge. Software limits −3° to 135°.
- Width 78.6 mm at the elbow (pivot boss Y −10.85 to forearm outer face Y 67.7; the stub screw head adds 3 mm inboard). Mass 978 g: upper arm with motor 801 g, forearm 178 g (print estimate).
- Elbow ratings (calc §2): dummy hand 0.15 kg holds at 0.64 N·m, 7.0 A, 7.0 W. Continuous rating 0.70–0.99 N·m depending on the motor thermal resistance (2–4 K/W, to be measured). ODESC `current_lim` 20 A = 1.84 N·m.
- The printed arm limits the shoulder to 10 N·m output (half-lap screws carry 14.5 N·m alone, calc §6); the dummy-hand demand is 4.8 N·m.

## 201 / 202 Upper inner plate (elbow piece, shoulder piece)

3D print, PETG. Y 0 to 7. Outline: R44 shoulder lobe, Bezier waist, R52 elbow lobe and a heel tab between 222° and 240.3° out to r 72. Slots 12 wide at v 62–98 and v 194–232.

- 201 elbow piece (v ≤ 135, half-lap v 105–135 keeps the Y 3.5–7 half): 4 × M4 CSK on Ø40 at 0° + 90° for the motor (heads flush on the inboard face); Ø17 lead hole at r 32, 135° (up and back, never swept by the forearm); encoder pocket 30.6 × 30.6 from the outboard face down to Y 2.6; 4 × M2.5 CSK on the Meukron pattern (diagonals 24 mm and 19 mm, not a square); 6 × 2 cable groove at 135°; pivot stub on the inboard face (neck Ø13 at Y −1.6 to 0, shoulder Ø22 at Y −2.05 to −1.6, journal Ø19.2 at Y −9.15 to −2.15, M3 insert hole Ø4.0 × 6.7).
- 202 shoulder piece (v ≥ 105, half-lap keeps the Y 0–3.5 half): Ø39.8 × 1.8 spigot into the shoulder flange pilot; 6 × Ø5.15 for M5 on Ø52 at 30° + 60°; 3 × Ø9 × 0.4 reliefs over the shoulder carrier screw heads on Ø54.
- Both: M3 CSK holes for the spacers and the 4 lap screws (± 10, v 120 ± 9), countersinks on the inboard face. Inner-plate screws are M3 × 12.
- Print with the outboard face (Y 7) on the bed: the pocket is a 30.6 bridge (P2S limit about 30), the stub and the spigot face up.

The encoder board fits the pocket. The screws did not, because the old holes were a square on Ø34. On this Meukron board one diagonal is 24 mm centre to centre and the other is 19 mm. The M2.5 × 6 screws come from the inboard face and stop at Y 6. The nuts sit on the board inside the pocket and stop at Y 6.2, short of the plate face at Y 7, so they cannot meet the magnet at Y 7.25.

## 203 / 204 Upper outer plate (elbow piece, shoulder piece)

3D print, PETG. Y 50.2 to 55.2, same outline and slots as 201/202. Half-lap at v 155 (203 keeps the Y 50.2–52.7 half, 204 keeps Y 52.7–55.2). Ø34.6 hole for the hub-bearing sleeve; 6 × Ø11 hex-key access holes over the shoulder M5 heads; M3 CSK holes (countersinks on the outer face). Print with the outer face up.

204 is the same shape as the previous print. 203 is not: the hole is Ø34.6 and the sleeve (213) is what the bearing sits in. An already-printed 203 can be kept if the Ø32.8 sleeve slides through its hole.

## 205 Upper spacer sleeves (11)

3D print, PETG. Ø9 × 43.2 (Y 7 to 50.2), M3 heat-set insert in each end (hole Ø4.0 × 6.7). 8 along the plate edges, inset 7.5, and 3 in the shoulder lobe at (± 36, v 298) and (0, v 258). Print standing.

## 206 Motor standoffs (4)

3D print, PETG. Ø11 / Ø4.5 × 5 (Y 7 to 12), on the motor screws. They keep a 5 mm air gap between the stator base and the PETG (hdt 62 °C). Contact pressure is in calc §7: tighten to 0.5 N·m with Loctite 243 and re-check after the thermal test.

## 207 Rotor hub

3D print, PETG. Flange Ø42 × 4 on the rotor face (Y 44.5 to 48.5), journal Ø19.2 from Y 48.5 to the end flange, end flange Ø28 × 6 (Y 57.7 to 63.7). 4 × M3 CSK on Ø31 at 45° into the rotor; Ø3.5 bore over the 2.9 mm shaft stub; 3 × M3 insert holes on Ø20 in the end flange. The end flange is what comes out of 203: 8.5 mm past the plate face. The old tube ended 1 mm past the plate, which is why it did not come out.

## 208 Forearm outer plate

3D print, PETG. Y 63.7 to 67.7. Lobe R26 (solid) with 3 × M3 CSK on Ø20 to the hub end flange; truss rims 7 wide along both Bezier edges, zig-zag diagonals 6 wide between the 7 spacer nodes, bottom bar at v −228. Print with the outer face up.

## 209 Forearm inner plate

3D print, PETG. Y −5 to −1 (truss as 208), pivot boss R25.5 from Y −10.85. Bore Ø32.0 (0.25 radial over the measured 31.5) from the boss end to Y −2.05, then a Ø26.4 lip that keeps the outer ring in. No O-ring. Print with the inboard face up.

## 210 Forearm spacer sleeves (7)

3D print, PETG. Ø8 × 64.7 (Y −1 to 63.7), inserts in both ends. Nodes on the rims: back v −60, −110, −160, −205; front v −85, −135, −205. The v −60 and v −85 sleeves carry the stop tubes (217).

## 211 Wrist block

3D print, PETG. u ± 20, v −234 to −216, between the forearm plates. 2 + 2 side inserts for the plates; Ø19.98 × 1.8 spigot and 4 × M3 inserts on Ø30 at 45° on the v −234 face for the future hand. Print spigot up.

## 212 Magnet holder

Resin (Saturn). Plugs into the motor rear-cap centre hole and carries the Ø6 × 2.5 diametric magnet, face at Y 7.25 (1.95 mm from the AS5047P, inside the 0.5–3.0 mm range). Concentricity to the cap hole within 0.05 mm; bond with structural epoxy. Same geometry as shoulder part 8.

## 213 Hub bearing sleeve

3D print, PETG. Flange Ø38 × 1.2 (Y 49.0 to 50.2) against the inboard face of 203, body Ø32.8 through the Ø34.6 hole, out to Y 57.4. Bore Ø26.9 for the measured 26.5 outer ring, with a lip (hole Ø22) in the last 1.2 mm so the bearing seats from the inboard side and cannot fall out. Glue the sleeve into 203 once it is concentric; the slip fit is what keeps this bearing from fighting the motor bearings.

## 214 Hub bearing spacer

3D print, PETG. Ø22 / Ø19.6 × 2.4, on the journal between the rotor flange and a 5 mm bearing. If the bearing is 7 mm wide, leave this ring out. If it is 4 mm, print it 1 mm longer.

## 217 / 218 Stops

- 217: silicone tube Ø8 / Ø10 over the v −60 (extension) and v −85 (flexion) sleeves.
- 218: 3 mm rubber pad glued on the heel face of both upper plates. It gives the 3 mm travel that keeps an unpowered fall from horizontal (0.62 J) near 200 N (calc §4).

## 240 Motor

EaglePower LA8308 KV90, Ø92 × 27.5 flat-to-flat measured (mounting face Y 12 to rotor face Y 39.5), 336 g, 20 pole pairs, 84.6 mΩ phase, Kt 0.0919 N·m/A. Phase leads exit the rear face at r 32 through the Ø17 hole at 135°. A 10k NTC bonded to a stator coil goes to the ODESC thermistor input. The measured stack from the magnet face to the old hub face is 48 mm; that is Y 7.25 to Y 55.25, which is where the old tube ended. The new end flange is at Y 63.7.

## 242 / 245 Encoder

Meukron 30 × 30 AS5047P board in the 201 pocket (Y 2.6 to 4.2), chip toward the motor. 4 × M2.5 × 6 CSK from the inboard face, nuts on the board inside the pocket. Hole centres, from the chip: (±8.49, ±8.49) and (±6.72, ∓6.72). The motor angle is the joint angle: absolute over the whole range, no homing.

## 250 Pivot

6804Z on the stub. Catalog size is 20 × 32 × 7; this bearing measures about 19.5 inner and 31.5 outer, and the model uses those diameters with the catalog 7 mm width. Journal Ø19.2, bore Ø32.0. A printed Ø22 washer and an M3 × 6 screw clamp the inner ring. The outer ring slips in the 209 bore. There is no O-ring.

## 255 Hub bearing

Measured inner 19.5, outer 26.5. Width was not given; the model uses 5 mm and the sleeve accepts 4–7 mm (see 214). It sits in the sleeve, on the Ø19.2 journal. This bearing was left out of Rev 2 on purpose: the Ø34 hole was clearance so a third tight support would not bind the motor bearings. It is in now because the hub has to be located in 203, and the sleeve is the part that can be fitted without pressing the plate onto the motor axis.

## Fasteners

- Spacers and wrist: M3 CSK into inserts, both ends, heads flush. Inner-plate ends are M3 × 12 (the plate is 7 mm). Outer-plate ends, forearm sleeves and the wrist stay M3 × 10.
- Laps: 4 × M3 CSK + nyloc per lap, plus epoxy over the 30 × ~54 overlap. Inner lap M3 × 12, outer lap M3 × 10.
- Shoulder: 6 × M5 × 14 socket head with ISO 7089 washers, 2 N·m, so 6 mm still lands in the 8 mm tap. Re-torque after the first week (PETG creep).
- Motor: 4 × M4 × 18 CSK through the 7 mm plate and the 5 mm standoffs, 0.5 N·m + Loctite 243. Thread in the motor is 6 mm.
- Hub: 4 × M3 × 10 CSK into the rotor; forearm plate 3 × M3 × 10 CSK into the hub inserts.

## Checks (`gen.log`)

- 154 arm solids, all valid. The only overlaps are screws threaded into the motor and the encoder screws in their nuts.
- Flexion sweep −5° to 140°: stop sleeves touch only at −5° (heel pad) and 140° (front edge); every other moving part keeps ≥ 0.9 mm.
- All printed parts fit the P2S bed with a 5 mm margin (largest 201.4 × 201.4 mm).
