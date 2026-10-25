# Elbow: research and decision record

Status: Rev 2 = direct-drive EaglePower LA8308 KV90, built into the twin-plate arm. The elbow no longer has its own CAD: geometry, checks and assembly are in [`../arm/parts.md`](../arm/parts.md), [`../arm/arm_bom.md`](../arm/arm_bom.md) and `../arm/cad/` (numbers below are from `../arm/cad/calc.txt` and `gen.log`). Rev 1 (T-Motor MN5008 + printed 20:1 cycloid) is in git history.

## 1. Decision

| Item | Rev 2 |
|---|---|
| Motor | EaglePower LA8308 KV90 (the MN5008 KV170 was unavailable): Ø92 × 32.5 measured, 336 g, 20 pole pairs, 84.6 mΩ phase (measured), Kt = 8.27 / KV = 0.0919 N·m/A ([ODrive](https://docs.odriverobotics.com/v/latest/articles/component-selection.html), [ODrive 0.5.4](https://docs.odriverobotics.com/v/0.5.4/commands.html)) |
| Reduction | None (direct drive) |
| Load | Dummy hand 0.15 kg: 0.62 N·m hold (6.8 A, 6.6 W), 0.83 N·m moving, 1.39 N·m proof |
| Continuous rating | 0.70–0.99 N·m for a thermal resistance of 4–2 K/W (stator 70 °C, ambient 35 °C); payload with the dummy hand 0.03–0.12 kg |
| Driver | ODESC 3.6 axis 1, `current_lim` 20 A (1.84 N·m), `vel_limit` 0.5 turn/s, NTC limit 70 °C, soft limits −3° / 135° |
| Encoder | AS5047P on the motor = joint angle: absolute over the range, no homing, 0.022° |
| Stops | Rubber-sleeved forearm spacers: −5° on a 3 mm heel pad, 140° on the upper-plate edge |
| Constraints | Print only (Bambu P2S PETG, Saturn resin), Indian parts, no machining, one motor, 20 V bench |

Upgrade path: gripper and hand loads (S1 2.5 N·m static = 27 A) need gearing. That comes with frameless motors and metal gears later; the arm keeps its structure and wrist interface.

## 2. Requirements

- Prototype: shoulder pitch + elbow pitch, dummy hand now. Software range 0–135° (daily tasks use 30–130°; [Morrey 1981](https://pubmed.ncbi.nlm.nih.gov/7240327/), [PMC6555111](https://pmc.ncbi.nlm.nih.gov/articles/PMC6555111/)).
- Speed 180°/s, 0.25 s to full speed (1.5 × healthy reaching speed; [Alt Murphy 2011](https://sage.cnpereading.com/doi/10.1177/1545968310370748), [Berkeley Humanoid Lite](https://arxiv.org/html/2504.17249v1)).
- Main goal of the redesign: minimum axial length at the elbow, human look.

## 3. Options evaluated

| Option | Axial / size | Result | Why |
|---|---|---|---|
| Printed cycloid on the rotor face (Route B) | 62–66 mm | Rejected | Too long; same printed-contact risks as Rev 1 |
| Printed cycloid or planetary inside the stator (gut the motor) | 45–50 mm | Rejected | At the ~Ø45 bore, PET-CF lobe stress is 56 MPa continuous with the dummy hand (limit about 56) and 111 MPa with a gripper. Plus rotor air gap held by printed seats and only one motor. Open internal designs all use custom motors or metal rings ([Musa](https://www.aaedmusa.com/projects/internalcycloidalactuator), [Xuti](https://github.com/timxuti/Integrated-Joint-Actuator), [Koshiro](https://koshirorobot.github.io/KoshiroRobot/Projects/Internal_Cycloidal_Drive/internal_cycloidal_drive.html)) |
| Rope capstan, motor in the upper arm | joint about 35 mm | Rejected | Needs imported Dyneema SK78 (DM20 retail starts at 3 mm; [Kanirope](https://www.kanirope.com/liros-d-pro-static-dyneema-dm20), [English Braids](https://www.englishbraids.com/products/dyneema-hmpe-ropes/)) and a metal drum (24–30 MPa rope pressure at D/d 10; [BR Ropes](https://brropes.com/hmpe-handling-guide/), [OSTI/Sandia](https://www.osti.gov/servlets/purl/1340266)) |
| GT2 belt to a sector, motor in the upper arm | joint about 42 mm | Rejected by review | Worked numerically (41 N per belt continuous vs 44 N rating; [SDP](https://fab.cba.mit.edu/classes/865.21/topics/mechanical_design/reference/BeltTensileProperties.pdf), [BEMONOC](https://www.amazon.com/dp/B019Z9H0RW)); the look and layout were not accepted |
| Off-the-shelf 12 V linear actuator | — | Rejected | 7 mm/s ≈ 9°/s at the elbow vs 180°/s, 889 g, 20 % duty ([Robu](https://oldwp.robu.in/product/linear-actuator-stroke-length-100mm7mm-s1500n12v/), [QuartzComponents](https://quartzcomponents.com/products/linear-actuator-stroke-length-12v-100mm-7mm-s)) |
| DIY screw linear actuator | — | Rejected | Pancake motor cannot lie along the arm; angle-dependent torque and linkage ([humanoid.guide](https://humanoid.guide/linear-vs-rotary-actuators-humanoid-joints/), [Humanoids Daily](https://www.humanoidsdaily.com/news/actuator-architecture-sparks-debate-figure-ceo-refutes-claim-of-using-planetary-roller-screws)) |
| Strain wave | short | Rejected | High ratio, poor backdrivability and torque transparency ([LAAS/HAL](https://hal.science/hal-01494676v2/file/iros-ddp-romeo.pdf)) |
| **Direct drive, motor clamped between the upper-arm plates** | elbow 64.5 mm wide | **Chosen** | No gearbox to print or jam, zero backlash, absolute joint encoder, enough torque for the dummy hand |

## 4. Thermal model (to be measured)

- Copper loss P = 1.5 · I² · R (R rises 0.393 %/K). Km = 0.258 N·m/√W cold.
- The LA8308 thermal resistance in still air is not published. Calc uses 2 / 3 / 4 K/W and a lumped capacity of about 194 J/K (thermal time constant 6–13 min).
- Measure with the bench GUI thermal-hold job (`odrive/backend/app/jobs/thermal.py`): lock the joint, hold 8 A for 30 min with the NTC on the stator; it fits the time constant and the final temperature. R_th = final rise / copper loss. Then update `R_TH` in `arm/cad/calc.py`.
- With the dummy hand: holding rises 13–27 K; continuous moving reaches the 70 °C NTC limit after about 45 min (R_th 3); a proof-level burst after about 4 min.

## 5. Falls and stops

- ODESC idle leaves the phases open: the arm falls freely. From horizontal to straight with the dummy hand: 0.62 J, 8.7 rad/s. Shorted phases would only give 0.067 N·m·s/rad.
- The 3 mm rubber pad on the heel face gives about 3 mm of travel: average 208 N instead of 624 N with the 1 mm silicone tube alone.
- A powered stall at the 20 A limit puts 22 N on the flexion sleeve: harmless.

## 6. Reference designs

- Aaed Musa OpenQDD uses this exact motor with a stacked 9:1 planetary (133 mm long) ([OpenQDD](https://www.aaedmusa.com/projects/openqdd), [RPi Magazine](https://magazine.raspberrypi.com/articles/tops-traverser-of-planar-surfaces)).
- Commercial 80xx-class actuators with internal planetaries are Ø92–98 × 38.5–44 mm ([SteadyWin GIM8108-8](https://steadywin.cn/en/pd.jsp?id=133), [CubeMars AK80-9](https://www.cubemars.com/product/ak80-9-v3-0-robotic-actuator.html)).
- UMA Northstar's arm (plates + spacers, actuators clamped between plates) set the Rev 2 structure ([Humanoids Daily](https://www.humanoidsdaily.com/companies/uma), [humanoidversus](https://humanoidversus.com/robots/uma-northstar)).

## 7. Rev 1 lesson: why the cycloid elbow jammed

Root cause: the ring-pin grooves had zero design clearance (`GROOVE_CLEAR = 0.0`) for m6 dowels (Ø5.004–5.012), and FDM holes print 0.1–0.3 mm undersize ([Makelab](https://www.makelab.com/insights/3d-printing-tolerances-explained), [Sovol](https://www.sovol3d.com/blogs/news/fdm-3d-printing-tolerances-clearances-how-to-design-parts-that-fit)). The pins stood into the disc path, which had only 0.08 mm profile relief on unannealed PET-CF. Rev 2 rules: every printed fit has a named clearance in `arm_params.py`, values come from the printed fit coupon, and nothing is hammered.
