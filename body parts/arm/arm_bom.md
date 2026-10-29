# VAYN Arm — BOM, Print and Assembly Guide, Rev 2

**Purpose:** print, buy and assemble one arm with the direct-drive elbow without opening the CAD. The shoulder actuator has its own BOM (`shoulder/shoulder-bom.md`).

**Source of truth:** geometry and part list `build_arm()` in `arm/cad/gen_arm.py`, dimensions `arm/cad/arm_params.py`, exact model `arm/cad/arm.step`, loads and settings `arm/cad/calc.txt`, part specification [`parts.md`](parts.md). Print files: `arm/cad/arm_print.zip` (every printed part in print orientation, plus `299_Fit_coupon`).

---

## 0. Summary

| Item | Value |
|---|---|
| Printed parts | 31 pieces of 13 designs, PETG (Bambu PETG HF) |
| Resin parts | 1 (magnet holder 212) |
| Bought parts | motor (in stock), 2 bearings, 48 heat-set inserts, screws, silicone tube, rubber pad, NTC, encoder board, magnet |
| Arm mass | 978 g (print estimate, including the motor) |
| Printer | Bambu P2S; largest part 201.4 × 201.4 mm |

---

## 1. Fit coupon first

Print `299_Fit_coupon` in the same PETG and settings as the plates, then check with the micrometer and pin gauges before printing anything else:

| Feature | Variants | Pick |
|---|---|---|
| Journal for both 19.5 bores (row y 16) | radius clearance 0.15 / 0.25 / 0.35 (Ø19.2 / 19.0 / 18.8) | the one each bearing's inner ring slides on by hand; set `STUB["journal_clear"]` and `HUB["journal_d"]` |
| 6804 seat (row y 50) | +0.15 / +0.25 / +0.35 radial over the measured 31.5 | the one the outer ring drops into; set `PIVOT_BORE_R` |
| Hub-bearing seat (row y 84) | +0.15 / +0.25 / +0.35 radial over the measured 26.5 | the one the outer ring drops into; set `SLEEVE["bore_r"]` |
| Sleeve outside diameter | Ø32.4 / 32.8 / 33.2 | the one that slides into the 203 hole; set `SLEEVE["od_r"]` |
| M2.5 / M3 / M4 / M5 holes | Ø3.2 / Ø3.4 / Ø4.5 / Ø5.15 | screws pass by hand; if not, raise the slicer hole compensation, not the model |
| Sleeve stubs Ø9 / Ø8 | insert holes Ø4.0 × 6.7 | inserts go in square and flush |
| Spigot ring Ø39.8 | — | slides into the shoulder flange pilot without force |

Nothing in this arm is pressed with a hammer. If a fit needs more than hand or vise pressure, change the parameter and reprint.

---

## 2. Print parts (Bambu P2S, PETG HF)

All: 0.4 nozzle, 0.2 layer, 4 walls, 40 % gyroid, top/bottom 5 layers, smooth PEI with glue, dry filament 65 °C 8 h (Bambu TDS).

| Model # | Part | Qty | Face on plate | Est. g |
|---|---|---|---|---|
| 201 | Upper inner plate, elbow piece | 1 | Outboard face (Y 7): pocket bridges 30.6 | reprint |
| 202 | Upper inner plate, shoulder piece | 1 | Outboard face: spigot up | reprint (lap is thicker) |
| 203 | Upper outer plate, elbow piece | 1 | Inner face: countersinks up | reprint, or keep if the sleeve slides in |
| 204 | Upper outer plate, shoulder piece | 1 | Inner face | unchanged, can keep |
| 205 | Upper spacer sleeve Ø9 × 43.2 | 11 | Standing | reprint (longer) |
| 206 | Motor standoff Ø11 × 5 | 4 | Flat | same length, can keep |
| 207 | Rotor hub | 1 | Flange down | reprint |
| 208 | Forearm outer plate | 1 | Inner face: countersinks up | reprint (screw circle is Ø20) |
| 209 | Forearm inner plate | 1 | Outer face (Y −1): boss up | reprint |
| 210 | Forearm spacer sleeve Ø8 × 64.7 | 7 | Standing | reprint (longer) |
| 211 | Wrist block | 1 | Spigot up | reprint (wider gap) |
| 212 | Magnet holder | 1 | Resin (Saturn), standard resin, wash + cure | can keep |
| 213 | Hub bearing sleeve | 1 | Flange down | new |
| 214 | Hub bearing spacer Ø22 × 2.4 | 1 | Flat | new; leave out if the bearing is 7 mm wide |
| 253 | Stub washer Ø22 × 1 | 1 | Flat | reprint |

---

## 3. Bought parts

| Item | Qty | Note |
|---|---|---|
| EaglePower LA8308 KV90 | 1 | in stock |
| Bearing 6804Z, measured Ø19.5 × Ø31.5 × 7 | 1 | pivot. Catalog 6804 is 20 × 32 × 7; use the measured diameters |
| Bearing, measured Ø19.5 × Ø26.5 | 1 | hub, in the sleeve. Width not measured; model assumes 5 mm |
| Heat-set insert M3 × 5.7 (Ø4.0 hole) | 48 | 22 upper sleeves, 14 forearm sleeves, 3 hub, 1 stub, 8 wrist block |
| M3 × 12 countersunk ISO 10642 | 15 | inner plate: 11 spacer ends + 4 lap screws |
| M3 × 10 countersunk ISO 10642 | 40 | outer spacers 11, outer lap 4, rotor 4, forearm sleeves 14, wrist 4, hub 3 |
| M3 × 6 socket head | 1 | stub |
| M3 nyloc nut | 8 | laps |
| M4 × 18 countersunk | 4 | motor, through the 7 mm plate |
| M5 × 14 socket head 12.9 + ISO 7089 washer | 6 + 6 | shoulder flange |
| M2.5 × 6 countersunk + nut | 4 + 4 | encoder board. The ×6 stops inside the plate |
| Silicone tube Ø8 / Ø10 | 120 mm | stop sleeves |
| Rubber sheet 3 mm | 2 × (20 × 5 mm) | heel pads |
| 10k NTC thermistor (B3950) | 1 | stator, to the ODESC thermistor input |
| Meukron AS5047P board, 30 × 30 | 1 | hole diagonals 24 mm and 19 mm |
| Magnet Ø6 × 2.5 NdFeB, diametric | 1 | not axial |
| Structural epoxy | — | laps, magnet holder, NTC |
| Loctite 243 | — | motor screws |

---

## 4. Assembly

1. Heat-set the inserts: both ends of every sleeve (205, 210), the hub end face, the stub, the wrist block sides and face.
2. Glue and screw the two half-laps: sand the faces, epoxy, 4 × M3 CSK + nyloc each (M3 × 12 on the inner plate, M3 × 10 on the outer). Check both plates lie flat and the stub is square to the plate.
3. Encoder: board into the 201 pocket (IC toward the motor), 4 × M2.5 × 6 from the inboard face, nuts on the board. The nuts must sit below the plate face. Route the cable along the groove and out with the motor leads.
4. Motor: bond the magnet in the resin holder and the holder in the rear-cap hole (concentric). Glue the NTC into a stator window. Pass the leads through the Ø17 hole, set the four standoffs, fit 4 × M4 × 18 CSK at 0.5 N·m with Loctite 243. The motor goes on after the encoder. The screw tips and the nuts stay inside the plate, so they no longer meet the magnet.
5. Hub: 4 × M3 × 10 CSK into the rotor through the hub flange. Slide the spacer (214) and the hub bearing onto the journal.
6. Upper link: screw the 11 sleeves to the inner plate. Glue the sleeve (213) into 203, lip outward, and seat the hub bearing against that lip. Lay 203/204 over the hub and sleeves and screw down. Glue the 3 mm heel pads on both plates.
7. Pivot: 6804Z on the stub, Ø22 washer and M3 × 6. The outer ring drops into 209; it is not pressed.
8. Forearm: sleeves (with the two silicone tubes on the v −60 and v −85 sleeves) and the wrist block between 208 and 209, slip 209 over the bearing, fasten 208 to the hub end flange (3 × M3 × 10), then all sleeve and wrist screws. The end flange should stand clear of 203.
9. Shoulder: spigot into the flange pilot, 6 × M5 × 14 with washers through the outer-plate access holes, 2 N·m. Re-torque after the first week.
10. ODESC axis 1 (calc §3): `pole_pairs 20`, `torque_constant 0.0919`, `current_lim 20`, `vel_limit 0.5` turn/s, thermistor limit 70 °C, soft limits −3° / 135°, flexion positive. Shoulder output limited to 10 N·m.
11. Bench: run the thermal-hold job on the locked joint (8 A, 30 min) to measure the motor thermal resistance; update `R_TH` in `calc.py`.
