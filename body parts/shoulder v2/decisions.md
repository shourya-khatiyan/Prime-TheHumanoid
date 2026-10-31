# Shoulder actuator v2

The Rev 1.4 model in `body parts/shoulder` is unchanged. This folder is the redesign.

## Locked choices

- Spur gears. Output bearings stay a 61813 pair, span 21 mm.
- Stage 1 stays 18/36/90, module 0.8, 20°.
- Stage 2 is 18/27/72, module 1.222 (ring pitch diameter 88 mm), 25°, three planets. Lead crown on the drawing is 10 µm. The solid is a straight tooth; 10 µm is a grind/hob note.
- Sun-2 is a separate pinion on the carrier-1 plate. Ring-2 is a separate ring, not cut into the bearing cartridge. Carrier-2 clamps with three M5 screws.
- Rear stack follows the measured LA8308 and Meukron board. Envelope from the first mesh is Ø100 × 123 mm.
- No pin magnet holder. The magnet cover is already glued on the hex cap.
- Encoder screws follow the measured 24 mm and 19 mm diagonals, M3.
- Sun-1 uses 4 × M2 on a 38 mm circle. Flange Ø44. Housing bore at the flange is Ø45.
- Arm interface is unchanged: Ø40 pilot, 6 × M5 on Ø52.

## Why stage 2 moved

The old stage-2 teeth sat inside the 61813 bore, so the pitch diameter could not grow. At 30 N·m the sun face stress was 1350 MPa against a 1500 MPa case-hardened limit. Moving the mesh beside the bearings, to a pitch diameter of 88 mm and a 25° tooth, is the change that raises that margin without growing the 100 mm diameter. A 25° tooth is inside the ISO 6336 range of 15° to 25°.

The motor is still the continuous limit: 30 N·m at about 12 A. The gears are sized so they are no longer the part that gives up first.

The first pass of `cad/calc.py` puts stage-2 sun contact stress at 993 MPa at 30 N·m (factor 1.51 against 1500 MPa) and 1253 MPa in the combined proof case.

## Still open

- Magnet-cover wall thickness. The air gap to the cover is 1 mm. The magnetic gap is that plus the unknown wall.
- Re-run the face-load factor on the new carrier before calling the stress final. `cad/calc.py` is the first pass.
- The M3 screws that lock ring-2 to the housing, and the M3 screws that hold sun-2, need the same slip check the Rev 1.4 joints had.
