"""Printable 250 ml Bisleri neck claw for one Tower Pro MG995.

The mast, jaws, cam and mounts are PLA. Bought parts are the servo,
a 25T metal horn, two guide springs, M3 screws and nuts.

Z is zero on the top face of the drone plate and increases toward the bottle.
Run:
  D:\\VAYN-CAD-env\\venv\\Scripts\\python.exe gen_claw.py
"""

import ctypes
import math
import os
import zipfile

import cadquery as cq
import lib3mf
from OCP.BRepExtrema import BRepExtrema_DistShapeShape
from OCP.TopAbs import TopAbs_SOLID
from OCP.TopExp import TopExp_Explorer

HERE = os.path.dirname(os.path.abspath(__file__))
STL_DIR = os.path.join(HERE, "stl")

# --- bought-part sizes, mm. sources are listed in bom.md ---
SERVO_L, SERVO_W, SERVO_H = 40.2, 20.2, 36.0
SERVO_HOLE_X, SERVO_HOLE_Y = 47.8, 10.2
EAR_SPAN, EAR_T, EAR_W = 54.0, 2.5, 18.0
SHAFT_D, SHAFT_H = 6.0, 5.0
HORN_OD, HORN_DISK_T, HORN_HUB_T, HORN_HUB_D = 20.0, 2.0, 2.5, 10.0
HORN_PCD = 14.0
# music wire, G from the spring formula page cited in bom.md
SPRING_D_WIRE, SPRING_D_MEAN, SPRING_NA = 0.4, 8.0, 22
SPRING_FREE = 70.0
SPRING_OD = SPRING_D_MEAN + SPRING_D_WIRE
G_MPA = 80000.0

# --- printed fits ---
SLIDE = 0.45
M3_CLEAR = 3.4
NUT_AF, NUT_T = 5.6, 2.5
NUT_POCKET_T = 2.8
PIN_D, SLOT_W = 5.0, 7.2
SHELF_R, OPEN_R = 15.25, 25.0
PIN_R_CLOSED = 28.0
PIN_TRAVEL = OPEN_R - SHELF_R
PIN_R_OPEN = PIN_R_CLOSED + PIN_TRAVEL
CAM_TURN = 75.0
CAP_GAP = 17.0
JAW_T = 7.0
CAM_T = 5.0
PLATE_T = 8.0
RAIL_A, RAIL_B = 10.0, 16.0
RAIL_PITCH = 70.0
STROKE = 20.0
SPRING_GAP = 35.0
BLADE_T, BLADE_W, BLADE_L = 3.0, 8.0, 40.0
STOP_GAP = 6.0
SHOE_DEG = 35.0
# bottle height is a listing, not a vernier reading. checks.txt says so.
BOTTLE_H = 150.0
# shelf sits this far above the ground when the feet are down, near the neck ring
SHELF_ABOVE_GROUND = 132.0
GUIDE_TOP_R = 27.0
GUIDE_MOUTH_R = 55.0
GUIDE_WALL = 1.6
GUIDE_H = 28.0
WALL_LOAD = 1.35
BED = 246.0
PAYLOAD_LIMIT = 500.0
PROP_R = 127.0
PLA = 1.24e-3  # g/cm3 as g/mm3. solid mass. infill is a separate line.


def k_one_spring():
    """Spring rate of one spring, N/mm."""
    d, D, n = SPRING_D_WIRE, SPRING_D_MEAN, SPRING_NA
    return G_MPA * d ** 4 / (8.0 * D ** 3 * n)


def box(cx, cy, zc, dx, dy, dz):
    """Centered box."""
    return cq.Workplane("XY").box(dx, dy, dz).translate((cx, cy, zc))


def cyl_z(x, y, z0, r, h):
    """Cylinder along +Z starting at z0."""
    return cq.Workplane("XY").circle(r).extrude(h).translate((x, y, z0))


def hole_z(x, y, z0, r, h):
    """Cutting cylinder, a little long so the cut goes through."""
    return cyl_z(x, y, z0 - 0.2, r, h + 0.4)


def nut_slot(x, y, zc, axis):
    """Side-entry pocket for one M3 hex nut. axis is the screw direction."""
    af, t = NUT_AF + 0.3, NUT_POCKET_T
    across = af / math.cos(math.radians(30)) + 0.4
    if axis == "z":
        pocket = box(x, y, zc, across, af, t)
        mouth = box(x, y + af, zc, af, af * 2, t)
    elif axis == "y":
        pocket = box(x, y, zc, across, t, af)
        mouth = box(x + af, y, zc, af * 2, t, af)
    else:
        pocket = box(x, y, zc, t, across, af)
        mouth = box(x, y + af, zc, t, af * 2, af)
    return pocket.union(mouth)


def rot_z(shape, deg):
    """Rotate a solid about Z."""
    return shape.rotate((0, 0, 0), (0, 0, 1), deg)


def gap(a, b):
    """Minimum distance between two solids, mm."""
    d = BRepExtrema_DistShapeShape(a.val().wrapped, b.val().wrapped)
    d.Perform()
    return float(d.Value())


def vol(shape):
    """Volume in mm3."""
    return float(shape.val().Volume())


def solid_count(shape):
    """How many separate solids are in this part. A printed part must be one."""
    exp = TopExp_Explorer(shape.val().wrapped, TopAbs_SOLID)
    count = 0
    while exp.More():
        count += 1
        exp.Next()
    return count


class Joint:
    """One screw joint, checked against the holes that were cut."""

    def __init__(self, name, screw, points, direction, parts):
        self.name = name
        self.screw = screw
        self.points = points
        self.direction = direction
        self.parts = parts


HOLES = []
JOINTS = []


def cut_holes(shape, points, diameter, z0, depth, name, part, record=True):
    """Cut vertical clearance holes and remember them."""
    for i, (x, y) in enumerate(points):
        shape = shape.cut(hole_z(x, y, z0, diameter / 2, depth))
        if record:
            HOLES.append((part, name, i, (x, y, z0 + depth / 2), diameter))
    return shape


def spring_forces():
    """Preload and full-stroke force for the two springs together."""
    k = 2.0 * k_one_spring()
    solid = (SPRING_NA + 2) * SPRING_D_WIRE
    c0 = SPRING_FREE - SPRING_GAP
    c1 = c0 + STROKE
    length_min = SPRING_FREE - c1
    return k, k * c0, k * c1, solid, length_min


def make_mast():
    """Drone plate, soft blades, cross block, two rails, two spring sleeves."""
    z_blade0 = 4.0
    blades = None
    for sx, sy, dx, dy in (
        (18, 0, BLADE_T, BLADE_W),
        (-18, 0, BLADE_T, BLADE_W),
        (0, 14, BLADE_W, BLADE_T),
        (0, -14, BLADE_W, BLADE_T),
    ):
        b = box(sx, sy, z_blade0 + BLADE_L / 2, dx, dy, BLADE_L)
        blades = b if blades is None else blades.union(b)
    z_block0 = z_blade0 + BLADE_L
    # center block plus two bridges so both rails are actually joined to the blades
    block = box(0, 0, z_block0 + 4, 40, 72, 8)
    for x in (-28, 28):
        block = block.union(box(x, 0, z_block0 + 4, 30, 16, 8))
    # posts on the plate stop the block after 6 mm of sideways drift
    stops = None
    for x, y in ((28, 0), (-28, 0)):
        p = box(x, y, z_block0 / 2 + 2, 6, 6, z_block0)
        stops = p if stops is None else stops.union(p)
    rails = None
    z_rail0 = z_block0 + 6
    # rail ends 10 mm past the carriage so the stop can screw into a free stub
    z_rail1 = z_rail0 + SPRING_GAP + PLATE_T + 10
    for x in (-RAIL_PITCH / 2, RAIL_PITCH / 2):
        r = box(x, 0, (z_rail0 + z_rail1) / 2, RAIL_A, RAIL_B, z_rail1 - z_rail0)
        # elephant-foot relief on the free end
        r = r.cut(box(x, 0, z_rail1 - 0.4, RAIL_A + 2, RAIL_B + 2, 0.8))
        r = r.union(box(x, 0, z_rail1 - 0.8, RAIL_A - 0.8, RAIL_B - 0.8, 1.6))
        nut_z = z_rail1 - 6
        pocket = nut_slot(x, 0, nut_z, "y")
        r = r.cut(pocket)
        r = r.cut(hole_z(x, 0, z_rail1 - 14, M3_CLEAR / 2, 16))
        HOLES.append(("mast", "stop", 0 if x < 0 else 1, (x, 0, nut_z), M3_CLEAR))
        rails = r if rails is None else rails.union(r)
    # bores the carriage tubes enter when the mast shortens
    for y in (-24, 24):
        block = block.cut(cyl_z(0, y, z_block0 - 1, 7.4, 12))
    plate = box(0, 0, 2, 80, 64, 3.2)
    for x, y in ((22, 16), (22, -16), (-22, 16), (-22, -16)):
        plate = plate.cut(box(x, y, 2, 16, M3_CLEAR, 6))
    plate = plate.cut(cyl_z(0, 0, -1, 6, 8))
    mast = plate.union(blades).union(block).union(stops).union(rails)
    meta = {"z_rail0": z_rail0, "z_rail1": z_rail1, "z_block0": z_block0}
    return mast, meta


def make_carriage(meta):
    """Plate that slides on the rails and holds the servo."""
    zc = meta["z_rail0"] + SPRING_GAP + PLATE_T / 2
    # spider, not a solid disk: servo pad, two rail pads, three arms
    plate = box(0, 0, zc, 62, 32, PLATE_T)
    for x in (-RAIL_PITCH / 2, RAIL_PITCH / 2):
        plate = plate.union(box(x, 0, zc, 24, 26, PLATE_T))
    for i in range(3):
        arm = box(32, 0, zc, 44, 14, PLATE_T)
        plate = plate.union(rot_z(arm, 60 + 120 * i))
    # loose channel between three tight ribs, so a slightly bowed rail does not bind
    rib_h = 2.4
    for x in (-RAIL_PITCH / 2, RAIL_PITCH / 2):
        plate = plate.cut(box(x, 0, zc, RAIL_A + 2 * SLIDE, RAIL_B + 2 * SLIDE, PLATE_T + 2))
        for dz in (-PLATE_T / 2 + rib_h / 2, 0, PLATE_T / 2 - rib_h / 2):
            rib = box(x, 0, zc + dz, RAIL_A + 2.4, RAIL_B + 2.4, rib_h)
            rib = rib.cut(box(x, 0, zc + dz, RAIL_A + 2 * SLIDE, RAIL_B + 2 * SLIDE, rib_h + 1))
            plate = plate.union(rib)
    # servo body passes through; ears land on the bottle side of the plate
    plate = plate.cut(box(0, 0, zc, SERVO_L + 0.4, SERVO_W + 0.4, PLATE_T + 2))
    pts = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            pts.append((sx * SERVO_HOLE_X / 2, sy * SERVO_HOLE_Y / 2))
    z0 = zc - PLATE_T / 2
    # slots, not tight holes: MG995 clones vary by about 1 mm on this pattern
    for x, y in pts:
        plate = plate.cut(box(x, y, z0 + PLATE_T / 2, 6.0, M3_CLEAR, PLATE_T + 1))
        HOLES.append(("carriage", "servo", len(HOLES), (x, y, z0 + PLATE_T / 2), M3_CLEAR))
    for x, y in pts:
        plate = plate.cut(nut_slot(x, y, z0 + 4.6, "z"))
    # housing screws, between the jaws
    hpts = []
    for i in range(3):
        a = math.radians(60 + 120 * i)
        hpts.append((50 * math.cos(a), 50 * math.sin(a)))
    plate = cut_holes(plate, hpts, M3_CLEAR, z0, PLATE_T, "housing", "carriage")
    for x, y in hpts:
        plate = plate.cut(nut_slot(x, y, z0 + 5.4, "z"))
    for y in (-24, 24):
        # tube sticks up into the spring and, when collapsed, into the block
        plate = plate.union(cyl_z(0, y, zc - PLATE_T / 2 - 22, 6.6, 22))
        plate = plate.cut(cyl_z(0, y, zc - PLATE_T / 2 - 23, 5.3, 24))
    plate = plate.cut(cyl_z(32, 0, z0 - 1, 4, PLATE_T + 4))  # zip tie
    meta = dict(meta)
    meta["z_carriage"] = zc
    meta["carriage_bottom"] = zc + PLATE_T / 2
    return plate, meta


def make_stop(meta):
    """Bar under the rails. The carriage rests on it when the mast is extended."""
    # seat is the carriage bottom; the pad hangs on the 10 mm rail stub
    seat = meta["z_rail1"] - 10
    zc = seat + 2.5
    stop = box(0, 0, zc, RAIL_PITCH, 8, 4)
    for x in (-RAIL_PITCH / 2, RAIL_PITCH / 2):
        stop = stop.union(box(x, 0, zc, 16, 16, 5))
    pts = [(-RAIL_PITCH / 2, 0), (RAIL_PITCH / 2, 0)]
    stop = cut_holes(stop, pts, M3_CLEAR, seat, 5, "stop", "stop")
    return stop


def make_servo(meta):
    """Reference solid of the MG995. Not printed."""
    zb = meta["carriage_bottom"]
    # ears sit on the plate; the case continues up into the mast (-Z)
    case = box(0, 0, zb - EAR_T - SERVO_H / 2, SERVO_L, SERVO_W, SERVO_H)
    ears = box(0, 0, zb - EAR_T / 2, EAR_SPAN, EAR_W, EAR_T)
    shaft = cyl_z(0, 0, zb, SHAFT_D / 2, SHAFT_H)
    return case.union(ears).union(shaft)


def make_horn(meta):
    """25T metal disk horn. Not printed. Hub faces the servo."""
    zb = meta["carriage_bottom"] + SHAFT_H
    disk = cyl_z(0, 0, zb, HORN_OD / 2, HORN_DISK_T)
    hub = cyl_z(0, 0, zb - HORN_HUB_T, HORN_HUB_D / 2, HORN_HUB_T)
    horn = disk.union(hub).cut(cyl_z(0, 0, zb - HORN_HUB_T - 1, 3.0, HORN_DISK_T + HORN_HUB_T + 2))
    for i in range(4):
        a = math.radians(45 + 90 * i)
        x, y = (HORN_PCD / 2) * math.cos(a), (HORN_PCD / 2) * math.sin(a)
        horn = horn.cut(cyl_z(x, y, zb - 1, 1.25, HORN_DISK_T + 2))
        HOLES.append(("horn", "cam", i, (x, y, zb + 1), 2.5))
    meta = dict(meta)
    meta["z_horn_face"] = zb + HORN_DISK_T
    return horn, meta


def screw_plus(x, y, z_head, length):
    """Screw with the head at z_head and the thread running toward +Z."""
    return cyl_z(x, y, z_head, 1.5, length).union(cyl_z(x, y, z_head - 2.2, 2.8, 2.2))


def screw_minus(x, y, z_head, length):
    """Screw with the head at z_head and the thread running toward -Z."""
    return cyl_z(x, y, z_head - length, 1.5, length).union(cyl_z(x, y, z_head, 2.8, 2.2))


def nut(x, y, z0):
    """M3 hex nut. Not printed."""
    return cq.Workplane("XY").polygon(6, 6.4).extrude(2.4).translate((x, y, z0))


def make_springs(meta):
    """Two bought springs, sitting in the carriage tubes."""
    z_carriage_top = meta["z_carriage"] - PLATE_T / 2
    z0 = z_carriage_top - SPRING_GAP
    parts = []
    for i, y in enumerate((-24.0, 24.0)):
        wall = cyl_z(0, y, z0, SPRING_OD / 2, SPRING_GAP)
        wall = wall.cut(cyl_z(0, y, z0 - 0.4, SPRING_OD / 2 - 0.55, SPRING_GAP + 0.8))
        parts.append((f"spring_{i + 1}", wall))
    return parts


def make_fasteners(meta):
    """Bought screws and nuts. Not printed."""
    parts = []
    for i, (x, y) in enumerate(((22, 16), (22, -16), (-22, 16), (-22, -16))):
        parts.append((f"screw_drone_{i + 1}", screw_plus(x, y, 0.0, 8)))
        parts.append((f"nut_drone_{i + 1}", nut(x, y, 3.6)))
    for i, x in enumerate((-RAIL_PITCH / 2, RAIL_PITCH / 2)):
        parts.append((f"screw_stop_{i + 1}", screw_minus(x, 0, meta["z_rail1"] - 4, 12)))
        parts.append((f"nut_stop_{i + 1}", nut(x, 0, meta["z_rail1"] - 8)))
    for i, (sx, sy) in enumerate(((-1, -1), (-1, 1), (1, -1), (1, 1))):
        x, y = sx * SERVO_HOLE_X / 2, sy * SERVO_HOLE_Y / 2
        parts.append((f"screw_servo_{i + 1}", screw_minus(x, y, meta["carriage_bottom"] + 2, 10)))
        parts.append((f"nut_servo_{i + 1}", nut(x, y, meta["carriage_bottom"] - 6)))
    for i in range(3):
        a = math.radians(60 + 120 * i)
        x, y = 50 * math.cos(a), 50 * math.sin(a)
        parts.append((f"screw_post_{i + 1}", screw_plus(x, y, meta["z_carriage"] - PLATE_T / 2, 16)))
        parts.append((f"nut_post_{i + 1}", nut(x, y, meta["carriage_bottom"] + 4)))
    z_cam = meta["z_horn_face"] + CAM_T
    for i in range(4):
        a = math.radians(45 + 90 * i)
        x, y = (HORN_PCD / 2) * math.cos(a), (HORN_PCD / 2) * math.sin(a)
        parts.append((f"screw_cam_{i + 1}", screw_minus(x, y, z_cam, 8)))
    z_jaw = meta["z_jaw0"]
    for i in range(3):
        a = math.radians(60 + 120 * i)
        x, y = 57 * math.cos(a), 57 * math.sin(a)
        parts.append((f"screw_retainer_{i + 1}", screw_plus(x, y, z_jaw, 10)))
        parts.append((f"nut_retainer_{i + 1}", nut(x, y, z_jaw + 6)))
    z_g = meta["z_floor"] + 3.2
    for i in range(3):
        a = math.radians(120 * i)
        x, y = 36 * math.cos(a), 36 * math.sin(a)
        parts.append((f"screw_guide_{i + 1}", screw_plus(x, y, z_g, 8)))
        parts.append((f"nut_guide_{i + 1}", nut(x, y, meta["z_floor"] + 1.2)))
    z_foot = z_g + GUIDE_H - 3
    for i, deg in enumerate((45, 135, 225, 315)):
        a = math.radians(deg)
        x, y = 62 * math.cos(a), 62 * math.sin(a)
        parts.append((f"screw_foot_{i + 1}", screw_plus(x, y, z_foot, 8)))
        parts.append((f"nut_foot_{i + 1}", nut(x, y, z_foot + 3)))
    return parts


def make_guide(meta):
    """Wide mouth under the jaws. Narrow end bolts to the housing.

    The wall leans 45 degrees, so it prints from the wide rim without support.
    """
    z0 = meta["z_floor"] + 3.2
    outer = (
        cq.Workplane("XY").circle(GUIDE_TOP_R + GUIDE_WALL).workplane(offset=GUIDE_H).circle(GUIDE_MOUTH_R + GUIDE_WALL).loft()
    )
    inner = (
        cq.Workplane("XY").circle(GUIDE_TOP_R - 0.4).workplane(offset=GUIDE_H + 0.6).circle(GUIDE_MOUTH_R + 0.2).loft()
    )
    guide = outer.cut(inner).translate((0, 0, z0))
    flange = cyl_z(0, 0, z0, 42, 3.2).cut(cyl_z(0, 0, z0 - 0.4, GUIDE_TOP_R - 0.2, 4.2))
    guide = guide.union(flange)
    pts = []
    for i in range(3):
        a = math.radians(120 * i)
        x, y = 36 * math.cos(a), 36 * math.sin(a)
        pts.append((x, y))
        guide = guide.union(cyl_z(x, y, z0, 6, 3.2))
    guide = cut_holes(guide, pts, M3_CLEAR, z0, 3.2, "guide", "guide")
    # four ears for the feet, outside the mouth
    for i, deg in enumerate((45, 135, 225, 315)):
        a = math.radians(deg)
        x, y = 62 * math.cos(a), 62 * math.sin(a)
        guide = guide.union(cyl_z(x, y, z0 + GUIDE_H - 3, 7, 4))
        guide = cut_holes(guide, [(x, y)], M3_CLEAR, z0 + GUIDE_H - 3, 4, "foot", "guide")
    meta = dict(meta)
    meta["z_guide_mouth"] = z0 + GUIDE_H
    return guide, meta


def make_foot():
    """One leg. The ear sits on the bed, the tube prints upward."""
    ear = box(0, 0, 2, 16, 14, 4)
    ear = ear.cut(hole_z(0, 0, 0, M3_CLEAR / 2, 5))
    tube = cyl_z(0, 0, 4, 4, 8).cut(cyl_z(0, 0, 3.5, 2.4, 9))
    return ear.union(tube)


def place_foot(index, z_ear, z_tip):
    """Stand a foot on the guide ear. The tube is lengthened to the ground line."""
    deg = 45 + 90 * index
    a = math.radians(deg)
    x, y = 62 * math.cos(a), 62 * math.sin(a)
    length = z_tip - (z_ear + 4)
    tube = cyl_z(x, y, z_ear + 4, 4, length).cut(cyl_z(x, y, z_ear + 3.5, 2.4, length + 1))
    ear = box(x, y, z_ear + 2, 14, 14, 4)
    ear = ear.cut(hole_z(x, y, z_ear, M3_CLEAR / 2, 5))
    return ear.union(tube)


def make_drone_dummy():
    """Size dummy of the TBS 500 as a V-tail. Not printed.

    Specs from the frame listing: 500 mm wheelbase, arms 220 x 40 mm,
    motor-mount holes 3 mm. Forward is +X. The 500 mm is the span
    between the two front motors. The rear pair is the V.
    Props are the usual 10 inch size for this wheelbase.
    """
    plate = box(0, 0, -1.5, 160, 120, 3)
    tail = box(-70, 0, -1.5, 80, 70, 3)
    parts = [("drone_plate", plate.union(tail))]
    # front span is the 500 mm wheelbase. rear motors sit close, forming the V.
    motors = ((110, 250), (110, -250), (-190, 80), (-190, -80))
    for i, (mx, my) in enumerate(motors):
        length = math.hypot(mx, my)
        ang = math.degrees(math.atan2(my, mx))
        arm = box(length - 110, 0, -1.5, 220, 40, 4)
        arm = rot_z(arm, ang)
        mount = cyl_z(mx, my, -6, 16, 3).cut(cyl_z(mx, my, -7, 1.5, 5))
        motor = cyl_z(mx, my, -28, 14, 22)
        prop = cyl_z(mx, my, -31, 127, 2)
        parts.append((f"drone_arm_{i + 1}", arm))
        parts.append((f"drone_mount_{i + 1}", mount))
        parts.append((f"drone_motor_{i + 1}", motor))
        parts.append((f"drone_prop_{i + 1}", prop))
    return parts


def make_cam(meta, angle):
    """Spiral disk. angle 0 is closed. Negative angle opens the jaws."""
    z0 = meta["z_horn_face"]
    cam = cyl_z(0, 0, z0, 12, CAM_T).union(cyl_z(0, 0, z0, 44, CAM_T).cut(cyl_z(0, 0, z0 - 1, 26, CAM_T + 2)))
    for i in range(3):
        spoke = box(19, 0, z0 + CAM_T / 2, 16, 8, CAM_T)
        cam = cam.union(rot_z(spoke, 30 + 120 * i))
    cam = cam.cut(cyl_z(0, 0, z0 - 1, 4.2, 3.2))  # room for the horn screw head
    cam = cam.cut(cyl_z(0, 0, z0 + 2.5, 3.2, CAM_T))
    pts = []
    for i in range(4):
        a = math.radians(45 + 90 * i)
        pts.append(((HORN_PCD / 2) * math.cos(a), (HORN_PCD / 2) * math.sin(a)))
    cam = cut_holes(cam, pts, M3_CLEAR, z0, CAM_T, "cam", "cam", record=(angle == 0))
    tool = None
    steps = int(CAM_TURN / 3) + 1
    for jaw in range(3):
        base = 120.0 * jaw
        for s in range(steps + 1):
            frac = s / steps
            ang = math.radians(base + CAM_TURN * frac)
            radius = PIN_R_CLOSED + PIN_TRAVEL * frac
            c = cyl_z(radius * math.cos(ang), radius * math.sin(ang), z0 - 0.2, SLOT_W / 2, CAM_T + 0.6)
            tool = c if tool is None else tool.union(c)
        # mouth so the pin can be slid in at the open end
        ang = math.radians(base + CAM_TURN)
        mouth = box(PIN_R_OPEN + 4, 0, z0 + CAM_T / 2, 12, SLOT_W + 2, CAM_T + 1)
        mouth = rot_z(mouth, base + CAM_TURN)
        tool = tool.union(mouth)
    cam = cam.cut(tool)
    if angle:
        cam = rot_z(cam, angle)
    return cam


def make_jaw(index, shift):
    """One shelf jaw. shift 0 is closed. The shelf is the face toward the drone."""
    # built along +X, then rotated to its 120 degree station
    shoe = cyl_z(0, 0, 0, 20, JAW_T).cut(cyl_z(0, 0, -1, SHELF_R, JAW_T + 2))
    mask = cq.Workplane("XY").moveTo(0, 0).lineTo(40, -40 * math.tan(math.radians(SHOE_DEG))).lineTo(40, 40 * math.tan(math.radians(SHOE_DEG))).close().extrude(JAW_T + 2).translate((0, 0, -1))
    shoe = shoe.intersect(mask)
    arm = box(31, 0, JAW_T / 2, 26, 8, JAW_T)
    pin = cyl_z(PIN_R_CLOSED, 0, -(CAP_GAP + 4), PIN_D / 2, CAP_GAP + 7)
    jaw = shoe.union(arm).union(pin)
    jaw = jaw.translate((shift, 0, 0))
    jaw = rot_z(jaw, 120 * index)
    return jaw


def make_housing(meta):
    """Floor, guide fences and three posts. The jaws slide on the floor."""
    z_jaw0 = meta["z_horn_face"] + CAM_T + CAP_GAP
    z_floor = z_jaw0 + JAW_T + 0.4
    floor = cyl_z(0, 0, z_floor, 54, 3.2).cut(cyl_z(0, 0, z_floor - 1, OPEN_R + 2, 6))
    # lead-in is a cut, so it cannot become a loose piece
    chamfer = cq.Workplane("XY").add(cq.Solid.makeCone(OPEN_R + 2, OPEN_R + 8, 2.4)).translate((0, 0, z_floor + 2.0))
    floor = floor.cut(chamfer)
    fences = None
    for i in range(3):
        for side in (-1, 1):
            fence = box(43, side * 5.4, z_floor - 3, 18, 1.4, 10)
            fence = rot_z(fence, 120 * i)
            fences = fence if fences is None else fences.union(fence)
    posts = None
    z_post1 = meta["carriage_bottom"]
    for i in range(3):
        a = math.radians(60 + 120 * i)
        x, y = 50 * math.cos(a), 50 * math.sin(a)
        post = cyl_z(x, y, z_post1, 4.5, (z_floor + 4) - z_post1)
        post = post.cut(hole_z(x, y, z_post1 - 1, M3_CLEAR / 2, 12))
        post = post.cut(nut_slot(x, y, z_post1 + 5.5, "z"))
        HOLES.append(("housing", "housing", i, (x, y, z_post1 - 4), M3_CLEAR))
        posts = post if posts is None else posts.union(post)
    for i in range(3):
        a = math.radians(60 + 120 * i)
        x, y = 57 * math.cos(a), 57 * math.sin(a)
        floor = floor.union(cyl_z(x, y, z_floor, 8, 3.2))
        floor = floor.cut(hole_z(x, y, z_floor - 1, M3_CLEAR / 2, 6))
        floor = floor.cut(nut_slot(x, y, z_floor + 1.8, "z"))
        HOLES.append(("housing", "retainer", i, (x, y, z_floor + 2), M3_CLEAR))
    for i in range(3):
        a = math.radians(120 * i)
        x, y = 36 * math.cos(a), 36 * math.sin(a)
        floor = floor.cut(hole_z(x, y, z_floor - 1, M3_CLEAR / 2, 6))
        floor = floor.cut(nut_slot(x, y, z_floor + 1.6, "z"))
        HOLES.append(("housing", "guide", i, (x, y, z_floor + 1.6), M3_CLEAR))
    housing = floor.union(fences).union(posts)
    meta = dict(meta)
    meta["z_jaw0"] = z_jaw0
    meta["z_floor"] = z_floor
    return housing, meta


def make_retainer(meta):
    """Three tabs, joined by a thin rim, that stop the jaws falling out."""
    z = meta["z_jaw0"]
    ring = cyl_z(0, 0, z, 62, 3).cut(cyl_z(0, 0, z - 1, 55, 5))
    for i in range(3):
        tab = box(62, 0, z + 1.5, 14, 14, 3)
        ring = ring.union(rot_z(tab, 120 * i))
    pts = []
    for i in range(3):
        a = math.radians(60 + 120 * i)
        pts.append((57 * math.cos(a), 57 * math.sin(a)))
    ring = cut_holes(ring, pts, M3_CLEAR, z, 3, "retainer", "retainer")
    return ring


def make_ring():
    """Reference slice of the 33 mm neck ring. Not printed."""
    return cyl_z(0, 0, 0, 16.5, 2.0).cut(cyl_z(0, 0, -1, 13.0, 4))


def place_jaws(meta, shift):
    """Three jaws with their shelf on z_jaw0."""
    jaws = None
    for i in range(3):
        j = make_jaw(i, shift).translate((0, 0, meta["z_jaw0"]))
        jaws = j if jaws is None else jaws.union(j)
    return jaws


def screw_shank(p, direction, length, head):
    """Simple screw: shank plus head, for the clearance check."""
    x, y, z = p
    if direction == (0, 0, 1):
        shank = cyl_z(x, y, z, 1.5, length)
        cap = cyl_z(x, y, z - head, 2.8, head)
    elif direction == (0, 0, -1):
        shank = cyl_z(x, y, z - length, 1.5, length)
        cap = cyl_z(x, y, z, 2.8, head)
    else:
        raise ValueError(direction)
    return shank.union(cap)


def on_bed(shape, rx=0):
    """Turn a part so the requested face is down, then sit it on z = 0."""
    if rx:
        shape = shape.rotate((0, 0, 0), (1, 0, 0), rx)
    bb = shape.val().BoundingBox()
    return shape.translate((-bb.xmin, -bb.ymin, -bb.zmin))


def write_print_3mf(parts, path):
    """Write named print parts, spaced along X, as one 3MF."""
    w = lib3mf.get_wrapper()
    model = w.CreateModel()
    model.SetUnit(lib3mf.ModelUnit.MilliMeter)
    cursor = 0.0
    for name, shape in parts:
        bb = shape.val().BoundingBox()
        shape = shape.translate((cursor, 0, 0))
        verts, tris = shape.val().tessellate(0.08, 0.4)
        obj = model.AddMeshObject()
        obj.SetName(name)
        obj.SetGeometry(
            [lib3mf.Position((ctypes.c_float * 3)(*p.toTuple())) for p in verts],
            [lib3mf.Triangle((ctypes.c_uint32 * 3)(*tri)) for tri in tris],
        )
        model.AddBuildItem(obj, w.GetIdentityTransform())
        cursor += (bb.xmax - bb.xmin) + 6.0
    model.QueryWriter("3mf").WriteToFile(path)


def draw_change(guide, feet, jaws, path):
    """Save a shaded view of the guide, the feet, and the open jaws."""
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection

    def faces(shape, color):
        verts, tris = shape.val().tessellate(0.6, 0.6)
        pts = [v.toTuple() for v in verts]
        tri = [[pts[i] for i in t] for t in tris]
        return tri, color

    meshes = [faces(guide, (0.93, 0.72, 0.25)), faces(jaws, (0.9, 0.45, 0.1))]
    meshes += [faces(foot, (0.75, 0.45, 0.15)) for foot in feet]
    fig = plt.figure(figsize=(8, 8), facecolor="white")
    ax = fig.add_subplot(111, projection="3d")
    for tri, rgb in meshes:
        ax.add_collection3d(Poly3DCollection(tri, facecolor=rgb, edgecolor="none", alpha=0.95))
    ax.view_init(elev=18, azim=-60)
    ax.set_xlim(-80, 80)
    ax.set_ylim(-80, 80)
    ax.set_zlim(100, 280)
    ax.set_box_aspect((1, 1, 1.4))
    ax.set_axis_off()
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)


def export_stl(shape, name):
    """Write one print STL in the part's own print orientation."""
    os.makedirs(STL_DIR, exist_ok=True)
    path = os.path.join(STL_DIR, name + ".stl")
    cq.exporters.export(shape, path)
    return path


def main():
    """Build the claw, reject it if a joint or fit is wrong, then write files."""
    HOLES.clear()
    k, f0, fmax, solid, length_min = spring_forces()
    problems = []
    if not (1.2 <= f0 <= 2.2):
        problems.append(f"preload {f0:.2f} N is outside 1.2 to 2.2 N")
    if fmax > 3.0:
        problems.append(f"full stroke force {fmax:.2f} N is over 3 N")
    if length_min < solid + 3:
        problems.append("spring reaches solid height")
    lateral = fmax * math.tan(math.radians(12))
    if lateral > 0.55:
        problems.append(f"side push {lateral:.2f} N can tip the bottle")

    mast, meta = make_mast()
    carriage, meta = make_carriage(meta)
    stop = make_stop(meta)
    servo = make_servo(meta)
    horn, meta = make_horn(meta)
    cam = make_cam(meta, 0)
    housing, meta = make_housing(meta)
    jaws = place_jaws(meta, 0)
    retainer = make_retainer(meta)
    guide, meta = make_guide(meta)
    z_tip = meta["z_jaw0"] + SHELF_ABOVE_GROUND
    feet = [place_foot(i, meta["z_guide_mouth"] + 1, z_tip) for i in range(4)]
    ring = make_ring().translate((0, 0, meta["z_jaw0"] - 2.0))

    pairs = {
        "mast-carriage": (mast, carriage, 0.3, 0.7),
        "carriage-servo": (carriage, servo, 0.0, 1.2),
        "horn-cam": (horn, cam, 0.0, 0.4),
        "mast-servo": (mast, servo, 1.0, 40.0),
        "jaws-housing": (jaws, housing, 0.2, 0.8),
        "ring-jaws": (ring, jaws, 0.0, 0.3),
    }
    gaps = {}
    for name, (a, b, lo, hi) in pairs.items():
        g = gap(a, b)
        gaps[name] = g
        if not (lo - 0.05 <= g <= hi + 0.05):
            problems.append(f"{name} gap {g:.2f} mm, wanted {lo:.2f} to {hi:.2f}")

    # screws that must pass a real hole in every part they join
    screw_checks = [
        ("servo to carriage", "M3x10", 4, "carriage", "servo"),
        ("cam to horn", "M3x6", 4, "cam", "cam"),
        ("stop to mast", "M3x12", 2, "stop", "stop"),
        ("housing to carriage", "M3x12", 3, "carriage", "housing"),
        ("guide to housing", "M3x8", 3, "guide", "guide"),
        ("feet to guide", "M3x8", 4, "guide", "foot"),
    ]
    for label, screw, count, part_a, name in screw_checks:
        found = [h for h in HOLES if h[0] == part_a and h[1] == name]
        if len(found) != count:
            problems.append(f"{label}: found {len(found)} holes, wanted {count} {screw}")

    # open pose: cam turned, jaws slid out, pin still misses the cam
    cam_open = make_cam(meta, -CAM_TURN)
    jaws_open = place_jaws(meta, PIN_TRAVEL)
    g_open = gap(jaws_open, cam_open)
    gaps["jaws-cam open"] = g_open
    if g_open < 0.15:
        problems.append(f"open jaws hit the cam, gap {g_open:.2f}")
    g_closed = gap(jaws, cam)
    gaps["jaws-cam closed"] = g_closed
    if g_closed < 0.15:
        problems.append(f"closed jaws hit the cam, gap {g_closed:.2f}")
    g_house = gap(jaws_open, housing)
    gaps["open jaws vs guides"] = g_house
    if g_house < 0.25:
        problems.append(f"open jaws hit the guides, gap {g_house:.2f}")
    retainer_open_gap = gap(jaws_open, retainer)
    gaps["open jaws vs retainer"] = retainer_open_gap
    if retainer_open_gap < 0.25:
        problems.append(f"open jaws hit the retainer, gap {retainer_open_gap:.2f}")
    cam_mid = make_cam(meta, -CAM_TURN * 0.5)
    jaws_mid = place_jaws(meta, PIN_TRAVEL * 0.5)
    g_mid = gap(jaws_mid, cam_mid)
    gaps["jaws-cam halfway"] = g_mid
    if g_mid < 0.15:
        problems.append(f"jaws hit the cam halfway open, gap {g_mid:.2f}")
    g_mid_house = gap(jaws_mid, housing)
    gaps["halfway jaws vs guides"] = g_mid_house
    if g_mid_house < 0.25:
        problems.append(f"jaws hit the guides halfway, gap {g_mid_house:.2f}")
    mouth_z = meta["z_guide_mouth"] - 2
    g_fit = gap(cyl_z(0, 0, mouth_z, 50, 3), guide)
    g_clash = gap(cyl_z(0, 0, mouth_z, 57, 3), guide)
    gaps["100 mm probe in mouth"] = g_fit
    gaps["114 mm probe in mouth"] = g_clash
    if g_fit < 0.3:
        problems.append(f"mouth will not pass a 100 mm probe, gap {g_fit:.2f}")
    if g_clash > 0.2:
        problems.append(f"mouth is larger than 110 mm, 114 mm probe gap {g_clash:.2f}")
    drop = max(f.val().BoundingBox().zmax for f in feet) - meta["z_jaw0"]
    gaps["shelf above feet"] = drop
    if abs(drop - SHELF_ABOVE_GROUND) > 2:
        problems.append(f"shelf is {drop:.1f} mm above the feet, wanted {SHELF_ABOVE_GROUND:.0f}")
    motors = ((110, 250), (110, -250), (-190, 80), (-190, -80))
    prop_clear = 999.0
    for i in range(4):
        a = math.radians(45 + 90 * i)
        fx, fy = 62 * math.cos(a), 62 * math.sin(a)
        for mx, my in motors:
            prop_clear = min(prop_clear, math.hypot(fx - mx, fy - my) - PROP_R - 4)
    gaps["foot to prop disk"] = prop_clear
    if prop_clear < 8:
        problems.append(f"foot is {prop_clear:.1f} mm from a prop disk, wanted at least 8")
    for i, foot in enumerate(feet):
        buried = vol(foot.intersect(guide))
        if buried > 20:
            problems.append(f"foot {i + 1} is inside the guide by {buried:.0f} mm3")
    if GUIDE_WALL < WALL_LOAD:
        problems.append(f"guide wall {GUIDE_WALL:.2f} mm is under {WALL_LOAD:.2f}")

    # collapsed mast: carriage and springs move up by STROKE, tubes must miss the block
    carriage_up = carriage.translate((0, 0, -STROKE))
    seat_gap = gap(carriage, stop)
    gaps["carriage on stop"] = seat_gap
    if seat_gap > 0.2:
        problems.append(f"carriage does not sit on the stop, gap {seat_gap:.2f}")
    if carriage.intersect(stop).val().Volume() > 5:
        problems.append("stop is buried in the carriage")
    g_up = gap(carriage_up, mast)
    gaps["collapsed carriage"] = g_up
    if g_up < 0.4:
        problems.append(f"collapsed carriage hits the mast, gap {g_up:.2f}")

    printed = {
        "01_mast": mast,
        "02_carriage": carriage,
        "03_stop": stop,
        "04_cam": cam,
        "05_housing": housing,
        "06_jaw": make_jaw(0, 0),
        "07_retainer": retainer,
        "08_guide": guide,
        "09_foot": feet[0],
    }
    for name, shape in printed.items():
        if vol(shape) < 10:
            problems.append(f"{name} has no volume")
        if solid_count(shape) != 1:
            problems.append(f"{name} is {solid_count(shape)} separate pieces")

    report = [
        "motion: feet stop the drone on the ground, the guide gathers the cap, then the servo turns the horn, the horn turns the cam, and the slots slide the jaws under the ring",
        f"closed shelf diameter {2 * SHELF_R:.1f} mm, open diameter {2 * OPEN_R:.1f} mm, cam turn {CAM_TURN:.0f} deg",
        f"preload {f0:.2f} N", f"full stroke {fmax:.2f} N", f"side push {lateral:.2f} N",
        f"spring rate {k:.3f} N/mm for two", f"min spring length {length_min:.1f} mm, solid {solid:.1f} mm",
    ]
    report += [f"{n}: {g:.2f} mm" for n, g in gaps.items()]
    text = "\n".join(report + problems)
    with open(os.path.join(HERE, "checks.txt"), "w", encoding="utf-8") as f:
        f.write(text + "\n")
    print(text)
    if problems:
        raise SystemExit(1)

    # full reference assembly. the 3mf and stl stay printable parts only
    assy = cq.Assembly(name="Bisleri250_neck_claw")
    named = [
        ("mast", mast, cq.Color(0.85, 0.55, 0.15)),
        ("carriage", carriage, cq.Color(0.9, 0.7, 0.2)),
        ("stop", stop, cq.Color(0.8, 0.5, 0.1)),
        ("cam", cam_open, cq.Color(0.95, 0.75, 0.2)),
        ("housing", housing, cq.Color(0.85, 0.55, 0.15)),
        ("retainer", retainer, cq.Color(0.7, 0.45, 0.1)),
        ("guide", guide, cq.Color(0.95, 0.8, 0.3)),
        ("servo", servo, cq.Color(0.15, 0.15, 0.15)),
        ("horn", horn, cq.Color(0.75, 0.78, 0.82)),
    ]
    for i in range(3):
        named.append((f"jaw_{i + 1}", make_jaw(i, PIN_TRAVEL).translate((0, 0, meta["z_jaw0"])), cq.Color(0.95, 0.6, 0.1)))
    for i, foot in enumerate(feet):
        named.append((f"foot_{i + 1}", foot, cq.Color(0.85, 0.55, 0.15)))
    for name, shape in make_springs(meta):
        named.append((name, shape, cq.Color(0.75, 0.75, 0.78)))
    for name, shape in make_fasteners(meta):
        color = cq.Color(0.55, 0.56, 0.58) if name.startswith("screw") else cq.Color(0.35, 0.36, 0.38)
        named.append((name, shape, color))
    for name, shape in make_drone_dummy():
        color = cq.Color(0.25, 0.25, 0.28) if "prop" not in name else cq.Color(0.15, 0.15, 0.16)
        named.append((name, shape, color))
    for name, shape, color in named:
        assy.add(shape, name=name, color=color)
    step_path = os.path.join(HERE, "claw.step")
    assy.save(step_path)
    print("step", os.path.getsize(step_path))

    masses = {n: vol(s) * PLA for n, s in printed.items()}
    total = sum(masses.values()) + masses["06_jaw"] * 2 + masses["09_foot"] * 3
    print("grams solid PLA", {n: round(m, 1) for n, m in masses.items()})
    print("total solid PLA", round(total, 1))
    hardware = 55 + 4 + 4 + 12
    bottle = 280
    printed_guess = total * 0.45
    report.append(f"solid PLA {total:.0f} g")
    report.append(f"about 15 percent infill, printed guess {printed_guess:.0f} g")
    report.append(f"pickup guess {printed_guess + hardware + bottle:.0f} g, limit 500 g")
    with open(os.path.join(HERE, "checks.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(report) + "\n")
    if printed_guess + hardware + bottle > PAYLOAD_LIMIT:
        problems.append(
            f"pickup guess {printed_guess + hardware + bottle:.0f} g is over {PAYLOAD_LIMIT:.0f} g"
        )
        print("\n".join(problems))
        raise SystemExit(1)
    bed_parts = [
        ("01_mast", on_bed(mast)),
        ("02_carriage", on_bed(carriage, 180)),
        ("03_stop", on_bed(stop)),
        ("04_cam", on_bed(cam)),
        ("05_housing", on_bed(housing, 180)),
        ("06_jaw_1", on_bed(make_jaw(0, 0), 180)),
        ("06_jaw_2", on_bed(make_jaw(0, 0), 180)),
        ("06_jaw_3", on_bed(make_jaw(0, 0), 180)),
        ("07_retainer", on_bed(retainer)),
        ("08_guide", on_bed(guide, 180)),
        ("09_foot_1", on_bed(feet[0])),
        ("09_foot_2", on_bed(feet[1])),
        ("09_foot_3", on_bed(feet[2])),
        ("09_foot_4", on_bed(feet[3])),
    ]
    for name, shape in bed_parts:
        bb = shape.val().BoundingBox()
        sides = (bb.xmax - bb.xmin, bb.ymax - bb.ymin, bb.zmax - bb.zmin)
        report.append(f"bed {name}: {sides[0]:.0f} x {sides[1]:.0f} x {sides[2]:.0f} mm")
        if max(sides) > BED:
            problems.append(f"{name} is {max(sides):.0f} mm, bed limit {BED:.0f}")
    report.append(f"guide wall {GUIDE_WALL:.2f} mm, load wall minimum {WALL_LOAD:.2f}")
    with open(os.path.join(HERE, "checks.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(report + problems) + "\n")
    if problems:
        print("\n".join(problems))
        raise SystemExit(1)
    draw_change(guide, feet, jaws_open, os.path.join(HERE, "claw_preview.png"))
    write_print_3mf(bed_parts, os.path.join(HERE, "claw_print.3mf"))
    zip_path = os.path.join(HERE, "claw_print_stl.zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for name, shape in bed_parts:
            z.write(export_stl(shape, name), name + ".stl")
    print("3mf", os.path.getsize(os.path.join(HERE, "claw_print.3mf")))


if __name__ == "__main__":
    main()
