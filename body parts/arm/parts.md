# Arm, Rev 2 (twin plates, direct-drive elbow)

World frame: origin on the shoulder axis at the shoulder output-flange face, +Y outboard along the shoulder axis, +X forward, +Z up; the arm hangs along −Z and the elbow axis is parallel to Y at Z −298. Arm-plane coordinates (u, v): u = X, v = height above the elbow axis. All dimensions come from `arm/cad/arm_params.py`; the exact solid is `arm/cad/arm.step`; masses are in `arm/cad/mass.txt`; loads, fits and settings are printed by `arm/cad/calc.py` into `arm/cad/calc.txt`; interference, sweep and bed checks are in `arm/cad/gen.log`. Ordering, print settings and assembly: [`arm_bom.md`](arm_bom.md). Elbow decisions and research: [`../elbow/research.md`](../elbow/research.md).

## Summary

- Two DoF: shoulder pitch (existing Ø100 actuator, [`../shoulder/parts.md`](../shoulder/parts.md)) and elbow pitch driven directly by an EaglePower LA8308 KV90 (no gearbox).
- Upper arm: two shaped PETG plates 5 mm thick, 37.5 mm apart (inner faces), joined by 11 spacer sleeves. Each plate is printed in two pieces joined by a glued, screwed half-lap; the inner plate splits at v 120, the outer at v 155, so the link is never cut at one height on both sides.
- Elbow: the motor sits between the plates on four 5 mm standoffs. Its rotor drives a printed hub that passes through the outer plate and carries the forearm outer plate. The forearm inner plate pivots on a printed stub through a 6705 bearing seated in an O-ring, so it takes load only from knocks; the motor bearings set the axis.
- Forearm: two 4 mm PETG truss plates outside the upper plates, 7 spacer sleeves, wrist block with the Ø20 spigot and 4 × M3 for the future hand.
- Stops: rubber-sleeved forearm spacers. Extension at −5° against a 3 mm rubber pad on the heel tab; flexion at 140° against the upper-plate front edge. Software limits −3° to 135°.
- Width 64.5 mm at the elbow (pivot boss Y −7 to forearm outer face Y 57.5; the stub screw head adds 3 mm inboard), 62.5 mm along the forearm. Mass 897 g: upper arm with motor 741 g, forearm 157 g (print estimate).
- Elbow ratings (calc §2): dummy hand 0.15 kg holds at 0.62 N·m, 6.8 A, 6.6 W. Continuous rating 0.70–0.99 N·m depending on the motor thermal resistance (2–4 K/W, to be measured). ODESC `current_lim` 20 A = 1.84 N·m.
- The printed arm limits the shoulder to 10 N·m output (half-lap screws carry 12.1 N·m alone, calc §6); the dummy-hand demand is 4.6 N·m.

## 201 / 202 Upper inner plate (elbow piece, shoulder piece)

3D print, PETG. Y 0 to 5. Outline: R44 shoulder lobe, Bezier waist, R52 elbow lobe and a heel tab between 222° and 240.3° out to r 72. Slots 12 wide at v 62–98 and v 194–232.

- 201 elbow piece (v ≤ 135, half-lap v 105–135 keeps the Y 2.5–5 half): 4 × M4 CSK on Ø40 at 0° + 90° for the motor (heads flush on the inboard face); Ø17 lead hole at r 32, 135° (up and back, never swept by the forearm); encoder pocket 30.6 × 30.6 from the outboard face down to Y 1.5; 4 × M2.5 CSK on Ø34 at 45° for the PCB; 6 × 2 cable groove at 135°; pivot stub on the inboard face (shoulder Ø28.4 at Y −2 to 0, journal Ø24.9 at Y −5.9 to −2, M3 insert hole Ø4.0 × 6.7).
- 202 shoulder piece (v ≥ 105, half-lap keeps the Y 0–2.5 half): Ø39.8 × 1.8 spigot into the shoulder flange pilot; 6 × Ø5.15 for M5 on Ø52 at 30° + 60°; 3 × Ø9 × 0.4 reliefs over the shoulder carrier screw heads on Ø54.
- Both: M3 CSK holes for the spacers and the 4 lap screws (± 10, v 120 ± 9), countersinks on the inboard face.
- Print with the outboard face (Y 5) on the bed: the pocket is a 30.6 bridge (P2S limit about 30), the stub and the spigot face up.

## 203 / 204 Upper outer plate (elbow piece, shoulder piece)

3D print, PETG. Y 47.5 to 52.5, same outline and slots as 201/202. Half-lap at v 155 (203 keeps the Y 47.5–50 half, 204 keeps Y 50–52.5). Ø34 clearance hole for the hub (2 mm radial); 6 × Ø11 hex-key access holes over the shoulder M5 heads; M3 CSK holes (countersinks on the outer face). Print with the outer face up.

## 205 Upper spacer sleeves (11)

3D print, PETG. Ø9 × 42.5 (Y 5 to 47.5), M3 heat-set insert in each end (hole Ø4.0 × 6.7). 8 along the plate edges, inset 7.5, and 3 in the shoulder lobe at (± 36, v 298) and (0, v 258). Print standing.

## 206 Motor standoffs (4)

3D print, PETG. Ø11 / Ø4.5 × 5 (Y 5 to 10), on the motor screws. They keep a 5 mm air gap between the stator base and the PETG (hdt 62 °C). Contact pressure 7.9 MPa at 0.5 N·m: tighten to 0.5 N·m with Loctite 243 and re-check after the thermal test (calc §7).

## 207 Rotor hub

3D print, PETG. Flange Ø42 × 4 on the rotor face (Y 42.5 to 46.5), tube Ø22 to Y 53.5. 4 × M3 CSK on Ø31 at 45° into the rotor (heads outside the tube); Ø3.5 bore over the 2.9 mm shaft stub; 3 × M3 insert holes on Ø14 in the end face. At the 20 A limit the forearm screws bear 7.3 MPa; at the motor's 40 A peak they would reach 14.6 MPa (allowable 15), so keep `current_lim` at 20 A.

## 208 Forearm outer plate

3D print, PETG. Y 53.5 to 57.5. Lobe R26 (solid) with 3 × M3 CSK on Ø14 to the hub; truss rims 7 wide along both Bezier edges, zig-zag diagonals 6 wide between the 7 spacer nodes, bottom bar at v −228. Print with the outer face up.

## 209 Forearm inner plate

3D print, PETG. Y −5 to −1 (truss as 208), pivot boss R25.5 from Y −7. Bore Ø32.6 (0.3 radial float) with an O-ring groove Ø34.25 × 2 at Y −4. Print with the inboard face up.

## 210 Forearm spacer sleeves (7)

3D print, PETG. Ø8 × 54.5 (Y −1 to 53.5), inserts in both ends. Nodes on the rims: back v −60, −110, −160, −205; front v −85, −135, −205. The v −60 and v −85 sleeves carry the stop tubes (217).

## 211 Wrist block

3D print, PETG. u ± 20, v −234 to −216, between the forearm plates. 2 + 2 side inserts for the plates; Ø19.98 × 1.8 spigot and 4 × M3 inserts on Ø30 at 45° on the v −234 face for the future hand. Print spigot up.

## 212 Magnet holder

Resin (Saturn). Plugs into the motor rear-cap centre hole and carries the Ø6 × 2.5 diametric magnet, face at Y 5.25 (1.25 mm from the AS5047P). Concentricity to the cap hole within 0.05 mm; bond with structural epoxy. Same geometry as shoulder part 8.

## 217 / 218 Stops

- 217: silicone tube Ø8 / Ø10 over the v −60 (extension) and v −85 (flexion) sleeves.
- 218: 3 mm rubber pad glued on the heel face of both upper plates. It gives the 3 mm travel that keeps an unpowered fall from horizontal (0.62 J) near 200 N (calc §4).

## 240 Motor

EaglePower LA8308 KV90, Ø92 × 32.5 measured (mounting face Y 10 to rotor face Y 42.5), 336 g, 20 pole pairs, 84.6 mΩ phase, Kt 0.0919 N·m/A. Phase leads exit the rear face at r 32 through the Ø17 hole at 135°. A 10k NTC bonded to a stator coil goes to the ODESC thermistor input. Measure on the motor before printing: the rotor M3 pattern (Ø31 or Ø25) and thread depth, the base M4 thread depth, and the angle of the lead exit relative to the base holes.

## 242 Encoder

Same 30 × 30 AS5047P board as shoulder P12, in the 201 pocket (Y 1.5 to 3.1), 4 × M2.5 × 6 CSK from the inboard face with nuts on the board. The motor angle is the joint angle: absolute over the whole range, no homing.

## 250 / 251 Pivot

6705-2RS (25 × 32 × 4) on the stub, clamped by a printed Ø26 washer and an M3 × 6 screw into the stub insert; outer ring floats 0.3 mm in the 209 bore, centred by an O-ring 31.5 × 1.5 NBR 70. A 50 N side push at the hand puts 249 N on it (calc §7).

## Fasteners

- Spacers and wrist: M3 × 10 CSK into inserts, both ends; heads flush so the forearm plates can pass 1 mm away.
- Laps: 4 × M3 × 10 CSK + nyloc per lap, plus epoxy over the 30 × ~54 overlap.
- Shoulder: 6 × M5 × 12 socket head with ISO 7089 washers, 2 N·m, re-torque after the first week (PETG creep).
- Motor: 4 × M4 × 16 CSK through the plate and standoffs, 0.5 N·m + Loctite 243.
- Hub: 4 × M3 × 10 CSK into the rotor; forearm plate 3 × M3 × 8 CSK into the hub inserts.

## Checks (`gen.log`)

- 146 valid solids; the only interferences are screws threaded into the motor envelope.
- Flexion sweep −5° to 140°: stop sleeves touch only at −5° (heel pad) and 140° (front edge); every other moving part keeps ≥ 0.9 mm.
- All printed parts fit the P2S bed with a 5 mm margin (largest 201.4 × 201.4 mm).
