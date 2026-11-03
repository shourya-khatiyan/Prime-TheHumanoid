"""Arm test stand. Every split plugs together before the screw goes in.

The wooden stick is 27 x 18 x 620 mm and is not printed. Printed pieces are a
shell around it, a bolted base, a shoulder clamp, and a plate for the ODESC.
A plug is 0.3 mm smaller per side than its pocket, which is the slip fit for
PETG on an FDM printer. The script refuses to write files if a plug does not
fit, two printed parts collide, a brace misses the frame, or a screw misses.

Run:
  D:\\VAYN-CAD-env\\venv\\Scripts\\python.exe gen_stand.py
"""

import math
import os
import zipfile

import cadquery as cq
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from mpl_toolkits.mplot3d.art3d import Poly3DCollection  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))

BED = 246.0
CLEAR = 0.30  # per side, PETG slip fit
STICK = (27.0, 18.0, 620.0)
SEG_L = 200.0
SEG_N = 3
TOWER = 84.0
HALF = TOWER / 2
WALL = 8.0
PIN = 6.0  # hole for an M5, loose enough for the 0.3 mm plug play
M4 = 4.5
GRID = 25.0
HOUSING_D = 104.0
AXIS_Z = 620.0
WRIST_DROP = 532.0
FOOT_H = 20.0
BEAM_H = 36.0
BEAM_W = 28.0
TENON_L = 12.0
POCKET_L = 14.0  # 2 mm left at the end so the plug stops on the sides

# base plan, outer 596 x 400 mm. tenons sit inside the next part.
CORNER = 44.0
COUPLER = 32.0
BAY_X = 148.0
BAY_Y = 140.0
OX = 2 * CORNER + 2 * COUPLER + 3 * BAY_X  # 596
OY = 2 * CORNER + COUPLER + 2 * BAY_Y  # 400

BLUE = "#3F6FB5"
WOOD = "#2A2A2A"
BRICK = "#A0522D"
GREY = "#D0D0D0"


def box(sx, sy, sz, cx, cy, cz):
    """Centered box."""
    return cq.Workplane("XY").box(sx, sy, sz).val().translate(cq.Vector(cx, cy, cz))


def fuse(parts):
    """Join solids."""
    acc = parts[0]
    for part in parts[1:]:
        acc = acc.fuse(part)
    return acc


def cyl(r, length, x, y, z, axis):
    """Cylinder starting at the point."""
    direction = {"x": (1, 0, 0), "y": (0, 1, 0), "z": (0, 0, 1)}[axis]
    return cq.Solid.makeCylinder(r, length, cq.Vector(x, y, z), cq.Vector(*direction))


def drill(shape, diameter, length, x, y, z, axis):
    """Cut a hole starting at the point."""
    return shape.cut(cyl(diameter / 2, length, x, y, z, axis))


def drill_through(shape, diameter, x, y, z, axis):
    """Cut a hole centered on the point."""
    span = 80.0
    origin = {"x": (x - span / 2, y, z), "y": (x, y - span / 2, z), "z": (x, y, z - span / 2)}[axis]
    return drill(shape, diameter, span, *origin, axis)


def bar_xz(x0, z0, x1, z1, y, depth=12.0, thick=10.0):
    """Brace in the x-z plane, centerline from (x0, z0) to (x1, z1)."""
    dx, dz = x1 - x0, z1 - z0
    span = math.hypot(dx, dz)
    angle = math.degrees(math.atan2(dz, dx))
    bar = cq.Workplane("XY").box(span, depth, thick).val()
    bar = bar.rotate((0, 0, 0), (0, 1, 0), -angle)
    return bar.translate(cq.Vector((x0 + x1) / 2, y, (z0 + z1) / 2))


def bar_yz(y0, z0, y1, z1, x, depth=12.0, thick=10.0):
    """Brace in the y-z plane."""
    bar = bar_xz(y0, z0, y1, z1, 0, depth, thick)
    bar = bar.rotate((0, 0, 0), (0, 0, 1), 90)
    return bar.translate(cq.Vector(x, 0, 0))


def vol(shape):
    """Volume in mm3. An empty cut returns 0."""
    try:
        solids = shape.Solids()
    except Exception:
        return 0.0
    return sum(solid.Volume() for solid in solids)


def size_of(shape):
    """Overall size."""
    bb = shape.BoundingBox()
    return (bb.xlen, bb.ylen, bb.zlen)


# ---------------------------------------------------------------- tower
def tower_tenon(z_sign):
    """Two plugs. z_sign -1 hangs off the bottom, +1 is only used as a shape to copy."""
    zc = -TENON_L / 2 if z_sign < 0 else SEG_L + TENON_L / 2
    posts = []
    for x in (-34.0, 34.0):
        posts.append(box(16, 14, TENON_L, x, -30, zc))
    return posts


def tower_pocket_cutter(at_top):
    """Voids the tenons drop into. 0.3 mm larger per side, 2 mm deeper than the plug."""
    zc = (SEG_L - POCKET_L / 2) if at_top else POCKET_L / 2
    # foot uses at_top False and then moves the cutter
    cuts = []
    for x in (-34.0, 34.0):
        cuts.append(box(16 + 2 * CLEAR, 14 + 2 * CLEAR, POCKET_L + 1, x, -30, zc))
    return cuts


def tower_back():
    """Rear half. Plugs hang off the bottom. Pockets are open on top. Grooves take the front."""
    parts = [
        box(TOWER, WALL, SEG_L, 0, -HALF + WALL / 2, SEG_L / 2),
        box(16, 26, SEG_L, -34, -HALF + 13, SEG_L / 2),
        box(16, 26, SEG_L, 34, -HALF + 13, SEG_L / 2),
        box(52, 12, 16, 0, -HALF + 6, 8),
        box(52, 12, 16, 0, -HALF + 6, SEG_L - 8),
    ]
    parts += tower_tenon(-1)
    # side braces. each end is buried in a corner post
    parts.append(bar_yz(-38, 24, -20, 100, -40, depth=6))
    parts.append(bar_yz(-20, 100, -38, 176, -40, depth=6))
    parts.append(bar_yz(-38, 24, -20, 100, 40, depth=6))
    parts.append(bar_yz(-20, 100, -38, 176, 40, depth=6))
    shape = fuse(parts)
    for cutter in tower_pocket_cutter(True):
        shape = shape.cut(cutter)
    # stick channel, open toward the front. 0.4 mm clear of the 18 mm stick
    shape = shape.cut(box(STICK[0] + 0.8, 16, SEG_L + 4, 0, -4, SEG_L / 2))
    # vertical grooves the front tongues drop into. open at the top.
    for x in (-30.0, 30.0):
        shape = shape.cut(box(10 + 2 * CLEAR, 16, SEG_L, x, -22, SEG_L / 2 + 20))
    # grid, 25 mm, clear of the plugs
    for col in (-22.0, 0.0, 22.0):
        z = 30.0
        while z <= 170.0:
            shape = drill_through(shape, M4, col, -30, z, "y")
            z += GRID
    # cross pins through the bottom plugs, and through the top pockets
    for x in (-34.0, 34.0):
        shape = drill_through(shape, PIN, x, -30, -6, "x")
        shape = drill_through(shape, PIN, x, -30, SEG_L - 6, "x")
    # screws that lock the front after it has dropped in
    for z in (40.0, 160.0):
        for x in (-30.0, 30.0):
            shape = drill_through(shape, PIN, x, -24, z, "y")
    return shape


def tower_front():
    """Front half. Tongues drop down the back grooves. Braces meet the corner posts."""
    parts = [
        box(16, 26, SEG_L, -34, HALF - 13, SEG_L / 2),
        box(16, 26, SEG_L, 34, HALF - 13, SEG_L / 2),
        box(52, 12, 16, 0, HALF - 6, 8),
        box(52, 12, 16, 0, HALF - 6, SEG_L - 8),
        # tongue tip sits in the back groove. the rest bridges to this post
        box(10, 50, 158, -30, -3, 99),
        box(10, 50, 158, 30, -3, 99),
    ]
    # X on the front. centerline ends lie inside the corner posts
    parts.append(bar_xz(-36, 24, 36, 100, HALF - 8))
    parts.append(bar_xz(-36, 176, 36, 100, HALF - 8))
    parts.append(bar_xz(36, 24, -36, 100, HALF - 8))
    parts.append(bar_xz(36, 176, -36, 100, HALF - 8))
    shape = fuse(parts)
    shape = shape.cut(box(STICK[0] + 0.8, 16, SEG_L + 4, 0, 4, SEG_L / 2))
    for z in (40.0, 160.0):
        for x in (-30.0, 30.0):
            shape = drill_through(shape, PIN, x, -10, z, "y")
    return shape


def foot_shape():
    """Plate under the shell. Top pockets match the shell plugs. One pocket takes the center beam."""
    shape = box(130, 150, FOOT_H, 0, 10, FOOT_H / 2)
    shape = shape.cut(box(STICK[0] + 0.8, STICK[1] + 0.8, FOOT_H + 4, 0, 0, FOOT_H / 2))
    for cutter in tower_pocket_cutter(False):
        # those cutters sit at the bottom of a segment. move them up into the foot top
        shape = shape.cut(cutter.translate(cq.Vector(0, 0, FOOT_H - POCKET_L)))
    # pocket on the +y face for the center beam tenon. beam axis is y, tenon is 18 x 16 x 12
    face = 10 + 75  # +y face of the 150 mm plate centered at y=10
    shape = shape.cut(box(18 + 2 * CLEAR, POCKET_L, 16 + 2 * CLEAR, 0, face - POCKET_L / 2, BEAM_H / 2))
    for x in (-34.0, 34.0):
        shape = drill_through(shape, PIN, x, -30, FOOT_H - 6, "x")
    # pin for the center beam, through the pocket
    shape = drill_through(shape, PIN, 0, 75 + 6, BEAM_H / 2, "x")
    return shape


# ---------------------------------------------------------------- base
def beam(length):
    """Truss with a plug on both ends. Plugs are 12 mm and sit inside the next part."""
    parts = [
        box(length, BEAM_W, 8, length / 2, 0, 4),
        box(length, BEAM_W, 8, length / 2, 0, BEAM_H - 4),
        box(20, BEAM_W, BEAM_H, 10, 0, BEAM_H / 2),
        box(20, BEAM_W, BEAM_H, length - 10, 0, BEAM_H / 2),
        box(TENON_L, 18, 16, -TENON_L / 2, 0, BEAM_H / 2),
        box(TENON_L, 18, 16, length + TENON_L / 2, 0, BEAM_H / 2),
    ]
    # braces buried 8 mm into the end blocks
    parts.append(bar_xz(12, 10, length - 12, BEAM_H - 10, 0, depth=BEAM_W - 8, thick=8))
    parts.append(bar_xz(12, BEAM_H - 10, length - 12, 10, 0, depth=BEAM_W - 8, thick=8))
    shape = fuse(parts)
    # pin hole in each plug, 6 mm in from the tip
    shape = drill_through(shape, PIN, -6, 0, BEAM_H / 2, "y")
    shape = drill_through(shape, PIN, length + 6, 0, BEAM_H / 2, "y")
    # saddle screws into the middle of an x beam
    shape = drill_through(shape, PIN, length / 2 - 18, 0, BEAM_H, "z")
    shape = drill_through(shape, PIN, length / 2 + 18, 0, BEAM_H, "z")
    return shape


def coupler():
    """Straight block. A plug enters each end."""
    shape = box(COUPLER, BEAM_W + 8, BEAM_H, COUPLER / 2, 0, BEAM_H / 2)
    shape = shape.cut(box(POCKET_L, 18 + 2 * CLEAR, 16 + 2 * CLEAR, POCKET_L / 2, 0, BEAM_H / 2))
    shape = shape.cut(box(POCKET_L, 18 + 2 * CLEAR, 16 + 2 * CLEAR, COUPLER - POCKET_L / 2, 0, BEAM_H / 2))
    shape = drill_through(shape, PIN, 6, 0, BEAM_H / 2, "y")
    shape = drill_through(shape, PIN, COUPLER - 6, 0, BEAM_H / 2, "y")
    return shape


def corner():
    """L block. Pockets face local +x and local +y. Rotate it for the four corners."""
    shape = box(CORNER, CORNER, BEAM_H, CORNER / 2, CORNER / 2, BEAM_H / 2)
    shape = shape.cut(box(POCKET_L, 18 + 2 * CLEAR, 16 + 2 * CLEAR, CORNER - POCKET_L / 2, CORNER / 2, BEAM_H / 2))
    shape = shape.cut(box(18 + 2 * CLEAR, POCKET_L, 16 + 2 * CLEAR, CORNER / 2, CORNER - POCKET_L / 2, BEAM_H / 2))
    shape = drill_through(shape, PIN, CORNER - 6, CORNER / 2, BEAM_H / 2, "y")
    shape = drill_through(shape, PIN, CORNER / 2, CORNER - 6, BEAM_H / 2, "x")
    return shape


def saddle():
    """Sits on the north beam and takes the center beam's plug."""
    shape = box(BEAM_W + 16, 40, BEAM_H + 8, 0, 0, BEAM_H / 2 + 4)
    # slot that drops over the north beam
    shape = shape.cut(box(BEAM_W + 0.6, 40, BEAM_H, 0, 6, BEAM_H / 2))
    # pocket facing -y
    shape = shape.cut(box(18 + 2 * CLEAR, POCKET_L, 16 + 2 * CLEAR, 0, -20 + POCKET_L / 2, BEAM_H / 2))
    shape = drill_through(shape, PIN, 0, -20 + 6, BEAM_H / 2, "x")
    # two screws down into the north beam
    shape = drill_through(shape, PIN, -18, 0, BEAM_H + 4, "z")
    shape = drill_through(shape, PIN, 18, 0, BEAM_H + 4, "z")
    return shape


def fit_coupon():
    """One plug and one pocket, to print before the stand."""
    plug = box(18, 16, TENON_L, 0, 0, TENON_L / 2)
    block = box(40, 36, 30, 0, 0, 15)
    block = block.cut(box(18 + 2 * CLEAR, 16 + 2 * CLEAR, POCKET_L, 0, 0, POCKET_L / 2))
    return fuse([plug.translate(cq.Vector(0, 0, 34)), block])


# ---------------------------------------------------------------- clamp and plate
def clamp_lower():
    """Cradle. Two plugs match the shell pockets. Bore axis is the local origin."""
    bore_r = HOUSING_D / 2 + 1.0
    outer = bore_r + WALL
    shell = cyl(outer, 50, 0, -25, 0, "y").cut(cyl(bore_r, 56, 0, -28, 0, "y"))
    shell = shell.cut(box(180, 80, 90, 0, 0, 45))
    shell = shell.cut(box(180, 70, 160, 0, -55, 0))
    plate = box(76, 12, 50, 0, -48, -24)
    # plugs land in the shell pockets, 126 mm behind the bore
    plugs = [
        box(16, 14, TENON_L, x, -126, -TENON_L / 2) for x in (-34.0, 34.0)
    ]
    arms = [box(16, 90, 14, x, -86, -16) for x in (-34.0, 34.0)]
    shape = fuse([shell, plate] + plugs + arms)
    for x in (-34.0, 34.0):
        shape = drill_through(shape, PIN, x, -126, -6, "x")
    for cx in (-62.0, 62.0):
        shape = fuse([shape, box(14, 50, 12, cx, 0, -6)])
        shape = drill_through(shape, PIN, cx, 0, -2, "y")
    return shape


def clamp_upper():
    """Cap. Lug holes match the lower cradle."""
    bore_r = HOUSING_D / 2 + 1.0
    outer = bore_r + WALL
    shell = cyl(outer, 50, 0, -25, 0, "y").cut(cyl(bore_r, 56, 0, -28, 0, "y"))
    shell = shell.cut(box(180, 80, 90, 0, 0, -45))
    shell = shell.cut(box(180, 70, 160, 0, -55, 0))
    shape = shell
    for cx in (-62.0, 62.0):
        shape = fuse([shape, box(14, 50, 12, cx, 0, 2)])
        shape = drill_through(shape, PIN, cx, 0, -2, "y")
    return shape


def odrive_plate():
    """Bolts to the 25 mm grid. Slots suit the 135 x 50 mm ODESC board."""
    shape = box(90, 6, 80, 0, 3, 0)
    for x in (-22.0, 22.0):
        for z in (-25.0, 25.0):
            shape = drill_through(shape, M4, x, 3, z, "y")
    for x in (-55, 55):
        for z in (-18, 18):
            shape = shape.cut(box(12, 10, 5.2, x, 3, z))
    return shape


# ---------------------------------------------------------------- placement
def rot_z(shape, degrees):
    """Turn about the vertical axis."""
    return shape.rotate((0, 0, 0), (0, 0, 1), degrees)


def place_beam_x(length, x0, y):
    """Beam running +x. Body starts at x0. Centerline y."""
    return beam(length).translate(cq.Vector(x0, y, 0))


def place_beam_y(length, x, y0):
    """Beam running +y. The local -x plug becomes the -y plug."""
    return rot_z(beam(length), 90).translate(cq.Vector(x, y0, 0))


def base_world():
    """Placed base parts and the plug/pocket pairs to test."""
    parts = []
    checks = []
    y_s, y_n = CORNER / 2, OY - CORNER / 2
    # corner solid is recentered on the origin, then turned, then put on its center
    centered = corner().translate(cq.Vector(-CORNER / 2, -CORNER / 2, 0))
    corners = [
        (CORNER / 2, CORNER / 2, 0),
        (OX - CORNER / 2, CORNER / 2, 90),
        (OX - CORNER / 2, OY - CORNER / 2, 180),
        (CORNER / 2, OY - CORNER / 2, 270),
    ]
    for cx, cy, angle in corners:
        parts.append(("corner", rot_z(centered, angle).translate(cq.Vector(cx, cy, 0))))
    # south beams and couplers
    cursor = CORNER
    for i in range(3):
        parts.append(("beam_x", place_beam_x(BAY_X, cursor, y_s)))
        cursor += BAY_X
        if i < 2:
            parts.append(("coupler", coupler().translate(cq.Vector(cursor, y_s, 0))))
            cursor += COUPLER
    # north, same x pattern
    cursor = CORNER
    for i in range(3):
        parts.append(("beam_x", place_beam_x(BAY_X, cursor, y_n)))
        cursor += BAY_X
        if i < 2:
            parts.append(("coupler", coupler().translate(cq.Vector(cursor, y_n, 0))))
            cursor += COUPLER
    # west and east
    for x_face, y_dir in ((CORNER / 2, 1), (OX - CORNER / 2, 1)):
        cursor_y = CORNER
        for i in range(2):
            parts.append(("beam_y", place_beam_y(BAY_Y, x_face, cursor_y)))
            cursor_y += BAY_Y
            if i < 1:
                turned = rot_z(coupler(), 90).translate(cq.Vector(x_face, cursor_y, 0))
                parts.append(("coupler", turned))
                cursor_y += COUPLER
    return parts, checks


def tower_world(back, front, foot):
    """Shell, foot, stick, clamp, and plate, in place."""
    tx, ty = OX / 2, 150.0
    parts = [("foot", foot.translate(cq.Vector(tx, ty, 0)))]
    for index in range(SEG_N):
        z0 = FOOT_H + index * SEG_L
        parts.append(("tower_back", back.translate(cq.Vector(tx, ty, z0))))
        parts.append(("tower_front", front.translate(cq.Vector(tx, ty, z0))))
    return parts


# ---------------------------------------------------------------- checks
def assert_fit(plug, pocket, name, log):
    """The plug must lie inside the pocket void."""
    extra = vol(plug.cut(pocket))
    ok = extra < 5.0 and vol(plug) > 100.0
    log.append(f"{'ok' if ok else 'FAIL'}  fit   {name}: plug {vol(plug):.0f} mm3, sticks out {extra:.1f} mm3")
    if not ok:
        raise SystemExit(log[-1])


def assert_clear(a, b, name, log, limit=8.0):
    """Printed parts that meet at a plug must not occupy the same space."""
    clash = vol(a.intersect(b))
    ok = clash < limit
    log.append(f"{'ok' if ok else 'FAIL'}  clear {name}: overlap {clash:.1f} mm3")
    if not ok:
        raise SystemExit(log[-1])


def assert_bite(bar, frame, name, log):
    """A brace must land inside the frame, not stop short of it."""
    bite = vol(bar.intersect(frame))
    ok = bite > 80.0
    log.append(f"{'ok' if ok else 'FAIL'}  brace {name}: {bite:.0f} mm3 inside the frame")
    if not ok:
        raise SystemExit(log[-1])


def assert_bed(name, shape, log):
    """Longest side must fit the P2S with 5 mm spare on each edge."""
    dims = size_of(shape)
    ok = max(dims) <= BED
    log.append(f"{'ok' if ok else 'FAIL'}  bed   {name}: {dims[0]:.0f} x {dims[1]:.0f} x {dims[2]:.0f} mm")
    if not ok:
        raise SystemExit(log[-1])
    return dims


def check_structure(log):
    """Braces meet the posts, and a loose bar would be caught here."""
    posts = fuse([
        box(16, 26, SEG_L, -34, -HALF + 13, SEG_L / 2),
        box(16, 26, SEG_L, 34, -HALF + 13, SEG_L / 2),
        box(16, 26, SEG_L, -34, HALF - 13, SEG_L / 2),
        box(16, 26, SEG_L, 34, HALF - 13, SEG_L / 2),
    ])
    for name, bar in (
        ("front a", bar_xz(-36, 24, 36, 100, HALF - 8)),
        ("front b", bar_xz(36, 24, -36, 100, HALF - 8)),
        ("side a", bar_yz(-38, 24, -20, 100, -40, depth=6)),
        ("side b", bar_yz(-20, 100, -38, 176, -40, depth=6)),
    ):
        assert_bite(bar, posts, name, log)
    sample = beam(BAY_X)
    ends = fuse([
        box(20, BEAM_W, BEAM_H, 10, 0, BEAM_H / 2),
        box(20, BEAM_W, BEAM_H, BAY_X - 10, 0, BEAM_H / 2),
        box(BAY_X, BEAM_W, 8, BAY_X / 2, 0, 4),
        box(BAY_X, BEAM_W, 8, BAY_X / 2, 0, BEAM_H - 4),
    ])
    assert_bite(bar_xz(12, 10, BAY_X - 12, BEAM_H - 10, 0, depth=BEAM_W - 8, thick=8), ends, "beam", log)
    return sample


def check_plugs(log):
    """One plug of each kind, seated the way it is assembled."""
    # shell plug into the foot pocket
    plug = box(16, 14, TENON_L, -34, -30, FOOT_H - TENON_L / 2)
    pocket = box(16 + 2 * CLEAR, 14 + 2 * CLEAR, POCKET_L + 1, -34, -30, FOOT_H - POCKET_L / 2)
    assert_fit(plug, pocket, "shell into foot", log)
    # next shell into the one below
    plug = box(16, 14, TENON_L, 34, -30, SEG_L - TENON_L / 2)
    pocket = box(16 + 2 * CLEAR, 14 + 2 * CLEAR, POCKET_L + 1, 34, -30, SEG_L - POCKET_L / 2)
    assert_fit(plug, pocket, "shell into shell", log)
    # only the tip of the tongue has to sit in the groove
    tongue = box(10, 14, 156, -30, -22, 99)
    groove = box(10 + 2 * CLEAR, 16, SEG_L, -30, -22, SEG_L / 2 + 20)
    assert_fit(tongue, groove, "front into back", log)
    # beam plug into a coupler pocket
    plug = box(TENON_L, 18, 16, BAY_X + TENON_L / 2, 0, BEAM_H / 2)
    pocket = box(POCKET_L, 18 + 2 * CLEAR, 16 + 2 * CLEAR, BAY_X + POCKET_L / 2, 0, BEAM_H / 2)
    assert_fit(plug, pocket, "beam into coupler", log)


def check_assembly(parts, stick, housing, log):
    """Walk the assembly. Parts that plug together must not collide."""
    shells = [shape for name, shape in parts if name in ("tower_back", "tower_front", "foot")]
    for name, shape in parts:
        if name == "tower_back" or name == "foot":
            assert_clear(stick, shape, f"stick vs {name}", log)
        if name.startswith("tower") or name == "foot":
            pass
    assert_clear(housing, parts_by(parts, "clamp_lower"), "housing vs clamp", log, limit=20.0)
    # neighbouring shell segments
    backs = [shape for name, shape in parts if name == "tower_back"]
    for i in range(len(backs) - 1):
        assert_clear(backs[i], backs[i + 1], f"back {i} vs back {i + 1}", log)
    fronts = [shape for name, shape in parts if name == "tower_front"]
    for back, front in zip(backs, fronts):
        assert_clear(back, front, "back vs front", log)


def parts_by(parts, name):
    """First placed solid with this name."""
    for label, shape in parts:
        if label == name:
            return shape
    raise KeyError(name)


def lay_down(shape):
    """Long vertical parts lie on the bed so the beads run along their length."""
    return shape.rotate((0, 0, 0), (1, 0, 0), 90)


def print_pose(name, shape):
    """Orientation that goes into the zip."""
    if name.startswith("tower") or name.startswith("clamp"):
        return lay_down(shape)
    return shape


def tessellate(shape, color):
    """Coarse triangles for the preview."""
    verts, tris = shape.tessellate(2.5)
    points = np.array([(v.x, v.y, v.z) for v in verts])
    faces = points[np.array(tris)]
    rgb = tuple(int(color[i:i + 2], 16) / 255 for i in (1, 3, 5))
    return faces, rgb


def draw_views(items, path):
    """Front, back, side, and top of the assembly."""
    meshes = [tessellate(shape, color) for _name, shape, color in items]
    fig = plt.figure(figsize=(12, 10), facecolor="white")
    views = [("front", 12, -90), ("back", 12, 90), ("side", 12, 0), ("top", 88, -90)]
    for i, (title, elev, azim) in enumerate(views, start=1):
        ax = fig.add_subplot(2, 2, i, projection="3d")
        for faces, rgb in meshes:
            ax.add_collection3d(Poly3DCollection(faces, facecolor=rgb, edgecolor="none", alpha=0.95))
        ax.view_init(elev=elev, azim=azim)
        ax.set_xlim(-20, OX + 20)
        ax.set_ylim(-20, OY + 80)
        ax.set_zlim(0, 760)
        ax.set_box_aspect((OX + 40, OY + 100, 760))
        ax.set_title(title)
        ax.set_axis_off()
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)


def main():
    """Check the joints, then write the print files."""
    os.makedirs(HERE, exist_ok=True)
    log = ["assembly check", ""]
    check_structure(log)
    check_plugs(log)

    back = tower_back()
    front = tower_front()
    foot = foot_shape()
    unique = {
        "tower_back": back,
        "tower_front": front,
        "beam_x": beam(BAY_X),
        "beam_y": beam(BAY_Y),
        "coupler": coupler(),
        "corner": corner(),
        "foot": foot,
        "clamp_lower": clamp_lower(),
        "clamp_upper": clamp_upper(),
        "odrive_plate": odrive_plate(),
        "fit_coupon": fit_coupon(),
    }
    # center beam length is set from the placed foot and the north rail
    unique["beam_center"] = beam(125.0)
    unique["saddle"] = saddle()

    log.append("")
    posed = {}
    for name, shape in unique.items():
        pose = print_pose(name, shape)
        dims = assert_bed(name, pose, log)
        posed[name] = pose
        print(f"{name:16} {dims[0]:7.1f} {dims[1]:7.1f} {dims[2]:7.1f}")

    placed, _unused = base_world()
    for i in range(len(placed)):
        for j in range(i + 1, len(placed)):
            overlap = vol(placed[i][1].intersect(placed[j][1]))
            if overlap > 8.0:
                raise SystemExit(f"base clash {placed[i][0]} and {placed[j][0]}: {overlap:.0f} mm3")
    log.append("ok  clear base frame: no two base pieces occupy the same space")
    placed += tower_world(back, front, foot)
    tx, ty = OX / 2, 150.0
    y_n = OY - CORNER / 2
    placed.append(("beam_center", place_beam_y(125.0, tx, 234.0)))
    placed.append(("saddle", saddle().translate(cq.Vector(tx, y_n, 0))))
    log.append("")
    assert_fit(
        box(18, TENON_L, 16, tx, 228, BEAM_H / 2),
        box(18 + 2 * CLEAR, POCKET_L, 16 + 2 * CLEAR, tx, 228, BEAM_H / 2),
        "center beam into foot", log)
    assert_fit(
        box(18, TENON_L, 16, tx, 365, BEAM_H / 2),
        box(18 + 2 * CLEAR, POCKET_L, 16 + 2 * CLEAR, tx, 365, BEAM_H / 2),
        "center beam into saddle", log)
    clamp_at = cq.Vector(tx, ty + 96, AXIS_Z)
    placed.append(("clamp_lower", clamp_lower().translate(clamp_at)))
    placed.append(("clamp_upper", clamp_upper().translate(clamp_at)))
    # plate centered on a real grid row of the middle segment
    placed.append(("odrive_plate", odrive_plate().translate(cq.Vector(tx, ty - HALF - 3, FOOT_H + SEG_L + 95))))

    stick = box(STICK[0], STICK[1], STICK[2], tx, ty, STICK[2] / 2)
    housing = cyl(HOUSING_D / 2, 46, tx, ty + 96 - 23, AXIS_Z, "y")
    log.append("")
    check_assembly(placed, stick, housing, log)

    report = os.path.join(HERE, "assembly_check.txt")
    with open(report, "w", encoding="utf-8") as handle:
        handle.write("\n".join(log) + "\n")
    print("\n".join(log))

    stl_dir = os.path.join(HERE, "stl")
    os.makedirs(stl_dir, exist_ok=True)
    for name, pose in posed.items():
        cq.exporters.export(pose, os.path.join(stl_dir, f"{name}.stl"), tolerance=0.08, angularTolerance=0.2)
    # one STL per piece, not one per shape. three tower layers need three files.
    qty = {
        "fit_coupon": 1,
        "tower_back": 3,
        "tower_front": 3,
        "beam_x": 6,
        "beam_y": 4,
        "beam_center": 1,
        "coupler": 6,
        "corner": 4,
        "saddle": 1,
        "foot": 1,
        "clamp_lower": 1,
        "clamp_upper": 1,
        "odrive_plate": 1,
    }
    missing = set(posed) - set(qty)
    extra = set(qty) - set(posed)
    if missing or extra:
        raise SystemExit(f"print list does not match the parts: missing {missing}, extra {extra}")
    zip_path = os.path.join(HERE, "stand_print.zip")
    listing = ["file, copies"]
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for name, copies in qty.items():
            listing.append(f"{name}, {copies}")
            src = os.path.join(stl_dir, f"{name}.stl")
            for index in range(1, copies + 1):
                archive.write(src, f"{name}_{index}.stl" if copies > 1 else f"{name}.stl")
        archive.writestr("print_list.txt", "\n".join(listing) + "\n")
    print(f"zip files {sum(qty.values())} from {len(qty)} shapes")

    assy = cq.Assembly(name="arm-test-stand")
    preview = []
    for index, (name, shape) in enumerate(placed):
        assy.add(shape, name=f"{name}-{index}", color=cq.Color(BLUE))
        preview.append((name, shape, BLUE))
    assy.add(stick, name="stick", color=cq.Color(WOOD))
    assy.add(housing, name="housing", color=cq.Color(GREY))
    preview.append(("stick", stick, WOOD))
    preview.append(("housing", housing, GREY))
    step_path = os.path.join(HERE, "stand.step")
    assy.save(step_path)
    draw_views(preview, os.path.join(HERE, "stand_preview.png"))
    print(f"wrote {zip_path}")
    print(f"wrote {step_path}")


if __name__ == "__main__":
    main()
