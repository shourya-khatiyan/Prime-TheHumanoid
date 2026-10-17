"""Write the shoulder milling quotation pack.

Geometry is Rev 1.4. This pack keeps only the parts a shop machines from bar
or plate, in three alloys. The rear plate is not included. Run:

  D:\\VAYN-CAD-env\\venv\\Scripts\\python.exe gen_milling_pack.py

Outputs, under shoulder/cad/milling/:
  step/VAYN_shoulder_milling.step
  quote/VAYN_shoulder_milling_quotation.pdf
  drawing/<one sheet per part>
  VAYN_shoulder_milling_quotation.zip
"""

import os
import re
import time
import zipfile
from xml.sax.saxutils import escape

import cadquery as cq
from OCP.BRepAdaptor import BRepAdaptor_Curve
from OCP.GCPnts import GCPnts_QuasiUniformDeflection
from OCP.HLRAlgo import HLRAlgo_Projector
from OCP.HLRBRep import HLRBRep_Algo, HLRBRep_HLRToShape
from OCP.TopAbs import TopAbs_EDGE
from OCP.TopExp import TopExp_Explorer
from OCP.TopoDS import TopoDS
from OCP.gp import gp_Ax2, gp_Dir, gp_Pnt
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A3, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen import canvas as pdfcanvas
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

import gen_actuator_3mf as g
import gen_actuator_occ as occ

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "milling")
STEP_NAME = "VAYN_shoulder_milling.step"
QUOTE_NAME = "VAYN_shoulder_milling_quotation.pdf"
ZIP_NAME = "VAYN_shoulder_milling_quotation.zip"

# one colour per alloy, so the step tree reads as three metals
ALLOY_COLOR = {
    "7075-T651": cq.Color(0.72, 0.75, 0.78),
    "16MnCr5": cq.Color(0.54, 0.44, 0.31),
    "42CrMo4": cq.Color(0.43, 0.35, 0.27),
}
DENSITY = {"7075-T651": 2.81, "16MnCr5": 7.85, "42CrMo4": 7.85}  # g/cm3

# model material key that build() must still be using
MODEL_MAT = {
    "01": "7075-T6", "06": "7075-T6", "15": "7075-T6", "45": "7075-T6",
    "18": "16MnCr5 carburized", "22": "16MnCr5 carburized",
    "24": "16MnCr5 carburized", "36": "16MnCr5 carburized",
    "16": "42CrMo4 nitrided", "33": "42CrMo4 nitrided",
    "21": "42CrMo4 Q&T", "32": "42CrMo4 Q&T", "42": "42CrMo4 Q&T",
}

# view name, projector direction, projector x, sign applied to view y
VIEWS = (
    ("FRONT", (0, 1, 0), (0, 0, 1), 1),
    ("END", (0, 0, -1), (1, 0, 0), -1),
    ("SIDE", (-1, 0, 0), (0, 0, 1), 1),
    ("ISO", (-1, 1, -1), (1, 1, 0), 1),
)

PAGE = landscape(A3)

# id, drawing file, title, qty, alloy, group, size, stock, process, finish, notes
PARTS = [
    ("01", "01_encoder_lid.pdf", "Encoder lid", 1, "7075-T651", "Housing family",
     "Ø59.8 × 2 mm", "5 mm 7075-T651 plate, shared with the cover",
     "CNC mill", "Clear anodize, type II",
     ["4 × M2 countersunk on Ø54 mm.", "Cable slot at 0°. Notch at 180° for the phase-lead slot.",
      "Screws are a light joint, 0.3 N·m."]),
    ("06", "06_magnet_holder.pdf", "Magnet holder", 1, "7075-T651", "Housing family",
     "Ø10 × 4.75 mm, pin Ø2.8 × 2 mm", "Ø12 × 40 mm 7075-T651 bar",
     "CNC lathe", "No anodize",
     ["Must stay non-magnetic. 7075 is non-magnetic.",
      "Magnet pocket Ø6 × 2.5 mm in the rear face.",
      "Pin Ø2.8 is a stand-in. Turn the pin to the measured rotor-cap hole, clearance 0–0.02 mm.",
      "Pocket concentric to the pin within 0.03 mm TIR."]),
    ("15", "15_housing.pdf", "Housing", 1, "7075-T651", "Housing family",
     "Ø100 × 87 mm", "Ø105 × 100 mm 7075-T6511 bar",
     "CNC lathe and mill, 4th axis for the radial holes",
     "Clear anodize, type II. Mask every fit and every thread.",
     ["Rear bore Ø94.5, rear 8 mm H7, open through the rear face (future metal plate).",
      "8 × Ø3.2 radial holes with 90° countersinks at Z 6.1, centres 0.1 mm forward of the plug threads.",
      "Rear-face notches 4 × 1 mm at 0° and 15 × 3 mm at 180°.",
      "Partition 2.5 mm at Z 45–47.5. Labyrinth Ø41.0 H8.",
      "Ring-1 bore Ø85 K6. Cartridge bore Ø89 G7.",
      "12 cooling slots, 3 × 20 mm. Two ring-1 dowel slots, width 3.02–3.04 mm, 1.5 mm deep.",
      "8 × M3 in the front face, 6 mm thread engagement."]),
    ("45", "45_front_cover.pdf", "Front cover", 1, "7075-T651", "Housing family",
     "Ø100 / Ø80 × 3 mm", "5 mm 7075-T651 plate, 110 × 110 mm, shared with the lid",
     "CNC mill", "Clear anodize, type II",
     ["8 × M2.5 countersunk on Ø93.2 mm.",
      "Lip touches the front bearing outer ring only.",
      "Hall-sensor pocket at 270°, with a wire slot to the outside edge."]),
    ("18", "18_sun_1.pdf", "Sun-1", 1, "16MnCr5", "Gears",
     "Flange Ø40 × 3 mm, teeth Ø16 × 10.4 mm, overall 18.2 mm",
     "Ø45 × 30 mm 16MnCr5, annealed, same heat as the other 16MnCr5",
     "Turn, hob or shape",
     "Carburize, case 0.12–0.18 mm, 58–62 HRC, core 30–40 HRC. Hard-finish the teeth.",
     ["18 teeth, module 0.8, 20° pressure angle, profile shift 0.",
      "Span over 3 teeth W3 = 6.082 mm, minus 0.015 / plus 0.",
      "ISO 1328 grade 6–7. Backlash 0.05 ± 0.02 mm per mesh.",
      "4 × M3 countersunk on Ø31 mm, and 4 × M3 countersunk on Ø25 mm at 45°. Use the pattern the rotor has.",
      "Bore Ø3.5 × 10.5 mm for the motor stub. Hub relief Ø18 × 0.5 mm.",
      "Flange Ø40 h8."]),
    ("22", "22_carrier_1_front.pdf", "Carrier-1 front and sun-2", 1, "16MnCr5", "Gears",
     "Plate Ø60 mm, sun Ø20 × 10 mm face, overall about 24 mm",
     "Ø65 × 35 mm 16MnCr5, annealed, same heat",
     "Turn, hob, drill",
     "Carburize the sun only. Case 0.15–0.20 mm, 58–62 HRC. Mask the plate.",
     ["Sun-2: 18 teeth, module 1.0. Span over 3 teeth W3 = 7.609 mm, minus 0.015 / plus 0.",
      "ISO 1328 grade 6–7.",
      "3 × Ø8 mm R7 holes for the planet pins.",
      "3 × M3 countersunk on Ø44 mm.",
      "Rear recess Ø19 × 1.2 mm, so the sun-1 tips clear by 1.5 mm."]),
    ("24", "24_planet_1.pdf", "Planet-1", 3, "16MnCr5", "Gears",
     "Ø30.4 × 10 mm face, bore Ø12 mm",
     "Ø35 × 120 mm 16MnCr5 bar, same heat. Hob the three blanks as one stack.",
     "Turn, hob, part off",
     "Carburize, case 0.12–0.18 mm, 58–62 HRC. Grind the bore after hardening.",
     ["36 teeth, module 0.8. Span over 5 teeth W5 = 11.008 mm, minus 0.015 / plus 0.",
      "ISO 1328 grade 6–7.",
      "Bore Ø12 N6, roundness IT5/2, Ra 0.8 µm or finer.",
      "Three identical parts. In the STEP they are 24.1, 24.2 and 24.3."]),
    ("36", "36_planet_2.pdf", "Planet-2", 3, "16MnCr5", "Gears",
     "Ø29 × 10 mm face, bore Ø12 mm",
     "Same Ø35 bar as planet-1",
     "Turn, hob, part off",
     "Carburize, case 0.15–0.20 mm, 58–62 HRC. Grind the bore after hardening.",
     ["27 teeth, module 1.0. Span over 4 teeth W4 = 10.687 mm, minus 0.015 / plus 0.",
      "ISO 1328 grade 6–7. This is the high-load mesh, about 1,350 MPa at 30 N·m.",
      "Bore Ø12 N6.",
      "Three identical parts. In the STEP they are 36.1, 36.2 and 36.3."]),
    ("16", "16_ring_1.pdf", "Ring-1", 1, "42CrMo4", "Around the gears",
     "Ø85 h5 × 15.35 mm", "Ø105 mm 42CrMo4 (EN19) bar, Q&T, shared with the other EN19 parts",
     "Turn, then wire-EDM the teeth",
     "Buy at 28–34 HRC. Gas or plasma nitride after EDM. No tooth grind. Allow 0.03–0.04 mm growth.",
     ["Internal gear, 90 teeth, module 0.8.",
      "Measure between Ø1.2 mm pins, Mi = 70.813 mm, plus 0.015 / minus 0.",
      "2 × Ø3 mm H7 dowel holes, 7 mm deep from the rear face, on Ø79.5 mm."]),
    ("21", "21_carrier_1_rear.pdf", "Carrier-1 rear", 1, "42CrMo4", "Around the gears",
     "Ø60 × 14 mm, three posts", "Same EN19 bar",
     "CNC mill", "Already quenched and tempered, 28–34 HRC. Do not nitride.",
     ["3 × Ø8 mm R7 pin holes on Ø43.2 mm.",
      "Posts tapped M3, on Ø44 mm.",
      "R7 on an h6 pin is 4–28 µm interference."]),
    ("32", "32_carrier_2_rear.pdf", "Carrier-2 rear", 1, "42CrMo4", "Around the gears",
     "Hub Ø65 × 10 mm, envelope about Ø67 × 21 mm", "Same EN19 bar",
     "CNC mill", "Already quenched and tempered, 28–34 HRC. Do not nitride.",
     ["Hub Ø65 j5, rear inner-ring seat.",
      "3 × Ø8 mm R7 holes on Ø45 mm, 6 mm deep, ending on a 1.0 mm shoulder.",
      "Ø3 mm hole through each shoulder, for venting and punch-out.",
      "Rear lightening groove Ø42–Ø59 mm, 3 mm deep. It must not break the pin shoulder.",
      "Posts tapped M4. Post faces are the inner-ring shoulders."]),
    ("33", "33_cartridge.pdf", "Bearing cartridge and ring-2", 1, "42CrMo4", "Around the gears",
     "Flange Ø100 × 7.5 mm, spigot Ø89 mm, overall 31.5 mm", "Same EN19 bar",
     "Turn, wire-EDM the ring-2 teeth, drill and tap",
     "Buy at 28–34 HRC. Tap the 8 × M2.5 before nitriding and mask them. Nitride after EDM. Finish Ø89 and Ø85 after nitriding, or mask them.",
     ["Spigot Ø89 h6.",
      "Bearing bore Ø85 is selective: 3–10 µm larger than the measured 61813 outer diameter. The rear ring must still slide.",
      "Ring-2: 72 teeth, module 1.0. Between Ø1.5 mm pins, Mi = 70.499 mm, plus 0.015 / minus 0.",
      "8 × M3 counterbored holes on Ø93 mm. 2 × Ø4 mm dowel holes.",
      "8 × M2.5 tapped for the cover, before nitride."]),
    ("42", "42_carrier_2_front.pdf", "Carrier-2 front", 1, "42CrMo4", "Around the gears",
     "Flange Ø78 mm, hub Ø65 mm, overall 14 mm", "Same EN19 bar",
     "CNC lathe and mill", "Already quenched and tempered, 28–34 HRC. Do not nitride.",
     ["Hub Ø65 j5, front inner-ring seat.",
      "6 × M5 tapped, 8 mm deep, on Ø52 mm.",
      "Pilot Ø40 H7 × 2 mm. Runout within 0.02 mm TIR. Face flatness within 0.03 mm.",
      "3 × Ø8 mm R7 holes, blind 6.3 mm deep.",
      "3 × M4 counterbores on Ø54 mm.",
      "Ø3 mm radial hole in the rim at Z 98.75 for the homing magnet."]),
]

# not in the step. listed so the actuator is complete on paper.
OTHERS = [
    ("3D-printed this order", "08 Rear mount plate", "1",
     "Rim Ø100 × 2 mm plus plug Ø94.5 × 8 mm", "130 g",
     "Printed plastic this build. A later metal plate is 7075-T651.",
     "Not milled. The housing is still cut to accept a metal plug later."),
    ("Bought shaft, cut to length", "26 Planet pins 1", "3",
     "Ø8 h6 × 17 mm", "6.6 g each",
     "52100, through-hardened 58–64 HRC, ground, Ra 0.2 µm or finer",
     "Not milled. Pressed into the carrier. Do not use a g6 shaft or an m6 dowel."),
    ("Bought shaft, cut to length", "38 Planet pins 2", "3",
     "Ø8 h6 × 23 mm", "9.0 g each",
     "Same 52100 shaft as the stage-1 pins",
     "Grind a 0.2 mm vent flat on the front 6 mm only, clear of the needle track."),
    ("Shim or catalogue ring", "20 Carrier-1 rear washer", "1",
     "Ø48 / Ø42 × 0.3 mm", "1.0 g", "Hardened spring steel, flat within 0.02 mm",
     "Laser, wire-cut, or a shim stack. Not a milled part."),
    ("Shim or catalogue ring", "30 Carrier-1 front washer", "1",
     "Ø40 / Ø24 × 0.3 mm", "1.9 g", "Same strip", "Runs between the two carriers."),
    ("Shim or catalogue ring", "27 28 39 40 Planet washers", "12",
     "Ø14 / Ø8.2 × 0.3 mm", "0.24 g each",
     "DIN 988 8 × 14 × 0.3, or the same strip",
     "Bore must spin free on the Ø8 h6 pin. Check one sample first."),
    ("Shim stock", "48 Motor shims", "a 0.25 and 0.5 mm set",
     "Ø50 / Ø19.5 mm, 4 × Ø4.5 on Ø40 at 45°", "12.5 g for two 0.5 mm shims",
     "Stainless or spring-steel shim stock, flat within 0.02 mm",
     "Nominal pack is 1.0 mm. Not milled."),
    ("Catalogue", "12 Motor", "1", "EaglePower LA8308, Ø92.0 × 32.5 mm", "336 g",
     "KV90, front stub Ø2.9 × 8.9, rear cap Ø17.4", "Purchase."),
    ("Catalogue", "02 Lid screws", "4", "M2 × 4 countersunk", "0.13 g each",
     "ISO 7046 or 14581, grade 8.8 or A2", "Purchase. Torque 0.3 N·m."),
    ("Catalogue", "03 Encoder PCB", "1", "30 × 30 × 1.6 mm", "—",
     "FR4, 4 × Ø2.7 on Ø34", "Purchase."),
    ("Catalogue", "04 Encoder IC", "1", "TSSOP-14", "—", "AS5047P-ATSM", "Purchase."),
    ("Catalogue", "05 PCB screws", "4", "M2.5 × 5 pan head", "0.46 g each",
     "ISO 7045 or 14583", "Purchase. Torque 0.4 N·m."),
    ("Catalogue", "07 Encoder magnet", "1", "Ø6 × 2.5 mm, diametric", "0.53 g",
     "NdFeB, AS5000-MD6H-2", "Purchase. Glue into the magnet holder."),
    ("Catalogue", "09 Plate screws", "8", "M3 × 8 countersunk", "0.55 g each",
     "ISO 10642, grade 12.9", "Purchase. Used when the metal plate is fitted. Torque 1.2 N·m."),
    ("Catalogue", "11 Stator screws", "4", "M4 × 10 countersunk", "1.24 g each",
     "ISO 10642", "Purchase. 2.0 N·m maximum into the motor."),
    ("Catalogue", "17 Ring-1 dowels", "2", "Ø3 × 8 mm m6", "0.44 g each",
     "ISO 8734, hardened", "Purchase. Pressed into ring-1, sliding in the housing slot."),
    ("Catalogue", "19 Sun-1 screws", "4", "M3 × 5 countersunk", "0.38 g each",
     "ISO 10642, grade 12.9", "Purchase. Torque 0.8 N·m."),
    ("Catalogue", "23 Carrier-1 screws", "3", "M3 × 10 countersunk", "0.66 g each",
     "ISO 10642, grade 12.9", "Purchase. Torque 1.2 N·m."),
    ("Catalogue", "25 and 37 Needle bearings", "6", "HK0810, 8 × 12 × 10 mm", "3.1 g catalogue",
     "INA or SKF, open ends", "Purchase. Press into the Ø12 N6 bores."),
    ("Catalogue", "29 Wave spring", "1", "Smalley SSB-0335", "8.6 g in the model",
     "Carbon steel. Bore clears 71.4, outside fits inside 85.", "Purchase."),
    ("Catalogue", "31 Rear output bearing", "1", "61813-2Z/C3, 65 × 85 × 10 mm", "130 g catalogue",
     "Metal shields. C3 is required.", "Purchase. Spare bearing is useful for matching the cartridge bore."),
    ("Catalogue", "34 Cartridge screws", "8", "M3 × 10 socket head", "1.01 g each",
     "ISO 4762, grade 12.9", "Purchase. Torque 1.2 N·m."),
    ("Catalogue", "35 Cartridge dowels", "2", "Ø4 × 8 mm m6", "0.78 g each",
     "ISO 8734, hardened", "Purchase."),
    ("Catalogue", "41 Front output bearing", "1", "61813-2RS1/C3, 65 × 85 × 10 mm", "131 g catalogue",
     "Contact seals. C3 is required.", "Purchase. The seals are the gearbox seal."),
    ("Catalogue", "43 Carrier-2 screws", "3", "M4 × 16 socket head", "2.65 g each",
     "ISO 4762, grade 12.9", "Purchase. Torque 4.0 N·m exactly."),
    ("Catalogue", "44 Homing magnet", "1", "Ø3 × 2 mm, axial, N52", "0.10 g",
     "NdFeB", "Purchase. Glued into the output-flange rim."),
    ("Catalogue", "46 Hall sensor", "1", "SOT-23", "—", "TI DRV5033FAQDBZR", "Purchase."),
    ("Catalogue", "47 Cover screws", "8", "M2.5 × 6 countersunk", "0.29 g each",
     "ISO 7046 or 14581", "Purchase. Torque 0.8 N·m, low-strength threadlocker."),
]

FITS = [
    ("Ring-1 outside in the housing", "Ø85 K6 / h5"),
    ("Cartridge spigot in the housing", "Ø89 G7 / h6"),
    ("61813 outer rings in the cartridge", "Bore = measured bearing OD +3 / +10 µm"),
    ("61813 inner rings on carrier-2", "Ø65 j5"),
    ("Sun-1 flange in the partition", "Ø41.0 H8 / Ø40 h8"),
    ("Future plate plug in the housing", "Ø94.5 H7 / k6"),
    ("Planet bore for HK0810", "Ø12 N6"),
    ("Planet pins in the carriers", "Ø8 h6 in Ø8 R7, 4–28 µm interference"),
    ("Output flange pilot", "Ø40 H7 × 2 mm, runout ≤ 0.02 mm"),
    ("Sun-1 span", "W3 = 6.082 −0.015 / 0"),
    ("Planet-1 span", "W5 = 11.008 −0.015 / 0"),
    ("Sun-2 span", "W3 = 7.609 −0.015 / 0"),
    ("Planet-2 span", "W4 = 10.687 −0.015 / 0"),
    ("Ring-1, over Ø1.2 pins", "Mi = 70.813 +0.015 / 0"),
    ("Ring-2, over Ø1.5 pins", "Mi = 70.499 +0.015 / 0"),
    ("Gear quality", "Suns and planets ISO 1328 grade 6–7. Rings grade 7–8."),
    ("Untoleranced sizes", "ISO 2768-1 class m, ISO 2768-2 class K"),
]

STOCK = [
    ("7075-T6511 round", "Ø105 × 100 mm", "Housing"),
    ("7075-T651 plate", "5 mm, 110 × 110 mm", "Front cover and encoder lid"),
    ("7075-T651 round", "Ø12 × 40 mm", "Magnet holder"),
    ("42CrMo4 / EN19, Q&T 28–34 HRC", "Ø105 × 160 mm, one bar",
     "Ring-1, cartridge, carrier-1 rear, both carrier-2 halves"),
    ("16MnCr5, annealed, one heat", "Ø65 × 35, Ø45 × 30, Ø35 × 120 mm",
     "Carrier-1 front and sun-2, sun-1, six planets"),
]


def part_by_id(part_id):
    """Return the spec row for a numeric part id such as '15'."""
    for row in PARTS:
        if row[0] == part_id:
            return row
    raise KeyError(part_id)


def split_id(model_name):
    """Return (base id, suffix) from a model name. '24.2 Planet' -> ('24', 2)."""
    token = model_name.split()[0]
    base, _, suffix = token.partition(".")
    return base, int(suffix) if suffix else 0


def step_label(model_name, alloy):
    """Short solid name for the step tree."""
    token = model_name.split()[0]
    title = part_by_id(token.split(".")[0])[2]
    return f"{token} {title} ({alloy})"


def check_views():
    """Fail fast if a view maps the model axes onto the wrong sheet axes."""
    box = cq.Solid.makeBox(10, 4, 6)  # x 0..10, y 0..4, z 0..6
    expect = {
        "FRONT": (0, 6, 0, 10),
        "END": (0, 10, 0, 4),
        "SIDE": (0, 6, 0, 4),
    }
    for name, direction, xdir, y_sign in VIEWS:
        if name not in expect:
            continue
        lines = project(box, direction, xdir, y_sign, 0.2)
        xs = [p[0] for ln in lines for p in ln]
        ys = [p[1] for ln in lines for p in ln]
        got = (min(xs), max(xs), min(ys), max(ys))
        want = expect[name]
        if any(abs(a - b) > 0.2 for a, b in zip(got, want)):
            raise RuntimeError(f"view {name} spans {got}, expected {want}")


def project(shape, direction, xdir, y_sign, tol):
    """Visible edges of shape as polylines in the view plane, in millimetres.

    hlr already writes the view plane into point x and y. y_sign flips a view
    whose projector y comes out reversed.
    """
    ax = gp_Ax2(gp_Pnt(0, 0, 0), gp_Dir(*direction), gp_Dir(*xdir))
    algo = HLRBRep_Algo()
    algo.Add(shape.wrapped)
    algo.Projector(HLRAlgo_Projector(ax))
    algo.Update()
    algo.Hide()
    shown = HLRBRep_HLRToShape(algo)
    lines = []
    for getter in (shown.VCompound, shown.OutLineVCompound):
        comp = getter()
        if comp is None or comp.IsNull():
            continue
        exp = TopExp_Explorer(comp, TopAbs_EDGE)
        while exp.More():
            curve = BRepAdaptor_Curve(TopoDS.Edge_s(exp.Current()))
            disc = GCPnts_QuasiUniformDeflection(curve, tol)
            if disc.IsDone() and disc.NbPoints() >= 2:
                lines.append([(disc.Value(i).X(), y_sign * disc.Value(i).Y())
                              for i in range(1, disc.NbPoints() + 1)])
            exp.Next()
    return lines


def collect(model):
    """Pull the milling solids out of the full actuator build.

    returns a list of dicts, one per solid, sorted by part number.
    """
    found = {row[0]: [] for row in PARTS}
    for name, mat, solid in model:
        base, suffix = split_id(name)
        if base not in found:
            continue
        if mat != MODEL_MAT[base]:
            raise RuntimeError(f"{name} is {mat}, expected {MODEL_MAT[base]}")
        row = part_by_id(base)
        alloy = row[4]
        volume = solid.volume()  # mm3
        found[base].append({
            "name": step_label(name, alloy),
            "alloy": alloy,
            "solid": solid,
            "suffix": suffix,
            "mass_g": volume / 1000.0 * DENSITY[alloy],
            "box": solid.bounding_box(),
        })
    items = []
    for row in PARTS:
        parts = found[row[0]]
        if len(parts) != row[3]:
            raise RuntimeError(f"part {row[0]} count {len(parts)}, expected {row[3]}")
        items.extend(sorted(parts, key=lambda item: item["suffix"]))
    return items


def write_step(items, path):
    """Write one named step assembly of the milling solids, in millimetres."""
    def order(item):
        # tree order is the part number, so the shop can tick the list
        token = item["name"].split()[0]
        base, _, suffix = token.partition(".")
        return (int(base), int(suffix) if suffix else 0)

    assy = cq.Assembly(name="VAYN_Shoulder_Milling_Qty1")
    for item in sorted(items, key=order):
        assy.add(item["solid"].s, name=item["name"], color=ALLOY_COLOR[item["alloy"]])
    assy.save(path, exportType="STEP")


def check_step_names(path):
    """Raise if the step tree contains a part that is not milled."""
    text = open(path, encoding="utf-8", errors="ignore").read()
    names = re.findall(r"PRODUCT\('([^']*)'", text)
    allowed = {row[0] for row in PARTS}
    bad = []
    for name in names:
        token = name.split()[0] if name else ""
        if not token or not token[0].isdigit():
            continue
        if token.split(".")[0] not in allowed:
            bad.append(name)
    if bad:
        raise RuntimeError("step lists non-milling parts: " + "; ".join(bad))
    missing = [row[2] for row in PARTS if not any(row[2] in name for name in names)]
    if missing:
        raise RuntimeError("step is missing: " + ", ".join(missing))
    return len([n for n in names if n.split() and n.split()[0][0].isdigit()])


def register_fonts():
    """Use Arial so the pdf can print diameters and other symbols."""
    pdfmetrics.registerFont(TTFont("Arial", r"C:\Windows\Fonts\arial.ttf"))
    pdfmetrics.registerFont(TTFont("Arial-Bold", r"C:\Windows\Fonts\arialbd.ttf"))


def styles():
    """Paragraph styles for the quotation pdf."""
    common = dict(fontName="Arial", textColor=colors.black, leading=11)
    return {
        "h1": ParagraphStyle("h1", fontName="Arial-Bold", fontSize=16, leading=20, spaceAfter=6),
        "h2": ParagraphStyle("h2", fontName="Arial-Bold", fontSize=12, leading=15, spaceBefore=12, spaceAfter=4),
        "body": ParagraphStyle("body", fontSize=9, alignment=TA_LEFT, spaceAfter=4, **common),
        "cell": ParagraphStyle("cell", fontName="Arial", fontSize=7.5, leading=9.5, textColor=colors.black),
        "head": ParagraphStyle("head", fontName="Arial-Bold", fontSize=7.5, leading=9.5, textColor=colors.white),
        "group": ParagraphStyle("group", fontName="Arial-Bold", fontSize=8, leading=10, textColor=colors.black),
    }


def P(text, style):
    """Paragraph with symbols escaped for reportlab."""
    return Paragraph(escape(str(text)), style)


def section_table(headers, rows, widths, sty):
    """Table with a dark header. A row that is a single string spans the table."""
    head = [P(h, sty["head"]) for h in headers]
    data = [head]
    spans = []
    for row in rows:
        if isinstance(row, str):
            data.append([P(row, sty["group"])] + [""] * (len(headers) - 1))
            spans.append(len(data) - 1)
        else:
            data.append([P(cell, sty["cell"]) for cell in row])
    style = TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.Color(0.12, 0.12, 0.12)),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Arial-Bold"),
        ("GRID", (0, 0), (-1, -1), 0.3, colors.Color(0.25, 0.25, 0.25)),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING", (0, 0), (-1, -1), 3),
        ("RIGHTPADDING", (0, 0), (-1, -1), 3),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("BACKGROUND", (0, 1), (-1, -1), colors.white),
    ])
    for index in spans:
        style.add("SPAN", (0, index), (-1, index))
        style.add("BACKGROUND", (0, index), (-1, index), colors.Color(0.88, 0.88, 0.88))
    table = Table(data, colWidths=[w * mm for w in widths], repeatRows=1)
    table.setStyle(style)
    return table


def write_quote(path, items):
    """Write the guidance pdf: milled parts, stock, and everything left out."""
    sty = styles()
    story = []
    story.append(P("VAYN shoulder actuator — milling quotation", sty["h1"]))
    story.append(P("Pack A. Geometry revision 1.4. Quantity: one actuator. Units: millimetres. Date: 17 October 2026.", sty["body"]))
    story.append(P("Quote the parts in section 1 only. The price should include the metal, machining, wire-EDM of the two internal gears, carburizing, nitriding, and clear anodize. Deliver finished parts. Section 4 is not part of the machining price.", sty["body"]))
    story.append(P("The STEP file is the geometric master. Each drawing controls the features printed on that sheet. Sizes with no tolerance on the sheet follow ISO 2768-1 class m and ISO 2768-2 class K.", sty["body"]))
    story.append(P("Part 08, the rear mount plate, is 3D-printed for this build and is not in the STEP. The housing is still machined with the Ø94.5 H7 bore and the eight radial screw holes, so a metal plate can replace the print later.", sty["body"]))

    story.append(P("Three metals", sty["h2"]))
    story.append(P("7075-T651 for the housing family: lid, magnet holder, housing, front cover. 16MnCr5, carburized, for every external gear, including carrier-1 front because sun-2 is cut on that part. 42CrMo4 (EN19), quenched and tempered, for ring-1, the cartridge, and the three carrier pieces that are not gears. Ring-1 and the cartridge are nitrided. The carriers are not.", sty["body"]))

    story.append(P("1. Parts to machine", sty["h2"]))
    by_name = {}
    for item in items:
        by_name.setdefault(item["name"].split()[0].split(".")[0], []).append(item)
    rows = []
    last_group = None
    milled_mass = 0.0
    for row in PARTS:
        if row[5] != last_group:
            last_group = row[5]
            rows.append(f"{row[5]} — {row[4]}")
        solids = by_name[row[0]]
        each = solids[0]["mass_g"]
        milled_mass += each * row[3]
        mass = f"{each:.2f} g each" if row[3] > 1 else f"{each:.2f} g"
        notes = " ".join(row[10])
        rows.append([
            f"{row[0]}  {row[2]}",
            str(row[3]),
            row[6],
            mass,
            row[7],
            f"{row[8]}. {row[9]}",
            notes,
        ])
    rows.append([
        "Milled parts, total", "17", "—", f"{milled_mass:.0f} g", "—", "—",
        "Seventeen solids. Thirteen unique parts.",
    ])
    # part, qty, size, mass, stock, process, notes
    story.append(section_table(
        ["Part", "Qty", "Finished size", "Mass", "Raw stock", "Process and finish", "Controlled features"],
        rows, [32, 12, 42, 22, 48, 55, 185], sty))

    story.append(P("2. Metal to buy for this one actuator", sty["h2"]))
    story.append(P("One heat of 16MnCr5 covers every gear, so one carburizing coupon qualifies the batch. One EN19 bar covers the rings and the carriers. No EN24 and no 6061.", sty["body"]))
    story.append(section_table(
        ["Material", "Buy", "Used for"],
        [[a, b, c] for a, b, c in STOCK],
        [70, 80, 246], sty))

    story.append(P("3. Fits and gear checks", sty["h2"]))
    story.append(section_table(
        ["Feature", "Value"],
        [[a, b] for a, b in FITS],
        [120, 276], sty))

    story.append(P("4. Not in the STEP — do not mill these", sty["h2"]))
    story.append(P("These complete the actuator. They are bought, cut from ground shaft, cut from shim stock, or 3D-printed. They are not in the milling price.", sty["body"]))
    other_rows = []
    last = None
    for group, name, qty, size, mass, spec, why in OTHERS:
        if group != last:
            other_rows.append(group)
            last = group
        other_rows.append([name, qty, size, mass, spec, why])
    story.append(section_table(
        ["Item", "Qty", "Size", "Mass", "Material or spec", "Why it is not milled"],
        other_rows, [48, 28, 62, 32, 100, 126], sty))

    story.append(P("5. Still open before the pin is finished", sty["h2"]))
    story.append(P("The plain hole in the motor rear cap is not measured yet. The model uses Ø3 mm, at least 2 mm deep. Machine the magnet-holder pocket now, and turn the pin after that hole is measured. The cartridge bore Ø85 is machined after the two 61813 bearings are measured.", sty["body"]))

    def footer(c, doc):
        c.saveState()
        c.setFont("Arial", 8)
        c.drawString(14 * mm, 8 * mm, "VAYN shoulder milling pack A  ·  one actuator  ·  step/VAYN_shoulder_milling.step")
        c.drawRightString(PAGE[0] - 14 * mm, 8 * mm, str(doc.page))
        c.restoreState()

    doc = SimpleDocTemplate(path, pagesize=PAGE, leftMargin=12 * mm, rightMargin=12 * mm,
                            topMargin=12 * mm, bottomMargin=14 * mm, title="VAYN shoulder milling quotation")
    doc.build(story, onFirstPage=footer, onLaterPages=footer)
    return milled_mass


def wrap_lines(text, font, size, width):
    """Break text into lines that fit a width in points."""
    words = text.split()
    lines, cur = [], ""
    for word in words:
        trial = (cur + " " + word).strip()
        if pdfmetrics.stringWidth(trial, font, size) <= width:
            cur = trial
        else:
            if cur:
                lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines


def draw_sheet(path, row, sample):
    """One A3 sheet: four views of the part, plus the machining notes."""
    part_id, filename, title, qty, alloy, group, size, stock, process, finish, notes = row
    c = pdfcanvas.Canvas(path, pagesize=PAGE)
    c.setTitle(f"{part_id} {title}")
    width, height = PAGE
    c.setStrokeColor(colors.black)
    c.setLineWidth(1)
    c.rect(8 * mm, 8 * mm, width - 16 * mm, height - 16 * mm)
    c.setFont("Arial-Bold", 13)
    c.drawString(12 * mm, height - 16 * mm, f"VAYN shoulder  ·  milling drawing  ·  {part_id}  {title}")
    c.setFont("Arial", 8)
    c.drawRightString(width - 12 * mm, height - 15 * mm, "Pack A  ·  geometry Rev 1.4  ·  qty 1 actuator")

    # centre the solid so the views fill the sheet
    box = sample["box"]
    cx = (box[0] + box[3]) / 2
    cy = (box[1] + box[4]) / 2
    cz = (box[2] + box[5]) / 2
    local = sample["solid"].s.translate(cq.Vector(-cx, -cy, -cz))
    dx, dy, dz = box[3] - box[0], box[4] - box[1], box[5] - box[2]

    view_left, view_bottom = 12 * mm, 14 * mm
    view_w, view_h = width * 0.62, height - 32 * mm
    cell_w, cell_h = view_w / 2, view_h / 2
    labels = {
        "FRONT": "FRONT  ·  Z horizontal, +X up",
        "END": "END  ·  from the arm side (+Z)",
        "SIDE": "SIDE  ·  Z horizontal, +Y up",
        "ISO": "ISOMETRIC",
    }
    for index, (vname, direction, xdir, y_sign) in enumerate(VIEWS):
        col, row_i = index % 2, index // 2
        x0 = view_left + col * cell_w
        y0 = view_bottom + (1 - row_i) * cell_h
        c.setStrokeColor(colors.Color(0.8, 0.8, 0.8))
        c.setLineWidth(0.3)
        c.rect(x0, y0, cell_w, cell_h)
        c.setFillColor(colors.black)
        c.setFont("Arial", 7)
        c.drawString(x0 + 2 * mm, y0 + cell_h - 4 * mm, labels[vname])
        try:
            lines = project(local, direction, xdir, y_sign, 0.2)
        except Exception as exc:  # projection of one view must not drop the sheet
            c.setFont("Arial", 8)
            c.drawString(x0 + 4 * mm, y0 + cell_h / 2, f"view failed: {exc}")
            continue
        if not lines:
            c.drawString(x0 + 4 * mm, y0 + cell_h / 2, "no visible edges")
            continue
        xs = [p[0] for ln in lines for p in ln]
        ys = [p[1] for ln in lines for p in ln]
        span_x = max(xs) - min(xs) or 1
        span_y = max(ys) - min(ys) or 1
        pad = 8 * mm
        scale = min((cell_w - 2 * pad) / span_x, (cell_h - 2 * pad) / span_y)
        ox = x0 + cell_w / 2 - (min(xs) + max(xs)) / 2 * scale
        oy = y0 + cell_h / 2 - (min(ys) + max(ys)) / 2 * scale - 1 * mm
        c.setStrokeColor(colors.black)
        c.setLineWidth(0.4)
        c.setLineCap(1)
        c.setLineJoin(1)
        for ln in lines:
            pth = c.beginPath()
            pth.moveTo(ox + ln[0][0] * scale, oy + ln[0][1] * scale)
            for px, py in ln[1:]:
                pth.lineTo(ox + px * scale, oy + py * scale)
            c.drawPath(pth, stroke=1, fill=0)
        paper = scale / (72 / 25.4)
        if paper >= 1:
            scale_txt = f"scale {paper:.2f}:1"
        else:
            scale_txt = f"scale 1:{1 / paper:.2f}"
        c.setFont("Arial", 7)
        c.drawString(x0 + 2 * mm, y0 + 2 * mm, f"{scale_txt}   view span {span_x:.1f} × {span_y:.1f} mm")

    # notes column
    nx = view_left + view_w + 4 * mm
    nw = width - nx - 12 * mm
    c.setStrokeColor(colors.black)
    c.setLineWidth(0.6)
    c.line(nx - 2 * mm, 14 * mm, nx - 2 * mm, height - 22 * mm)
    y = height - 24 * mm
    c.setFont("Arial-Bold", 14)
    c.drawString(nx, y, f"{part_id}")
    y -= 6 * mm
    c.setFont("Arial-Bold", 11)
    for line in wrap_lines(title, "Arial-Bold", 11, nw):
        c.drawString(nx, y, line)
        y -= 5 * mm
    y -= 2 * mm
    facts = [
        f"Quantity in this actuator: {qty}",
        f"Material: {alloy}",
        f"Group: {group}",
        f"Finished size: {size}",
        f"Mass: {sample['mass_g']:.2f} g each",
        f"Model bounding box, X × Y × Z: {dx:.1f} × {dy:.1f} × {dz:.1f} mm",
        f"Raw stock: {stock}",
        f"Process: {process}",
        f"Heat treatment / finish: {finish}",
        f"STEP solid: {sample['name']}",
    ]
    c.setFont("Arial", 8)
    for fact in facts:
        for line in wrap_lines(fact, "Arial", 8, nw):
            c.drawString(nx, y, line)
            y -= 3.6 * mm
        y -= 0.6 * mm
    y -= 1.5 * mm
    c.setFont("Arial-Bold", 8)
    c.drawString(nx, y, "Controlled features")
    y -= 4 * mm
    c.setFont("Arial", 7.5)
    for note in notes:
        bullet = "• " + note
        for i, line in enumerate(wrap_lines(bullet, "Arial", 7.5, nw)):
            if y < 28 * mm:
                break
            c.drawString(nx, y, line if i == 0 else "  " + line)
            y -= 3.3 * mm
        y -= 0.8 * mm
    y -= 2 * mm
    c.setFont("Arial", 7)
    foot = ("STEP file is the geometric master. Do not scale this sheet. "
            "Sizes not listed here follow ISO 2768-1 class m and ISO 2768-2 class K. "
            "Drawing " + filename)
    for line in wrap_lines(foot, "Arial", 7, nw):
        if y < 16 * mm:
            break
        c.drawString(nx, y, line)
        y -= 3.2 * mm
    c.save()


def write_drawings(items):
    """Write one sheet per unique part, using the first solid of that part."""
    folder = os.path.join(OUT, "drawing")
    os.makedirs(folder, exist_ok=True)
    first = {}
    for item in items:
        base = item["name"].split()[0].split(".")[0]
        first.setdefault(base, item)
    for row in PARTS:
        t0 = time.time()
        draw_sheet(os.path.join(folder, row[1]), row, first[row[0]])
        print(f"  drawing {row[1]} in {time.time() - t0:.0f} s", flush=True)


def write_zip():
    """Zip the step, the quotation, and the drawings into one file to send."""
    zip_path = os.path.join(OUT, ZIP_NAME)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for folder in ("step", "quote", "drawing"):
            root = os.path.join(OUT, folder)
            for dirpath, _, files in os.walk(root):
                for name in files:
                    full = os.path.join(dirpath, name)
                    zf.write(full, os.path.relpath(full, OUT))
    return zip_path


def main():
    """Build the actuator, then write the milling step, quotation, and drawings."""
    t0 = time.time()
    check_views()
    print("views ok", flush=True)
    register_fonts()
    occ.use_occ_kernel()
    print("building exact solids...", flush=True)
    model = g.build()
    print(f"built {len(model)} solids in {time.time() - t0:.0f} s", flush=True)
    items = collect(model)
    print(f"milling solids: {len(items)}", flush=True)
    for item in items:
        print(f"  {item['mass_g']:8.2f} g  {item['name']}", flush=True)

    os.makedirs(os.path.join(OUT, "step"), exist_ok=True)
    os.makedirs(os.path.join(OUT, "quote"), exist_ok=True)
    step_path = os.path.join(OUT, "step", STEP_NAME)
    write_step(items, step_path)
    print(f"wrote {step_path} ({os.path.getsize(step_path) / 1e6:.1f} MB)", flush=True)
    check_step_names(step_path)

    quote_path = os.path.join(OUT, "quote", QUOTE_NAME)
    total = write_quote(quote_path, items)
    print(f"wrote {quote_path}  milled mass {total:.0f} g", flush=True)

    print("drawings...", flush=True)
    write_drawings(items)
    zip_path = write_zip()
    print(f"wrote {zip_path} ({os.path.getsize(zip_path) / 1e6:.1f} MB)", flush=True)
    print(f"total {time.time() - t0:.0f} s", flush=True)


if __name__ == "__main__":
    main()
