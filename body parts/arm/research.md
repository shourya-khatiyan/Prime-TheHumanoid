# Arm: research

Status: CAD Rev 2 done (twin-plate structure, direct-drive LA8308 elbow). Part specification in [`parts.md`](parts.md), ordering, print and assembly in [`arm_bom.md`](arm_bom.md), model and checks in `cad/`. The elbow decision record (why direct drive, what else was evaluated) is [`../elbow/research.md`](../elbow/research.md).

## 1. Summary

| Item | Decision |
|---|---|
| Layout | Planar 2-DOF arm: shoulder pitch + elbow pitch, axes parallel; left and right mirrored |
| Height | Nominal 5'3" (160 cm), lengths checked at 5'5" (165.1 cm) |
| Structure | UMA Northstar style: each link is two shaped plates joined by spacer bars; the elbow motor is clamped between the upper-arm plates |
| Elbow | EaglePower LA8308 KV90, direct drive (no gearbox), dummy hand only |
| Material | Bambu PETG HF, all printed parts; resin only for the magnet holder |
| Mass | 897 g per arm including the elbow motor (Rev 0 with the cycloid elbow: 1.414 kg) |
| Shoulder | Actuator unchanged; output limited to 10 N·m by the printed arm (demand 4.6 N·m) |

## 2. Geometry from anthropometry

Datum: all lengths are from the shoulder-axis centreline.

Segment ratios (Drillis–Contini): upper arm 0.186 H, forearm 0.146 H, hand 0.108 H ([PMC11398373](https://pmc.ncbi.nlm.nih.gov/articles/PMC11398373/), [O&P Library 1964](https://oandplibrary.org/al/pdf/1964_01_044.pdf)). At 160 cm: upper arm 298 mm, forearm 234 mm, hand 173 mm. ANSUR II men scaled to 160 cm give 305 / 243 / 176 mm, which agrees ([ANSUR II data](https://tools.openlab.psu.edu/publicData/ANSUR_II_MALE_Public.csv), [ANSUR explorer](https://ergoassessment.cam/ansur-2-data-explorer/)).

Girths (male build, chosen for the look):

| Segment | Target | Basis |
|---|---|---|
| Upper arm at the biceps | 275–280 mm round, about 95 × 80 mm | Indian adult men mean MUAC 26.9 cm ([NFHS-4, PMC](https://pmc.ncbi.nlm.nih.gov/articles/PMC11145931/), [Cureus](https://www.cureus.com/articles/246327-comparing-mid-upper-arm-circumference-with-body-mass-index-for-assessing-nutritional-status-in-indian-adults-evidence-from-the-national-family-health-survey-2015-16-nfhs-4)) |
| Elbow | about 68 mm wide | humerus bi-epicondylar width 4.9–5.6 cm ([IJSR](https://worldwidejournals.com/international-journal-of-scientific-research-(IJSR)/article/evaluation-of-sex-in-humerus/ODE3OQ==), [IJMRHS](https://www.ijmrhs.com/medical-research/a-study-on-sexual-dimorphism-of-the-humerus-in-tamilnadu-region.pdf)) plus tissue |
| Forearm, widest | about 0.86 × biceps girth | ANSUR II flexed forearm / flexed biceps |
| Wrist | 155–160 mm round | ANSUR II scaled 161 mm; Haryana men median 165 mm ([Haryana hand study](https://www.researchgate.net/publication/271520706_Analysis_of_Hand_Anthropometric_Dimensions_of_Male_Industrial_Workers_of_Haryana_State)) |
| Hand breadth | 80–85 mm | ANSUR II scaled 80 mm; Haryana knuckle breadth median 85 mm |

Order of girth: shoulder (deltoid) > upper arm > elbow ≈ forearm maximum > hand > wrist. The Rev 2 skeleton is exposed for now (elbow mechanism 78.6 mm wide after the fit fix, forearm 62.5 mm); covers can clip onto the spacer bars later.

## 3. Reference arms

| Arm | What we borrow |
|---|---|
| UMA Northstar (2026) | Two shaped plates + spacer bars per link, actuator bodies clamped between plates, exposed structure, cables outside ([Humanoids Daily](https://www.humanoidsdaily.com/companies/uma), [humanoidversus](https://humanoidversus.com/robots/uma-northstar)). Arm specs are not published; the layout is read from photos |
| OpenArm v1 | 7-DOF human-scale arm on QDD motors, open fabrication data ([OpenArmory](https://openarmory.dev/hw/openarm/), [growbotics](https://robotics.growbotics.ai/projects/hardware/openarm)) |
| Berkeley Humanoid Lite | PLA body, actuators at each joint ([paper](https://arxiv.org/html/2504.17249v1), [docs](https://berkeley-humanoid-lite.gitbook.io/docs/in-depth-contents/motor-characterization)) |
| Barrett WAM / LIMS | Remote elbow motors with cable drives; evaluated and not used ([Barrett](https://web.barrett.com/support/WAM_Documentation/WAM_UserManual_AH-00.pdf), [LIMS](https://www.cs.cmu.edu/~cga/c/0749.pdf)) |

## 4. Structure

- Upper arm: two PETG plates (inner 7 mm, Y 0–7; outer 5 mm, Y 50.2–55.2) with a bone outline (R44 shoulder lobe, waist, R52 elbow lobe, heel tab = extension stop), 11 spacer sleeves, two lightening slots. Each plate is printed in two pieces (394 mm does not fit the 256 mm bed): glued, screwed half-laps at v 120 (inner) and v 155 (outer).
- Shoulder: the inner plate bolts straight to the shoulder flange (Ø40 spigot, 6 × M5 in close-fit holes); no aluminium adapter.
- Elbow: motor on 4 standoffs (5 mm air gap) between the plates. The hub journal (Ø19.2) runs through a bearing in a sleeve in the outer plate, and the hub end flange bolts to the forearm outer plate. The forearm inner plate pivots on a stub through a 6804Z in a slip bore. Both new bearings are slip fits so they do not fight the motor bearings.
- Forearm: two 4 mm truss plates outside the upper plates, 7 sleeves, wrist block with the Ø20 spigot and 4 × M3 on Ø30 for the future hand.
- Cables: the stator is fixed to the upper arm, so the motor leads and encoder cable never flex at the elbow; they leave through a hole up and behind the axis (never swept) and run along the upper arm.

## 5. Material

| Material | Use | Data |
|---|---|---|
| Bambu PETG HF | All printed parts | 34 ± 4 MPa X-Y, 23 ± 4 MPa Z, E 1.81 GPa, hdt 62 °C at 1.8 MPa, 1.28 g/cm³ ([Bambu TDS](https://store.bblcdn.com/3a230e260a3a47c2b0db0156e07eef91.pdf), [Bambu TDS mirror](https://filament.ee/en/index.php?controller=attachment&id_attachment=4)) |
| Standard resin | Magnet holder only (precise, unloaded) | 33 MPa, brittle ([Elegoo TDS](https://www.advancedadditiveinnovations.com/_files/ugd/82283a_42d5bfd023b24c3ca1eb3b28b04409ff.pdf)) |

Allowables are (mean − 1 sd) / 2. The highest printed stress is 1.9 MPa at the 10 N·m shoulder limit (calc §6). Every fit has a named clearance in `arm_params.py`, set from the fit coupon; nothing is pressed with a hammer (Rev 1 jam lesson, elbow research §7).

## 6. Mass (`cad/mass.txt`, print estimate)

| Group | Mass |
|---|---|
| Upper-arm plates, sleeves, standoffs, fasteners, encoder | 465 g |
| LA8308 motor | 336 g |
| Forearm (hub, plates, sleeves, wrist block, fasteners) | 178 g |
| **Arm total** | **978 g** |

Dummy hand 0.15 kg (not in the total).

## 7. End-effector roadmap

1. Dummy hand (now): the direct-drive elbow holds it at 0.62 N·m.
2. Gripper, wrist, hand: need more elbow torque than direct drive can give (S1 needs 2.5 N·m static, 27 A). Planned with frameless motors and metal gearing; the arm structure and wrist interface stay.

## 8. Shoulder re-check (calc §5)

Arm horizontal with the dummy hand: gravity 3.30 N·m, with 12.57 rad/s² acceleration 4.83 N·m, against 30 N·m continuous (SF 6.2). The printed arm sets the shoulder current limit: 10 N·m output (half-lap screws alone carry 14.5 N·m, epoxy alone 67.7 N·m).

## 9. Open items

1. Measure on the motor: rotor M3 pattern (Ø31 or Ø25) and thread depths, base M4 depth, lead-exit angle against the base holes.
2. Print and read the fit coupon; update `STUB["journal_clear"]`, `HUB["journal_d"]`, `PIVOT_BORE_R` and `SLEEVE["bore_r"]`. Measure the hub bearing width and set `HUB_BRG["B"]` and `HUB["spacer_l"]`.
3. Bench thermal-hold test for the motor thermal resistance; then fix the continuous rating and confirm the 70 °C NTC limit.
4. Re-torque the shoulder M5 and check the motor standoffs after the first week (PETG creep).
5. Set the shoulder output limit to 10 N·m in the ODESC profile.
