"""Printable 250 ml Bisleri neck claw for one Tower Pro MG995.

The mast, jaws, cam and mounts are PETG. Bought parts are the servo,
a 25T metal horn, two guide springs, M3 screws and nuts.

Z is zero on the top face of the drone plate and increases toward the bottle.
Run:
  D:\\VAYN-CAD-env\\venv\\Scripts\\python.exe gen_claw.py
"""

import math
import os
import zipfile

import cadquery as cq
from OCP.BRepExtrema import BRepExtrema_DistShapeShape

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
PIN_D, SLOT_W = 5.0, 5.8
SHELF_R, OPEN_R = 15.25, 25.0
PIN_R_CLOSED = 28.0
PIN_TRAVEL = OPEN_R - SHELF_R
PIN_R_OPEN = PIN_R_CLOSED + PIN_TRAVEL
CAM_TURN = 75.0
CAP_GAP = 17.0
JAW_T = 7.0
CAM_T = 8.0
PLATE_T = 8.0
RAIL_A, RAIL_B = 10.0, 16.0
RAIL_PITCH = 70.0
STROKE = 20.0
SPRING_GAP = 35.0
BLADE_T, BLADE_W, BLADE_L = 1.0, 6.0, 50.0
STOP_GAP = 6.0
PETG = 1.27e-3  # g/mm3


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
    plate = box(0, 0, 2, 84, 68, 4)
    # four slots so the screws can meet the slots already in the carbon plate
    for x, y in ((24, 18), (24, -18), (-24, 18), (-24, -18)):
        plate = plate.cut(box(x, y, 2, 16, M3_CLEAR, 6))
    plate = plate.cut(cyl_z(0, 0, -1, 6, 8))  # wire
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
    block = box(0, 0, z_block0 + 5, 52, 44, 10)
    # hard stop ring: the block can drift until it hits this frame
    stop = box(0, 0, z_block0 + 5, 52 + 2 * STOP_GAP + 8, 44 + 2 * STOP_GAP + 8, 8)
    stop = stop.cut(box(0, 0, z_block0 + 5, 52 + 2 * STOP_GAP, 44 + 2 * STOP_GAP, 12))
    stop = stop.cut(cyl_z(0, 0, z_block0 - 1, 8, 14))
    rails = None
    z_rail0 = z_block0 + 10
    z_rail1 = z_rail0 + SPRING_GAP + 28 + STROKE
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
    for y in (-18, 18):
        block = block.cut(cyl_z(0, y, z_block0 + 1, 7.4, 9))
    mast = plate.union(blades).union(block).union(stop).union(rails)
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
    plate = cut_holes(plate, pts, M3_CLEAR, z0, PLATE_T, "servo", "carriage")
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
    for y in (-18, 18):
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
    z1 = meta["z_rail1"]
    zc = z1 + 3
    stop = box(0, 0, zc, RAIL_PITCH + RAIL_A + 8, 22, 6)
    pts = [(-RAIL_PITCH / 2, 0), (RAIL_PITCH / 2, 0)]
    stop = cut_holes(stop, pts, M3_CLEAR, zc - 3, 6, "stop", "stop")
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
    shoe = cyl_z(0, 0, 0, 24, JAW_T).cut(cyl_z(0, 0, -1, SHELF_R, JAW_T + 2))
    mask = cq.Workplane("XY").moveTo(0, 0).lineTo(40, -40 * math.tan(math.radians(50))).lineTo(40, 40 * math.tan(math.radians(50))).close().extrude(JAW_T + 2).translate((0, 0, -1))
    shoe = shoe.intersect(mask)
    arm = box(33, 0, JAW_T / 2, 20, 8, JAW_T)
    pin = cyl_z(PIN_R_CLOSED, 0, -(CAP_GAP + 4), PIN_D / 2, CAP_GAP + 7)
    jaw = shoe.union(arm).union(pin)
    jaw = jaw.translate((shift, 0, 0))
    jaw = rot_z(jaw, 120 * index)
    return jaw


def make_housing(meta):
    """Floor, guide fences and three posts. The jaws slide on the floor."""
    z_jaw0 = meta["z_horn_face"] + CAM_T + CAP_GAP
    z_floor = z_jaw0 + JAW_T + 0.4
    floor = cyl_z(0, 0, z_floor, 48, 3.2).cut(cyl_z(0, 0, z_floor - 1, 18, 6))
    # 12 degree lead-in on the bottle side of the hole
    cone = cq.Workplane("XY").add(cq.Solid.makeCone(18, 32, 3)).translate((0, 0, z_floor + 4))
    floor = floor.union(cone)
    fences = None
    for i in range(3):
        for side in (-1, 1):
            fence = box(36, side * 5.2, z_floor - 3, 22, 1.4, 10)
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
        x, y = 60 * math.cos(a), 60 * math.sin(a)
        floor = floor.union(cyl_z(x, y, z_floor, 8, 3.2))
        floor = floor.cut(hole_z(x, y, z_floor - 1, M3_CLEAR / 2, 6))
        floor = floor.cut(nut_slot(x, y, z_floor + 1.8, "z"))
        HOLES.append(("housing", "retainer", i, (x, y, z_floor + 2), M3_CLEAR))
    housing = floor.union(fences).union(posts)
    meta = dict(meta)
    meta["z_jaw0"] = z_jaw0
    meta["z_floor"] = z_floor
    return housing, meta


def make_retainer(meta):
    """Ring that closes the three jaw exits."""
    z = meta["z_jaw0"]
    ring = cyl_z(0, 0, z, 64, JAW_T).cut(cyl_z(0, 0, z - 1, 56, JAW_T + 2))
    pts = []
    for i in range(3):
        a = math.radians(60 + 120 * i)
        pts.append((60 * math.cos(a), 60 * math.sin(a)))
    ring = cut_holes(ring, pts, M3_CLEAR, z, JAW_T, "retainer", "retainer")
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

    # collapsed mast: carriage and springs move up by STROKE, tubes must miss the block
    carriage_up = carriage.translate((0, 0, -STROKE))
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
    }
    for name, shape in printed.items():
        if vol(shape) < 10:
            problems.append(f"{name} has no volume")

    report = [f"preload {f0:.2f} N", f"full stroke {fmax:.2f} N", f"side push {lateral:.2f} N",
              f"spring rate {k:.3f} N/mm for two", f"min spring length {length_min:.1f} mm, solid {solid:.1f} mm"]
    report += [f"{n}: {g:.2f} mm" for n, g in gaps.items()]
    text = "\n".join(report + problems)
    with open(os.path.join(HERE, "checks.txt"), "w", encoding="utf-8") as f:
        f.write(text + "\n")
    print(text)
    if problems:
        raise SystemExit(1)

    assy = cq.Assembly(name="Bisleri250_neck_claw")
    named = [
        ("mast", mast, cq.Color(0.85, 0.55, 0.15)),
        ("carriage", carriage, cq.Color(0.9, 0.7, 0.2)),
        ("stop", stop, cq.Color(0.8, 0.5, 0.1)),
        ("cam", cam, cq.Color(0.95, 0.75, 0.2)),
        ("housing", housing, cq.Color(0.85, 0.55, 0.15)),
        ("jaws", jaws, cq.Color(0.95, 0.6, 0.1)),
        ("retainer", retainer, cq.Color(0.7, 0.45, 0.1)),
        ("servo", servo, cq.Color(0.15, 0.15, 0.15)),
        ("horn", horn, cq.Color(0.75, 0.75, 0.78)),
        ("neck ring", ring, cq.Color(0.2, 0.45, 0.8)),
    ]
    for name, shape, color in named:
        assy.add(shape, name=name, color=color)
    step_path = os.path.join(HERE, "claw.step")
    assy.save(step_path)
    print("step", os.path.getsize(step_path))

    paths = []
    for name, shape in printed.items():
        paths.append(export_stl(shape, name))
    # one more jaw is the same STL printed three times; the zip carries one file
    zip_path = os.path.join(HERE, "claw_print_stl.zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as z:
        for p in paths:
            z.write(p, os.path.basename(p))
    masses = {n: vol(s) * PETG for n, s in printed.items()}
    total = sum(masses.values()) + masses["06_jaw"] * 2
    print("grams", {n: round(m, 1) for n, m in masses.items()})
    print("total petg", round(total, 1))
    if total > 250:
        problems.append(f"printed mass {total:.0f} g is over 250 g")
        print("\n".join(problems))
        raise SystemExit(1)
    bed = cq.Assembly(name="Bisleri250_print")
    offsets = {
        "01_mast": (0, 0, 0),
        "02_carriage": (160, 0, 0),
        "03_stop": (160, 80, 0),
        "04_cam": (250, 0, 0),
        "05_housing": (0, 180, 0),
        "06_jaw": (140, 160, 0),
        "07_retainer": (220, 160, 0),
    }
    for name, shape in printed.items():
        bed.add(shape.translate(offsets[name]), name=name, color=cq.Color(0.9, 0.6, 0.15))
    bed.save(os.path.join(HERE, "claw_print.3mf"))


if __name__ == "__main__":
    main()
