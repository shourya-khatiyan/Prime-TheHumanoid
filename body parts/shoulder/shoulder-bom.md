# VAYN Shoulder Actuator — BOM and Sourcing Guide, Rev 1.4

**Purpose:** buy or make every part of one actuator without needing to read the CAD. For each item it lists quantity, material and grade equivalents, raw-stock size, process, heat treatment, critical features and approved alternates.

**Source of truth:**
- Geometry and part list: `build()` in `shoulder/cad/gen_actuator_3mf.py`. The exact model is `shoulder/cad/actuator.step`.
- Loads, fits and torques: `shoulder/cad/calc.py`, with results in `shoulder/cad/calc.txt`.
- Part specification: `shoulder/parts.md`.

Part IDs (`M..` = make, `P..` = purchase) are used only in this doc. The "Model #" column is the object number in the STEP/3MF.

**Milling pack A** (geometry still Rev 1.4, materials revised 30 October 2026) is the quotation set in `shoulder/cad/milling/`. It drops the rear plate (3D-printed this build) and uses two alloys: **6082-T6** for the housing family and **20MnCr5** for every steel part. Teeth are carburized. The three carriers that have no teeth stay annealed. 6061-T6 may replace 6082, and 16MnCr5 may replace 20MnCr5, but the order still uses one aluminium and one steel. 7075, EN19, EN24, nitriding and anodize are not in this pack. The full rules are in the quotation PDF there.

---

## 0. Summary

| Item | Value |
|---|---|
| Make parts | 19 unique (40 pieces, including 14 thrust washers and 2 motor shims) |
| Purchased parts | 26 lines (≈ 85 pieces, not counting spares) |
| Envelope | Plain Ø100 × 100.5 cylinder |
| Actuator mass | ≈ 2.74 kg: ≈ 2.41 kg modelled parts plus the 336 g motor (6082-T6 at 2.70 g/cm³) |
| Heaviest parts | Housing 342 g, cartridge 351 g, carrier-2 front 314 g, carrier-2 rear 232 g, ring-1 191 g |
| Longest-lead items (order first) | LA8308 motor, 61813/C3 bearings, SSB-0335 wave spring, one carburizing batch |
| Must-measure before machining | LA8308 is measured (Ø92.0 × 32.5 mounting face to hub face, front stub Ø2.9 × 8.9, rear cap Ø17.4 turning with the rotor, M4 holes > 6 deep, flexible leads in a 13 mm bundle). Still open: diameter and depth of the plain hole in the rear cap |

**Rev 1.4 changes (motor fit after the first build; all in the model and the calc):**
1. **The lip moves from the housing to the rear plate.** The Rev 1.3 rear lip was Ø88 and the front was closed by the partition, so the Ø92 motor could not enter. The housing bore (Ø94.5) is now open at the rear, and the plate becomes a Ø94.5 k6 plug with a Ø100 × 2 seat rim. Eight radial M3 × 8 CSK screws go through the 2.75 mm wall into the plug, with the countersinks 0.1 forward of the threads so tightening draws the housing onto the rim. That gives 258 N per screw at the proof case, shear SF 12.5 (calc §6). The body stays a plain Ø100 cylinder, and the plate dowels are deleted.
2. **Measured motor height (32.5, not the catalogue 28.5) and the 8.9 mm front stub.** The gearbox moves forward 5.0 mm, the partition becomes 2.5 thick, sun-1 gets a Ø3.5 × 10.5 stub bore, and carrier-1 front gets a Ø19 × 1.2 tip recess. Every axial gap is 1.5 at the nominal shim, and the labyrinth opens to Ø41.0 (0.5 radial).
3. **Motor shim pack (M19)**, 0.5–1.5, nominal 1.0. It sets the motor and sun-1 axial position without touching the gearbox (calc §9).
4. **Encoder centring.** The rotating Ø17.4 cap gets a Ø19.5 relief. The magnet holder pins into the cap's centre hole, and the PCB holes tighten to Ø2.7. Budget 0.22 RSS / 0.55 worst case against 0.5 allowed (calc §9).
5. **Phase leads** (flexible, 13 mm bundle) exit through a 15 mm slot at 180° (r 25–39) and bend into a 5 mm rear groove to the rim.

**Rev 1.3 review changes:**
1. **Homing hall sensor: DRV5032FB → DRV5033FAQDBZR.**
   - The DRV5032FB samples at **5 Hz** [S7], which is once every 200 ms.
   - The magnet (r 36.8 mm) at the 72 rpm output speed moves at 2π × 36.8 × 1.2 ≈ 277 mm/s. With a ≈ 4 mm trigger window it is inside the window for ≈ 14 ms, so the sensor catches it on fewer than 1 in 10 passes.
   - The DRV5033 has **20–30 kHz bandwidth**, the same SOT-23 package, BOP ±3.5 mT (max 6.8 mT) and runs on 2.5–38 V [S8][S9].
   - The magnet gives 97 mT at 2 mm (calc §7), so there is a large margin.
   - It has an open-drain output, so fit a 10 kΩ pull-up to 3.3 V.
2. **Output bearings must be C3 clearance.** With the ISO 492 Normal bore tolerance for 50–80 mm (0/−15 µm), the j5 inner-ring fit plus a 5 K ring gradient removes ≈ 21.1 µm of radial clearance. A Normal-clearance bearing would then be at −13.1 µm (preloaded); a C3 bearing keeps +1.9 µm (calc §5).
3. **Planet pins are R7 press fits and cannot walk.** P7 on an h6 pin can be zero interference. The stage-2 pins now sit on a 1.0 mm shoulder in carrier-2 rear, with a Ø3 hole under each pin for venting and punch-out. Without the shoulder, a loose pin could slide rearward into carrier-1, which turns at a different speed.
4. **Ring-1 dowels are Ø3 × 8, pressed into ring-1 and sliding in radial slots in the housing.** Ø4 dowels pressed into both the steel ring and the aluminium housing would bind, because the two expand by different amounts.

---

## 1. Make parts

Stock sizes below include ≈ 5 mm on the diameter and ≈ 5 mm on the length for facing and parting. Add chucking length if the shop cannot bar-feed.

| ID | Model # | Part | Qty | Material (delivery condition) | Finished size (mm) | Raw stock (each) | Process | Heat treatment / finish | Critical features | Mass (g) |
|---|---|---|---|---|---|---|---|---|---|---|
| M01 | 01 | Encoder lid | 1 | 6082-T6 | Ø59.8 × 2 | 5 mm plate offcut (shared with the cover) | CNC mill | None | 4 × M2 CSK, cable slot | 14.2 |
| M02 | 06 | Magnet holder | 1 | 6082-T6 (**must be non-magnetic** [S10]; 6082 is an Al-Si-Mg alloy, Fe ≤ 0.50% [S18]) | Ø10 × 4.75 + pin Ø2.8 × 2 | Ø12 bar | Lathe | None | Magnet pocket Ø6 × 2.5; **pin turned to the measured cap hole, 0–0.02 clearance**; pocket concentric to pin ≤ 0.03 TIR | 0.85 |
| M03 | 08 | Rear mount plate (plug) | 1 | 3D print for milling pack A. Later metal plate is 6082-T6, same alloy as the housing | Rim Ø100 × 2 + plug Ø94.5 × 8 | not in the milling order | 3D print this build | none this build | **Not in `cad/milling/`.** Housing is still cut for the future plug: Ø94.5 k6, 8 × M3 radial. Later metal plate keeps the Rev 1.4 feature list | 125 |
| M04 | 15 | Housing (one-piece) | 1 | 6082-T6 round bar. 6061-T6 is allowed if 6082 is not in stock | Ø100 × 87 | Ø105 × 92 | CNC lathe + 4th-axis or 3-axis mill | None. Do not anodize | **Bore Ø94.5 open through the rear face, rear 8 mm H7** (plate plug); 8 × Ø3.2 radial + 90° CSK at Z 6.1 (**0.1 forward of the plug threads**); rear-face notches 4 × 1 at 0° and 15 × 3 at 180°; partition 2.5 thick at Z 45–47.5; ring-1 bore Ø85 **K6**; cartridge bore Ø89 **G7**; labyrinth Ø41.0 **H8**; 12 × cooling slots 3 × 20; 8 × M3 front (6 engagement); 2 × ring-1 dowel slots in the partition face, radial, open to the Ø85 bore, width 3.02–3.04 (dowel slides), 1.5 deep | 342 |
| M05 | 16 | Ring-1, 90T m0.8 internal | 1 | 20MnCr5, annealed. Same heat as every other steel part | Ø85 h5 × 15.2 | Ø90 × 20 | Turn, then **wire-EDM teeth while soft** | Carburize the teeth only, CHD **0.12–0.18**, 58–62 HRC. Mask the OD. **No tooth grind.** Allow 0.03–0.05 mm growth. Finish Ø85 h5 after heat treatment | Teeth: Mi over Ø1.2 pins **70.813 +0.015/0**; 2 × Ø3 H7 dowel holes, 7 deep from the rear face, on PCD 79.5 | 191 |
| M06 | 18 | Sun-1 18T m0.8 flanged pinion | 1 | 20MnCr5, annealed (16MnCr5 allowed) | Flange Ø40 × 3, teeth Ø16 × 10.4, total 18.2 | Ø45 × 25 | Turn, hob or shape, CSK holes | Carburize CHD **0.12–0.18** @ 550 HV, 58–62 HRC surface, core 30–40 HRC, temper. Grade 7–8 is accepted. Do not grind the teeth | W3 **6.082 −0.015/0**; 4 × M3 CSK on PCD 31 **and** 4 × M3 CSK on PCD 25 at 45° (fits either published rotor pattern); **Ø3.5 × 10.5 bore for the motor's 8.9 shaft stub**, Ø18 × 0.5 hub relief | 42 |
| M07 | 21 | Carrier-1 rear plate + posts | 1 | 20MnCr5, annealed, same heat | Ø60 × 14 | Ø105 bar, shared with the other steel parts | CNC | Leave annealed. Do not carburize | 3 × Ø8 **R7** pin holes on PCD 43.2; posts tapped M3 | 76 |
| M08 | 22 | Carrier-1 front plate + sun-2 18T m1 | 1 | 20MnCr5, same heat | Ø60 plate + sun Ø20 × 10, total 24 | Ø65 × 30 | Turn, hob, drill | Carburize the sun only, CHD **0.15–0.20**, 58–62 HRC. **Mask the plate and the pin holes.** Grade 7–8 is accepted. Do not grind the teeth | W3 **7.609 −0.015/0**; 3 × Ø8 **R7** holes; 3 × M3 CSK; Ø19 × 1.2 recess in the rear face (1.5 axial clearance over the sun-1 tips) | 92 |
| M09 | 24.1–3 | Planet-1 36T m0.8 | 3 | 20MnCr5, same heat | Ø30.4 × 10, bore Ø12 | Ø35 bar; hob a stack of 4 blanks (3 + 1 spare) | Turn blanks, hob as a stack, part off | Carburize CHD 0.12–0.18, 58–62 HRC; grind the bore after hardening. Do not grind the teeth. Grade 7–8 is accepted | Bore **Ø12 N6**, roundness IT5/2, Ra ≤ 0.8 [S5]; W5 **11.008 −0.015/0** | 41.6 each |
| M10 | 32 | Carrier-2 rear half (hub + posts) | 1 | 20MnCr5, annealed, same heat | Hub Ø65 × 10 + 3 posts; envelope Ø67 × 21 | Ø105 bar, shared | CNC | Leave annealed. Do not carburize | Hub Ø65 **j5** (inner-ring seat); 3 × Ø8 **R7** pin holes on PCD 45, 6 deep from the front, ending on a **1.0 mm shoulder** with a Ø3 through-hole into the rear groove (vent and punch-out); rear lightening groove Ø42–Ø59 × 3.0 deep; posts tapped M4; post faces are the inner-ring shoulders | 232 |
| M11 | 33 | Bearing cartridge + ring-2 72T m1 | 1 | 20MnCr5, annealed, same heat | Flange Ø100 × 7.5, spigot Ø89, total 31.5 | Ø105 × 37 | Turn, wire-EDM ring-2 teeth while soft, drill/tap | Carburize the teeth only, CHD **0.15–0.20**, 58–62 HRC. **Tap the 8 × M2.5 first and mask them.** Mask Ø89 and the Ø85 bore. No tooth grind. Finish Ø89 and Ø85 after heat treatment | Spigot Ø89 **h6**; bearing bore Ø85 **selective**: measure both 61813 ODs and machine +3/+10 µm clearance (rear ring must slide under the spring); ring-2 Mi over Ø1.5 pins **70.499 +0.015/0**; 8 × M3 c'bore; 8 × M2.5 tapped; 2 × Ø4 dowel | 351 |
| M12 | 36.1–3 | Planet-2 27T m1 | 3 | 20MnCr5, same heat | Ø29 × 10, bore Ø12 | Ø35 bar; stack of 4 | As M09 | Carburize CHD 0.15–0.20, 58–62 HRC; grind the bore. Do not grind the teeth. Grade 7–8 is accepted | Bore Ø12 N6; W4 **10.687 −0.015/0** | 35.2 each |
| M13 | 42 | Carrier-2 front half + output flange | 1 | 20MnCr5, annealed, same heat | Flange Ø78, hub Ø65, total 14 | Ø105 bar, shared | CNC lathe + mill | Leave annealed. Do not carburize | Hub Ø65 **j5**; **6 × M5 tapped in this steel**, 8 deep as modelled (spec asks 10; confirm against arm screw length), PCD 52 (arm); pilot Ø40 H7 × 2; 3 × M4 c'bore; 3 × Ø8 **R7** pin holes, blind 6.3 deep (0.3 pin end clearance); Ø3 radial magnet pocket in rim; runout ≤ 0.02 TIR | 314 |
| M14 | 45 | Front cover / bearing retainer | 1 | 6082-T6, same plate as M01 | Ø100 / Ø80 × 3 | 5 mm plate, 105 × 105 | CNC | None | 8 × M2.5 CSK; hall sensor pocket + wire slot; lip contacts the front outer ring only | 22 |
| M15 | 26.1–3, 38.1–3 | Planet pins (needle raceways) | 3 + 3 | 52100 / EN31 / 100Cr6 / SUJ2 | Pin-1 Ø8 × 17; pin-2 Ø8 × 23 | Ø8 h6 ground, hardened shaft, 200 mm | Cut, chamfer, re-check | Through-hardened **58–64 HRC**, **ground h6, Ra ≤ 0.2 µm** [S5][S6] | Press fit into R7 (4–28 µm interference). Pin-2: grind a 0.2 mm vent flat on the front 6 mm only, outside the needle track, for the blind hole in M13. Do **not** use g6 linear shaft or ISO 8734 m6 dowels without checking the needle clearance | 6.6 / 9.0 each |

**Custom thin parts** (laser-cut or wire-cut from 0.3 mm hardened strip, or buy the nearest standard):

| ID | Model # | Part | Qty | Size (mm) | Material | Notes |
|---|---|---|---|---|---|---|
| M16 | 20 | Carrier-1 rear thrust washer | 1 | Ø48 / Ø42 × 0.3 | Hardened spring steel C75S (1.1248) or 52100 strip, ≥ 45 HRC, flat ≤ 0.02 | Runs between the stationary partition and carrier-1 |
| M17 | 30 | Carrier-1 front thrust washer | 1 | Ø40 / Ø24 × 0.3 | As M16 | Runs between carrier-1 and carrier-2 |
| M18 | 27, 28, 39, 40 | Planet thrust washers | 12 | Ø14 / Ø8.2 × 0.3 | As M16 | Standard candidate: **DIN 988 8 × 14 × 0.3** shim ring. Its ID is 8 D12 (8.04–8.19), which must run free on the Ø8 h6 pin, so check one before ordering |
| M19 | 48 | Motor shim pack | 2 nominal, plus a 0.25 / 0.5 set | Ø50 / Ø19.5 × 0.5 (and × 0.25), 4 × Ø4.5 on PCD 40 at 45° | Stainless or spring-steel shim stock, flat ≤ 0.02 | Between plate and motor. Pack = 1.0 + (33.5 − measured plate-front-face to hub-face with 1.0 fitted), 0.5–1.5 (calc §9) |

---

## 2. Purchased parts

| ID | Model # | Part | Qty (+spare) | Exact spec | Approved / alternate | Why this part | Notes |
|---|---|---|---|---|---|---|---|
| P01 | 12–14 | BLDC motor | 1 | EaglePower **LA8308 KV90**, measured Ø92.0 × 32.5 (mounting face to hub face; catalogue says 28.5), 336 g | — | Fixed by requirements | Front stub Ø2.9 × 8.9, rear cap Ø17.4 turns with the rotor (plain centre hole), M4 holes > 6 deep, flexible leads out of the rear face at r 32 (13 mm bundle). **Still measure:** cap hole diameter and depth |
| P02 | 31 | Rear output bearing | 1 (+1) | **61813-2Z/C3**, 65 × 85 × 10, metal shields | SKF 61813-2Z/C3; NSK/NTN 6813ZZ C3 (confirm C3 on the box) | Thin section, so it fits the Ø100 envelope; shields keep grease in | **C3 required** (Section 0). The spare lets you select the best OD match for the cartridge bore (M11). C 11.9 kN, C0 11.5 kN, 0.13 kg [S2] |
| P03 | 41 | Front output bearing (also the output seal) | 1 (+1) | **61813-2RS1/C3**, 65 × 85 × 10, contact seals | SKF 61813-2RS1/C3; NSK 6813DDU C3, NTN 6813LLU C3 | The contact seal is the gearbox front seal | C 11.9 kN, C0 9.65 kN (use the lower SKF value), d1 ≈ 71.4, D2 ≈ 80.3, 0.131 kg [S1][S2] |
| P04 | 25, 37 | Planet needle bearings | 6 (+2) | **HK0810** drawn cup, Fw 8 × D 12 × C 10, open ends | INA HK0810-B; SKF HK 0810 | Highest capacity for the smallest planet bore | INA Cr 3.80 / C0r 3.95 kN; SKF lists C 3.69 kN, so design to 3.69 [S5][S6]. Press into Ø12 N6 with a stepped mandrel on the stamped end |
| P05 | 29 | Bearing preload wave spring | 1 (+1) | **Smalley SSB-0335**, carbon steel: bore 85, clears 71.38, 231.4 N at 2.77 work height, free 5.59, t 0.76, wall 5.92, 83 N/mm | Lispring **LB-0335** (stated drop-in alternate); stainless option SSB-0335-S17 | Keeps both 61813s preloaded at ≈ 206–252 N across tolerances and −40 to +60 K (calc §4) | [S3][S4]. Acts on the rear (floating) outer ring only |
| P06 | 17 | Dowel pin, ring-1 to housing | 2 (+2) | ISO 8734 Ø3 × 8, hardened, m6 | Any ISO 8734 / DIN 6325 | Stops ring-1 rotating | Pressed into ring-1, slides in the housing slot (16 MPa shear, calc §6) |
| P07 | 35 | Dowel pin, cartridge to housing | 2 (+2) | ISO 8734 Ø4 × 8 | Same | Back-up anti-rotation (friction carries the load) | — |
| P09 | 07 | Motor encoder magnet | 1 (+1) | Ø6 × 2.5 NdFeB, **diametrically** magnetised | Bomatec **AS5000-MD6H-2** (ams kit magnet) [S10] | Size required by the AS5047P | Gap to IC 1.25 at the nominal shim, 0.75–1.75 across the shim range (0.5–3.0 allowed); centred ≤ 0.5 mm [S10], budget 0.22 RSS (calc §9) |
| P10 | 44 | Homing magnet | 1 (+2) | Ø3 × 2 NdFeB **N52**, axially magnetised | Any N52 disc | Gives 97–201 mT at 1.2–2.0 mm (calc §7) | Glue radially into the flange rim (M13) with the pole facing outward |
| P11 | 04 | Motor encoder IC | 1 (+1) | **AS5047P-ATSM** (TSSOP-14) | ams-OSRAM / distributor stock | 14-bit absolute angle; needed for FOC | Field 35–70 mT at the die [S11] |
| P12 | 03 | Encoder PCB | 1 (+2) | 30 × 30 × 1.6 FR4, 2-layer, 4 × Ø2.7 holes (M2.5 fine clearance, centres ±0.1) on PCD 34 | Any PCB fab | Carries the AS5047P on the motor axis | Shielded SPI cable out through the plate groove |
| P13 | 46 | Homing hall sensor | 1 (+2) | **TI DRV5033FAQDBZR** (SOT-23, omnipolar, 30 kHz, open-drain) | DRV5033AJ (less sensitive, also OK) | **Replaces DRV5032FB (5 Hz, too slow)**, see Section 0 [S7][S8][S9] | 10 kΩ pull-up to 3.3 V; 3-wire lead |
| P14 | — | Winding thermistor | 1 (+1) | 10 kΩ NTC, β ≈ 3435–3950, glass bead or epoxy | Any | Feeds the ODrive motor-thermistor input [spec 6.5] | Bond to the end winding with thermal epoxy |
| P15 | — | Motor controller (system item) | 1 | ODrive / ODESC class, ≥ 20 A phase current | — | Required by the design's current limits [spec 12] | Settings: `torque_constant 0.0919`, `current_lim ≤ 20 A` |

### 2.1 Fasteners (all steel, grade 12.9 unless noted; black oxide)

| ID | Model # | Fastener | Standard | Qty (+spare) | Joint | Torque (N·m) | Threadlocker |
|---|---|---|---|---|---|---|---|
| F01 | 02 | M2 × 4 countersunk | ISO 7046 / ISO 14581 (grade 8.8 or A2 is fine) | 4 (+4) | Lid to plate | 0.3 | None |
| F02 | 05 | M2.5 × 5 pan | ISO 7045 / ISO 14583 | 4 (+4) | PCB to plate bosses | 0.4 | None |
| F03 | 09 | M3 × 8 countersunk | ISO 10642 12.9 | 8 (+4) | Housing wall to plate plug, radial, heads flush with Ø100 | **1.2** (calc §6: 258 N shear each at proof, SF 12.5; strip SF 2.9 in 6082-T6) | Loctite 243 |
| F04 | 11 | M4 × 10 countersunk | ISO 10642 (10.9 standard) | 4 (+2) | Stator to plate through the shim pack (engagement 6.0 − shim = 4.5–5.5; motor holes ≥ 6 deep) | Per motor maker; ≤ 2.0 into an aluminium base (strip SF ≥ 2.9, calc §9) | Loctite 243 |
| F05 | 19 | M3 × 5 countersunk | ISO 10642 | 4 (+4) | Sun-1 to rotor face (use the PCD that matches the rotor) | **0.8** (calc §6: slip SF 6.4 on PCD 25; only ≈ 2 mm thread in the rotor) | Loctite 243 |
| F06 | 23 | M3 × 10 countersunk | ISO 10642 | 3 (+2) | Carrier-1 front plate to posts | 1.2 | Loctite 243 |
| F07 | 34 | M3 × 10 socket head cap | ISO 4762 12.9 | 8 (+4) | Cartridge flange to housing | **1.2** (slip SF 3.4) | Loctite 243 |
| F08 | 43 | M4 × 16 socket head cap | ISO 4762 12.9 | 3 (+2) | Carrier-2 halves | **4.0** (slip SF 1.4: torque exactly, use a torque driver) | Loctite 243 |
| F09 | 47 | M2.5 × 6 countersunk | ISO 7046 / ISO 14581 | 8 (+4) | Cover to cartridge | 0.8 | Loctite 222 |
| F10 | — | M4 wire thread insert, 1.5D | Helicoil / ISO 13050 type | 6 (+4) | Torso bracket threads in the later 6082-T6 plate | — | — |
| F11 | — | Torso bracket screws M4 | ISO 4762 12.9 | 6 | Torso to rear plate (supplied with torso) | **3.0** (slip SF 3.1) | Loctite 243 |
| F12 | — | Arm screws M5 | ISO 4762 10.9 or 12.9 | 6 | Arm to output flange (supplied with arm) | **8.0** (slip SF 4.6) | Loctite 243 |

The torques above are calculated for 12.9 screws at μ ≈ 0.12 (VDI 2230 basis in `shoulder/cad/calc.py`). The F01, F02, F04 and F09 values are practical limits for small screws in light joints, not calculated values.

### 2.2 Consumables

| Item | Spec | Qty per actuator | Where |
|---|---|---|---|
| Gear grease | NLGI-2, EP, lithium-complex (e.g. Mobilux EP 2, Shell Gadus S2 V220 2) | ≈ 5 g | Gear meshes, planet needles, thrust washers. **None on the encoder magnet or PCB** |
| Threadlocker, medium | Loctite 243 | ≈ 0.5 ml | F03–F08, F11, F12 |
| Threadlocker, low strength | Loctite 222 | few drops | F09 (small screws) |
| Magnet adhesive | Structural epoxy (e.g. Loctite EA 9466) | few drops | P09 in M02; P10 in M13 |
| Thermal epoxy | Thermally conductive epoxy | few drops | P14 on the winding |

---

## 3. Materials: exact use case of each

| Material | Grade equivalents (EN / DIN / AISI / IS / JIS) | Used for | Why this material here | Delivery condition and final state | Buy with |
|---|---|---|---|---|---|
| **6082-T6 aluminium** | EN AW-6082 / AlSi1MgMn / HE30 / IS 64430. Accepted substitute: **6061-T6**, one alloy only | Housing (M04), front cover (M14), encoder lid (M01), magnet holder (M02). Rear plate (M03) is printed for milling pack A; a later metal plate is this same alloy | One aluminium for every machined aluminium part. The thinnest housing wall sees 1.4–3.7 MPa (calc §7). The highest aluminium stress is the plate-screw bearing, 69 MPa, against Rp0.2 260 MPa for 6082-T6 bar from 20 to 150 mm [S17]. Thread strip in the housing is SF 3.3, and in the plate plug SF 2.9 (calc §6). 6082 is non-magnetic, which the magnet holder requires [S10][S18] | T6 bar or plate. No anodize on this order | Grade mark from the stockist. A mill certificate is not required for this first article |
| **20MnCr5 case-hardening steel** | 20MnCr5 / 1.7147 / ≈ SAE 5120. Accepted substitute: **16MnCr5** / 1.7131, one steel only [S12][S13] | Every milled steel part. Teeth: sun-1 (M06), carrier-1 front sun (M08), planets (M09, M12), ring-1 (M05), ring-2 (M11). Same bar, left annealed: carrier-1 rear (M07), carrier-2 halves (M10, M13) | Stage-2 sun contact stress is σH ≈ 1350 MPa at 30 N·m. Case-hardened steel is rated σHlim 1500 MPa [S19]. The rings see about half of that and use the same carburized steel, so there is no second heat treatment. The carriers have no tooth contact. They stay annealed so the bearing seats and pin holes do not distort, and the M5 arm threads are cut in this steel | Buy annealed, one heat. Carburize only the teeth, 58–62 HRC, core 30–40 HRC. Do not carburize M07, M10 or M13 | Grade mark from the stockist, plus a heat-treat report with case depth on one witness coupon of the same bar |
| **52100 / EN31 bearing steel** | 100Cr6 / 1.3505 / AISI 52100 / IS 103Cr2 / SUJ2 [S12][S13] | Planet pins (M15), and the dowels' material class | The pins are the needle raceways and need ≥ 58 HRC and Ra ≤ 0.2 [S5] | Through-hardened 58–64 HRC, ground h6 | Hardness and roughness report |
| **Hardened spring steel strip** | C75S / 1.1248 (DIN 988 standard material) | Thrust washers (M16–M18) | Thin, hard, flat wear faces against rotating parts | 0.3 mm hardened and tempered strip | — |
| **Spring steel (bought in)** | Smalley carbon steel (SAE 1070–1090 class) | Wave spring (P05) | Catalogue part | — | — |
| **NdFeB** | N35–N52 | Encoder magnet (P09), homing magnet N52 (P10) | Field strength. Keep below ≈ 80 °C (standard NdFeB grade limit) | Ni-Cu-Ni coated | Grade and magnetisation direction on the order |

---

## 4. Consolidated raw-stock order (per actuator; double it for a spare set)

| Material | Stock to buy | Covers |
|---|---|---|
| 6082-T6 round bar (6061-T6 if 6082 is not in stock) | **Ø105 × 100** | Housing (M04) only. The rear plate is not milled |
| 6082-T6 plate, same alloy as the bar | **5 mm**, 110 × 110 | Cover (M14) and encoder lid (M01), faced to thickness |
| 6082-T6 round, same alloy | **Ø12 × 40** | Magnet holder (M02) |
| 20MnCr5 round, annealed, one heat (16MnCr5 allowed) | **Ø105 × 160** | Ring-1, cartridge, carrier-1 rear, both carrier-2 halves (M05, M11, M07, M10, M13) |
| 20MnCr5 round, annealed, the same heat | **Ø65 × 35**, **Ø45 × 30**, **Ø35 × 120** (six planets, no spare blank) | M08, M06, M09, M12 |
| 52100 Ø8 h6 hardened ground shaft | **200 mm** | 6 pins (M15) |
| Hardened strip 0.3 mm | 100 × 100 sheet | M16–M18 (if not buying DIN 988) |

Buy all 20MnCr5 parts from **one heat**. They then share the carburizing batch, and one witness coupon qualifies the teeth. The planet pins (M15) stay a bought 52100 shaft. They are the needle race and are not a milled alloy.

---

## 5. Fits and inspection data to put on vendor drawings

| Feature | Fit / value | Source |
|---|---|---|
| Ring-1 OD in housing | Ø85 **K6 / h5** (clearance at 80 °C is +43 to +80 µm, so the dowels centre the ring when hot) | calc §5 |
| Cartridge spigot in housing | Ø89 **G7 / h6** | calc §5 |
| 61813 outer rings in cartridge | **Selective**: bore = measured bearing OD **+3 / +10 µm** | calc §5 |
| 61813 inner rings on carrier-2 | Ø65 **j5** (−21 to +7 µm with the 0/−15 µm bearing bore) | calc §5 |
| Labyrinth (sun-1 flange in partition) | Ø41.0 H8 / Ø40 h8 (1.00–1.08 mm diametral clearance at 20 °C) | calc §5 |
| Plate plug in housing | Ø94.5 **H7 / k6** (−25 to +32 µm; both 6082-T6, no change with temperature) | calc §5 |
| Radial plate screws | Housing CSK centres **0.1 forward** of the plug threads (draws the housing onto the plate rim) | calc §6 |
| Motor in housing bore | Ø92.0 in Ø94.5 (1.25 radial); rear cap Ø17.4 in plate relief Ø19.5 (1.05 radial) | calc §9 |
| Magnet holder pin in rotor cap | Turned to the measured hole, 0–0.02 clearance | calc §9 |
| Ring-1 dowel slot in housing | Width 3.02–3.04 over the Ø3 m6 dowel; ring-1 hole Ø3 H7 | calc §6 |
| Planet bore for HK0810 | Ø12 **N6** (steel housing) | [S5] |
| Planet pins | Ø8 **h6**, Ra ≤ 0.2, in Ø8 **R7** holes (4–28 µm interference) | [S5], [S14] |
| Output flange | Pilot Ø40 H7 × 2; runout ≤ 0.02 TIR; flatness ≤ 0.03 | spec 10 |
| Sun-1 span | W3 = **6.082 −0.015/0** | calc §8 |
| Planet-1 span | W5 = **11.008 −0.015/0** | calc §8 |
| Sun-2 span | W3 = **7.609 −0.015/0** | calc §8 |
| Planet-2 span | W4 = **10.687 −0.015/0** | calc §8 |
| Ring-1, between Ø1.2 pins | Mi = **70.813 +0.015/0** | calc §8 |
| Ring-2, between Ø1.5 pins | Mi = **70.499 +0.015/0** | calc §8 |
| Gear data (all) | 20° PA, x = 0, backlash 0.05 ± 0.02 mm per mesh (output 0.09–0.22°) | spec 7.1, calc §3 |
| Gear quality | ISO 1328 grade 7–8 is accepted on this order. Do not grind the teeth | spec 7.1 |

---

## 6. Prototype builds: what to buy for each

| Build | Gears | Structure | Buy from this BOM |
|---|---|---|---|
| **P0 fit check** | SLA tough resin, backlash 0.15–0.20 mm per mesh | PETG prints of M03, M04, M11, M14 | Motor, bearings, HK0810, pins, fasteners; no heat treatment |
| **P1 functional** | **Real steel gears** (M05, M06, M08, M09, M11 ring section, M12) | PA-CF prints (100% infill), bearing seats printed undersize and reamed | Everything in Section 2 |
| **P2 metal** | Full Section 1 | Full Section 1 | Everything |

Steel gears are needed from P1 because m0.8 and m1 teeth cannot be printed accurately by FDM (spec 14).

---

## 7. Sourcing checklist (in order)

1. Measure the open motor items (Section 8), then release M02, M03 and F04. The rest of the motor is measured and already in `build()`.
2. Order the bearings (P02, P03 with **C3**; P04) and the wave spring (P05). These are long-lead and decide final bore sizes.
3. Order the two alloys in Section 4. Keep the 20MnCr5 from one heat. A grade mark is enough for this first article.
4. Release the machining drawings, with the Section 5 values on them.
5. Send one carburizing batch for the toothed parts, with a witness coupon. Tap and mask the M2.5 threads first. Do not send the three toothless carriers. Do not nitride anything.
6. Finish-grind the planet bores and the cartridge selective bore (using the measured bearing ODs).
7. Order electronics (P09–P14), fasteners and consumables (2.1, 2.2).
8. Incoming inspection: gear span and pin measurements, case-depth report, bearing clearance class on the box label.

---

## 8. Open sourcing items

| Item | Status |
|---|---|
| LA8308 rear cap centre hole | Plain hole; **measure** diameter and depth (model assumes Ø3 × ≥ 2), then turn the M02 pin to it |
| M18 planet washers: DIN 988 ID tolerance on the Ø8 pin | Check one sample before ordering 12 |
| Cartridge Ø89/Ø85 finishing after carburizing | Mask the bore and the spigot. Finish them after heat treatment |
| Part specification | Written in `shoulder/parts.md` |

---

## References

- [S1] SKF 61813-2RS1 product page (dimensions, C 11.9 / C0 9.65 kN, d1 71.4, D2 80.3): https://www.skf.com/uk/products/rolling-bearings/ball-bearings/deep-groove-ball-bearings/productid-61813-2RS1
- [S2] Tradebearings technical sheets, 61813-2RS1, 61813-2Z and 61813-C3 (mass, ratings, C3 availability): https://en.tradebearings.com/data/pdf/19/a4/61813_2RS1-149964.pdf, https://en.tradebearings.com/61813_2Z-80293.html, https://en.tradebearings.com/data/pdf/96/4a/61813_C3-1123798.pdf
- [S3] Smalley SSB-0335 part page and catalogue: https://www.smalley.com/wave-spring/ssb-0335, https://www.smalley.com/sites/default/files/pdfs/CC2013-Wave%20Springs.pdf
- [S4] Lispring LB-0335 (alternate to SSB-0335): https://store.wave-spring.com/lb-0335.html
- [S5] INA HK0810 data (Cr 3.80 / C0r 3.95 kN, 3.1 g): https://www.noksbearings.com/brand/ina/hk0810/needle-roller-bearings-ina, https://motionparts.de/products/hk0810-ina
- [S6] SKF HK 0810 data sheet (C 3.69 / C0 4.05 kN): https://documents.klium.nl/9ad58f0c-40d4-47fb-ab4e-48a1f5b26eee/en/technical-data-sheet-skf-hk-0810-hk-0810-en.pdf
- [S7] TI DRV5032 datasheet (FB = 5 Hz sampling, BOP max 4.8 mT): https://www.ti.com/lit/ds/symlink/drv5032.pdf
- [S8] TI DRV5033 datasheet (20–30 kHz bandwidth, FA BOP ±3.5 mT, 2.5–38 V, open-drain): https://www.ti.com/lit/ds/symlink/drv5033.pdf
- [S9] TI DRV5033 product page: https://www.ti.com/product/DRV5033
- [S10] ams AS5047P adapter-board manual (Ø6 × 2.5 diametric magnet AS5000-MD6H-2, gap 0.5–3 mm, holder not ferromagnetic): https://media.digikey.com/pdf/Data%20Sheets/Austriamicrosystems%20PDFs/AS5047P-TS_EK_AB.pdf
- [S11] AS5047P datasheet (35–70 mT at the die): https://www.infineon.com/assets/row/public/documents/24/49/infineon-as5047p-datasheet-en.pdf
- [S12] Steel grade equivalents, India (EN24 = 34CrNiMo6 = 4340; EN19 = 42CrMo4 = 4140; EN31 = 100Cr6 = 52100; 16MnCr5): https://goswamiheattreatment.com/Tools/SteelGradesIndia, https://www.technocnc.in/upload/brochure/1567530912_technocnc.pdf
- [S13] Ambhe Ferro grade guide and 16MnCr5 cross-reference: https://ambhe.com/other-info/steel-grades/, https://www.ambhe.com/16mncr5-steel/
- [S14] ISO 286 press-fit limits (H7/r6 = R7/h6 at Ø8–10: 4–28 µm) and fit lists: https://mechsheet.com/guide/press-fit-tolerance/, https://www.threadspecification.com/hole-shaft-tolerances/
- [S15] EN19 listed as the general high-tensile engineering grade, EN24 as the higher-toughness grade: https://www.partwork.io/materials/cnc-machining-alloy-steel
- [S16] EN19 stocked as rounds for high-tensile parts; EN24 listed mainly as forging rod: https://rbsgroupglobal.com/en-series-steel-supply/
- [S17] EN AW-6082 T6 extruded bar, diameter over 20 mm up to 150 mm: Rm min 310 MPa, Rp0.2 min 260 MPa (EN 755-2): https://www.alumeco.com/aluminium/data/mechanical-properties/round-bars-extruded/, https://hlinik.cz/wp-content/uploads/2024/07/kl-upr-tyce-6082-t6511-en.pdf
- [S18] EN AW-6082 datasheet: Al-Si-Mg, Fe max 0.50%, density 2700 kg/m³: https://nedal.com/images/Files__pdfs/legeringen/nedal_datasheet_6082.pdf
- [S19] Case-carburized gear contact rating σHlim 1500 N/mm², against a lower rating for through-hardened steel: ISO 6336-5:2016 https://cdn.standards.iteh.ai/samples/55353/ba79aa11e5ed453fbde881d3514241bc/ISO-6336-5-2016.pdf ; IMO acceptable contact limits, carburised pair 1500 N/mm²: https://www.imorules.com/NSR_V2_PT3_CH1_7.html
- Project files: `shoulder/cad/calc.txt` (calc §1–§8), `shoulder/parts.md` (part specification), `shoulder/cad/actuator.step` (geometry), `shoulder/cad/milling/` (quotation pack).
