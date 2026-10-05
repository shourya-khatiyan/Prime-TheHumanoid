# VAYN Shoulder Actuator — CAD Design Specification, Revision 1.2

**For:** VAYN CAD engineer (original actuator designer)
**Supersedes:** Rev 1.0 (20:1, RU66 concept) and Rev 1.1 ("CAD Master Spec Rev 1.1 FINAL", 6:1 × 5:1, 2 × 6008)
**Units:** mm, N, N·m, degrees, °C
**Status:** Prototype engineering release. Architecture, gear data, bearing types, fits and load cases are fixed. Detailed part geometry belongs to the CAD engineer, within the rules in Section 16.

---

## 0. Summary for the CAD engineer

| Item | Rev 1.2 value |
|---|---|
| Continuous output torque (after losses) | 30 N·m target, 20 N·m minimum useful |
| Structural proof case | 50 N·m output torque **plus** 50 N·m tilt moment (Section 3) |
| Motor | EaglePower LA8308 KV90 (Ø92 × 28.5 mm, 336 g) |
| Reduction | 30:1 = Stage 1 6:1 (m0.8, 18/36/90) × Stage 2 5:1 (m1.0, 18/27/72) |
| Motor current for 30 N·m | 12.1 A (Kt = 0.0919 N·m/A, η = 0.90) |
| Output bearings | 2 × 61813 (65 × 85 × 10), back-to-back, straddling the stage-2 planets |
| Interstage bearing | None. Stage-1 carrier + stage-2 sun float |
| Planet bearings | 6 × HK0810 on Ø8 hardened pins |
| Envelope target | **Ø100 × 94 mm** (Rev 1.1 claimed Ø102 × 102 but cannot be built; a buildable version of that layout is ≈ Ø102 × 115–120) |
| Mass estimate | ≈ 2.0 kg (7075 output carrier) to 2.3 kg (EN24T output carrier) |
| Housing | One-piece 7075-T6 body: motor pocket + partition + single straight Ø85 gear/bearing bore |

---

## 1. Why Rev 1.2 exists: review of Rev 1.1

Rev 1.1's performance basis is correct: the 8.27/KV torque constant, the 30:1 current table, the gravity calculation, the tooth counts and the Lewis screening numbers all check out (Appendix A). Its **mechanical layout and several specifications are not buildable**. The CAD engineer should treat Rev 1.1 as superseded.

| # | Rev 1.1 item | Problem (with the numbers) | Rev 1.2 resolution |
|---|---|---|---|
| 1 | Rear 6008 at Z 64–79, stage-2 planets at Z 57.9–67.9 | The planets reach radius 22.5 + 14.5 = 37 mm, and the bearing occupies radius 20–34 mm. Over Z 64–67.9 they occupy the same space. The stage-2 front cheek (Ø64, Z 68.2–72.2) also overlaps the bearing. The Ø68 bore at Z 64–68.9 falls inside the stage-2 ring gear | Bearings moved radially outward (61813) and axially outside the gear zones |
| 2 | Output flange Z 94–102 (r 27–45) and central web Ø52 at Z 94–95 | The front bearing ends at Z 95 (r 20–34), so the flange and web overlap it at Z 94–95 | New front-end layout (Section 5) |
| 3 | Stationary seal boss inside the Ø54 bore of the rotating flange | The six support webs would have to cross the rotating flange, which is impossible. The 40×52×7 seal needs a Ø52 bore, but the boss *OD* is Ø52, which leaves zero wall. No rotating Ø40 surface exists at Z 95–102 for the seal lip | Front bearing is 61813-**2RS1**, so the bearing is the seal. No separate seal |
| 4 | Output encoder: magnet on the rear of a 1 mm **EN24T steel** web, sensor in front of it, PCB with a Ø12.5 hole "around output shaft" while the sensor is "centred on Datum A" | ams says the magnet surroundings must not be ferromagnetic [R5][R6]. An on-axis sensor cannot have a hole at the axis | On-axis output encoder is impossible in this architecture (the axis is occupied by the stage-2 sun). Rev 1.2 uses an output homing sensor; absolute output is a Rev 2 item (Section 11) |
| 5 | Motor encoder inside a 3 mm rear cover (Z 0–3); motor starts at Z 3 | PCB 1.6 + IC ≈1 + air gap 1.0 + magnet 2.5 + holder ≈7 mm, so it does not fit | 10 mm reserved: 4 mm motor mount plate + 6 mm encoder pocket and cap |
| 6 | 12 mm split-clamp hub on Ø6 shaft, between motor (Z 31.5) and sun (Z 36.3) | Only 4.8 mm of axial space. Slip torque of a single M3 clamp at 1.2 N·m ≈ 1.8–2.8 N·m, against 1.85 N·m needed at the 50 N·m case and 2.02 N·m at 22 A, so the safety factor is about 1.0–1.4 | Sun-1 hub bolted to the rotor face, as in proven 8308/8318 actuators [R12][R13]. Slip torque ≈ 15 N·m |
| 7 | "Continuous sealing wall at Z = 33" | Zero thickness: the stage-1 carrier starts at Z 33 | 3 mm integral partition with labyrinth |
| 8 | Motor cup Ø100 h6 register into a Ø100 H7 recess in a Ø102 housing, with 8 × M4 | Leaves a 1 mm wall, and M4 screws cannot fit | One-piece housing |
| 9 | 6001 interstage bearing on a Ø12 journal integral with the carrier and stage-2 sun | No stationary seat is defined. It cannot be assembled: the sun OD (Ø20) and the carrier (Ø62) both exceed the bearing bore (Ø12). The BOM says the sun is separate while the assembly steps say it is integral | Bearing deleted. Floating carrier-1/sun-2 (Section 7.1) |
| 10 | 20MnCr5 carburized to **0.9 mm** case on m0.8/m1 teeth | Tooth thickness at the pitch circle is only 1.26 mm (m0.8) / 1.57 mm (m1), so a 0.9 mm case from both flanks through-hardens the tooth. ISO 6336-5 allowables assume 0.15–0.2·mₙ case depth [R7], and tip case should be ≤ 0.4·mₙ [R8] | CHD 0.12–0.18 mm (m0.8) and 0.15–0.20 mm (m1) |
| 11 | "Ground" internal rings + "ISO 9" quality | Grinding small internal teeth after carburizing is impractical, and ring distortion is the known problem [R9]. "Ground" and "ISO 9" also contradict each other (ground gears are ISO 5–7) | Rings: EDM/shaped, then nitrided (low distortion, no grinding) [R9][R10]. ISO 7–8 |
| 12 | Backlash 0.10 mm per mesh **and** acceptance ≤ 0.20° | 0.10 mm per mesh gives **0.31°** at the output (Appendix A.6), so the spec fails its own acceptance test | 0.05 ± 0.02 mm per mesh, giving 0.09–0.22°. Acceptance ≤ 0.25° |
| 13 | Bearing check "F = 30 / 0.016" | Uses the joint *torque* as if it were a *tilt* moment. Torque about the axis puts no load on the bearings | Separate tilt load case defined (Section 3.2) |
| 14 | 2 × 6008 CN at 16 mm, "no preload" | CN clearance + 16 mm spacing lets the output wobble. 6008 is 18.6/11.5 kN in Rev 1.1, but SKF lists 17.8/11.0 [R3] | 61813 pair at 21 mm, back-to-back, set to zero end-play (s₀ = 3.9 at the proof case) |
| 15 | HK0810 in an Ø12 **M7** planet bore, pin Ra ≤ 0.4 µm | Schaeffler: steel housing **N6**, raceway h6, **Ra ≤ 0.2 µm**, ≥ 670 HV [R4][R11] | Corrected (Section 8) |
| 16 | Planet pins: Ø8 h6 hardened 52100 (60 HRC) with an **M4 tapped into the pin** + M4 head facing a 1.5 mm gap | You cannot tap 60 HRC; it leaves a 2 mm wall; the 4 mm head does not fit the gap | Press-fit pins, trapped by the opposite cheek. No threaded pins |
| 17 | Arm bolts: "6 × Ø6.6 *clearance* holes" in the flange, with a Ø60 pilot recess | The back of the flange is inside the actuator, so nuts cannot be reached. The Ø60 recess (r 30) cuts into the holes (r 28.2–34.8) | Tapped holes, pilot inside the bolt circle (Section 10) |
| 18 | Ring "10 mm teeth + 1 mm lands" | A land at ring-tip diameter is flush with the planet faces, so the planets rub on it | Ring teeth span the full planet cavity |
| 19 | No controller current cap | At 22 A the 30:1 output is 54.6 N·m, above the 50 N·m structural case. The vendor lists up to 40–45 A peak [R1b] | ODrive `current_lim` ≤ 20 A until the proof test passes (Section 12) |
| 20 | Mass not addressed | Steel carrier with Ø40 shaft + Ø90 flange ≈ 0.75 kg, plus 2 × 6008 ≈ 0.38 kg | 61813 pair 0.26 kg; carrier ≈ 0.15 kg (7075) or 0.41 kg (EN24T) |

---

## 2. Fixed requirements

| Requirement | Value |
|---|---|
| Function | Single-axis shoulder actuator; output axis = Datum A |
| Continuous output | 30 N·m target; 20 N·m minimum useful |
| Peak/proof | 50 N·m output torque (static proof); controller-limited |
| Tilt load | 50 N·m tilt moment + 150 N radial + ±150 N axial, simultaneous, static |
| Motor | EaglePower LA8308 KV90 |
| Ratio | 30:1 (6:1 then 5:1). Do not change the order, tooth counts or modules |
| Max diameter | Ø100.0 (set by motor Ø92 + 1.25 clearance + 2.75 wall) |
| Axial length target | 94.0 mm; hard limit 98.0 mm |
| Supply | 24 V nominal (speeds below scale linearly with voltage) |

---

## 3. Performance and load basis

### 3.1 Torque, current, speed, heat

- Kt = 8.27 / KV = 8.27 / 90 = **0.0919 N·m/A** (ODrive convention, torque = Kt × Iq) [R14][R15]
- Output torque = 0.0919 × I × 30 × 0.90 = **2.481 × I** N·m
- Copper loss = 1.5 × I² × R_phase. R_phase = 0.093 Ω is **assumed**: the vendor lists 0.186 Ω "internal resistance" [R1], assumed to be line-to-line. **Measure it.** Copper resistance rises by +26% at a 90 °C winding (+0.393 %/K).

| Output | Motor current | Cu loss @25 °C | Cu loss @90 °C winding |
|---|---|---|---|
| 20 N·m | 8.1 A | 9 W | 11 W |
| 30 N·m | 12.1 A | 20 W | 26 W |
| 37 N·m | 15.0 A | 31 W | 39 W |
| 50 N·m | 20.2 A | 57 W | 71 W |
| *(20:1 for 30 N·m)* | *18.1 A* | *46 W* | *57 W* |

**What this means for the design:** at 30 N·m continuous the motor makes about 26 W of heat. To stay at or below 90 °C winding in 25 °C still air, the motor plus housing needs a winding-to-ambient thermal resistance of **≤ 2.5 K/W**. 20:1 would need ≤ 1.1 K/W, which is why 30:1 is retained. The thermal test gate (Section 15) measures this number.

Speeds at 24 V, no load: motor 2160 rpm, stage-1 carrier 360 rpm, output **72 rpm (432°/s)**.

### 3.2 Load cases

| Case | Definition | Used for |
|---|---|---|
| L1 continuous | 30 N·m output torque | Thermal, gear fatigue, HK life |
| L2 proof | 50 N·m output torque, static | Gear, carrier, pin, fastener sizing |
| L3 tilt | 50 N·m tilt moment + 150 N radial + ±150 N axial, static | Output bearings, front cover, housing |

**Where the L3 tilt load comes from.** In a multi-DOF shoulder, the downstream arm's gravity moment can act about an axis perpendicular to this actuator's axis. When it does, the full moment becomes tilt load on these bearings. That moment is 9.86 N·m for the uniform arm alone and 19.7 N·m with a 1.5 kg payload at 670 mm; × 2.5 gives ≈ 50 N·m.

**Arm basis (owner to confirm):** 3.0 kg spread uniformly over 670 mm gives 9.86 N·m of gravity torque. If the mass is actually concentrated at the tip, it becomes 19.7 N·m, and × 2.5 = 49 N·m continuous, which this actuator **cannot** deliver continuously. Confirm the arm's center-of-mass position before tooling.

---

## 4. Architecture (section through Datum A)

```
 Z=0                 10                  38.5 42.5        60.5      70.5      81.5     91.5  94
 |cap|enc|mnt|        LA8308 (outrunner)       |P|  STAGE 1  |sp| 61813 | STAGE 2 | 61813 |lip|OUT
 |   |   |   |  stator base @Z10, rotor face @38.5 |  6:1 m0.8 |  |  rear | 5:1 m1  | -2RS1 |   |
 |   |   |   |                                |a| 18/36/90  |  |       | 18/27/72|       |   |
 |   |mag|   |== shaft                        |r|  carrier-1 floats    | carrier-2 on 2x61813 |
 |   |   |   |                     sun-1 hub==|t|=sun-1  ==> sun-2 (integral w/ carrier-1)   |
 one-piece 7075 housing: motor pocket Ø94.5 | partition | straight Ø85 bore Z42.5→81.5 | front cover
```

Torque path: rotor face → bolted sun-1 hub → stage-1 planets (fixed ring-1) → **carrier-1, floating** → integral sun-2 → stage-2 planets (fixed ring-2) → carrier-2 → output face.

Why it is this short: the output bearings sit **beside** the stage-2 gear zone (rear bearing between the stages, front bearing in front of them). They replace the Rev 1.1 interstage gap and the separate Ø40 output shaft.

---

## 5. Axial layout basis (Z = 0 at the rear outer face)

The CAD engineer may move features by ±1 mm, provided the overall length stays ≤ 98 and the radial-zone rules hold. Re-run the full 360° interference check after any change.

| Feature | Z start | Z end | Radial zone | Notes |
|---|---|---|---|---|
| Encoder cap (6061) | 0.0 | 2.0 | ≤ r 50 | |
| Encoder pocket | 2.0 | 6.0 | — | PCB, AS5047P, 1.0 gap, magnet in non-magnetic holder |
| Motor mount plate (6061/7075, 4 mm) | 6.0 | 10.0 | ≤ r 50 | Stator base seats at Z 10.0. Carries motor reaction torque |
| LA8308 envelope | 10.0 | 38.5 | r ≤ 46 | Measure (Section 6) |
| Rotor-to-partition clearance | 38.5 | 39.5 | — | ≥ 1.0 mm. The sun-1 hub flange (rotating) sits in the partition's centre opening |
| Partition (integral to housing) | 39.5 | 42.5 | r ≥ hub opening | Labyrinth ≤ 0.3 mm radial around the hub flange |
| Thrust washer | 42.5 | 43.0 | r ≤ 28 | PTFE-bronze or hardened steel |
| Carrier-1 rear plate (7075) | 43.0 | 46.0 | r ≤ 30 | |
| Stage-1 cavity / planets | 46.0 | 57.0 | planets to r 36.8 | Planets Z 46.5–56.5; 0.3 washer + 0.2 gap each side |
| Ring-1 (OD Ø85) | 42.5 | 57.0 | r 35.2–42.5 | 14.5 wide, teeth through full width. Seats on partition. 2 × Ø4 axial dowels into partition |
| Carrier-1 front plate + sun-2 (one steel part) | 57.0 | 60.0 | r ≤ 30 | Sun-2 extends forward to Z 81.0 |
| Spacer ring Ø85/Ø79 | 57.0 | 60.5 | r 39.5–42.5 | Contacts the bearing outer ring only |
| Thrust washer | 60.0 | 60.5 | r ≤ 28 | Limits carrier-1 forward float |
| Rear 61813 (open or -2Z) | 60.5 | 70.5 | r 32.5–42.5 | On carrier-2 rear hub Ø65 |
| Stage-2 cavity / planets | 70.5 | 81.5 | planets to r 37.0 | Planets Z 71.0–81.0. Sun-2 teeth Z 71.0–81.0 |
| Ring-2 (OD Ø85) | 70.5 | 81.5 | r 35.0–42.5 | 11.0 wide. Acts as the spacer between the outer rings. 2 × Ø4 radial dowels through the housing wall. **Face relief Ø74 × 0.3 deep on both faces:** the tooth tips (r 35.0) otherwise rub the rotating 61813 inner-ring faces (OD ≈ Ø70) |
| Front 61813-2RS1 | 81.5 | 91.5 | r 32.5–42.5 | In the front cover. This is the output seal |
| Front cover lip | 91.5 | 93.0 | r ≥ 40.0 | Retains the front outer ring |
| Output flange Ø78 (carrier-2) | 92.0 | 94.0 | r ≤ 39.0 | 0.5 axial gap to the bearing seal; 1.0 radial gap to the lip |

---

## 6. Motor interface

1. **Measure the motor before CAD.** These are not published reliably [R1][R2]:
   - rotor-face hole pattern, thread and PCD; any centre boss or shaft stub (height, Ø)
   - rear shaft protrusion beyond the stator base, and shaft Ø
   - stator-base mounting holes and PCD; stator-base OD
   - true overall height, Ø92 bell runout, and bell-to-base step
2. **Sun-1 drive:** sun-1 is a flanged pinion (18T m0.8 teeth + hub flange). Bolt it to the rotor face with all available rotor holes (≥ 4 × M3, grade 12.9, Loctite 243) plus a centring pilot on the rotor boss. **No set-screw or split-clamp drive.** This is how proven Eaglepower 8318 actuators do it: WOLF uses "4 × M3 to secure sun gear to motor" [R12], and SpryDrive presses the sun into a rotor adapter plate [R13]. Slip torque of 4 × M3 at r 12.5: ≈ 15 N·m, against 2.0 N·m needed.
3. Stator mounts to the motor mount plate with the measured pattern. Pocket Ø94.5 (1.25 radial clearance), concentric to Datum A within ≤ 0.05 TIR.
4. Cooling: 12 slots 3 × 18 mm in the motor-pocket wall. Airflow stays in the motor chamber only.
5. Fit a 10 kΩ NTC thermistor to the stator winding and wire it to the ODrive motor-thermistor input [R16].

---

## 7. Gearbox

### 7.1 Gear data (Rev 1.1 tooth data retained — verified in Appendix A)

| Parameter | Stage 1 | Stage 2 |
|---|---|---|
| Sun / planet ×3 / ring | 18 / 36 / 90 | 18 / 27 / 72 |
| Module, pressure angle, helix | 0.8, 20°, 0° | 1.0, 20°, 0° |
| Profile shift | 0 | 0 |
| Pitch Ø sun / planet / ring | 14.4 / 28.8 / 72.0 | 18.0 / 27.0 / 72.0 |
| Tip Ø sun / planet; ring tip (minor) Ø | 16.0 / 30.4; 70.4 | 20.0 / 29.0; 70.0 |
| Centre distance (planet PCD) | 21.6 (Ø43.2) | 22.5 (Ø45.0) |
| Face width (sun, planet) | 10.0 | 10.0 |
| Ring width / OD | 14.5 / Ø85 h6 | 11.0 / Ø85 h6 |
| Ring rim below root | 5.5 mm | 5.25 mm (≥ 1.2 × tooth depth) |
| Tangential backlash per mesh (metal) | 0.05 ± 0.02 mm | 0.05 ± 0.02 mm |
| Tangential backlash per mesh (printed/SLA check) | 0.15–0.20 mm | 0.15–0.20 mm |
| Gear quality (ISO 1328-1) | sun/planets 6–7, ring 7–8 | same |

- Backlash is set by tooth-thickness allowance; the centre distances are fixed by the geometry.
- Planet phasing: all (S+R)/3 values are integers (36 and 30), so the three planets assemble at 0°/120°/240° in phase.

**Floating member rule:** each stage has exactly one floating member [R17][R18]. In stage 1, sun-1 is fixed (motor bearings) and **carrier-1 floats**. In stage 2, carrier-2 is fixed (61813s) and **sun-2 floats**. Carrier-1 and sun-2 are one rigid body, located radially by the planet meshes in two planes. Axial float is limited by the two thrust washers to 0.3–0.5 mm total. Do not add a bearing to this body.

### 7.2 Materials and heat treatment (metal prototype)

| Part | Preferred | Alternative (common in India) | Requirement |
|---|---|---|---|
| Sun-1 (with hub flange), sun-2 (with carrier-1 front plate), planets | 20MnCr5 carburized, CHD @550 HV **0.12–0.18 (m0.8), 0.15–0.20 (m1)**, 58–62 HRC, core 30–40 HRC, ground | EN40B / 31CrMoV9 nitrided ≥ 650 HV, NHD 0.2–0.3 | Tip case ≤ 0.4·m. Mask the plate area on the sun-2 part |
| Rings | 42CrMo4 (EN19) Q&T 28–34 HRC; teeth wire-EDM or shaped; then gas/plasma nitride | EN40B nitrided | **No grinding.** Allow for the ≈ 0.03–0.04 mm growth from nitriding [R10] |

Stress margins (Appendix A.3): at the stage-2 sun–planet mesh at L1, σH ≈ 883 MPa. Against carburized σHlim 1500 [R7] that gives S_H ≈ 1.7; nitriding steel (σHlim 1250) gives ≈ 1.4. Do **not** use plain nitrided 42CrMo4 for the stage-2 sun or planets: σHlim 998 gives S_H ≈ 1.13. Rings see only 441 MPa, so nitrided 42CrMo4 gives S_H ≈ 2.3.

---

## 8. Carriers, pins, planet bearings

**Carrier-1 (low torque, floating):** two 7075 plates (Ø60, 3 mm), joined by 3 posts at 60°/180°/300° (each Ø ≥ 10, with an M3 + Ø3 dowel). The front plate and sun-2 are one steel part (Section 7.2), bolted and dowelled to the posts. Thrust washers go against the partition (rear) and carrier-2 (front).

**Carrier-2 (output):** two halves bolted through 3 posts:
- **Rear half:** Ø65 k5 hub (Z 60.5–70.5, bore Ø23 to clear sun-2) plus the posts.
- **Front half:** Ø65 k5 hub (Z 81.5–92.0) plus the Ø78 output flange.
- The posts reach out to r 34.5 (0.5 clearance to the ring-2 tip). Their end faces at Z 70.5 and Z 81.5 are the **inner-ring shoulders** for both 61813s.
- Material: 7075-T6 with steel thread inserts for the arm screws (≈ 0.15 kg), or EN24T (≈ 0.41 kg). Pick 7075 for the mass target. Switch to EN24T if the bearing seats fret in the endurance test.

**Pins:** stage 2: 3 × Ø8 × 23 mm (Z 64.5–87.5); stage 1: 3 × Ø8 × 17 mm (Z 43–60, full depth of both 3 mm plates). Through-hardened bearing steel (52100/SUJ2), 58–64 HRC, **ground h6, Ra ≤ 0.2 µm** (needle raceway) [R4][R11]. Press-fit into Ø8 P7 holes in both cheeks/hubs, about 6 mm engagement each side on carrier-2. No threads in the pins. Do not use ISO 8734 m6 dowels as raceways without checking the resulting needle clearance.

**Planet bearings:** HK0810 (Cr 3.8 kN, C0r 3.95 kN [R19][R20]). Planet bore **Ø12 N6** (steel housing, Schaeffler) [R4][R11]. Roundness IT5/2, Ra ≤ 0.8. Thrust washers Ø8.2 × Ø14 × 0.3, hardened, both sides of each planet.

**Checks at L2 (50 N·m), including a 1.2 load-sharing factor:**
- Stage-2 pin load = 2 × F_t = 936 N
- HK0810 L10 ≈ 9,300 h at full speed (≈ 51,000 h at L1)
- Pin bending ≈ 74 MPa
- Pin bearing pressure in 7075 ≈ 12 MPa
- All acceptable.

---

## 9. Output bearings and housing

**Bearings:** 61813 (rear, open or -2Z) and 61813-2RS1 (front, sealed), both 65 × 85 × 10. SKF lists C 11.9 kN and C0 9.65 kN [R21]; a distributor quotes 12.4 / 12.7 kN, so use the lower values.

**Arrangement:** back-to-back (O). The outer rings are clamped from outside, by the spacer behind the rear bearing and by the cover lip in front of the front bearing, with ring-2 between them as the spacer. The inner rings bear on the carrier-2 post faces on the cavity side.

**End play:** set at assembly to **0–0.01 mm** using a ground shim between ring-2 and the front outer ring (this is an adjusted arrangement [R22]). Rev 1.1's "CN, no preload, 0.15 mm float" is removed: on a 16 mm span it produces visible output wobble.

**Tilt check at L3:** spacing 21.0 mm. 50 / 0.021 = 2.38 kN, + 75 N radial = 2.46 kN per bearing, so **s₀ = 3.9**. The 6008 pair at 16 mm gives 3.5, and is longer and heavier.

**Housing:** one-piece 7075-T6.
- Motor pocket Ø94.5 (machined from the rear).
- Integral 3 mm partition.
- **Single straight Ø85 bore** from Z 42.5 to 81.5, machined in one setup. It takes ring-1, the spacer, the rear 61813 and ring-2, which makes them coaxial by construction.
- Bore tolerance: H7 in the ring zones; **K6** at the rear bearing seat. SKF says light-alloy housings need tighter fits [R23][R24].
- Wall ≥ 4 mm everywhere, except the motor pocket (2.75 mm).

**Ring centring when hot:** 7075 expands ≈ 12 µm/m/K more than steel, so on Ø85 at ΔT = 40 K the ring fit loosens by ≈ 0.04 mm. The dowels (ring-1 axial into the partition, ring-2 radial through the wall) keep the rings centred. Rings: Ø85 h6 in H7 (transition).

**Front cover (7075 or 6061):**
- Ø85 K6 seat for the front bearing; lip ID Ø80.
- Locates on a Ø96 h6 × 3 mm spigot on the housing front.
- 8 × M3 12.9 into the housing front face on Ø92–93 PCD, ≥ 6 mm thread engagement.
- The cover OD carries the hall homing sensor (Section 11).

**Motor mount plate joint:** no fastener hole may break into the Ø94.5 rotor pocket. Use radial screws, or axial screws placed where the pocket narrows behind the bell (measure first).

---

## 10. Output interface

- Face: Ø78 output flange, front face at Z 94.0, 1.0 mm proud of the cover.
- **6 × M5 tapped (steel inserts if 7075), 10 mm deep, on Ø52 PCD.**
- **Female pilot Ø40 H7 × 2.0 deep.** It sits inside the bolt circle and carries the shear and centring; the screws provide clamping.
- Screws: grade 10.9, 6 N·m. Friction capacity ≈ 140 N·m against 50 N·m. Bolt tension from the 50 N·m tilt is ≈ 0.64 kN against ≈ 6 kN preload.
- The Rev 1.1 pattern (6 × M6 on Ø63) does not fit inside the Ø65 bearing journal (the holes would break out). If an existing arm bracket uses Ø63, add a 6 mm adapter flange.
- Output runout ≤ 0.02 TIR; flatness ≤ 0.03.

---

## 11. Sensors

| Sensor | Spec |
|---|---|
| Motor encoder (required for FOC) | AS5047P on-axis on the rear shaft end. Ø6 × 2.5 diametric magnet in an **aluminium/brass holder** (ams: holder must not be ferromagnetic [R5][R6]) that spaces it ≥ 2 mm from the steel shaft end. Gap 1.0 (0.8–1.2). Magnet centred within ≤ 0.10 TIR (ams allows 0.5 mm). Acceptance: AGC mid-range, MAGH/MAGL flags clear across a full revolution |
| Output position, Rev 1.2 | Digital hall switch in the front cover lip + Ø3 × 2 magnet in the output-flange rim, used for ODrive homing [R25]. The motor encoder then gives output position through 30:1 |
| Output absolute, Rev 2 (not in this CAD) | On-axis is impossible because the axis is occupied by sun-2. Rev 2 needs an off-axis ring encoder on the carrier-2 OD |
| Winding temperature | NTC on the stator (Section 6) |

---

## 12. Controller settings (needed for validity of the design)

- `torque_constant = 0.0919`
- `current_lim ≤ 20 A` until the 50 N·m proof test passes. At 22 A the output would be 54.6 N·m, above the structural case.
- Continuous target 12.1 A (30 N·m). Characterize 15 A.
- Motor thermistor limits: derate from 80 °C, cut at 100 °C.
- Note: external impacts can still back-drive the output above 50 N·m. The current limit only caps self-generated torque.

---

## 13. Lubrication and sealing

- Gears: NLGI-2 EP lithium grease, ≈ 5 g total.
- Gearbox sealed at the front by the 61813-2RS1 and at the rear by the partition labyrinth around the sun-1 hub.
- No grease on the encoder magnet or PCB.

---

## 14. Prototype sequence

Teeth at m0.8 and m1.0 cannot be printed accurately with a 0.4 mm FDM nozzle. The tooth tip is thinner than two extrusion widths. The guidance is m ≥ 1.5 for FDM, with m < 1 recommended only for SLA or a fine nozzle [R26][R27], and a published study could not even measure FDM gears of m ≤ 1.5 because of deformation [R28]. So:

| Build | Gears | Housing / carriers | Allowed tests |
|---|---|---|---|
| P0 fit check | SLA tough resin, backlash 0.15–0.20 mm | PETG | Assembly order, phasing, interference, encoder gaps. No powered load |
| P1 functional | **Real steel gears, pins, HK0810, 61813s** | PA-CF (100% infill, bearing seats printed undersize and reamed) | Powered running, backlash, efficiency at low torque (≤ 10 N·m), thermal at low load |
| P2 metal | Steel gears per 7.2 | 7075 per this spec | All gates in Section 15 |

This is the same approach as SpryDrive (metal gears in a printed housing [R13]). It tests the real meshes from day one instead of plastic teeth that do not represent the metal ones.

---

## 15. Acceptance and test gates

| Gate | Criterion |
|---|---|
| Interference | Full 360° output rotation in CAD, all planets, no clashes; clearances per Section 5 |
| Manual rotation | Smooth through 2 output revolutions; no hard spots |
| Output backlash (metal) | ≤ 0.25° (low-force, bidirectional) |
| Output play | Radial ≤ 0.02 mm and axial ≤ 0.02 mm at the output face |
| Torque constant | Measured output torque vs Iq; update `torque_constant` |
| Efficiency | Measured; replaces 0.90 in the control model |
| 20 N·m hold | No abnormal heating or damage |
| 30 N·m continuous | 30 min hold at 25 ± 5 °C ambient, near-zero speed; winding ≤ 90 °C (thermistor); backlash growth ≤ 0.05° |
| Thermal resistance | Report winding-to-ambient K/W (target ≤ 2.5) |
| 50 N·m proof | Fixture-applied torque; no permanent set, tooth marks or bearing damage |
| L3 tilt proof | 50 N·m tilt + 150 N radial via fixture; output tilt deflection recorded; no permanent set |

---

## 16. What the CAD engineer must keep and what they own

**Fixed (needs a new revision to change):** ratio and stage order, all tooth data, bearing types (61813 pair, HK0810), floating carrier-1/sun-2 concept, back-to-back adjusted output bearings, one-piece straight-bore housing, sun-1 bolted to the rotor face, load cases, materials and heat-treatment classes, fits listed above, Ø100 max OD, ≤ 98 mm length.

**Owned by CAD:** post shapes, lightening pockets, screw positions and counts (within the stated sizes), labyrinth geometry, cover web shapes, connector/cable exit, thermistor routing, exact Z positions (±1 mm).

**Rules:**
1. No feature crosses a rotating/stationary boundary (check every Z-band against the radial zones in Section 5).
2. No fastener hole breaks into the rotor pocket or a bearing seat.
3. Every press-fit or bearing seat gets a 10–15° lead chamfer (HK) or the standard bearing chamfer.
4. Every joint that transmits torque or sets concentricity has a pilot or register; the screws only clamp.
5. Gears are true involutes from the Section 7.1 data, not sketched teeth.

**Deliverables:** parametric Fusion 360 assembly; drawings with fits, GD&T and heat treatment; interference report; mass report; STEP (assembly + parts); SLA/FDM print package for P0/P1.

**Reference model:** the geometry is defined once, in `build()` inside `cad/gen_actuator_3mf.py`. That build now reflects the Rev 1.3 changes. Two kernels use it:
- `cad/gen_actuator_occ.py` (OpenCascade via CadQuery; environment `D:\VAYN-CAD-env\venv`) builds exact B-rep solids, with true cylinders and tori and involute B-spline tooth flanks. It writes:
  - `cad/rev1_3/VAYN_Shoulder_Actuator_Rev1_3.step`: a named, coloured assembly. Open it in Fusion with File > Open; this is the file to edit.
  - `cad/rev1_3/VAYN_Shoulder_Actuator_Rev1_3_OCC.3mf`: meshes tessellated to 0.01 mm.
  - `cad/rev1_3/VAYN_Shoulder_Actuator_Rev1_3_OCC_STL_parts.zip`: one STL per part.
- `cad/gen_actuator_3mf.py` (manifold3d) builds the faster mesh-only version.

Both runs print the same checks: 113 parts, 0 interferences, gear mesh gaps of 0.023–0.024 mm, and ≈ 2.75 kg including the motor. Motor, PCB and purchased bearings are envelope models. Tapped holes are shown at thread major diameter. The motor hole patterns must be confirmed by measurement (Section 6).

---

## 17. Open items for the project owner

1. Confirm the arm's center-of-mass position and payload (Section 3.2). If the mass is tip-concentrated, 30 N·m continuous is not enough.
2. Set an actuator mass budget (this design ≈ 2.0–2.3 kg).
3. Decide whether absolute output position is required at power-up. If yes, it is a Rev 2 off-axis encoder.
4. Supply voltage. 24 V gives 72 rpm output; 48 V doubles the speed (check ODESC limits).

---

## Appendix A — Verification calculations

**A.1 Kinematics.** Stage 1: 18 + 2 × 36 = 90 ✓, i = 1 + 90/18 = 6 ✓, (18 + 90)/3 = 36 ✓. Stage 2: 18 + 2 × 27 = 72 ✓, i = 5 ✓, (18 + 72)/3 = 30 ✓. Total 30:1.

Planet adjacency gap at the tips: stage 1 is 21.6·√3 − 30.4 = 7.0 mm ✓; stage 2 is 22.5·√3 − 29.0 = 10.0 mm ✓.

Ring tip is outside the base circle (Ø67.66) in both stages ✓. 18T sun > 17T undercut limit ✓.

**A.2 Torque chain (η per stage 0.95), L2 50 N·m:**
- Stage-2 sun torque = 50 / (5 × 0.95) = 10.53 N·m
- Motor torque = 10.53 / (6 × 0.95) = 1.85 N·m
- Ring reactions: stage 2 = 39.5 N·m; stage 1 = 8.7 N·m

**A.3 Tooth loads and stresses** (per planet, K_γ = 1.2; contact stress with K_A·K_V·K_Hβ = 1.65; Z_E 189.8, Z_H 2.495, Z_ε 0.9):

| Case | Mesh | F_t/planet | Lewis σ_b | σ_H sun–planet | σ_H planet–ring |
|---|---|---|---|---|---|
| L1 30 N·m | Stage 1 | 62 N | 24 MPa | 438 MPa | 196 MPa |
| L1 30 N·m | Stage 2 | 281 N | 87 MPa | 883 MPa | 441 MPa |
| L2 50 N·m | Stage 1 | 103 N | 40 MPa | 566 MPa | 253 MPa |
| L2 50 N·m | Stage 2 | 468 N | 144 MPa | 1139 MPa | 570 MPa |

Allowables (ISO 6336-5 MQ) [R7]: carburized σHlim 1500 / σFlim 500 (core ≥ 30 HRC); nitriding steel 1250 / 420; through-hardened alloy nitrided 998 / 363.

**A.4 Planet bearings.** Pin load = 2·F_t.
- Stage 2 at L1: 561 N; at L2: 936 N
- Planet speed relative to carrier: (360 − 72) × 18/27 = 192 rpm
- L10 = (3800/P)^(10/3) × 10⁶ / (192 × 60) → 51,000 h (L1), 9,300 h (L2)

**A.5 Output bearings.** F = M_tilt / spacing.
- 61813 pair at 21 mm: 2.38 kN, s₀ = 9.65/2.46 = 3.9
- 6008 pair at 16 mm: 3.13 kN, s₀ = 11.0/3.13 = 3.5

**A.6 Backlash to output.** With sun-2 held, carrier-2 free angle = (j_sp + j_pr) / (2·a₂) = j / 22.5 rad. Stage 1 adds j / (21.6 × 5) rad. Total ≈ 3.08°/mm × j:

| j per mesh | Output backlash | Movement at 670 mm |
|---|---|---|
| 0.20 mm | 0.62° | 7.2 mm |
| 0.10 mm (Rev 1.1) | 0.31° | 3.6 mm |
| 0.07 mm | 0.22° | — |
| 0.05 mm | 0.15° | 1.8 mm |
| 0.03 mm | 0.09° | — |

**A.7 Motor coupling.** M3 12.9 at 1.2 N·m gives preload ≈ 2.0 kN.
- Single-screw split clamp on Ø6: T ≈ μ·(2 to π)·F·r = 1.8–2.8 N·m
- 4 × M3 on a rotor face at r 12.5: 4 × 2.0 kN × 0.15 × 0.0125 = 15 N·m
- Required: 1.85 N·m (L2), 2.02 N·m (22 A)

**A.8 Dowel shear, ring-2 at L2.** 39.5 / 0.0425 = 929 N over 2 × Ø4 = 37 MPa. Friction from the clamped stack alone also exceeds 150 N·m.

**A.9 Rev 1.1 collision proof (rear bearing).** Planets occupy Z 57.9–67.9, r 8.0–37.0. The 6008 occupies Z 64–79, r 20–34. Intersection: Z 64.0–67.9 × r 20–34, which is non-empty.

---

## References

- [R1] Technobotix — Eaglepower LA8308 KV90 specs (92 × 28.5, 336 g, 22 A, 0.186 Ω): https://www.technobotix.in/products/eagle-powor-la-8308-kv90-motor/1781252000000073016
- [R1b] Technobotix blog — LA8308 KV90 (6 mm shaft, ~40–45 A max): https://www.technobotix.in/blogs/post/eagle-power-la-8308-kv90-brushless-motor-%E2%80%93-unmatched-power-for-heavy-lift-drones
- [R2] HobbyRC BD — Eaglepower 8308 KV90 (36N40P, 22 A, 900 W): https://hobbyrcbd.com/product/eaglepower-8308/
- [R3] SKF 6008 product page (C 17.8 kN, C0 11 kN): https://www.skf.com/group/products/rolling-bearings/ball-bearings/deep-groove-ball-bearings/productid-6008
- [R4] Schaeffler — Drawn cup needle roller bearings (N6 steel / R6 Al housings; raceway h6, Ra 0.2, ≥ 670 HV): https://medias.schaeffler.no/en/knowledge-center/rolling-bearings/drawn-cup-needle-roller-bearings
- [R5] ams AS5047P adapter-board manual (6 × 2.5 magnet, 0.5–3 mm gap, holder not ferromagnetic): https://media.digikey.com/pdf/Data%20Sheets/Austriamicrosystems%20PDFs/AS5047P-TS_EK_AB.pdf
- [R6] ams AS5047P datasheet: https://look.ams-osram.com/m/d05ee39221f9857/original/AS5047P-DS000324.pdf
- [R7] ISO 6336-5:2016 (allowables; derived for case depth ≈ 0.15–0.2·mₙ): https://cdn.standards.iteh.ai/samples/55353/ab3cdac04a254a878b8bc9f2ad3a52b0/SIST-ISO-6336-5-2018.pdf
- [R8] Gear Technology — Optimum carburized case depth (0.15·mₙ; tip case limits): https://www.geartechnology.com/ext/resources/issues/0120x/case-depth.pdf
- [R9] Nippon Steel — High-strength nitriding steel for gears (ring gear carburizing distortion, internal teeth hard to re-machine): https://www.nipponsteel.com/en/tech/report/nssmc/pdf/116-03.pdf
- [R10] Gear Solutions — Carburizing vs nitriding (no quench transformation; small, uniform growth): https://gearsolutions.com/departments/hot-seat/hot-seat-jack-titus-3/
- [R11] NTN — Drawn cup needle roller bearings catalog (housing N6/N7): https://www.ntnglobal.com/en/products/catalog/pdf/2300E_04.pdf
- [R12] Anthrobotics WOLF actuator (Eaglepower 8318; "4 × M3 to secure sun gear to motor"; AS5047P): https://github.com/Anthrobotics/wolf-actuator
- [R13] SpryDrive (metal gears + 3D-printed housing; sun pressed into adapter plate; 0.13° backlash): https://github.com/bbokser/sprydrive
- [R14] ODrive documentation — torque_constant = 8.27/KV: https://docs.odriverobotics.com/v/latest/fibre_types/com_odriverobotics_ODrive.html
- [R15] ODrive community — LA8308 KV90 configured with torque_constant 0.09188: https://discourse.odriverobotics.com/t/motor-runs-once-then-never-again/8911
- [R16] ODrive documentation — thermistors: https://docs.odriverobotics.com/v/0.5.6/thermistors.html
- [R17] MDPI Machines — Planet load-sharing and phasing (float one member, not both): https://www.mdpi.com/2075-1702/10/8/634
- [R18] Caterpillar US 4092878 — Floating carrier retention (self-centring carrier, axial limits required): https://www.freepatentsonline.com/4092878.html
- [R19] INA HK0810 data (Cr 3.8 kN, C0r 3.95 kN): https://www.nodeshk.com/ina/needle-bearings/hk0810.html
- [R20] Schaeffler HK0810 sheet via TME: https://www.tme.eu/Document/becd9b92cceb0ed3c5184fe3e6c8c8a9/HK0810.pdf
- [R21] SKF 61813 product page (C 11.9 kN, C0 9.65 kN): https://www.skf.com/group/products/rolling-bearings/ball-bearings/deep-groove-ball-bearings/productid-61813
- [R22] SKF — Selecting preload (adjusted and spring-preloaded DGBB arrangements): https://www.skf.com/group/products/rolling-bearings/principles-of-rolling-bearing-selection/bearing-selection-process/bearing-execution/selecting-internal-clearance-or-preload/selecting-preload
- [R23] SKF — Selecting fits (thin-walled/other-material housings need tighter fits): https://www.skf.com/group/products/rolling-bearings/principles-of-rolling-bearing-selection/bearing-selection-process/bearing-interfaces/selecting-fits
- [R24] SKF — Radial location (light-alloy housings require tighter fit): https://www.skf.com/uk/products/plain-bearings/spherical-plain-bearings-rod-ends/principles/design-of-bearing-arrangements/radial-location
- [R25] ODrive documentation — endstops and homing: https://docs.odriverobotics.com/v/0.5.6/endstops.html
- [R26] meta-matic — Gear module for 3D printing (m ≥ 1.5 for 0.4 mm FDM): https://meta-matic.com/en/learn/gear-module/
- [R27] Sovol — 3D printing gears (m < 1.0 rounds off profiles on 0.4 mm nozzles): https://www.sovol3d.com/blogs/news/3d-printing-gears-that-actually-work-backlash-orientation-and-material-tips
- [R28] IOP J. Phys. Conf. Ser. — Shape deviation of printed gears (m 0.5–1.5 too deformed to measure): https://iopscience.iop.org/article/10.1088/1742-6596/3142/1/012008/pdf
