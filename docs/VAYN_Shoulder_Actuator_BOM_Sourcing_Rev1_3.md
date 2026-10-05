# VAYN Shoulder Actuator — BOM and Sourcing Guide, Rev 1.3

**Purpose:** buy or make every part of one actuator without needing to read the CAD. For each item it lists quantity, material and grade equivalents, raw-stock size, process, heat treatment, critical features and approved alternates.

**Source of truth:**
- Geometry and part list: `build()` in `cad/gen_actuator_3mf.py`. The exact model is `cad/rev1_3/VAYN_Shoulder_Actuator_Rev1_3.step`.
- Loads, fits and torques: `cad/calc_rev1_3.py`, with results in `cad/calc_rev1_3_output.txt`.
- Design spec: `docs/VAYN_Shoulder_Actuator_CAD_Spec_Rev1_2.md`. A Rev 1.3 spec has not been written yet.

Part IDs (`M..` = make, `P..` = purchase) are used only in this doc. The "Model #" column is the object number in the STEP/3MF.

---

## 0. Summary

| Item | Value |
|---|---|
| Make parts | 18 unique (38 pieces, including 14 thrust washers) |
| Purchased parts | 27 lines (≈ 85 pieces, not counting spares) |
| Actuator mass | ≈ 2.75 kg: ≈ 2.42 kg modelled parts plus the 336 g motor (model volumes × density) |
| Heaviest parts | Cartridge 351 g, housing 342 g, carrier-2 front 314 g, carrier-2 rear 227 g, ring-1 190 g |
| Longest-lead items (order first) | LA8308 motor, 61813/C3 bearings, SSB-0335 wave spring, carburizing and nitriding batches |
| Must-measure before machining | LA8308 rotor-face and stator-base hole patterns (the model uses 83xx family defaults: rotor 4 × M3 on PCD 31, stator 4 × M4 on PCD 40) |

**Changes made by this sourcing review (not yet in the model):**
1. **Homing hall sensor: DRV5032FB → DRV5033FAQDBZR.**
   - The DRV5032FB samples at **5 Hz** [S7], which is once every 200 ms.
   - The magnet (r 36.8 mm) at the 72 rpm output speed moves at 2π × 36.8 × 1.2 ≈ 277 mm/s. With a ≈ 4 mm trigger window it is inside the window for ≈ 14 ms, so the sensor catches it on fewer than 1 in 10 passes.
   - The DRV5033 has **20–30 kHz bandwidth**, the same SOT-23 package, BOP ±3.5 mT (max 6.8 mT) and runs on 2.5–38 V [S8][S9].
   - The magnet gives 97 mT at 2 mm (calc §7), so there is a large margin.
   - It has an open-drain output, so fit a 10 kΩ pull-up to 3.3 V.
2. **Output bearings must be C3 clearance.** The j5 inner-ring fit plus a 5 K ring gradient removes ≈ 18.7 µm of radial clearance. A Normal-clearance bearing would then be at −10.7 µm (preloaded); a C3 bearing keeps +4.3 µm (calc §5).

---

## 1. Make parts

Stock sizes below include ≈ 5 mm on the diameter and ≈ 5 mm on the length for facing and parting. Add chucking length if the shop cannot bar-feed.

| ID | Model # | Part | Qty | Material (delivery condition) | Finished size (mm) | Raw stock (each) | Process | Heat treatment / finish | Critical features | Mass (g) |
|---|---|---|---|---|---|---|---|---|---|---|
| M01 | 01 | Encoder lid | 1 | 6061-T6 | Ø59.8 × 2 | 3 mm plate, 65 × 65 | CNC mill | Clear anodize | 4 × M2 CSK, cable slot | 14.5 |
| M02 | 06 | Magnet holder sleeve | 1 | 6061-T6 (**must be non-magnetic** [S10]) | Ø10 / Ø6 × 3.6 | Ø12 bar | Lathe | None | Magnet bore Ø6, concentric ≤ 0.10 TIR | 0.5 |
| M03 | 08 | Rear mount plate | 1 | 7075-T651 | Ø100 × 10 | 12 mm plate 105 × 105, or Ø105 bar slice 15 | CNC 3-axis, 2 setups | Clear anodize type II; mask the M3 counterbores | 6 × M4 wire-thread inserts (torso), 2 × Ø4 torso dowel, 6 × M3 c'bore, 2 × Ø3 dowel, 4 × M4 CSK stator (**measure motor**), PCB bosses M2.5, lid M2 tapped, phase and encoder cable grooves | 148 |
| M04 | 15 | Housing (one-piece) | 1 | 7075-T651 / T6511 round bar | Ø100 × 74 | Ø105 × 80 | CNC lathe + 4th-axis or 3-axis mill | Clear anodize type II; **mask all fits and threads** | Motor pocket Ø94.5; ring-1 bore Ø85 **K6**; cartridge bore Ø89 **G7**; labyrinth Ø40.6 **H8**; 12 × cooling slots 3 × 18; 6 × M3 rear (2.6 engagement); 8 × M3 front (6 engagement); 2 × Ø4 ring-1 dowel holes | 342 |
| M05 | 16 | Ring-1, 90T m0.8 internal | 1 | 42CrMo4 / EN19, Q&T 28–34 HRC | Ø85 h5 × 15.2 | Ø90 × 20 | Turn, then **wire-EDM teeth** | Gas or plasma nitride after EDM; **no grinding** (allow 0.03–0.04 mm nitride growth) | Teeth: Mi over Ø1.2 pins **70.813 +0.015/0**; 2 × Ø4 dowel holes | 190 |
| M06 | 18 | Sun-1 18T m0.8 flanged pinion | 1 | 16MnCr5 (or 20MnCr5), annealed | Flange Ø40 × 3, teeth Ø16 × 10.4, total 18.2 | Ø45 × 25 | Turn, hob or shape, CSK holes | Carburize CHD **0.12–0.18** @ 550 HV, 58–62 HRC surface, core 30–40 HRC, temper; hard-finish teeth to ISO 1328 grade 6–7 | W3 **6.082 −0.015/0**; 4 × M3 CSK on PCD 31 (**measure rotor**); centring recess for rotor boss | 43 |
| M07 | 21 | Carrier-1 rear plate + posts | 1 | EN24T (34CrNiMo6 / 4340), Q&T | Ø60 × 14 | Ø65 × 20 | CNC | As supplied (T condition) | 3 × Ø8 **P7** pin holes on PCD 43.2; posts tapped M3 | 76 |
| M08 | 22 | Carrier-1 front plate + sun-2 18T m1 | 1 | 16MnCr5 | Ø60 plate + sun Ø20 × 10, total 24 | Ø65 × 30 | Turn, hob, drill | Carburize CHD **0.15–0.20**, 58–62 HRC; **mask the plate area** [spec 7.2] | W3 **7.609 −0.015/0**; 3 × Ø8 P7 holes; 3 × M3 CSK | 95 |
| M09 | 24.1–3 | Planet-1 36T m0.8 | 3 | 16MnCr5 | Ø30.4 × 10, bore Ø12 | Ø35 bar; hob a stack of 4 blanks (3 + 1 spare) | Turn blanks, hob as a stack, part off | Carburize CHD 0.12–0.18, 58–62 HRC; grind the bore after hardening | Bore **Ø12 N6**, roundness IT5/2, Ra ≤ 0.8 [S5]; W5 **11.008 −0.015/0** | 41.6 each |
| M10 | 32 | Carrier-2 rear half (hub + posts) | 1 | EN24T, Q&T | Hub Ø65 × 10 + 3 posts; envelope Ø67 × 21 | Ø75 × 27 | CNC | As supplied; nitride the hub only if fretting appears in endurance test | Hub Ø65 **j5** (inner-ring seat); 3 × Ø8 P7 pin holes on PCD 45; posts tapped M4; post faces are the inner-ring shoulders | 227 |
| M11 | 33 | Bearing cartridge + ring-2 72T m1 | 1 | 42CrMo4 / EN19, Q&T 28–34 HRC | Flange Ø100 × 7.5, spigot Ø89, total 31.5 | Ø105 × 37 | Turn, wire-EDM ring-2 teeth, drill/tap | Nitride after EDM. **Tap the 8 × M2.5 before nitriding and mask them.** Finish Ø89 and the Ø85 bore after nitriding, or mask them; agree with the heat-treater | Spigot Ø89 **h6**; bearing bore Ø85 **selective**: measure both 61813 ODs and machine +3/+10 µm clearance (rear ring must slide under the spring); ring-2 Mi over Ø1.5 pins **70.499 +0.015/0**; 8 × M3 c'bore; 8 × M2.5 tapped; 2 × Ø4 dowel | 351 |
| M12 | 36.1–3 | Planet-2 27T m1 | 3 | 16MnCr5 | Ø29 × 10, bore Ø12 | Ø35 bar; stack of 4 | As M09 | Carburize CHD 0.15–0.20, 58–62 HRC; grind bore | Bore Ø12 N6; W4 **10.687 −0.015/0** | 35.2 each |
| M13 | 42 | Carrier-2 front half + output flange | 1 | EN24T, Q&T | Flange Ø78, hub Ø65, total 14 | Ø85 × 20 | CNC lathe + mill | As supplied | Hub Ø65 **j5**; **6 × M5 tapped in steel**, 8 deep as modelled (spec asks 10; confirm against arm screw length), PCD 52 (arm); pilot Ø40 H7 × 2; 3 × M4 c'bore; 3 × Ø8 P7 pin holes; Ø3 radial magnet pocket in rim; runout ≤ 0.02 TIR | 314 |
| M14 | 45 | Front cover / bearing retainer | 1 | 7075-T651 | Ø100 / Ø80 × 3 | 5 mm plate, 105 × 105 | CNC | Clear anodize | 8 × M2.5 CSK; hall sensor pocket + wire slot; lip contacts the front outer ring only | 23 |
| M15 | 26.1–3, 38.1–3 | Planet pins (needle raceways) | 3 + 3 | 52100 / EN31 / 100Cr6 / SUJ2 | Pin-1 Ø8 × 17; pin-2 Ø8 × 23 | Ø8 h6 ground, hardened shaft, 200 mm | Cut, chamfer, re-check | Through-hardened **58–64 HRC**, **ground h6, Ra ≤ 0.2 µm** [S5][S6] | Press fit into P7. Do **not** use g6 linear shaft or ISO 8734 m6 dowels without checking the needle clearance | 6.6 / 9.0 each |

**Custom thin parts** (laser-cut or wire-cut from 0.3 mm hardened strip, or buy the nearest standard):

| ID | Model # | Part | Qty | Size (mm) | Material | Notes |
|---|---|---|---|---|---|---|
| M16 | 20 | Carrier-1 rear thrust washer | 1 | Ø48 / Ø42 × 0.3 | Hardened spring steel C75S (1.1248) or 52100 strip, ≥ 45 HRC, flat ≤ 0.02 | Runs between the stationary partition and carrier-1 |
| M17 | 30 | Carrier-1 front thrust washer | 1 | Ø40 / Ø24 × 0.3 | As M16 | Runs between carrier-1 and carrier-2 |
| M18 | 27, 28, 39, 40 | Planet thrust washers | 12 | Ø14 / Ø8.2 × 0.3 | As M16 | Standard candidate: **DIN 988 8 × 14 × 0.3** shim ring. Its ID is 8 D12 (8.04–8.19), which must run free on the Ø8 h6 pin, so check one before ordering |

---

## 2. Purchased parts

| ID | Model # | Part | Qty (+spare) | Exact spec | Approved / alternate | Why this part | Notes |
|---|---|---|---|---|---|---|---|
| P01 | 12–14 | BLDC motor | 1 | EaglePower **LA8308 KV90**, Ø92 × 28.5, 336 g, Ø6 shaft | — | Fixed by requirements | **Measure on arrival:** rotor-face holes, stator-base holes, rear shaft protrusion. Release M03, M06 and the M4 stator screws only after measuring |
| P02 | 31 | Rear output bearing | 1 (+1) | **61813-2Z/C3**, 65 × 85 × 10, metal shields | SKF 61813-2Z/C3; NSK/NTN 6813ZZ C3 (confirm C3 on the box) | Thin section, so it fits the Ø100 envelope; shields keep grease in | **C3 required** (Section 0). The spare lets you select the best OD match for the cartridge bore (M11). C 11.9 kN, C0 11.5 kN, 0.13 kg [S2] |
| P03 | 41 | Front output bearing (also the output seal) | 1 (+1) | **61813-2RS1/C3**, 65 × 85 × 10, contact seals | SKF 61813-2RS1/C3; NSK 6813DDU C3, NTN 6813LLU C3 | The contact seal is the gearbox front seal | C 11.9 kN, C0 9.65 kN (use the lower SKF value), d1 ≈ 71.4, D2 ≈ 80.3, 0.131 kg [S1][S2] |
| P04 | 25, 37 | Planet needle bearings | 6 (+2) | **HK0810** drawn cup, Fw 8 × D 12 × C 10, open ends | INA HK0810-B; SKF HK 0810 | Highest capacity for the smallest planet bore | INA Cr 3.80 / C0r 3.95 kN; SKF lists C 3.69 kN, so design to 3.69 [S5][S6]. Press into Ø12 N6 with a stepped mandrel on the stamped end |
| P05 | 29 | Bearing preload wave spring | 1 (+1) | **Smalley SSB-0335**, carbon steel: bore 85, clears 71.38, 231.4 N at 2.77 work height, free 5.59, t 0.76, wall 5.92, 83 N/mm | Lispring **LB-0335** (stated drop-in alternate); stainless option SSB-0335-S17 | Keeps both 61813s preloaded at ≈ 206–252 N across tolerances and −40 to +60 K (calc §4) | [S3][S4]. Acts on the rear (floating) outer ring only |
| P06 | 17 | Dowel pin, ring-1 to housing | 2 (+2) | ISO 8734 Ø4 × 10, hardened, m6 | Any ISO 8734 / DIN 6325 | Stops ring-1 rotating | — |
| P07 | 35 | Dowel pin, cartridge to housing | 2 (+2) | ISO 8734 Ø4 × 8 | Same | Back-up anti-rotation (friction carries the load) | — |
| P08 | 10 | Dowel pin, plate to housing | 2 (+2) | ISO 8734 Ø3 × 6 | Same | Locates the rear plate | — |
| P09 | 07 | Motor encoder magnet | 1 (+1) | Ø6 × 2.5 NdFeB, **diametrically** magnetised | Bomatec **AS5000-MD6H-2** (ams kit magnet) [S10] | Size required by the AS5047P | Gap to IC 1.0 (0.5–3.0 allowed), centred ≤ 0.5 mm [S10] |
| P10 | 44 | Homing magnet | 1 (+2) | Ø3 × 2 NdFeB **N52**, axially magnetised | Any N52 disc | Gives 97–201 mT at 1.2–2.0 mm (calc §7) | Glue radially into the flange rim (M13) with the pole facing outward |
| P11 | 04 | Motor encoder IC | 1 (+1) | **AS5047P-ATSM** (TSSOP-14) | ams-OSRAM / distributor stock | 14-bit absolute angle; needed for FOC | Field 35–70 mT at the die [S11] |
| P12 | 03 | Encoder PCB | 1 (+2) | 30 × 30 × 1.6 FR4, 2-layer, 4 × M2.5 holes on PCD 34 | Any PCB fab | Carries the AS5047P on the motor axis | Shielded SPI cable out through the plate groove |
| P13 | 46 | Homing hall sensor | 1 (+2) | **TI DRV5033FAQDBZR** (SOT-23, omnipolar, 30 kHz, open-drain) | DRV5033AJ (less sensitive, also OK) | **Replaces DRV5032FB (5 Hz, too slow)**, see Section 0 [S7][S8][S9] | 10 kΩ pull-up to 3.3 V; 3-wire lead |
| P14 | — | Winding thermistor | 1 (+1) | 10 kΩ NTC, β ≈ 3435–3950, glass bead or epoxy | Any | Feeds the ODrive motor-thermistor input [spec 6.5] | Bond to the end winding with thermal epoxy |
| P15 | — | Motor controller (system item) | 1 | ODrive / ODESC class, ≥ 20 A phase current | — | Required by the design's current limits [spec 12] | Settings: `torque_constant 0.0919`, `current_lim ≤ 20 A` |

### 2.1 Fasteners (all steel, grade 12.9 unless noted; black oxide)

| ID | Model # | Fastener | Standard | Qty (+spare) | Joint | Torque (N·m) | Threadlocker |
|---|---|---|---|---|---|---|---|
| F01 | 02 | M2 × 4 countersunk | ISO 7046 / ISO 14581 (grade 8.8 or A2 is fine) | 4 (+4) | Lid to plate | 0.3 | None |
| F02 | 05 | M2.5 × 5 pan | ISO 7045 / ISO 14583 | 4 (+4) | PCB to plate bosses | 0.4 | None |
| F03 | 09 | M3 × 8 socket head cap | ISO 4762 12.9 | 6 (+4) | Rear plate to housing lip | **1.2** (calc §6) | Loctite 243 |
| F04 | 11 | M4 × 8 countersunk | ISO 10642 (10.9 standard) | 4 (+2) | Stator to plate (**pattern to be measured**) | Per motor maker; ≤ 2.0 into an aluminium base | Loctite 243 |
| F05 | 19 | M3 × 5 countersunk | ISO 10642 | 4 (+4) | Sun-1 to rotor face | **1.2** (calc §6: slip SF 11.9) | Loctite 243 |
| F06 | 23 | M3 × 10 countersunk | ISO 10642 | 3 (+2) | Carrier-1 front plate to posts | 1.2 | Loctite 243 |
| F07 | 34 | M3 × 10 socket head cap | ISO 4762 12.9 | 8 (+4) | Cartridge flange to housing | **1.2** (slip SF 3.4) | Loctite 243 |
| F08 | 43 | M4 × 16 socket head cap | ISO 4762 12.9 | 3 (+2) | Carrier-2 halves | **4.0** (slip SF 1.4: torque exactly, use a torque driver) | Loctite 243 |
| F09 | 47 | M2.5 × 6 countersunk | ISO 7046 / ISO 14581 | 8 (+4) | Cover to cartridge | 0.8 | Loctite 222 |
| F10 | — | M4 wire thread insert, 1.5D | Helicoil / ISO 13050 type | 6 (+4) | Torso bracket threads in the 7075 plate | — | — |
| F11 | — | Torso bracket screws M4 | ISO 4762 12.9 | 6 | Torso to rear plate (supplied with torso) | **3.0** (slip SF 3.1) | Loctite 243 |
| F12 | — | Arm screws M5 | ISO 4762 10.9 or 12.9 | 6 | Arm to output flange (supplied with arm) | **8.0** (slip SF 4.6) | Loctite 243 |

The torques above are calculated for 12.9 screws at μ ≈ 0.12 (VDI 2230 basis in `calc_rev1_3.py`). The F01, F02, F04 and F09 values are practical limits for small screws in light joints, not calculated values.

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
| **7075-T651 aluminium** | AlZn5.5MgCu / 3.4365 / AA7075 | Housing (M04), rear plate (M03), front cover (M14) | Highest-strength common aluminium: the stiff, light structure for the Ø100 envelope. Housing stress at 50 N·m is only 0.7–1.4 MPa (calc §7), so the choice is for stiffness, thread strength and bearing-seat stability | T651 plate or T6511 bar; clear anodize type II with fits masked | EN 10204 3.1 mill certificate |
| **6061-T6 aluminium** | AlMg1SiCu / 3.3211 / AA6061 | Encoder lid (M01), magnet holder (M02) | Low-load parts. The magnet holder **must be non-magnetic** (ams rule [S10]) | As supplied; anodize the lid | Mill certificate |
| **16MnCr5 case-hardening steel** | 16MnCr5 / 1.7131 / ≈ SAE 5115 / IS 16Mn5Cr4 (17Mn1Cr95) / ≈ SCr415 [S12][S13]. Equal or better: **20MnCr5** | Sun-1 (M06), carrier-1 front + sun-2 (M08), all planets (M09, M12) | The highest-stressed parts: stage-2 sun contact stress σH ≈ 1350 MPa at 30 N·m, against σHlim 1500 for case-hardened steel (calc §3). A hard case on a tough core is needed; plain nitrided 42CrMo4 is **not** enough for the suns and planets (spec 7.2) | Buy annealed. After machining: carburize to the CHD in Section 1, harden 58–62 HRC, core 30–40 HRC, low temper | Mill certificate plus a heat-treat report with a case-depth profile on a witness coupon of the same bar |
| **42CrMo4 / EN19, Q&T** | 42CrMo4 / 1.7225 / AISI 4140–4142 / IS 40Cr4Mo3 / SCM440 [S12][S13] | Ring-1 (M05), cartridge + ring-2 (M11) | Ring contact stress is about half the sun's (σH ≈ 675–925 MPa), so nitrided 42CrMo4 has margin. Nitriding distorts very little, which suits thin internal rings that cannot be ground | Buy Q&T at 28–34 HRC, wire-EDM the teeth, then gas or plasma nitride | Mill certificate plus a nitride report (surface HV, NHD) |
| **EN24T** | 34CrNiMo6 / 1.6582 / AISI 4340 / IS 40Ni6Cr4Mo3 / SNCM439 [S12][S13] | Carrier-1 rear (M07), carrier-2 halves (M10, M13) | Output carrier: the M5 arm threads go directly into steel (no inserts), the bearing seats resist fretting, and it is stiff under 50 N·m tilt | Buy in T condition (Q&T, ≈ 850–1000 MPa); no further heat treatment | Mill certificate stating the T condition |
| **52100 / EN31 bearing steel** | 100Cr6 / 1.3505 / AISI 52100 / IS 103Cr2 / SUJ2 [S12][S13] | Planet pins (M15), and the dowels' material class | The pins are the needle raceways and need ≥ 58 HRC and Ra ≤ 0.2 [S5] | Through-hardened 58–64 HRC, ground h6 | Hardness and roughness report |
| **Hardened spring steel strip** | C75S / 1.1248 (DIN 988 standard material) | Thrust washers (M16–M18) | Thin, hard, flat wear faces against rotating parts | 0.3 mm hardened and tempered strip | — |
| **Spring steel (bought in)** | Smalley carbon steel (SAE 1070–1090 class) | Wave spring (P05) | Catalogue part | — | — |
| **NdFeB** | N35–N52 | Encoder magnet (P09), homing magnet N52 (P10) | Field strength. Keep below ≈ 80 °C (standard NdFeB grade limit) | Ni-Cu-Ni coated | Grade and magnetisation direction on the order |

---

## 4. Consolidated raw-stock order (per actuator; double it for a spare set)

| Material | Stock to buy | Covers |
|---|---|---|
| 7075-T6511 round bar | **Ø105 × 85** | Housing (M04) |
| 7075-T651 plate | **12 mm**, 110 × 110 and **5 mm**, 110 × 110 | Rear plate (M03), cover (M14) |
| 6061-T6 | 3 mm plate, 70 × 70; Ø12 bar, 30 | Lid (M01), magnet holder (M02) |
| 42CrMo4 (EN19) Q&T round | **Ø105 × 70** (one bar: cartridge 37 + ring-1 20 + kerf) | M11, M05 |
| EN24T round | **Ø85 × 80** (C2 front 20 + C2 rear 27 + C1 rear 20 + kerf) | M13, M10, M07 |
| 16MnCr5 round, annealed | **Ø65 × 35**, **Ø45 × 30**, **Ø35 × 150** (two 4-blank stacks, 3 planets + 1 spare per stage) | M08, M06, M09, M12 |
| 52100 Ø8 h6 hardened ground shaft | **200 mm** | 6 pins (M15) |
| Hardened strip 0.3 mm | 100 × 100 sheet | M16–M18 (if not buying DIN 988) |

Buy all 16MnCr5 parts from **one heat (one bar lot)**. They then share the carburizing batch, and one witness coupon qualifies the whole batch.

---

## 5. Fits and inspection data to put on vendor drawings

| Feature | Fit / value | Source |
|---|---|---|
| Ring-1 OD in housing | Ø85 **K6 / h5** (clearance at 80 °C is +43 to +80 µm, so the dowels centre the ring when hot) | calc §5 |
| Cartridge spigot in housing | Ø89 **G7 / h6** | calc §5 |
| 61813 outer rings in cartridge | **Selective**: bore = measured bearing OD **+3 / +10 µm** | calc §5 |
| 61813 inner rings on carrier-2 | Ø65 **j5** | calc §5 |
| Labyrinth (sun-1 flange in partition) | Ø40.6 H8 / Ø40 h8 (0.28–0.41 mm clearance) | calc §5 |
| Planet bore for HK0810 | Ø12 **N6** (steel housing) | [S5] |
| Planet pins | Ø8 **h6**, Ra ≤ 0.2, in Ø8 **P7** holes | [S5], spec 8 |
| Output flange | Pilot Ø40 H7 × 2; runout ≤ 0.02 TIR; flatness ≤ 0.03 | spec 10 |
| Sun-1 span | W3 = **6.082 −0.015/0** | calc §8 |
| Planet-1 span | W5 = **11.008 −0.015/0** | calc §8 |
| Sun-2 span | W3 = **7.609 −0.015/0** | calc §8 |
| Planet-2 span | W4 = **10.687 −0.015/0** | calc §8 |
| Ring-1, between Ø1.2 pins | Mi = **70.813 +0.015/0** | calc §8 |
| Ring-2, between Ø1.5 pins | Mi = **70.499 +0.015/0** | calc §8 |
| Gear data (all) | 20° PA, x = 0, backlash 0.05 ± 0.02 mm per mesh (output 0.09–0.22°) | spec 7.1, calc §3 |
| Gear quality | Suns and planets ISO 1328 grade 6–7; rings grade 7–8 | spec 7.1 |

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

1. Order the motor (P01) and measure it. Update the rotor and stator patterns in `build()`, then release M03, M06 and F04.
2. Order the bearings (P02, P03 with **C3**; P04) and the wave spring (P05). These are long-lead and decide final bore sizes.
3. Order the steel bars (Section 4) with mill certificates. Keep the 16MnCr5 from one heat.
4. Release the machining drawings, with the Section 5 values on them.
5. Send the heat-treatment batches: 16MnCr5 carburizing with a witness coupon; 42CrMo4 nitriding after EDM, with the M2.5 threads tapped and masked first.
6. Finish-grind the planet bores and the cartridge selective bore (using the measured bearing ODs).
7. Order electronics (P09–P14), fasteners and consumables (2.1, 2.2).
8. Incoming inspection: gear span and pin measurements, case-depth report, nitride report, bearing clearance class on the box label.

---

## 8. Open sourcing items

| Item | Status |
|---|---|
| LA8308 hole patterns and shaft protrusion | Model uses family defaults; **measure** |
| DRV5032FB to DRV5033FA | Sensor swap decided here. Update the name in `build()` and the calc (§7) on the next model revision |
| M18 planet washers: DIN 988 ID tolerance on the Ø8 pin | Check one sample before ordering 12 |
| Cartridge Ø89/Ø85 finishing after nitriding | Agree with the heat-treater: mask, or allow light grinding |
| Rev 1.3 design spec | Not yet written; this BOM follows the model and the calc |

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
- Project files: `cad/calc_rev1_3_output.txt` (calc §1–§8), `docs/VAYN_Shoulder_Actuator_CAD_Spec_Rev1_2.md` (spec sections), `cad/rev1_3/VAYN_Shoulder_Actuator_Rev1_3.step` (geometry).
