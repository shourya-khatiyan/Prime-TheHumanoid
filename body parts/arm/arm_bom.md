# VAYN Arm — BOM, Print and Assembly Guide, Rev 2

**Purpose:** print, buy and assemble one arm with the direct-drive elbow without opening the CAD. The shoulder actuator has its own BOM (`shoulder/shoulder-bom.md`).

**Source of truth:** geometry and part list `build_arm()` in `arm/cad/gen_arm.py`, dimensions `arm/cad/arm_params.py`, exact model `arm/cad/arm.step`, loads and settings `arm/cad/calc.txt`, part specification [`parts.md`](parts.md). Print files: `arm/cad/arm_print.zip` (every printed part in print orientation, plus `299_Fit_coupon`).

---

## 0. Summary

| Item | Value |
|---|---|
| Printed parts | 29 pieces of 11 designs, PETG (Bambu PETG HF), about 466 g |
| Resin parts | 1 (magnet holder 212) |
| Bought parts | motor (in stock), 1 bearing, 1 O-ring, 48 heat-set inserts, screws, silicone tube, rubber pad, NTC, encoder board, magnet |
| Arm mass | 897 g (print estimate) |
| Printer | Bambu P2S; largest part 201.4 × 201.4 mm |

---

## 1. Fit coupon first

Print `299_Fit_coupon` in the same PETG and settings as the plates, then check with the micrometer and pin gauges before printing anything else:

| Feature | Variants | Pick |
|---|---|---|
| 6705 journal (row y 15) | radius −0.05 / −0.10 / −0.15 | the one the bearing inner ring slides on by hand without play; set `STUB["journal_clear"]` in `arm_params.py` |
| 6705 seat with O-ring groove (row y 50) | +0.20 / +0.30 / +0.40 radial float | the one where the bearing floats freely without the O-ring and is centred with it; set `PIVOT_BORE_R` in `arm_params.py` |
| M3 / M4 / M5 / hub holes | Ø3.4 / Ø4.5 / Ø5.15 / Ø26 | screws pass by hand; if not, raise the slicer hole compensation, not the model |
| Sleeve stubs Ø9 / Ø8 | insert holes Ø4.0 × 6.7 | inserts go in square and flush |
| Spigot ring Ø39.8 | — | slides into the shoulder flange pilot without force |

Nothing in this arm is pressed with a hammer. If a fit needs more than hand or vise pressure, change the parameter and reprint.

---

## 2. Print parts (Bambu P2S, PETG HF)

All: 0.4 nozzle, 0.2 layer, 4 walls, 40 % gyroid, top/bottom 5 layers, smooth PEI with glue, dry filament 65 °C 8 h (Bambu TDS).

| Model # | Part | Qty | Face on plate | Est. g |
|---|---|---|---|---|
| 201 | Upper inner plate, elbow piece | 1 | Outboard face (Y 5): pocket bridges 30.6 | 75 |
| 202 | Upper inner plate, shoulder piece | 1 | Outboard face: spigot up | 77 |
| 203 | Upper outer plate, elbow piece | 1 | Inner face: countersinks up | 81 |
| 204 | Upper outer plate, shoulder piece | 1 | Inner face | 64 |
| 205 | Upper spacer sleeve Ø9 × 42.5 | 11 | Standing | 35 |
| 206 | Motor standoff Ø11 × 5 | 4 | Flat | 2 |
| 207 | Rotor hub | 1 | Flange down | 9 |
| 208 | Forearm outer plate | 1 | Inner face: countersinks up | 35 |
| 209 | Forearm inner plate | 1 | Outer face (Y −1): boss up | 33 |
| 210 | Forearm spacer sleeve Ø8 × 54.5 | 7 | Standing | 23 |
| 211 | Wrist block | 1 | Spigot up | 31 |
| 212 | Magnet holder | 1 | Resin (Saturn), standard resin, wash + cure | <1 |
| 253 | Stub washer Ø26 × 1 | 1 | Flat (print with 207) | <1 |

---

## 3. Bought parts

| Item | Qty | Note |
|---|---|---|
| EaglePower LA8308 KV90 | 1 | in stock |
| Bearing 6705-2RS, 25 × 32 × 4 | 1 | pivot; alternative 61805 (25 × 37 × 7) needs a thicker boss |
| O-ring 31.5 × 1.5 NBR 70 | 1 | pivot seat; from an O-ring kit |
| Heat-set insert M3 × 5.7 (Ø4.0 hole) | 48 | 22 upper sleeves, 14 forearm sleeves, 3 hub, 1 stub, 8 wrist block |
| M3 × 10 countersunk ISO 10642 | 52 | sleeves 36, laps 8, rotor 4, wrist 4 |
| M3 × 8 countersunk | 3 | forearm plate → hub |
| M3 × 6 socket head | 1 | stub |
| M3 nyloc nut | 8 | laps |
| M4 × 16 countersunk | 4 | motor |
| M5 × 12 socket head 12.9 + ISO 7089 washer | 6 + 6 | shoulder flange |
| M2.5 × 6 countersunk + nut | 4 + 4 | encoder board |
| Silicone tube Ø8 / Ø10 | 120 mm | stop sleeves |
| Rubber sheet 3 mm | 2 × (20 × 5 mm) | heel pads |
| 10k NTC thermistor (B3950) | 1 | stator, to the ODESC thermistor input |
| AS5047P encoder board (shoulder P12 design) | 1 | |
| Magnet Ø6 × 2.5 NdFeB, diametric | 1 | not axial |
| Structural epoxy | — | laps, magnet holder, NTC |
| Loctite 243 | — | motor screws |

---

## 4. Assembly

1. Heat-set the inserts: both ends of every sleeve (205, 210), the hub end face, the stub, the wrist block sides and face.
2. Glue and screw the two half-laps: sand the faces, epoxy, 4 × M3 × 10 CSK + nyloc each. Check both plates lie flat and the stub is square to the plate.
3. Encoder: board into the 201 pocket (IC up), 4 × M2.5 from the inboard face. Route the cable along the groove and out with the motor leads.
4. Motor: bond the magnet in the resin holder and the holder in the rear-cap hole (concentric). Glue the NTC into a stator window. Pass the leads through the Ø17 hole, set the four standoffs, fit 4 × M4 × 16 CSK at 0.5 N·m with Loctite 243.
5. Hub: 4 × M3 × 10 CSK into the rotor through the hub flange.
6. Upper link: screw the 11 sleeves to the inner plate, lay the outer plate over the hub and sleeves, screw down. Glue the 3 mm heel pads on both plates.
7. Pivot: bearing on the stub, Ø26 washer and M3 × 6. O-ring into the 209 groove.
8. Forearm: sleeves (with the two silicone tubes on the v −60 and v −85 sleeves) and the wrist block between 208 and 209, press 209 over the bearing, fasten 208 to the hub (3 × M3 × 8), then all sleeve and wrist screws.
9. Shoulder: spigot into the flange pilot, 6 × M5 × 12 with washers through the outer-plate access holes, 2 N·m. Re-torque after the first week.
10. ODESC axis 1 (calc §3): `pole_pairs 20`, `torque_constant 0.0919`, `current_lim 20`, `vel_limit 0.5` turn/s, thermistor limit 70 °C, soft limits −3° / 135°, flexion positive. Shoulder output limited to 10 N·m.
11. Bench: run the thermal-hold job on the locked joint (8 A, 30 min) to measure the motor thermal resistance; update `R_TH` in `calc.py`.
