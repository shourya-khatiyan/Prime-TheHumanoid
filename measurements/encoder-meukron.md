# Meukron encoder board

The board in the photos is a black square Meukron PCB. Silkscreen shows U1, 3.3V, MOSI, MISO, CLK, CS. The shoulder model does not use this board's real holes. The arm model does, partly.

## Measured or seen

| Item | Value | Status | Where it came from |
|---|---|---|---|
| Board name | Meukron | MEASURED | Silkscreen on the photo |
| Board outline | 30 × 30 | MEASURED | 2026-10-31. Thickness not taken |
| Mounting-hole diagonals | 24 and 19, centre to centre | MEASURED | Caliper. A rhombus, not a square. The 24 pair runs corner to corner of the board |
| Hole layout | Rhombus | MEASURED | The shoulder CAD puts these holes on a square Ø34 circle. That pattern is wrong |
| Each screw hole | An M3 screw passes freely | MEASURED | 2026-10-31. The hole itself was not calipered. A free M3 fit is a 3.2 mm or 3.4 mm hole |
| Chip position | On the board centre | MEASURED | 2026-10-31. Package name still not read off the chip |
| Rear cable | Leaves the motor rear, 30 from the axis, cover 11 × 5, can be bent | MEASURED | 2026-10-31. Same exit as the motor wires. See `eaglepower-la8308.md` |

## Used in CAD and not measured

| Item | Shoulder CAD | Arm CAD | Status |
|---|---|---|---|
| Board size | 30 × 30 × 1.6 | 30 × 30 × 1.6 | Outline 30 × 30 is now measured. Thickness 1.6 is still assumed |
| Mounting holes | 4 × Ø2.7 on a Ø34 circle, square, for M2.5 | Ø3.2 at the 24 / 19 diagonals | Shoulder pattern and M2.5 are wrong. Arm spacing is right. Arm Ø3.2 matches a close M3 fit |
| Screws | M2.5 × 5 pan into tapped bosses | M2.5 with a nut under the board | ASSUMED. The board takes an M3 screw |
| Chip | AS5047P, TSSOP-14, 5.0 × 4.4 × 1.1 | Same, top 1.1 above the board | CATALOGUE name. The photo chip was not identified |
| Magnet | Inside the cover already glued on the motor | — | The loose magnet size is no longer the interface |
| Magnet cover on the motor | Ø10, 6.5 past the hex face (13.2 past the mounting face) | MEASURED | Glued on. Both CAD holders (pin into the cap hole) are wrong |
| Magnet-to-chip gap | 1.25 at the 1.0 shim | Set from the holder length | Design target. Allowed range on the AS5047P board manual is 0.5–3 |

Datasheet limits, for when the magnet is chosen, not as a measurement of our parts:

- AS5047P wants 35–70 mT at the die, air gap 0.5–3 mm ([Infineon AS5047P datasheet](https://www.infineon.com/assets/row/public/documents/24/49/infineon-as5047p-datasheet-en.pdf), [ams AS5047P adapter board manual](https://media.digikey.com/pdf/Data%20Sheets/Austriamicrosystems%20PDFs/AS5047P-TS_EK_AB.pdf)).
- The kit magnet in that manual is Ø6 × 2.5, diametric. A different magnet needs its own diameter, thickness, and grade written here.

An M3 screw in a finished hole is 3.2 mm for a close fit and 3.4 mm for a normal fit ([EKINSUN hole chart, ISO 273](https://www.ekinsun.com/custom-parts/pcb-mounting-hole-standoff-chart/), [PCBMay mounting-hole chart](https://www.pcbmay.com/pcb-mounting-holes/)).

## Still needed

1. Board thickness.
2. The text printed on the chip.
