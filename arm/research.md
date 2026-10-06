# Arm: research

Status: elbow actuator CAD Rev 1.0 done ([`../elbow/parts.md`](../elbow/parts.md), [`../elbow/bom.md`](../elbow/bom.md)); arm structure CAD not started. Elbow research is in [`../elbow/research.md`](../elbow/research.md); shoulder actuator in [`../shoulder/parts.md`](../shoulder/parts.md).

## 1. Summary

| Item | Decision |
|---|---|
| Layout | Planar 2-DOF arm: shoulder pitch + elbow pitch, axes parallel; left and right mirrored |
| Height | Nominal 5'3" (160 cm), loads checked at 5'5" (165.1 cm) |
| Arm length | 70.4 cm nominal (shoulder axis to fingertip), up to 72.6 cm at 165 cm |
| Elbow axis | 29.8 cm from the shoulder axis (nominal) |
| Shoulder joint | L-bracket hub on a 5–6 mm 6061 aluminium adapter plate |
| Elbow joint | Clevis: actuator on one side, passive pin + bearing on the other |
| Material | ASA structure; PLA for dummy hand, fit checks and the elbow cam/carrier; PET-CF for the elbow cycloid discs |
| Mass today | about 1.18 kg per arm, excluding the shoulder actuator (elbow actuator 0.514 kg from CAD) |
| Shoulder | No change needed: 1.9–2.0× margin at stage 2 |

## 2. Geometry from anthropometry

Datum: all lengths are from the shoulder-axis centreline, because the arm hangs at right angles to that axis.

Segment ratios (Drillis–Contini): upper arm 0.186 H, forearm 0.146 H, hand 0.108 H, total 0.44 H ([PMC11398373](https://pmc.ncbi.nlm.nih.gov/articles/PMC11398373/), [O&P Library 1964](https://oandplibrary.org/al/pdf/1964_01_044.pdf)).

| Height | Upper arm (elbow axis) | Forearm (to wrist) | Hand | Total arm |
|---|---|---|---|---|
| 152 cm (old 67 cm arm) | 28.3 | 22.2 | 16.4 | 66.9 cm |
| 5'2" / 157.5 cm | 29.3 | 23.0 | 17.0 | 69.3 cm |
| **5'3" / 160 cm (nominal)** | **29.8** | **23.4** | **17.3** | **70.4 cm** |
| 5'4" / 162.6 cm | 30.2 | 23.7 | 17.6 | 71.5 cm |
| 5'5" / 165.1 cm (load check) | 30.7 | 24.1 | 17.8 | 72.6 cm |

Change from the original plan: the arm grows from 67 cm to 70.4 cm. The shoulder actuator absorbs this without redesign (section 8).

## 3. Reference arms

| Arm | What we borrow |
|---|---|
| InMoov | 30% infill, 2.5 mm walls; forearm + hand about 750 g ([InMoov bicep](https://inmoov.fr/bicep/), [InMoov hand](https://inmoov.fr/hand-and-forarm/)) |
| Reachy 2023 | 662 mm arm, 1.67 kg, printed parts, 500 g payload ([specs](https://pollen-robotics.github.io/reachy-2023-docs/advanced/specifications/arm-specs/)) |
| Berkeley Humanoid Lite | PLA FDM body, through-bolts and brass standoffs, actuator directly at each joint, printed cycloids ([paper](https://arxiv.org/html/2504.17249v1), [docs](https://berkeley-humanoid-lite.gitbook.io/docs/in-depth-contents/motor-characterization)) |
| Berkeley Blue | 0.7 m reach, 2 kg payload on low-ratio backdrivable drives ([IEEE Spectrum](https://spectrum.ieee.org/uc-berkeley-blue-low-cost-force-controlled-robot-arm), [Gealy et al. 2019](https://arxiv.org/abs/1904.03815)) |
| K-Bot / Unitree G1 | Small elbow actuators (about 5 N·m rated) suffice for 2–3 kg arms ([Unitree G1](https://support.unitree.com/home/en/G1_developer), [Robstride](https://openelab.io/products/robstride-10p-qdd-joint-actuator)) |
| UMA v0 | Exposed structure first, human-like shell later ([French Tech Journal](https://www.frenchtechjournal.com/uma-shows-its-hand-remi-cadene-unveils-a-humanoid-robot-designed-to-earn-europes-trust/)) |

## 4. Joint concepts

### 4.1 Shoulder: L-bracket hub

A yoke around the shoulder actuator is not possible because its rear plate is bolted to the torso. The stack is:

1. Shoulder output flange: 6× M5 on a 52 mm circle, Ø40 H7 pilot, Ø78 flange ([`../shoulder/parts.md`](../shoulder/parts.md), part 42).
2. 5–6 mm laser-cut 6061 aluminium adapter plate, so the M5 steel bolts clamp metal (printed plastic under bolts creeps and loses preload).
3. Printed upper-arm hub bolted to the adapter with more, smaller bolts spread over a larger area.

The arm centre line sits about 50 mm outboard of the flange face. The tilt load this adds is about 1 N·m, against the 50 N·m tilt proof case in [`../shoulder/cad/calc.txt`](../shoulder/cad/calc.txt).

### 4.2 Elbow: clevis

The elbow actuator output drives one cheek of the forearm. A passive pin with a bearing supports the other cheek. This keeps bending loads off the printed gearbox and stiffens the joint.

### 4.3 Wrist interface

A standard flange at the forearm end: 4× M3 on a Ø30 circle, Ø20 pilot. The dummy hand, then the gripper, then the wrist bolt straight on.

### 4.4 Left and right

Printed parts are mirrored; actuators are identical. Joint direction and encoder sign are set in software.

### 4.5 Cables

Service loop at the shoulder; external slack loop at the elbow (no hollow bore). Cables run inside the clamshell shells between joints.

## 5. Material and print rules

| Material | Density | Stiffness | Softening (HDT) | Use |
|---|---|---|---|---|
| **ASA** | 1.05 g/cm³ | 2.45 GPa | 92–100 °C | Structure ([Bambu ASA TDS](https://wiki.bambulab.com/filament-acc/abs-asa-pc/6eaf4c432d1d4014a1975e55a55ed00b.pdf), [Bambu ASA store](https://bambu-lab-global.myshopify.com/products/asa-filament)) |
| PETG HF | 1.28 g/cm³ | 1.81 GPa | 62–69 °C | Fallback if ASA warps ([Bambu PETG HF TDS](https://store.bblcdn.com/3a230e260a3a47c2b0db0156e07eef91.pdf)) |
| PLA | 1.24 g/cm³ | 2.58 GPa | 54–57 °C | Dummy hand, fit checks, elbow cam, cage rear ring and output carrier ([Bambu PLA TDS](https://wiki.bambulab.com/filament-acc/abs-asa-pc/bambu_pla_basic_technical_data_sheet.pdf), [Bambu PLA store](https://bambulab-us.myshopify.com/products/pla-basic-filament)) |
| PET-CF | 1.29 g/cm³ | 4.73 GPa | 205 °C | Elbow cycloid discs only. PLA fails the disc contact check; needs a hardened 0.6 nozzle and annealing ([Bambu PET-CF TDS](https://wiki.bambulab.com/filament-acc/petcf-ppacf/07689de83afd4cc480f136c7697e6de3.pdf), [Bambu PET-CF store](https://eu.store.bambulab.com/products/pet-cf), [`../elbow/research.md`](../elbow/research.md) §7.3) |

ASA is lighter, stiffer and more heat-tolerant than PETG; the printer is enclosed, so ASA is practical. PETG adds about 22% to printed part mass.

Print rules:
- Hollow clamshell shells (front and back halves), 4–5 walls.
- 15–25% gyroid infill only at bosses and bolt areas.
- Long axis flat on the bed, so layer lines run along the arm and bending does not peel layers apart.
- M3/M4 brass heat-set inserts for all repeat-assembly joints.
- Elliptical, tapered sections for a human-like bicep and forearm; cosmetic covers later.

## 6. Mass budget (one arm, excluding shoulder actuator)

| Part | Mass |
|---|---|
| Upper arm shell + hub + aluminium adapter | about 0.30 kg |
| Elbow actuator (MN5008 + 20:1 cycloid) | 0.514 kg (CAD; the research estimate was 0.40) |
| Forearm shell | about 0.14 kg |
| Wiring | about 0.08 kg |
| Dummy hand (PLA, printed light) | about 0.15 kg |
| **Total today** | **about 1.18 kg** |

Future stage masses (added at the wrist): gripper about 0.25 kg, 2-DOF wrist about 0.35 kg, 5-finger hand about 0.55 kg, payload 0.5 kg.

## 7. End-effector roadmap

1. Dummy hand (now).
2. 2- or 3-finger gripper.
3. 2-DOF wrist.
4. 4- or 5-finger hand.

The elbow is sized for stage 2 (gripper + wrist + 0.5 kg). Stage 3 needs about 6.3 N·m continuous at 165 cm; if the printed elbow proves weak there, the elbow actuator is replaced.

## 8. Shoulder re-check

Shoulder rating: 30 N·m continuous, 50 N·m proof, 50 N·m tilt proof ([`../shoulder/parts.md`](../shoulder/parts.md), [`../shoulder/cad/calc.txt`](../shoulder/cad/calc.txt)). Arm horizontal, same 180°/s in 0.25 s acceleration (12.57 rad/s²). The elbow actuator mass is the CAD value of 0.514 kg; it was 0.40 kg in the research estimate. The extra 0.114 kg at the elbow axis adds 0.33–0.34 N·m of gravity and 0.12–0.14 N·m of inertia torque.

| Case | Gravity | Gravity + acceleration | Margin vs 30 N·m |
|---|---|---|---|
| 157.5 cm, dummy hand (now) | 3.6 N·m | 5.3 N·m | 5.7× |
| 157.5 cm, stage 2 | 9.0 N·m | 14.9 N·m | 2.0× |
| **160 cm, stage 2 (nominal)** | **9.2 N·m** | **15.2 N·m** | **2.0×** |
| 165.1 cm, stage 2 (worst) | 9.5 N·m | 15.8 N·m | 1.9× |

Gravity torque grows with arm length; inertia grows with length squared, which is why the total rises faster. Even at 165 cm the shoulder runs at about half its continuous rating.

Bearing loads from the arm are about 20–30 N radial and about 1 N·m tilt, against the 974 N, 2,445 N and 50 N·m cases already designed for in `calc.txt`. **No shoulder change.**

Note: VAYN vault notes list the shoulder as 80:1 in one place and 20:1 in another; the finalized repo design is 30:1 and is treated as correct.

## 9. Open decisions

1. Approve the L-bracket hub with aluminium adapter plate at the shoulder.
2. Approve the clevis with passive pin at the elbow.
3. Approve ASA for structure.
4. Team approval of the motor plan (LA8308 on both shoulders, MN5008 KV170 on both elbows).
5. Fix the wrist flange before the gripper design starts.
6. Correct the shoulder ratio in the VAYN vault notes to 30:1.
7. Elbow interfaces for the arm CAD (from [`../elbow/parts.md`](../elbow/parts.md)):
   - The forearm clamps the 61807 inner ring (hub recessed 0.4 mm), with the plate inside Ø38 and the 2 × Ø3 hub dowels fitted (they carry the torque).
   - The upper arm mounts on the Ø80 front flange.
   - The flange screws must be lengthened if the cheek sits under their heads.
