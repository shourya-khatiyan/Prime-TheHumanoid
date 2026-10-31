# Elbow v0 cycloid: why it had to be hammered, and why it would not turn

Status: the printed 20:1 cycloid (this folder) was assembled once. The cage and both discs had to be driven into the housing with a hammer, and the joint then would not rotate. The dowels in the housing grooves were tight, and the dowels in the holes were tight as well. This note is the fit check of that build. Do not reprint this model.

The strength sections of `cad/calc.txt` (§1, §3–§5) are for parts that already have the CAD size and can mesh. Those sections are internally consistent. They do not cover this failure. The failure is in the fits, which §2b only checks at the ideal size.

## 1. What the model actually gives the dowels

ISO 8734 type A pins are tolerance m6. They are larger than the nominal diameter ([ISO 8734 table](https://www.pinfastener.com/uploads/48140/files/DIN-EN-ISO-8734.pdf), [ISO 286 m6](https://sfp.tw/en/tol/shaft/m6.html)):

| Nominal | Real pin | Where the CAD cuts the hole or groove |
|---|---|---|
| Ø5 ring pins and output pins | 5.004–5.012 | Ø5.000 (`GROOVE_CLEAR = 0`, and `D_PIN / 2` in the rear ring and the carrier) |
| Ø3 flange and hub dowels | 3.002–3.008 | Ø3.000 (`DOWEL_D / 2`) |

An m6 pin belongs in a reamed H7 hole. For Ø5 that hole is 5.000–5.012; for Ø3 it is 3.000–3.010. The fit is a transition: from a few micrometres of clearance to a light interference ([H7/m6](https://sfp.tw/en/tol/fit/h7-m6.html), [ISO 286 hole grades](http://www.jpe-innovations.com/precision-point/preferred-fits/)). The CAD hole is the bottom of that H7 band. A printed hole is smaller again, so every one of these joints is an interference before the printer adds its own error.

`GROOVE_CLEAR` is commented as “set from the printed slice test” and was left at 0. The BOM tells you to raise it if a slice is tight. The shipped model is the tight case.

## 2. Housing grooves (the dowels that stand in the disc’s path)

The ring-pin groove is a Ø5.000 cylinder on a Ø60 circle, open into the bore (`gen_actuator.py`, `GROOVE_CLEAR`). Two sizes already stop a drop-in:

- The pin is 5.004–5.012. The groove is 5.000. Interference 0.004–0.012 mm on the diameter, on a perfect print of the CAD.
- In the disc zone the bore cuts the groove down to a mouth of 4.993 mm. The smallest m6 pin is 5.004 mm, so the pin cannot pass that mouth. It has to be driven in along the groove. The rear 4.2 mm of the groove (mouth 4.67 mm) is there to keep a seated pin from falling inward. It does that only when the pin is already on centre.

The groove breaks into the bore, so it is an open path. Bambu Studio’s XY hole compensation does not act on open paths, and applying it there separates layers ([Bambu wiki](https://wiki.bambulab.com/en/software/bambu-studio/xy-hole-contour-compensation), [BambuStudio #10579](https://github.com/bambulab/BambuStudio/issues/10579)). The extra diameter has to be in the CAD. It was not.

FDM holes come out small. The Slic3r manual treats 0.1 mm on the diameter as a normal hole error ([Slic3r](https://manual.slic3r.org/troubleshooting/dimension-errors)). Measured holes of 0.2–0.3 mm small on the diameter are reported on the same class of printer ([Prusa forum](https://forum.prusa3d.com/forum/prusaslicer/hole-dimension-compensation/)). A clearance-fit study needed 0.13 mm of hole expansion per wall, about 0.26 mm on the diameter, before the fit opened up ([Processes, 2023](https://doi.org/10.3390/pr11102810)).

The solid side of the groove is the outside wall. The open side faces the disc. A pin forced into a groove that is smaller than the pin seats on the outer wall and moves inward, onto the lobes.

Calc §2b gives the disc 0.079 mm of radial gap to a nominal Ø5 pin, and 0.073 mm to a 5.012 pin. That gap is gone once the pin centre has moved inward by 0.073 mm. With the pin sitting on the outer wall, a groove that is 0.14 mm small on the diameter does that, before counting a fat disc outline. 0.14 mm is inside the error range above. Hammering the disc in then mashes the PET-CF lobes onto the pins. After that the mesh has no gap left, so it cannot turn.

The housing bore is not what blocked the disc. The disc sweeps to R 29.420 and the bore is R 29.97, a radial gap of 0.55 mm (`calc.txt` §2). The cage rear ring (R 25) and the pin plate (R 25.5) clear that bore by 4.5–5.0 mm. The cage is loose in the bore. The discs are tight on the pins.

## 3. Holes (the other dowels)

The same Ø5 m6 pins are the output pins. Three holes see them, and each one is drawn too small for a printed running or press fit.

| Hole | CAD | What a 5.012 pin needs | What a small print does |
|---|---|---|---|
| Rear ring and carrier, the press | Ø5.000 | already 0.004–0.012 mm tight on a perfect print | another 0.1–0.3 mm tight. Six pins driven in with a hammer do not stay parallel or on the Ø40 circle |
| Disc, the running hole | Ø7.20 (pin + 2×1.0 eccentricity + 2×0.10 play) | 0.094 mm radial play (§2b) | a hole 0.19 mm small on the diameter uses up that play. A hole 0.20 mm small is an interference at every cam angle |

The disc can orbit only while both gaps stay open: 0.07 mm on the ring pins and 0.09 mm on the output pins. A pin cocked by the hammered press uses the output-hole play even when the hole itself printed to size. That is the cage and the discs locking together, which is the “frame and disc would not rotate.”

The Ø3 dowels are the same mistake at the other end. Flange, retainer, cover and hub holes are Ø3.000 for pins of 3.002–3.008. They locate the cover and the forearm. They do not drive the cycloid. They are still a hammer fit in a print, and they get the same rule below.

## 4. What to do on the next printed gearbox

The coupon is a gate, not a note in the BOM. Print the groove and the holes in the real material, on the real nozzle, and try the real dowels before the housing or the discs are printed.

1. A printed hole or groove is drawn larger than the pin’s maximum, not at the nominal. m6 is already over nominal ([ISO 8734](https://www.pinfastener.com/uploads/48140/files/DIN-EN-ISO-8734.pdf), [m6 chart](https://sfp.tw/en/tol/shaft/m6.html)).
2. Open grooves cannot be saved in the slicer ([Bambu wiki](https://wiki.bambulab.com/en/software/bambu-studio/xy-hole-contour-compensation)). The extra diameter is a named CAD value. It has to be large enough that the pin still sits on its circle when the groove prints small.
3. Running play (lobe relief, output-hole play) has to be larger than the pin oversize plus the error measured on the coupon. 0.08 mm and 0.10 mm are smaller than a normal FDM hole error ([Slic3r](https://manual.slic3r.org/troubleshooting/dimension-errors), [Prusa forum](https://forum.prusa3d.com/forum/prusaslicer/hole-dimension-compensation/)).
4. A press in plastic is a light push after that measured error. It is not a metal H7 number, and it is not a hammer. If a pin needs a hammer, stop and reprint.
5. A cycloid that was hammered together is scrap. The lobes take a set, and the pins are no longer on their circle. Do not run it in.
6. A passing contact-stress or bearing check does not mean the fit passed. The fit line has to subtract the pin tolerance and a stated print allowance, and it has to fail the build when the gap left is zero or negative.
