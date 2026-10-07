# VAYN Arm — BOM, Print and Sourcing Guide, Rev 0

**Purpose:** print, buy and assemble one arm (two-plate upper arm, elbow clevis, cone-cage forearm; no hand in v0) without opening the CAD. The shoulder and the elbow actuator have their own BOMs (`shoulder/bom.md`, `elbow/bom.md`).

**Source of truth:**
- Geometry and part list: `build_arm()` in `arm/cad/gen_arm.py`, dimensions in `arm/cad/arm_params.py`. The exact model is `arm/cad/arm.step`.
- Loads, fits and torques: `arm/cad/calc.py`, results in `arm/cad/calc.txt`.
- Part specification and assembly order: `arm/parts.md`. References [A1]–[A15] are listed there.

The "Model #" column is the object number in the STEP/3MF.

---

## 0. Summary

| Item | Value |
|---|---|
| Print parts | 7 (all ASA) |
| Metal make parts | 4 (6061-T6: adapter, front ring, passive pin, encoder bracket) |
| Arm mass | 1.414 kg incl. the elbow actuator (0.499 kg as placed); printed parts at the print estimate |
| Printer | Bambu P1S, all parts fit the 256³ bed with a 5 mm margin (`gen.log`) |
| Elbow change | The elbow's 7 × M3 × 12 flange screws and washers (elbow parts 30, 31) are **not fitted**: arm parts 116/117 (M3 × 16 + washers) go through the front ring instead |

---

## 1. Print parts (Bambu P1S)

| ID | Model # | Part | Material | Layer | Walls / infill | Face on plate | Critical features | Mass (g, est.) |
|---|---|---|---|---|---|---|---|---|
| A01 | 104 | Upper arm, shoulder half | Bambu ASA | 0.16 | 6 / 40% gyroid, shells 2.5 | Inboard face (Y 1) | Hex pocket 76.3 AF × 5; 6 × Ø4.5; collar holes Ø4.5 / Ø4; plates 5; 2 X bays per wall (8 triangles a side) | 232 |
| A02 | 108 | Shoulder cap | Bambu ASA | 0.16 | 3 / 40% | Outer face | 4 × M3 CSK on Ø92; 4 spoke windows | 12 |
| A03 | 110 | Upper arm, elbow half | Bambu ASA | 0.16 | 4 / 40% gyroid | Inboard face (Y 1) | Saddle R41.5; ear bore Ø16; 4 + 4 RX-M4 holes Ø5.6; 3 RX-M3 holes Ø4.0; ring pocket 1.5; closed beam | 157 |
| A04 | 125 | Forearm + cheek A | Bambu ASA | 0.16 | 8 / 40% gyroid, shells 3.4 | Posterior face | Boss face Ø37.5; 6 × Ø3.4 + cbore Ø6.2; 2 dowel holes Ø3 × 11; stop slot 8.6 × 6; cone cage 4 bays × 8 windows (bars 10); wrist 56 × 44, spigot Ø20 h7 | 186 |
| A05 | 128 | Cheek B | Bambu ASA | 0.16 | 4 / 40% | Lip face | 61804 bore Ø32 slip; lip Ø29; 4 × Ø4.8 float holes | 33 |
| A06 | 133 | Bearing retainer | Bambu ASA | 0.16 | 100% | Either face | Ø29 bore | 2 |
| A07 | 140 | Encoder cover | Bambu ASA | 0.16 | 100% | End face | Magnet pocket Ø6; 3 cbore Ø6.2 | 7 |

The calc allowables are data-sheet values (mean − 1 sd) / 2.0 [A1]. The sections and frame bars in calc §3–§4 assume solid members, so do not reduce the slicer shells below:

- **A01**: 6 walls and top / bottom shells of 2.5 mm, so the 5 mm plates and 4 mm X walls print solid.
- **A04**: 8 walls and top / bottom shells of 3.4 mm, so the 6 mm cage shell, bars and rings print solid.
- **A03, A05**: 4 walls (the 2.5 mm skins print solid).

No supports anywhere: every window edge is 45° or steeper, and no bridge is longer than 33 mm.

---

## 2. Metal make parts (6061-T6)

| ID | Model # | Part | Qty | Finished size (mm) | Stock | Process | Critical features | Mass (g) |
|---|---|---|---|---|---|---|---|---|
| M01 | 101 | Adapter plate | 1 | Hex 76 AF × 6, R6 corners, spigot Ø39.982 × 1.8 | 8 mm plate | CNC | Spigot Ø40 g6; 6 × Ø5.5 on Ø52 at 30° + 60°; 6 × M4 through on Ø68 at 15° + 60°; 3 × Ø9 × 0.3 reliefs on Ø54; hub-face groove r 15–20 × 3 and 6 × Ø7 × 3 pockets on Ø52 at 0° + 60° | 64.0 |
| M02 | 115 | Front ring | 1 | Ø88 + tab, 4 thick, boss Ø10 × 3 | 8 mm plate (ring faced to 4, boss left at 7) | CNC | Bore Ø52.2; 7 × Ø3.4 on Ø71; 4 × M4 CSK; stop hole Ø5 H7 through ring + boss (m6 pin, light press); 4 kidney slots 11.5 wide on r 35.25 | 44.2 |
| M03 | 122 | Passive pin | 1 | Ø38 × 17.9 | Ø40 bar | Lathe | Journal Ø20 j6; spigot Ø16 g6; bore Ø10; 3 × M3 CSK on Ø30; 3 × M2.5 × 6 tapped on Ø15 | 16.2 |
| M04 | 134 | Encoder bracket | 1 | Ø40 × 4.9 | Ø42 bar | Lathe | Boss Ø22 on the 61804 inner ring only; 3 × M2.5 CSK on Ø15; 4 × M2.5 tapped on Ø34 | 10.4 |

---

## 3. Purchased parts

| ID | Model # | Part | Qty (+spare) | Exact spec | Notes |
|---|---|---|---|---|---|
| P01 | 132 | Passive bearing | 1 (+1) | **SKF 61804-2RS1**, 20 × 32 × 7, C 4.03 kN, C0 2.32 kN [A3] | Alternate: any 61804-2RS / 6804-2RS with C0 ≥ 2.3 kN |
| P02 | 120 | Stop pin | 1 (+1) | ISO 8734 Ø5 × 14, type A, m6 [A7] | Press 7 mm into M02 |
| P03 | 121 | Stop O-rings | 3 (+3) | 4.5 × 1.5 NBR 70 (DIN 3771) [A8] | Replace if cut or set |
| P04 | 114 | Joint dowels | 2 (+1) | ISO 8734 Ø4 × 16 | 8 mm into each upper-arm half |
| P05 | 127 | Hub dowels | 2 (+1) | ISO 8734 Ø3 × 16 | 5 mm into the elbow hub, 11 mm into the forearm (this is elbow P09) |
| P06 | 111, 118, 129 | Heat-set inserts M4 | 12 (+4) | **Ruthex RX-M4x8.1**, hole Ø5.6 × 9.1 [A6] | 4 collar, 4 crown, 4 forearm |
| P07 | 107, 123, 141, 143 | Heat-set inserts M3 | 14 (+4) | **Ruthex RX-M3x5.7**, hole Ø4.0 × 6.7 [A6] | 4 cap, 3 ear, 3 cheek B, 4 wrist |
| P08 | 136 | Output encoder PCB | 1 (+1) | 30 × 30 × 1.6, 4 × Ø2.7 on Ø34 | Shoulder P12 board |
| P09 | 137 | Output encoder IC | 1 (+1) | AS5047P-ATSM [A9] | — |
| P10 | 139 | Output magnet | 1 (+1) | ams AS5000-MD6H-2, Ø6 × 2.5 diametric [A9] | Bonded in the cover boss, 1.0 mm from the IC |

### 3.1 Fasteners (steel 12.9, black oxide)

| ID | Model # | Fastener | Standard | Qty (+spare) | Joint | Torque (N·m) | Threadlocker |
|---|---|---|---|---|---|---|---|
| F01 | 102 | M5 × 12 socket head | ISO 4762 | 6 (+2) | Adapter to shoulder flange | **8.0** (slip SF 4.64) | Loctite 243 |
| F02 | 103 | M5 washer | ISO 7089 | 6 (+2) | Under F01 | — | — |
| F03 | 105 | M4 × 16 socket head | ISO 4762 | 6 (+2) | Hub plate to adapter | **1.0** (slip SF 1.82; re-torque at 24 h) | Loctite 243 **in the adapter threads only** |
| F04 | 106, 113, 131 | M4 washer | DIN 9021 (4.3 / 12 × 1) [A13] | 14 (+4) | Under F03, F05, F09 | — | — |
| F05 | 112 | M4 × 16 socket head | ISO 4762 | 4 (+2) | Mid-span joint | **1.0** (no separation SF 4.0) | None (inserts) |
| F06 | 116 | M3 × 16 socket head | DIN 912 | 7 (+2) | Front ring + elbow cover to housing | **0.2** (as elbow) | None |
| F07 | 117 | M3 washer | ISO 7089 | 7 (+2) | Under F06 | — | — |
| F08 | 119 | M4 × 12 countersunk | ISO 10642 | 4 (+2) | Front ring to crown | **1.0** (slip SF 5.1) | None |
| F09 | 130 | M4 × 16 socket head | ISO 4762 | 4 (+2) | Cheek B to forearm | **1.0** (slip SF 4.4) | None |
| F10 | 109 | M3 × 8 countersunk | ISO 10642 | 4 (+2) | Cap | 0.4 | None |
| F11 | 124 | M3 × 8 countersunk | ISO 10642 | 3 (+2) | Pin to ear | **0.4** (SF 5.1) | None |
| F12 | 126 | M3 × 16 socket head | DIN 912 | 6 (+2) | Cheek A to elbow hub | **0.2** (as elbow; dowels carry the torque) | None |
| F13 | 135 | M2.5 × 10 countersunk | ISO 10642 | 3 (+2) | Bracket to pin | 0.2 | Loctite 243 (metal) |
| F14 | 138 | M2.5 × 4 socket head | DIN 912 | 4 (+2) | PCB to bracket | 0.2 | None |
| F15 | 142 | M3 × 12 socket head | DIN 912 | 3 (+2) | Cover to cheek B | 0.4 | None |

The calculated torques use the VDI 2230 preload table at μ 0.12 [A12]. F10 and F13–F15 are practical values for light joints. Keep anaerobic threadlocker off the printed parts and out of the inserts [A10].

### 3.2 Consumables

| Item | Spec | Where |
|---|---|---|
| ASA filament | Bambu ASA, ≈ 620 g with purge | A01–A07 |
| Retaining compound | **Loctite 641** + activator SF 7649 on aluminium [A11] | 61804 inner ring on the pin journal |
| Threadlocker | Loctite 243 | F01, F03 (adapter threads), F13 |
| Magnet adhesive | Structural epoxy | Magnet in the cover boss |

---

## 4. Fits and print calibration

The CAD is nominal. Set printed fits in Bambu Studio with per-object XY hole / contour compensation, as in `elbow/bom.md` §5.

| Feature | Target |
|---|---|
| Adapter hex in the 104 pocket (0.15 per flat) | Slides in by hand, no rattle |
| 61804 outer ring in cheek B (Ø32) | **Slip fit**, the ring must float axially (0.35–0.40) |
| Pin spigot Ø16 in the ear bore | Close slide fit |
| Wrist spigot Ø20 h7 in the future wrist / hand recess (H8) | Slide fit |
| Hub dowels Ø3 in cheek A | Light press |
| Insert holes Ø4.0 / Ø5.6 | Ruthex sizes [A6] |

---

## 5. Firmware requirements from the mechanics

1. Elbow soft limits 0° and 135°. **Cut motor current to 0 beyond them**: with the motor at the 10 A limit, any stop impact overloads the gearbox past its 8.23 N·m proof (calc §7).
2. Elbow approach speed ≤ 90°/s within the last few degrees before a soft limit. With the current cut, the stop absorbs the energy up to 98.6°/s.
3. Read the output AS5047P as the joint angle; use the motor encoder for commutation only.

---

## 6. Build checklist (in order)

1. Make M01–M04. Check the adapter spigot (Ø39.975–39.991) and the pin journal (Ø20 j6).
2. Print an ASA coupon with one RX-M4x8.1 and pull-test it. The calc assumes about 2,785 N; the joint needs ≥ 1,864 N.
3. Print A01–A07 and fit the inserts (including the 4 wrist inserts for the future hand).
4. Assemble in the order in `arm/parts.md` (Assembly).
5. Re-torque F03 after 24 h.
