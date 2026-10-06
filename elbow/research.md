# Elbow actuator: research

Status: CAD Rev 1.0 done. The part specification is in [`parts.md`](parts.md), ordering and print in [`bom.md`](bom.md), and the model and calc in `cad/`. Values below marked "CAD" come from `cad/calc.txt` and replace the earlier estimates. Arm geometry, structure and the shoulder re-check are in [`../arm/research.md`](../arm/research.md).

## 1. Summary

| Item | Decision |
|---|---|
| Joint | Elbow pitch, axis parallel to the shoulder pitch axis (planar 2-DOF arm) |
| Placement | On the joint, axis 29.8 cm from the shoulder axis (nominal 160 cm humanoid) |
| Rating | 4.9 N·m continuous, 8.2 N·m proof (sized at 165 cm, stage 2 load) |
| Motor | T-Motor MN5008 KV170 (128 g, Ø55.6 × 32 mm), bought in India |
| Gearbox | Single-stage printed cycloid, 20:1 (two 20-lobe PET-CF discs, 21 steel Ø5 ring pins on Ø60) |
| Envelope | Ø80 flange / Ø69 body × 78.3 mm, 0.508 kg (CAD) |
| Driver | ODESC 3.6, axis 1 (shoulder on axis 0), 24 V |
| Encoders | AS5047P motor side (ODESC), AS5047P output side (sensor MCU) |
| Protection | Backdrivable gearbox, 10 A current limit, cushioned hard stops, software limits |

For comparison the shoulder is Ø100 × 95.5 mm, 2.76 kg, 30 N·m continuous ([`../shoulder/parts.md`](../shoulder/parts.md)). The elbow is about 18% of its mass.

## 2. Requirements

- Prototype is 1 shoulder DOF + 1 elbow DOF per arm, mirrored left and right.
- Holding time is minutes. No payload until a working hand exists.
- End-effector roadmap: dummy hand (now) -> 2/3-finger gripper -> 2-DOF wrist -> 4/5-finger hand.
- Elbow sized for stage 2 (gripper + wrist + 0.5 kg). If stage 3 proves too much, the elbow actuator is swapped, not the arm.
- Height: nominal 5'3" (160 cm), loads checked at 5'5" (165.1 cm).
- Driver must be the ODESC 3.6 already planned for the arm (VAYN Phase-1 electronics notes).

## 3. Loads

Model: forearm horizontal (worst gravity case), centre-of-mass positions from Winter's tables ([Winter](https://courses.grainger.illinois.edu/me481/sp2021/Anthro-Winter.pdf), [Kinovea copy](https://www.kinovea.org/tools/references/2009%20-%20Winter%20-%20Table%204.1%20-%20Anthropometric%20data.pdf)). Acceleration 0 -> 180°/s in 0.25 s (α = 12.6 rad/s²). Proof = 1.67 × continuous, the same factor used on the shoulder.

Masses used: printed forearm 0.14 kg (scaled with length), wiring 0.05 kg, dummy hand 0.15 kg, gripper 0.25 kg, 2-DOF wrist 0.35 kg, 5-finger hand 0.55 kg, payload 0.5 kg.

| Stage | Static (N·m) | Continuous (N·m) | Proof (N·m) | Load inertia (kg·m²) |
|---|---|---|---|---|
| 160 cm, S0 dummy hand (now) | 0.62 | 0.94 | 1.57 | 0.025 |
| 160 cm, S1 gripper + 0.5 kg | 2.58 | 3.73 | 6.23 | 0.092 |
| 160 cm, S2 gripper + wrist + 0.5 kg | 3.38 | 4.77 | 7.97 | 0.111 |
| 160 cm, S3 hand + wrist + 0.5 kg | 4.33 | 6.11 | 10.21 | 0.142 |
| **165.1 cm, S2 (rating case)** | **3.47** | **4.93** | **8.23** | **0.116** |
| 165.1 cm, S3 | 4.44 | 6.31 | 10.53 | 0.148 |

The rating (4.9 / 8.2 N·m) is in the same class as K-Scale K-Bot's elbow (Robstride RS00: 5 N·m rated, 14 N·m peak; [Robstride](https://openelab.io/products/robstride-10p-qdd-joint-actuator), [K-Scale](https://www.youtube.com/watch?v=qIEj6IRXJt4)).

## 4. Motion targets

| Item | Value | Basis |
|---|---|---|
| Software range | 0–135° flexion | Daily tasks use 30–130° ([Morrey 1981](https://pubmed.ncbi.nlm.nih.gov/7240327/), [PMC6555111](https://pmc.ncbi.nlm.nih.gov/articles/PMC6555111/)) |
| Hard stops | −5° and 140°, elastomer cushioned | Normal maximum flexion is 143–148° ([PMC6555111](https://pmc.ncbi.nlm.nih.gov/articles/PMC6555111/), [Morrey 1981](https://pubmed.ncbi.nlm.nih.gov/7240327/)) |
| Speed limit | 180°/s (software) | 1.5 × healthy reaching speed of 122°/s ([Alt Murphy 2011](https://sage.cnpereading.com/doi/10.1177/1545968310370748), [Berkeley Humanoid Lite](https://arxiv.org/html/2504.17249v1)) |
| Acceleration | 0.25 s to full speed | Prototype choice |

## 5. Placement: on the joint

Putting the motor in the upper arm and driving the elbow by belt or cable would cut the shoulder load by only 1.0 N·m and 0.037 kg·m², out of about 14.7 N·m total at 160 cm. That does not justify belts, tensioners and the extra compliance. Remote drive helps when the shoulder is short of torque ([flexible-shaft study](https://exa.ai/library/publication/2ylg8t5v1l2), [belt-driven arm](https://exa.ai/library/publication/ck28gynkr1z)); ours has about 2× margin (see the arm doc).

## 6. Motor selection (India availability)

Kt is taken as 8.27 / KV N·m/A, the same convention as the shoulder (`torque_constant 0.0919` for the LA8308 KV90 in [`../shoulder/bom.md`](../shoulder/bom.md)). Gearbox efficiency 0.85. Supply 24 V (6S).

### 6.1 Candidates

| Motor | Mass / size | India price and lead time | Notes | Verdict |
|---|---|---|---|---|
| **T-Motor MN5008 KV170** | 128 g, Ø55.6 × 32, 24N28P, 6 mm shaft, 270 mΩ phase-to-phase, 15 A peak (180 s) ([T-Motor](https://store.tmotor.com/product/mn5008-kv170-motor-antigravity-type.html), [KJ Retail](https://www.kjretail.ca/products/t-motor-mn5008-antigravity-uav-motor)) | ₹8,413, ships in 25 days ([Robokits](https://robokits.co.in/multirotor-spare-parts/tiger-motor-esc-and-propeller/t-motor-motor/antigravity-type/t-motor-antigravity-mn5008-170kv)); ₹9,499 ([UAV Marketplace](https://www.uavmarketplace.in/products/t-motors-mn5008-kv170/895789000017087249)); ₹10,319, dispatch 3–5 days ([The Engineer Store](https://www.theengineerstore.in/products/t-motor-antigravity-mn5008-kv170)) | Lowest KV in stock in India in this size; 14 pole pairs gives smooth low-speed torque | **Chosen** |
| MAD 5010 EEE 110KV / IPE 150KV | 162–181 g, Ø56 | No Indian seller found; $84–88 import ([MAD](https://mad-motor.com/products/mad-components-5010-eee), [UnmannedRC](https://unmannedrc.com/products/5010-ipe-v3-0-brushless-motor)) | Electrically good, supply risk | Reject (import) |
| Tarot 5008 340KV | 168 g, Ø58.5 × 35, 12N14P | ₹5,799, 3–4 days ([Fioparts](https://fioparts.com/products/tarot-5008-340kv-brushless-motor-tl96020)); ₹6,200 + GST ([Robosync](https://robosynckits.in/product/6784/)) | Needs 30:1 and still 7.8 A continuous; 7 pole pairs, more cogging | Backup |
| Tarot 4114 320KV | 148 g, Ø46 | ₹4,989 ([Indian Robo Store](https://indianrobostore.com/product/tarot-tl100b08-02-4114-320kv-6s-multirotor-brushless-motor)); ₹5,554 ([Moglix](https://www.moglix.com/tarot-4114-320rpm-320kv-22-poles-brushless-motor/mp/msnvk13mqjgj91)) | Same current problem as Tarot 5008 | Reject |
| 5010 360KV (generic) | 92–112 g, Ø50 | about ₹1,600 ([Robu](https://oldwp.robu.in/product/5010-360kv-high-torque-brushless-motors-multicopter-quadcopter-multi-axis-aircraft/)) | 12–17 A continuous at our torque, overheats | Reject |
| SteadyWin GIM6010-8 | 370 g, Ø80 × 29.5, 8:1 steel, 5 / 11 N·m | No Indian seller found; $70–118 import, 12–26 days ([SteadyWin](https://steadywin-motor.com/products/built-in-star-gear-motor-motor-robot-joint-driver-actuator-controller-motor), [RobotDoo](https://robotdoo.com/products/steadywin-gim6010-8-gearmotor)) | Ready unit; encoder fit to ODESC unverified | Import fallback |
| EaglePower LA8308 KV90 | 336 g, Ø92 × 28.5 | ₹10,999 ([Technobotix](https://www.technobotix.in/products/eagle-powor-la-8308-kv90-motor/1781252000000073016), [`../shoulder/bom.md`](../shoulder/bom.md)) | Too wide and heavy for an elbow | Use on shoulders |

KV rule of thumb for this joint at 24 V: KV 150–170 works at about 20:1. Above about KV 300 the gearbox must go to about 30:1, which raises reflected inertia (worse backdrivability) and current.

### 6.2 Ratio trade (MN5008 KV170, rating case 165 cm S2)

Copper loss P = 1.5 · I² · R_phase, with R_phase = 0.270 / 2 = 0.135 Ω. Rotor inertia about 4 × 10⁻⁵ kg·m² is an estimate (not published).

| Ratio | Hold current / heat | Continuous current / heat | Proof current | No-load output speed | Reflected inertia (est.) |
|---|---|---|---|---|---|
| 15:1 | 5.5 A / 6.2 W | 7.8 A / 12.4 W | 13.1 A | 272 rpm | 0.009 kg·m² |
| 18:1 | 4.6 A / 4.3 W | 6.5 A / 8.6 W | 10.9 A | 227 rpm | 0.013 kg·m² |
| **20:1** | **4.2 A / 3.5 W** | **5.9 A / 7.0 W** | **9.8 A** | **204 rpm (1,220°/s)** | **0.016 kg·m²** |
| 25:1 | 3.3 A / 2.2 W | 4.7 A / 4.5 W | 7.8 A | 163 rpm | 0.026 kg·m² |

**Choice: 20:1.**
- Proof current 9.8 A stays under the motor's 15 A peak, with margin.
- Holding at stage 2 costs about 3.5 W; today with the dummy hand about 0.75 A and 0.1 W.
- 1,220°/s no-load is about 7 × the 180°/s target, so voltage is never the limit.
- Reflected motor inertia is about 14% of the stage-2 load inertia, so the joint should stay backdrivable (to be measured).
- 25:1 halves the heat again but needs 25 lobes, which is finer than we want to print at this size.

## 7. Gearbox

### 7.1 Type comparison

| Type | Pros | Cons | Verdict |
|---|---|---|---|
| Steel planetary (like shoulder) | Durable, compact | CNC + heat treat cost and lead time; module 0.8–1 teeth cannot be FDM printed ([`../shoulder/bom.md`](../shoulder/bom.md)) | Not for this phase |
| Printed planetary | Cheap | Small teeth print inaccurately; large teeth make it bulky; 20:1 needs two stages | Reject |
| **Printed cycloid** | Many lobes share load, coarse printable shapes, 10–30:1 in one stage | Eccentric vibration (fixed by two discs at 180°), opposite output direction | **Chosen** |

Printed cycloids are proven at this scale: Berkeley Humanoid Lite uses PLA cycloids at 15:1 with a 60-hour durability test and backlash ≤ 0.023 rad ([paper](https://arxiv.org/html/2504.17249v1), [docs](https://berkeley-humanoid-lite.gitbook.io/docs/in-depth-contents/motor-characterization)).

### 7.2 Geometry (20:1, CAD)

| Parameter | Value |
|---|---|
| Ratio | 20:1, output turns opposite to the motor (set direction in ODESC) |
| Discs | 2 discs, 20 lobes, 9 mm thick, phased 180° (disc B outline turned −9°) to cancel imbalance |
| Ring pins | 21 × Ø5 × 30 ISO 8734 hardened dowels on a Ø60 circle |
| Eccentricity | 1.0 mm |
| Curtate ratio | λ = e · Zp / Rp = 1.0 × 21 / 30 = 0.70 (usual window 0.5–0.8) |
| Profile relief | 0.08 mm equidistant (radial play on the pins) |
| Output | 6 × Ø5 steel pins on Ø40 straight in Ø7.2 disc holes (Ø pin + 2e + 2 × 0.10); no rollers |
| Disc bearings | 6704-2RS (20 × 27 × 4) on two eccentric cam journals |
| Cam support | The cam is carried by the output cage (6703 in the rear ring, 6701 in the pin plate) and driven by 4 dog screws in the rotor with 0.2 radial play, so the motor bearings carry no gearbox load. **Chosen during CAD without the user's confirmation (the question form failed twice)** |
| Output bearing | One 61807-2RS1 (35 × 47 × 7); the arm clevis carries the tilt |
| Disc material | Bambu PET-CF, annealed 80 °C for 12 h. PLA fails the contact check (§7.3) |
| Backlash (CAD) | 21.3 mrad = 1.22° (Berkeley Humanoid Lite ≤ 23 mrad) |

The CAD replaced the research geometry (Ø4 pins on Ø52, e 0.9, λ 0.73, 6806 bearings) with the values above. All checks in §7.3 and `cad/calc.txt` use the CAD geometry. The housing wall outside the pins is 2.0 mm.

### 7.3 Contact stress (CAD, `cad/calc.txt` §3)

- Basis: Hertz line contact of a steel pin on the printed lobe, rigid-disc load share, 55% of the output torque on one disc. First yield p0 = 1.67 Y (Tresca, τmax = 0.30 p0 at 0.78 a) ([maschinenbaurechner](https://maschinenbaurechner.de/en/hertzian-contact-stress), [Experimentální mechanika 2016](http://www.experimentalni-mechanika.cz/cs/konference/konference/2016.html?download=610%3Abearing-race-and-roller-line-contact-analysis-in-2d)). The proof limit is p0 at first yield; the continuous limit is that value / 1.5.
- Y is the data-sheet X-Y tensile strength, mean − 1 SD.
  - PLA Basic: 35 ± 4 → 31 MPa ([Bambu PLA TDS](https://wiki.bambulab.com/filament-acc/abs-asa-pc/bambu_pla_basic_technical_data_sheet.pdf), [copy](https://cdn.shopifycdn.net/s/files/1/0584/7236/6216/files/Bambu_PLA_Basic_Technical_Data_Sheet.pdf)).
  - PET-CF: 74 ± 6 → 68 MPa ([Bambu PET-CF TDS](https://wiki.bambulab.com/filament-acc/petcf-ppacf/07689de83afd4cc480f136c7697e6de3.pdf), [store](https://eu.store.bambulab.com/products/pet-cf)).
- PLA discs: 46 MPa continuous against a 34.5 MPa limit. **Fails**, so the discs changed to PET-CF.
- PET-CF discs: 61.8 MPa continuous (limit 75.7) and 79.8 MPa proof (limit 113.6), peak pin force 45 N, 10 or more pins loaded. If one disc carries 75% after a print error: 72.2 MPa continuous, still within the limit.
- The earlier 45–50 MPa estimate used Ø4 pins on Ø52 and no data-sheet yield value.

## 8. Size and mass (CAD)

| Group | Mass |
|---|---|
| MN5008 KV170 | 128 g |
| Ring pins (21) and output pins (6), steel | 124.2 g |
| Housing (with motor-zone vents), lid, retainer, cover (ASA) | 99.7 g |
| Cam, rear ring, carrier (PLA) | 41.3 g |
| Two discs (PET-CF) | 37.2 g |
| Bearings (61807, 2 × 6704, 6703, 6701) | 44.9 g |
| Clamp ring, magnet cup, magnet, inserts, fasteners, dowels | 32.8 g |
| **Total** | **508 g** (printed parts counted 100% solid) |

Envelope Ø80 flange / Ø69 body × 78.3 mm, longer and heavier than the 65 mm / 0.38–0.43 kg estimate: the 9 mm PET-CF discs, the Ø60 pin circle and the cage bearings set the size. No hollow bore: the output magnet sits on the axis. Effect on the shoulder: [`../arm/research.md`](../arm/research.md) §8.

## 9. Electronics, sensing, protection

- **Driver:** ODESC 3.6 axis 1, `pole_pairs 14`, `torque_constant 8.27 / 170 = 0.0486`, `current_lim 10 A` (about 8.3 N·m at the output, which acts as a torque fuse near the proof value).
- **Motor encoder:** AS5047P on the motor axis for commutation. In CAD the magnet cup is bonded to the rotating shaft-end retainer on the motor back, 1.0 mm from the IC. The mount pattern is taken from the official T-Motor STEP (4 × M3 on Ø25 in the base, 4 × M3 on Ø12 in the rotor top).
- **Output encoder:** AS5047P read by the sensor MCU. The joint turns less than 360°, so it gives absolute angle at power-up with no homing (VAYN Phase-1 dual-encoder plan).
- **Cables:** outside the joint with a slack loop covering 145° of travel.
- **Thermal:** 7 W continuous at the stage-2 rating and 3.5 W hold. MN5008 is rated 171 W continuous with propeller airflow ([T-Motor](https://store.tmotor.com/product/mn5008-kv170-motor-antigravity-type.html), [ISWFA](https://www.iswfa.com/drone-propulsion-power/multirotor-motors/t-motor-mn5008-kv170/)); we have no airflow, so log winding temperature during the first holding tests.
- **Fall and overload (prototype):** backdrivable gearbox, current limit, cushioned hard stops, software limits, printed forearm as the crumple zone, no slip clutch. First tests on the tethered rig (safe-state option D in VAYN notes).
- **Power loss:** with the dummy hand the forearm falls under only about 0.6 N·m; the cushioned stop absorbs it.

## 10. Open items

1. Team approval of the motor plan: LA8308 on both shoulders, two MN5008 KV170 for the elbows (₹16.8k–20.6k for two).
2. MN5008 pattern taken from the vendor STEP; measure the rotor-top and base thread depths on arrival (model 8.5 / 7.0).
3. Measure rotor inertia and backdrive torque on the built actuator (target breakaway under about 0.3 N·m at the output).
4. Contact stress passes in calc on annealed PET-CF (§7.3). Still to do: a printed pin-and-disc test after annealing, and confirming the cage-supported cam choice (§7.2).
5. Test whether the ODESC clone shorts the phases when idle (dynamic braking); not confirmed from documentation.
6. Backup if MN5008 is out of stock: Tarot 5008 340KV with a 30:1 cycloid, or import GIM6010-8.
