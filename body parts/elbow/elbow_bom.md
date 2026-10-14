# VAYN Elbow Actuator — BOM, Print and Sourcing Guide, Rev 1.0

**Purpose:** print, buy and assemble one elbow actuator without opening the CAD.

**Source of truth:**
- Geometry and part list: `build()` in `elbow/cad/gen_actuator.py`, dimensions in `elbow/cad/params.py`. The exact model is `elbow/cad/actuator.step`.
- Loads, fits and torques: `elbow/cad/calc.py`, results in `elbow/cad/calc.txt`.
- Part specification and assembly order: `elbow/parts.md`.

The "Model #" column is the object number in the STEP/3MF.

---

## 0. Summary

| Item | Value |
|---|---|
| Print parts | 9 (ASA 4, PLA 3, PET-CF 2) |
| Metal make parts | 2 (6061-T6 clamp ring, magnet cup) |
| Purchased lines | 21 (≈ 90 pieces, not counting spares) |
| Actuator mass | 508 g: 380.1 g modelled parts (100% solid) + 128 g motor |
| Heaviest parts | Ring pins 96.6 g (21), housing 70.0 g, output pins 27.6 g, 61807 27.0 g, carrier 23.6 g |
| Printer | Bambu P1S, 256 × 256 × 256. **PET-CF needs the hardened-steel upgrade** (the P1S ships with a stainless 0.4 nozzle and stainless gears) [E14] |
| Must measure on arrival | MN5008 rotor-top thread depth (model 8.5) and base thread depth (model 7.0) |

**Decisions made during the CAD (in the model and the calc):**
1. **Discs in Bambu PET-CF instead of PLA.**
   - With PLA at its data-sheet yield (35 ± 4 MPa, taken as 31) [E8], the continuous contact stress (46 MPa) was over the continuous limit (34.5).
   - PET-CF (74 ± 6 MPa, taken as 68) gives limits of 75.7 continuous and 113.6 proof against 61.8 / 79.8 MPa, with no geometry change [E7]. The first-yield rule p0 = 1.67 Y (Tresca, line contact) is from [E15].
2. **The cam is carried by the output cage**: 6703 in the rear ring, 6701 in the pin plate. It is driven by four dog screws with 0.2 radial play. The motor's own bearings carry no gearbox load, and the motor and cam do not need to be coaxial within better than 0.2 mm.
3. **Static safety factors use the SKF ball-bearing guide values**: s0 ≥ 1.5 continuous, ≥ 1.0 peak [E4]. Bearing ratings are the lowest of the sourced values [E2][E3].

---

## 1. Print parts (Bambu P1S)

| ID | Model # | Part | Material | Nozzle | Layer | Walls / infill | Orientation (face on plate) | Critical features | Mass (g) |
|---|---|---|---|---|---|---|---|---|---|
| M01 | 01 | Encoder lid | Bambu ASA | 0.4 | 0.16 | 3 / 40% | Outer face | 4 × M3 CSK, cable slot | 3.7 |
| M02 | 10 | Housing | Bambu ASA | 0.4 | 0.16 | 6 / 40% gyroid | Rear face | 21 ring-pin grooves Ø5 on Ø60; pilot Ø31; 7 insert holes Ø4.0 × 6.7; 2 dowel holes Ø3; 12 vent slots 4 × 23.6 | 70.0 |
| M03 | 26 | Retainer ring | Bambu ASA | 0.4 | 0.16 | 100% | Either face | Ø44.4 bore | 7.1 |
| M04 | 28 | Front cover | Bambu ASA | 0.4 | 0.16 | 100% | Flange | Ø47 bearing bore | 18.9 |
| M05 | 14 | Cam | Bambu PLA Basic | 0.4 | 0.12 | 100% | Rear face | Journals Ø17, Ø20 (±1.0 eccentric), Ø12; dog pockets Ø3.4 | 8.7 |
| M06 | 16 | Cage rear ring | Bambu PLA Basic | 0.4 | 0.12 | 100% | Lip face | 6703 seat Ø23; 6 pin holes Ø5 on Ø40 | 9.0 |
| M07 | 24 | Output carrier | Bambu PLA Basic | 0.4 | 0.12 | 100% | Pin-plate face | 6701 pocket Ø18; hub Ø35; 6 pin holes Ø5; 6 insert holes Ø4.0; 2 dowel holes Ø3 | 23.6 |
| M08 | 18 | Cycloid disc A | **Bambu PET-CF** | **0.6 hardened** | 0.2 | 100% | Lip face | 20-lobe outline; 6704 seat Ø27; 6 holes Ø7.2 on Ø40 | 18.6 |
| M09 | 20 | Cycloid disc B | **Bambu PET-CF** | **0.6 hardened** | 0.2 | 100% | Lip face | As M08, outline turned −9° | 18.6 |

The 100% infill on the cam, the rear ring, the carrier and the discs is required. The allowables in calc §3–§5 are from data-sheet specimens printed at 100% [E7][E8].

**PET-CF rules (Bambu)** [E7][E14]:
- Use a hardened-steel nozzle; 0.6 is recommended.
- Do not feed it through the AMS.
- Dry the filament at 80 °C for 8–12 h; print and store below 20% RH.
- Use glue on the plate: Engineering, High Temperature or Textured PEI plate, bed 80–100 °C.
- Nozzle 260–290 °C, under 100 mm/s.

**Anneal the PET-CF discs** at 80 °C for 12 h in a forced-air oven, away from the heater. The data-sheet strength used in the calc was measured on specimens annealed that way. Bambu warns that some prints warp when annealed [E7], so re-check each disc on the pins after annealing (Section 5).

**ASA and PLA:** use the Bambu Studio system presets for Bambu ASA and Bambu PLA Basic. The P1S is enclosed, which ASA needs [E14].

---

## 2. Metal make parts

| ID | Model # | Part | Qty | Material | Finished size (mm) | Stock | Process | Critical features | Mass (g) |
|---|---|---|---|---|---|---|---|---|---|
| M10 | 06 | Motor clamp ring | 1 | 6061-T6 | Ø46 / Ø12 × 2.5 | 3 mm plate, 50 × 50 | CNC, or drill and tap from a printed template | 4 × M3 CSK on PCD 25 at 84.8° + 90°; 4 × M2.5 tapped on PCD 34 at 62.3° + 90°; 4 × M3 tapped on PCD 37 at 107.3° + 90° | 9.7 |
| M11 | 08 | Magnet cup | 1 | 6061-T6 (non-magnetic) [E13] | Ø10 × 3, pocket Ø6 × 2.5 | Ø10–12 bar | Lathe or drill press | Pocket concentric ≤ 0.1 | 0.4 |

---

## 3. Purchased parts

| ID | Model # | Part | Qty (+spare) | Exact spec | Approved / alternate | Notes |
|---|---|---|---|---|---|---|
| P01 | 11, 12 | BLDC motor | 1 | **T-Motor MN5008 KV170**, 128 g, Ø55.6 can, 14 pole pairs [E1] | Indian sellers in `elbow/research.md` §6.1 | **Measure on arrival:** rotor-top M3 depth (model 8.5), base M3 depth (model 7.0) |
| P02 | 27 | Output bearing | 1 (+1) | **61807-2RS1**, 35 × 47 × 7, contact seals | SKF 61807-2RS1; NSK/NTN 6807DDU / 6807LLU | C 4.75 kN, C0 3.2 kN [E2] |
| P03 | 17, 19 | Disc bearings | 2 (+1) | **6704-2RS**, 20 × 27 × 4 | Any chrome-steel 6704-2RS / 61704-2RS1 | Calc uses C 1,010 N, C0 722 N [E3]. A low-grade bearing at C0 657 N still gives s0 2.0 at proof |
| P04 | 15 | Cam rear bearing | 1 (+1) | **6703-2RS**, 17 × 23 × 4 | 61703-2RS1 | C 999 N, C0 657 N [E3] |
| P05 | 23 | Cam front bearing | 1 (+1) | **6701-2RS**, 12 × 18 × 4 | 61701-2RS1 | C 922 N, C0 530 N [E3] |
| P06 | 21 | Ring pins | 21 (+3) | **ISO 8734 Ø5 × 30, type A, m6**, 550–650 HV30 | DIN 6325 5 m6 × 30 | m6 = Ø5.004–5.012 [E6]; calc §2b checks the maximum size |
| P07 | 22 | Output pins | 6 (+2) | As P06 | As P06 | Pressed into PLA |
| P08 | 32 | Flange dowels | 2 (+2) | ISO 8734 Ø3 × 12 | DIN 6325 | — |
| P09 | — | Hub dowels | 2 (+2) | ISO 8734 Ø3 × 16 (arm part 127) | DIN 6325 | 5 mm into the carrier, 11 mm into the forearm; they carry the output torque (calc §5, `arm/cad/calc.txt` §5) |
| P10 | 25, 29 | Heat-set inserts | 13 (+7) | **Ruthex RX-M3x5.7**, hole Ø4.0, wall ≥ 1.6, depth ≥ 6.7 [E5] | CNC Kitchen M3 × 5.7 (same hole) | 6 in the hub, 7 in the housing flange |
| P11 | 09 | Encoder magnet | 1 (+1) | Ø6 × 2.5 NdFeB, diametric | ams **AS5000-MD6H-2** [E13] | Gap 1.0 to the IC, centred ≤ 0.5 mm |
| P12 | 04 | Encoder IC | 1 (+1) | **AS5047P-ATSM** | — | Same as shoulder P11 |
| P13 | 03 | Encoder PCB | 1 (+2) | 30 × 30 × 1.6 FR4, 4 × Ø2.7 on PCD 34 | Shoulder P12 board | — |
| P14 | — | Winding thermistor | 1 (+1) | 10 kΩ NTC | Shoulder P14 | Log winding temperature in the first hold tests (`elbow/research.md` §9) |

### 3.1 Fasteners (steel, black oxide)

| ID | Model # | Fastener | Standard | Qty (+spare) | Joint | Torque (N·m) | Threadlocker |
|---|---|---|---|---|---|---|---|
| F01 | 02 | M3 × 8 countersunk | ISO 10642 | 4 (+2) | Lid to clamp ring (6061) | 0.3 | None |
| F02 | 05 | M2.5 × 5 socket head | DIN 912 | 4 (+2) | PCB to clamp ring (6061) | 0.2 | None |
| F03 | 07 | M3 × 10 countersunk | ISO 10642 | 4 (+2) | Clamp ring + wall to motor base | **0.5** (calc §5: slip SF 13.6) | Loctite 243 **in the motor holes only** |
| F04 | 13 | M3 × 8 set screw, flat point | ISO 4026, 45H | 4 (+2) | Dogs in the rotor top | Snug, then set 3.0 protrusion | Loctite 243 in the bottom third of the rotor holes |
| F05 | 31 | M3 × 12 socket head | DIN 912 | 7 (+3) | Cover + retainer to housing inserts | **0.2** (calc §5: slip SF 2.28) | None |
| F06 | 30 | M3 washer | ISO 7089 | 7 (+3) | Under F05 | — | — |
| F07 | — | M3 × 16 forearm screws | DIN 912 | 6 | Forearm to hub inserts (arm part 126) | **0.2** (calc §5) | None |

In the arm, F05 and F06 are replaced by arm parts 116 / 117 (M3 × 16 + washers through the front ring, `arm/bom.md`).

Calculated torques use the VDI 2230 preload table at μ 0.12 (`elbow/cad/calc.py`, same basis as the shoulder). F01, F02 and F04 are practical values for light joints.

Keep anaerobic threadlocker off the printed parts and out of the inserts. Henkel does not recommend Loctite 243 on thermoplastics, because it can stress-crack them [E11].

### 3.2 Consumables

| Item | Spec | Qty per actuator | Where |
|---|---|---|---|
| ASA filament | Bambu ASA | ≈ 120 g with purge | M01–M04 |
| PLA filament | Bambu PLA Basic | ≈ 50 g | M05–M07 |
| PET-CF filament | Bambu PET-CF (dried) | ≈ 50 g | M08, M09 |
| Hardened-steel upgrade | Bambu hardened-steel extruder gears + P1 Series hotend 0.6 hardened [E14] | 1 per printer | PET-CF only |
| Glue | Bambu glue stick or liquid glue | — | PET-CF plate |
| Grease | **Super Lube 21030** (synthetic PAO + PTFE, NLGI 2, rated plastic-safe) [E12] | ≈ 1 g | Ring pins, disc lobes, output pins. **None on the magnet or PCB** |
| Threadlocker | Loctite 243 | few drops | F03, F04 (metal threads only) |
| Magnet adhesive | Structural epoxy (e.g. Loctite EA 9466) | few drops | Magnet in cup, cup on rotor retainer |

---

## 4. Materials: exact use case of each

| Material | Used for | Why here | Data used in the calc |
|---|---|---|---|
| **Bambu PET-CF** | Discs (M08, M09) | Highest contact load in the actuator (79.8 MPa at proof); PLA fails it | X-Y tensile 74 ± 6 MPa → Y 68; E 4,730 MPa; ν 0.35 assumed (p0 moves < 3% for 0.30–0.40); 1.29 g/cm³ [E7] |
| **Bambu PLA Basic** | Cam, rear ring, carrier (M05–M07) | Stiff and accurate; stresses are low (dog pockets 8.1 MPa, pin bearing 6.2 MPa, hub dowels 21.1 MPa) | X-Y tensile 35 ± 4 MPa → Y 31; 1.24 g/cm³ [E8] |
| **Bambu ASA** | Housing, lid, retainer, cover (M01–M04) | Heat resistance next to the motor; stresses are low (13.0 MPa under the washers, 6.8 MPa at the dowels) | 1.05 g/cm³ [E9] |
| **6061-T6** | Clamp ring, magnet cup | Metal threads for the lid and PCB; non-magnetic cup [E13] | — |
| **Hardened dowel steel** | Ring and output pins | Line-contact counter-face for the printed lobes; bending only 82 MPa | ISO 8734 type A, 550–650 HV30 [E6] |

---

## 5. Fits and print calibration

The CAD is nominal. Printed fits are set in Bambu Studio, not by editing the model:
- **XY hole compensation** (Process › Quality › Precision) enlarges or shrinks closed holes. The diameter changes by twice the value entered [E10].
- **XY contour compensation** changes the outer outline only [E10].
- **Auto circle hole compensation** works only on complete horizontal circles under Ø50 [E10].

Each print part gets its own per-object setting, tuned on a test print.

| Feature | Target | How to set it |
|---|---|---|
| Bearing ODs in printed seats (6703, 6704, 6701, 61807) | Light press by hand or vice, no hammer | Hole compensation, tuned on a Bambu Studio Cut slice of the seat |
| Bearing bores on printed journals and hub (Ø17, Ø20, Ø12, Ø35) | Light press | Contour compensation on the cam and carrier |
| Output pins in the carrier and rear ring | Press | Hole compensation |
| Output pins in the disc holes Ø7.2 | 0.100 radial clearance (0.094 with maximum m6 pins) | Hole compensation on the discs |
| Ring pins in the housing grooves | Pins drop in by hand with no side play | **Hole compensation does not apply**: the grooves break into the bore, so they are open paths. Bambu warns that hole compensation on open paths causes layer separation [E10]. Print a Cut slice of the housing at Z 37.1–51.3 first and check the pins and disc A. If the pins are tight, raise `GROOVE_CLEAR` in `params.py` (steps of 0.02), regenerate, and reprint the slice. Do not scale the part, because that moves the Ø60 pin circle |
| Disc outline on the pins | Disc turns on its bearing through one full input turn on the pins with no tight spot; 0.05 feeler enters on the unloaded side (design relief 0.08, 0.073 with maximum pins) | Contour compensation on the discs, steps of 0.02 [E10]; **check again after annealing** |
| Inserts | Ruthex hole Ø4.0 | Insert holes are closed holes, so hole compensation applies |

---

## 6. Sourcing and build checklist (in order)

1. Order the MN5008 (P01) and measure the two thread depths. If the rotor depth is less than 5.0 + 1.0, shorten the dogs (F04) and update `DOG` in `params.py`.
2. Order the bearings (P02–P05), pins (P06–P08) and inserts (P10).
3. Fit the hardened-steel gears and 0.6 hotend to the P1S. Set the nozzle type in the printer settings [E14]. Dry the PET-CF.
4. Print the calibration slices (Section 5), then the parts (Section 1). Anneal the discs.
5. Make M10 and M11.
6. Assemble in the order in `elbow/parts.md` (Assembly).
7. First power-up on the tethered rig: check the encoder reading, then that the joint backdrives (target breakaway under 0.3 N·m at the output, `elbow/research.md` §10).

---

## 7. Open items

| Item | Status |
|---|---|
| Cam carried by the cage, driven by dogs | Chosen in CAD without your confirmation (the question form failed twice); see `elbow/research.md` §7.2 |
| PET-CF Poisson's ratio | Not published; 0.35 assumed (< 3% effect on p0) |
| PET-CF strength without annealing | Not published, so the discs must be annealed. Disc fit is re-checked after annealing |
| Hub screws alone slip below proof (SF 0.75) | The two hub dowels carry the torque (SF 1.5 in PLA bearing). The forearm design must include them |
| Cam skin outside the dog pockets | 0.8 mm (2 perimeters at 0.4); the dog load is tangential into the solid web |
| 6703 inner-ring land on the trimmed collar | 0.30 mm on one side (inner-ring chamfer ≈ 0.2). Axial load on it is near zero |
| Length and mass vs research | 78.3 mm and 508 g, against the research estimates of 65 mm and 0.38–0.43 kg. The shoulder re-check is in `arm/research.md` §8 |
| Ring pins are 96.6 g | Shorter pins are a later optimisation |
| Rotor and base thread depths | Measure on arrival (checklist item 1) |

---

## References

- [E1] T-Motor MN5008 KV170 (128 g, 24N28P, 270 mΩ, 15 A 180 s peak): https://store.tmotor.com/product/mn5008-kv170-motor-antigravity-type.html, https://www.kjretail.ca/products/t-motor-mn5008-antigravity-uav-motor
- [E2] SKF 61807-2RS1 (C 4.75 kN, C0 3.2 kN, d1 38.21, D2 44.4): https://www.skf.com/group/products/rolling-bearings/ball-bearings/deep-groove-ball-bearings/productid-61807-2RS1, https://www.coolenbearings.com/skf/ball-bearings/deep-groove/61807-2rs1
- [E3] 6700-series ratings (6701 0.928/0.532, 6703 0.999/0.657, 6704 1.010/0.722 kN; 6701 sheet 0.922/0.53; 6704 sheet 1.04/0.726): https://www.finerpt.com/site/DefaultSite/filesystem/documents/Finer%20Catalogue%20Files/Bearings/Ball%20Bearings/Deep%20Groove%20Ball%20Bearings/6700%20Series/EZO%20DGBB%206700.pdf, https://en.tradebearings.com/data/pdf/e8/aa/6701_2RS-191990.pdf, https://en.tradebearings.com/data/pdf/63/f8/6704_2RS-197506.pdf, https://www.kugellager-shop.net/mr-6704-2rs-6704rs-kugellager-27x20x4.html
- [E4] SKF static safety factor s0 = C0 / P0, ball-bearing guideline values: https://www.skf.com/group/products/rolling-bearings/principles-of-rolling-bearing-selection/bearing-selection-process/bearing-size/size-selection-based-on-static-load, https://www.skf.com/us/products/rolling-bearings/principles-of-rolling-bearing-selection/bearing-selection-process/bearing-size/size-selection-based-on-static-load
- [E5] Ruthex RX-M3x5.7 (hole Ø4.0, L 5.7, wall ≥ 1.6, depth ≥ L + 1): https://www.igo3d.com/mediafiles/Sonstiges/Ruthex/ruthex_Datenblatt_RX-Serie.pdf, https://machinistcalcs.com/guides/heat-set-insert-holes/
- [E6] ISO 8734 dowels (m6, type A 550–650 HV30, lengths): https://www.fasteners.eu/standards/ISO/8734/, https://www.opac.net/en/producto-166-iso-8734, https://www.ekinsun.com/custom-fasteners/dowel-pin-size-chart/
- [E7] Bambu PET-CF data sheet and usage guide (tensile, modulus, specimens 100% infill annealed 80 °C 12 h, drying, 0.6 hardened nozzle, glue, AMS not compatible): https://wiki.bambulab.com/filament-acc/petcf-ppacf/07689de83afd4cc480f136c7697e6de3.pdf, https://wiki.bambulab.com/en/filament/petcf_ppacf, https://eu.store.bambulab.com/products/pet-cf
- [E8] Bambu PLA Basic data sheet (X-Y tensile 35 ± 4 MPa, 1.24 g/cm³): https://wiki.bambulab.com/filament-acc/abs-asa-pc/bambu_pla_basic_technical_data_sheet.pdf, https://cdn.shopifycdn.net/s/files/1/0584/7236/6216/files/Bambu_PLA_Basic_Technical_Data_Sheet.pdf
- [E9] Bambu ASA data sheet and store page (1.05 g/cm³): https://wiki.bambulab.com/filament-acc/abs-asa-pc/6eaf4c432d1d4014a1975e55a55ed00b.pdf, https://bambu-lab-global.myshopify.com/products/asa-filament
- [E10] Bambu Studio XY hole / contour compensation and auto circle compensation: https://wiki.bambulab.com/en/software/bambu-studio/xy-hole-contour-compensation, https://wiki.bambulab.com/en/software/bambu-studio/manual/auto-circle-contour-compensation
- [E11] Henkel Loctite 243 data sheet (not recommended on thermoplastics; blind-hole application): https://datasheets.tdx.henkel.com/LOCTITE-243-en_GL.pdf, https://docs.rs-online.com/22f6/0900766b80076c5f.pdf
- [E12] Super Lube 21030 (PAO + PTFE, NLGI 2, plastic-safe, compatibility chart): https://www.super-lube.com/wp-content/uploads/2025/05/Technical_Data_Sheet_Multi_Purpose_Grease.pdf, https://www.super-lube.com/wp-content/uploads/2025/09/Super-Lube-Compatability-Chart-for-both-Polymers-and-Elastomers.pdf, https://kpaulsupply.com/products/super-lube-21030-multi-purpose-synthetic-grease-with-syncolon-r-3oz-tube
- [E13] ams AS5047P adapter-board manual (Ø6 × 2.5 diametric magnet, gap 0.5–3 mm, holder not ferromagnetic) and datasheet: https://media.digikey.com/pdf/Data%20Sheets/Austriamicrosystems%20PDFs/AS5047P-TS_EK_AB.pdf, https://www.infineon.com/assets/row/public/documents/24/49/infineon-as5047p-datasheet-en.pdf
- [E14] Bambu P1S (0.4 stainless nozzle included; enclosed; CF needs the extruder and hotend upgrade) and P1 hardened hotend: https://asia.store.bambulab.com/products/p1s, https://wiki.bambulab.com/en/p1/manual/p1s-extruder-upgrade, https://eu.store.bambulab.com/products/bambu-hotend-p1-series
- [E15] Hertz line contact: τmax = 0.30 p0 at 0.78 a, Tresca first yield p0 = 1.67 Y: https://maschinenbaurechner.de/en/hertzian-contact-stress, http://www.experimentalni-mechanika.cz/cs/konference/konference/2016.html?download=610%3Abearing-race-and-roller-line-contact-analysis-in-2d
- [E16] Berkeley Humanoid Lite printed cycloid (backlash ≤ 23 mrad): https://arxiv.org/html/2504.17249v1, https://berkeley-humanoid-lite.gitbook.io/docs/in-depth-contents/motor-characterization
- Project files: `elbow/cad/calc.txt`, `elbow/parts.md`, `elbow/cad/actuator.step`.
