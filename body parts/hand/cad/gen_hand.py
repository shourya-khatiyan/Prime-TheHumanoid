"""Hollow five-finger dummy hand for the Rev 2 forearm.

Z is zero on the wrist mating face and grows toward the fingertips.
+X is the thumb side. +Y is the palm. Nothing in the hand moves.

The wrist plate bolts to the wrist block. The shell slides onto the
plate collar and two screws lock the tabs. Run:
  D:\\VAYN-CAD-env\\venv\\Scripts\\python.exe gen_hand.py
"""

import ctypes
import math
import os
import sys
import zipfile

import cadquery as cq
import lib3mf
from OCP.BRepExtrema import BRepExtrema_DistShapeShape
from OCP.TopAbs import TopAbs_SOLID
from OCP.TopExp import TopExp_Explorer

HERE = os.path.dirname(os.path.abspath(__file__))
STL_DIR = os.path.join(HERE, "stl")
sys.path.insert(0, os.path.abspath(os.path.join(HERE, "..", "..", "arm", "cad")))
import arm_params as arm  # noqa: E402

# --- motion ---
# The plate bolts to the forearm. The shell sits on the plate. The hand does not move.

# --- bought / existing envelopes ---
# Wrist block 211, arm_params.WRIST and parts.md. Spigot is the model size, not a new caliper reading.
SPIGOT_R = arm.WRIST["spigot_r"]  # 9.99
SPIGOT_H = arm.WRIST["spigot_h"]  # 1.8
PCD = arm.WRIST["pcd_r"]  # 15, four M3 inserts
# PETG plug clearance already proven on the stand, 0.30 mm per side.
CLEAR = 0.30
M3_CLEAR = 3.4  # claw M3_CLEAR, proven
CSK_D, CSK_H = 6.3, 1.7  # arm M3 countersink
NUT_T, NUT_AF = 2.4, 5.5  # ISO 4032 M3
BED = 246.0
# gates.md PETG. Showcase only, so the arm's 150 g dummy-hand load is the ceiling.
PETG = 1.27e-3
MASS_LIMIT = 150.0
# Two perimeters are about 0.90 mm. A screw wall is 1.35 mm. The shell is showcase.
SHELL = 1.20
LOAD_WALL = 1.35
DECOR = 0.90
FLANGE_T = 6.0
COLLAR_Z0, COLLAR_Z1 = 6.0, 13.2
CUFF_TOP = 14.0
# Drillis-Contini hand on this arm is 173 mm. Greiner palm/hand sits near 0.565.
HAND_L = arm.L_HAND
KNUCKLE_Z = round(0.565 * HAND_L, 1)  # 97.7
# PMC11184424 male right fingers, mm. Middle matches HAND_L - KNUCKLE_Z.
FINGER_L = {"index": 66.5, "middle": 75.3, "ring": 70.6, "little": 58.5, "thumb": 50.6}
# Widths from ISO index ~18-19 and Greiner breadth ratios (middle 1.01, ring 0.94, little 0.82).
FINGER_W = {"little": 14.8, "ring": 16.9, "middle": 18.2, "index": 18.0, "thumb": 20.0}
FINGER_GAP = 4.7  # together at the knuckle; yaw opens the tips
BREADTH = 82.0  # project hand breadth, inside the 80-85 mm note
DEPTH_K = 0.86  # assumption: section depth / breadth, a bit under Greiner depth ~ breadth
TIP_K = 0.58
OVERLAP = 16.0
FINGER_Y = 1.0
YAW = {"little": -16.0, "ring": -7.0, "middle": 0.0, "index": 8.0}
# Thumb leans 36 deg off the fingers so the underside stays inside a 45 deg overhang.
THUMB_TILT = 36.0
THUMB_PALM = 20.0  # how much of that tilt points toward the palm
WRIST_RX, WRIST_RY = 27.0, 18.0  # 54 x 36 cuff, covers the Ø30 screws
# Palm starts inside the cuff so the two solids share volume, not a skin. OCC drops a shared skin.
PALM_OUTER = (
    (8.0, 25.5, 16.8),
    (CUFF_TOP, 26.2, 17.2),
    (24.0, 28.5, 17.2),
    (48.0, 31.0, 16.0),
    (72.0, 33.5, 15.0),
    (KNUCKLE_Z, 34.0, 14.0),
)
# Void stays one shell inside the palm, then narrows into the finger tunnels.
# It must not end as a flat lid. The tunnels leave through the fingertips.
PALM_VOID = (
    (FLANGE_T - 0.6, WRIST_RX - SHELL, WRIST_RY - SHELL),
    (13.5, WRIST_RX - SHELL, WRIST_RY - SHELL),
    (16.0, 25.0, 16.0),
    (24.0, 27.2, 16.0),
    (36.0, 28.0, 15.2),
    (60.0, 12.0, 5.0),
)


COLLAR_WALL = 2.4  # stays clear of the M3 countersinks, which sit on the 45 deg screws
EAR_Y = 5.5
EAR_X0, EAR_X1 = 26.0, 39.0
LOCK_X = 32.5
TAB_T = 3.0
# M3x8 button: length is under the head. Tip stays above the mating face.
LOCK_SHANK = 8.0


def box(cx, cy, zc, dx, dy, dz):
    """Box centered on the point."""
    return cq.Workplane("XY").box(dx, dy, dz).translate((cx, cy, zc))


def cyl_z(x, y, z0, r, h):
    """Cylinder along +Z from z0."""
    return cq.Workplane("XY").circle(r).extrude(h).translate((x, y, z0))


def ellipse_extrude(rx, ry, z0, h):
    """Elliptical puck from z0, height h."""
    return cq.Workplane("XY").workplane(offset=z0).ellipse(rx, ry).extrude(h)


def loft_ellipses(sections, ruled=False):
    """Loft (z, rx, ry) sections. Ruled keeps the wall from bowing out."""
    z0, rx, ry = sections[0]
    wp = cq.Workplane("XY").workplane(offset=z0).ellipse(rx, ry)
    prev = z0
    for z, rx, ry in sections[1:]:
        wp = wp.workplane(offset=z - prev).ellipse(rx, ry)
        prev = z
    return wp.loft(ruled=ruled)


def union_all(shapes, tol=None):
    """Fuse solids into one. tol lets a near-touching joint merge."""
    out = shapes[0]
    for shape in shapes[1:]:
        out = out.union(shape) if tol is None else out.union(shape, tol=tol)
    return out


def gap(a, b):
    """Minimum distance between two solids, mm."""
    meas = BRepExtrema_DistShapeShape(a.val().wrapped, b.val().wrapped)
    meas.Perform()
    return float(meas.Value())


def vol(shape):
    """Volume in mm3."""
    return float(shape.val().Volume())


def solid_count(shape):
    """How many solids are in this part. A print must be one."""
    exp = TopExp_Explorer(shape.val().wrapped, TopAbs_SOLID)
    count = 0
    while exp.More():
        count += 1
        exp.Next()
    return count


def span_along(shape, center, size, axis):
    """Thickness along one axis where a wall crosses the sample box.

    The box has to stick out past the wall on that axis. The other two
    sides of the box have to sit inside the wall.
    """
    bit = shape.intersect(box(center[0], center[1], center[2], size[0], size[1], size[2]))
    if vol(bit) < 0.05:
        return None
    bb = bit.val().BoundingBox()
    dims = (bb.xmax - bb.xmin, bb.ymax - bb.ymin, bb.zmax - bb.zmin)
    return dims[axis]


def unit(v):
    """Vector scaled to length 1."""
    n = math.sqrt(v[0] ** 2 + v[1] ** 2 + v[2] ** 2)
    return (v[0] / n, v[1] / n, v[2] / n)


def orient_z_to(shape, direction):
    """Rotate a solid so its +Z lies along direction."""
    d = unit(direction)
    axis = (-d[1], d[0], 0.0)
    ang = math.degrees(math.acos(max(-1.0, min(1.0, d[2]))))
    if math.hypot(axis[0], axis[1]) < 1e-9:
        if d[2] < 0:
            return shape.rotate((0, 0, 0), (1, 0, 0), 180)
        return shape
    return shape.rotate((0, 0, 0), axis, ang)


def finger_centers():
    """Knuckle centers for the four fingers, ulnar to radial, spanning 82 mm."""
    order = ("little", "ring", "middle", "index")
    x = -BREADTH / 2
    centers = {}
    for i, name in enumerate(order):
        w = FINGER_W[name]
        centers[name] = x + w / 2
        x += w
        if i < len(order) - 1:
            x += FINGER_GAP
    return centers


def finger_sections(visible, rx, ry, inner, slim=False):
    """Stations for one finger. The knuckle is z = 0. Negative z is buried in the palm."""
    if not inner:
        rows = (
            (-OVERLAP, rx, ry),
            (0.0, rx, ry),
            (0.42 * visible, rx * 0.90, ry * 0.90),
            (0.72 * visible, rx * 0.78, ry * 0.78),
            (visible, rx * TIP_K, ry * TIP_K),
        )
        return rows
    # the thumb stays a thin tube; a fat thumb tunnel breaks the palm surface
    root_x = rx - SHELL if slim else rx + 2.0
    root_y = ry - SHELL if slim else ry + 1.5
    mid_x = rx - SHELL if slim else rx + 0.8
    mid_y = ry - SHELL if slim else ry + 0.5
    bury = -18.0 if slim else -40.0
    return (
        (bury, max(root_x, 1.6), max(root_y, 1.4)),
        (-16.0, max(mid_x, 1.6), max(mid_y, 1.4)),
        (0.0, max(rx - SHELL, 1.8), max(ry - SHELL, 1.6)),
        (0.42 * visible, max(rx * 0.90 - SHELL, 1.6), max(ry * 0.90 - SHELL, 1.5)),
        (0.72 * visible, max(rx * 0.78 - SHELL, 1.5), max(ry * 0.78 - SHELL, 1.4)),
        (visible + 0.6, max(rx * TIP_K - SHELL, 1.4), max(ry * TIP_K - SHELL, 1.3)),
    )


def make_finger(name, origin, direction, inner, slim=False):
    """One tapered finger tube. inner=True is the void, not the print."""
    visible = FINGER_L[name]
    rx = FINGER_W[name] / 2
    ry = rx * DEPTH_K
    blank = loft_ellipses(finger_sections(visible, rx, ry, inner, slim), ruled=True)
    return orient_z_to(blank, direction).translate(origin)


def yaw_dir(deg):
    """Finger direction in the breadth plane, deg toward the thumb."""
    a = math.radians(deg)
    return (math.sin(a), 0.0, math.cos(a))


def thumb_dir():
    """Thumb direction, THUMB_TILT deg off distal, partly toward the palm."""
    tilt = math.radians(THUMB_TILT)
    palm = math.radians(THUMB_PALM)
    return (
        math.sin(tilt) * math.cos(palm),
        math.sin(tilt) * math.sin(palm),
        math.cos(tilt),
    )


def screw_xy(angle_deg):
    """Hole center on the mating face. Local X is outboard, local Y is forward."""
    du, dy = arm.polar(PCD, angle_deg)
    return dy, du


def csk_void(x, y):
    """Clearance hole plus a countersink opening on the distal face."""
    hole = cyl_z(x, y, -1.0, M3_CLEAR / 2, FLANGE_T + 2.0)
    cone = (
        cq.Workplane("XY")
        .workplane(offset=FLANGE_T - CSK_H)
        .center(x, y)
        .circle(M3_CLEAR / 2)
        .workplane(offset=CSK_H)
        .circle(CSK_D / 2)
        .loft()
    )
    return hole.union(cone)


def nut_hex(diameter, z0, h, x, y):
    """Hexagon extruded along Z. diameter follows CadQuery's polygon size."""
    return (
        cq.Workplane("XY")
        .workplane(offset=z0)
        .center(x, y)
        .polygon(6, diameter)
        .extrude(h)
    )


def ear_box(sign):
    """Lug on one side of the flange. sign is +1 for the thumb side."""
    cx = sign * (EAR_X0 + EAR_X1) / 2
    return box(cx, 0, FLANGE_T / 2, EAR_X1 - EAR_X0, EAR_Y * 2, FLANGE_T)


def nut_pocket(sign):
    """Hex pocket open on the distal face. The shell tab covers it after the nut is in."""
    x = sign * LOCK_X
    across = NUT_AF / math.cos(math.radians(30)) + 0.55
    return nut_hex(across, 1.7, FLANGE_T - 1.7 + 0.4, x, 0)


def make_plate():
    """Wrist plate: flange, collar plug, two lugs. Proximal face is z = 0."""
    flange = ellipse_extrude(WRIST_RX, WRIST_RY, 0, FLANGE_T)
    # four pads, not a full ring: a ring would sit on top of the countersinks
    c_rx = WRIST_RX - SHELL - CLEAR
    c_ry = WRIST_RY - SHELL - CLEAR
    ring = ellipse_extrude(c_rx, c_ry, COLLAR_Z0 - 1.0, COLLAR_Z1 - (COLLAR_Z0 - 1.0))
    ring = ring.cut(ellipse_extrude(c_rx - COLLAR_WALL, c_ry - COLLAR_WALL, COLLAR_Z0 - 1.2, COLLAR_Z1 - COLLAR_Z0 + 1.6))
    pad_boxes = []
    for sign in (1, -1):
        pad_boxes.append(box(0, sign * c_ry, (COLLAR_Z0 + COLLAR_Z1) / 2, 14, COLLAR_WALL + 2, COLLAR_Z1 - COLLAR_Z0 + 2))
        pad_boxes.append(box(sign * c_rx, 0, (COLLAR_Z0 + COLLAR_Z1) / 2, COLLAR_WALL + 2, 14, COLLAR_Z1 - COLLAR_Z0 + 2))
    pads = [ring.intersect(pad) for pad in pad_boxes]
    # fuse one at a time; a compound of pads does not all join the flange
    plate = flange
    collar = pads[0]
    for pad in pads:
        plate = plate.union(pad, tol=0.3)
    for pad in pads[1:]:
        collar = collar.union(pad, tol=0.3)
    plate = plate.union(ear_box(1), tol=0.3).union(ear_box(-1), tol=0.3)
    voids = [cyl_z(0, 0, -0.4, SPIGOT_R + CLEAR, SPIGOT_H + CLEAR + 0.4)]
    angles = [arm.WRIST["ang0"] + 90.0 * i for i in range(arm.WRIST["n"])]
    for ang in angles:
        voids.append(csk_void(*screw_xy(ang)))
    voids.append(nut_pocket(1))
    voids.append(nut_pocket(-1))
    for sign in (1, -1):
        voids.append(cyl_z(sign * LOCK_X, 0, -0.4, M3_CLEAR / 2, FLANGE_T + 0.8))
    return plate.cut(union_all(voids)), collar, flange


def make_shell(outers, inners):
    """Hollow hand. The cuff pocket is a straight ellipse, the mate for the collar."""
    cuff = ellipse_extrude(WRIST_RX, WRIST_RY, FLANGE_T, CUFF_TOP - FLANGE_T)
    # ball in the thumb crotch so the tube meets the palm without a gap
    crotch = cq.Workplane("XY").sphere(11).translate((23.0, 5.0, 64.0))
    tabs = []
    for sign in (1, -1):
        cx = sign * (EAR_X0 + EAR_X1) / 2
        tabs.append(box(cx, 0, FLANGE_T + TAB_T / 2, EAR_X1 - EAR_X0, EAR_Y * 2 + 1.0, TAB_T))
    outer = union_all([cuff, loft_ellipses(PALM_OUTER, ruled=True), crotch] + outers + tabs)
    inner = union_all([loft_ellipses(PALM_VOID, ruled=True)] + inners)
    shell = outer.cut(inner)
    for sign in (1, -1):
        shell = shell.cut(cyl_z(sign * LOCK_X, 0, FLANGE_T - 0.2, M3_CLEAR / 2, TAB_T + 0.6))
    return shell


def make_fingers():
    """Outer finger solids and the voids inside them."""
    outers, inners = [], []
    centers = finger_centers()
    for name, yaw in YAW.items():
        origin = (centers[name], FINGER_Y, KNUCKLE_Z)
        direction = yaw_dir(yaw)
        outers.append(make_finger(name, origin, direction, False))
        inners.append(make_finger(name, origin, direction, True))
    # thumb base sits in the radial palm, tip opens away from the fingers
    origin = (28.0, 6.0, 70.0)
    direction = thumb_dir()
    outers.append(make_finger("thumb", origin, direction, False))
    inners.append(make_finger("thumb", origin, direction, True, slim=True))
    return outers, inners


def make_block():
    """Existing wrist block and spigot, for the fit check. Not printed."""
    y0, y1 = arm.Y_FI[1], arm.Y_FO[0]
    yc = (y0 + y1) / 2
    width = y1 - y0
    block = box(0, 0, -9.0, width, 40.0, 18.0)
    spigot = cyl_z(0, 0, -0.2, SPIGOT_R, SPIGOT_H + 0.2)
    angles = [arm.WRIST["ang0"] + 90.0 * i for i in range(arm.WRIST["n"])]
    holes = []
    for ang in angles:
        x, y = screw_xy(ang)
        holes.append(cyl_z(x, y, -6.7, 2.0, 6.9))
    return block.cut(union_all(holes)), spigot, yc


def csk_screw(x, y):
    """M3x12 countersunk screw. Length includes the head. Not printed."""
    tip = FLANGE_T - 12.0  # overall 12, head at the distal face
    shank = cyl_z(x, y, tip, 1.5, 12.0 - CSK_H)
    head = (
        cq.Workplane("XY")
        .workplane(offset=FLANGE_T - CSK_H)
        .center(x, y)
        .circle(1.55)
        .workplane(offset=CSK_H)
        .circle(CSK_D / 2 - 0.15)
        .loft()
    )
    return shank.union(head)


def lock_screw(sign):
    """M3x8 button screw through one tab. Length is under the head."""
    x = sign * LOCK_X
    z_top = FLANGE_T + TAB_T
    shank = cyl_z(x, 0, z_top - LOCK_SHANK, 1.5, LOCK_SHANK)
    head = cyl_z(x, 0, z_top, 2.75, 1.6)
    return shank.union(head)


def lock_nut(sign):
    """M3 nut in one lug."""
    x = sign * LOCK_X
    nut = nut_hex(NUT_AF / math.cos(math.radians(30)), 1.8, NUT_T, x, 0)
    return nut.cut(cyl_z(x, 0, 1.4, 1.55, 3.2))


def on_bed(shape, flip=False):
    """Sit the part on z = 0. flip turns the plate so the collar points up."""
    if flip:
        shape = shape.rotate((0, 0, 0), (1, 0, 0), 180)
    bb = shape.val().BoundingBox()
    return shape.translate((-bb.xmin, -bb.ymin, -bb.zmin))


def face_area(shape, downward, z_min, allow):
    """Area of faces that lean past 45 deg. downward=True is an overhang.

    A face only counts when the space just outside it is empty. An internal
    seam left by a fuse is not an overhang.
    """
    from OCP.BRepClass3d import BRepClass3d_SolidClassifier
    from OCP.gp import gp_Pnt
    from OCP.TopAbs import TopAbs_OUT

    verts, tris = shape.val().tessellate(0.45, 0.45)
    pts = [v.toTuple() for v in verts]
    probe = BRepClass3d_SolidClassifier(shape.val().wrapped) if downward else None
    area = 0.0
    worst = None
    limit = -0.7071 if downward else 0.7071
    for i, j, k in tris:
        a, b, c = pts[i], pts[j], pts[k]
        ux, uy, uz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
        vx, vy, vz = c[0] - a[0], c[1] - a[1], c[2] - a[2]
        nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
        nlen = math.sqrt(nx * nx + ny * ny + nz * nz)
        if nlen < 1e-9:
            continue
        tri_area = 0.5 * nlen
        nx, ny, nz = nx / nlen, ny / nlen, nz / nlen
        cx = (a[0] + b[0] + c[0]) / 3
        cy = (a[1] + b[1] + c[1]) / 3
        cz = (a[2] + b[2] + c[2]) / 3
        if downward:
            hit = nz < limit and cz > z_min and not allow(cx, cy, cz)
        else:
            hit = nz > limit and cz > z_min
        if not hit:
            continue
        if probe is not None:
            probe.Perform(gp_Pnt(cx + nx * 0.25, cy + ny * 0.25, cz + nz * 0.25), 1e-6)
            if probe.State() != TopAbs_OUT:
                continue
        area += tri_area
        if worst is None or (downward and nz < worst[0]) or (not downward and nz > worst[0]):
            worst = (nz, (cx, cy, cz))
    return area, worst


def allow_plate(x, y, z):
    """Pocket roof and nut slots are bridges, not failed overhangs."""
    if x * x + y * y < 12.5 ** 2 and z < 3.4:
        return True
    if abs(abs(x) - LOCK_X) < 10 and abs(y) < 7 and 1.2 < z < 5.0:
        return True
    return False


def write_3mf(parts, path):
    """One 3MF of the print bodies, spaced so they do not touch."""
    wrapper = lib3mf.get_wrapper()
    model = wrapper.CreateModel()
    model.SetUnit(lib3mf.ModelUnit.MilliMeter)
    cursor = 0.0
    for name, shape in parts:
        bb = shape.val().BoundingBox()
        moved = shape.translate((cursor, 0, 0))
        verts, tris = moved.val().tessellate(0.08, 0.4)
        obj = model.AddMeshObject()
        obj.SetName(name)
        obj.SetGeometry(
            [lib3mf.Position((ctypes.c_float * 3)(*p.toTuple())) for p in verts],
            [lib3mf.Triangle((ctypes.c_uint32 * 3)(*tri)) for tri in tris],
        )
        model.AddBuildItem(obj, wrapper.GetIdentityTransform())
        cursor += (bb.xmax - bb.xmin) + 8.0
    model.QueryWriter("3mf").WriteToFile(path)


def export_stl(shape, name):
    """One STL in the print orientation."""
    os.makedirs(STL_DIR, exist_ok=True)
    path = os.path.join(STL_DIR, name + ".stl")
    cq.exporters.export(shape, path)
    return path


def draw_preview(shell, plate, path):
    """Cutaway of the shell so the hollow and the five fingers are visible."""
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d.art3d import Poly3DCollection

    cut = shell.intersect(box(0, -8, 100, 220, 70, 230))

    def faces(shape, color, alpha):
        verts, tris = shape.val().tessellate(0.7, 0.6)
        pts = [v.toTuple() for v in verts]
        tri = [[pts[i] for i in t] for t in tris]
        return tri, color, alpha

    fig = plt.figure(figsize=(9, 7), facecolor="white")
    ax = fig.add_subplot(111, projection="3d")
    for shape, color, alpha in (
        (plate, (0.75, 0.62, 0.45), 1.0),
        (cut, (0.86, 0.55, 0.32), 1.0),
    ):
        tri, rgb, alf = faces(shape, color, alpha)
        ax.add_collection3d(Poly3DCollection(tri, facecolor=rgb, edgecolor="none", alpha=alf))
    ax.view_init(elev=16, azim=-58)
    ax.set_xlim(-70, 80)
    ax.set_ylim(-30, 40)
    ax.set_zlim(0, 180)
    ax.set_box_aspect((150, 70, 180))
    ax.set_axis_off()
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    plt.close(fig)


def want(problems, name, value, lo, hi, unit="mm"):
    """Record a measurement and fail it when it leaves the band."""
    if value is None:
        problems.append(f"{name}: missing, wanted {lo:.2f} to {hi:.2f}")
        return f"{name}: missing"
    line = f"{name}: {value:.2f} {unit}"
    if not (lo <= value <= hi):
        problems.append(f"{name}: {value:.2f}, wanted {lo:.2f} to {hi:.2f}")
    return line


def main():
    """Build the hand, measure it, and write files only when the checks pass."""
    problems = []
    centers = finger_centers()
    span = (centers["index"] + FINGER_W["index"] / 2) - (centers["little"] - FINGER_W["little"] / 2)
    if abs(span - BREADTH) > 0.2:
        problems.append(f"finger span: {span:.2f}, wanted {BREADTH:.2f}")

    outers, inners = make_fingers()
    plate, collar, flange = make_plate()
    shell = make_shell(outers, inners)
    block, spigot, yc = make_block()

    # screws and nuts are bought, kept for the clash check
    angles = [arm.WRIST["ang0"] + 90.0 * i for i in range(arm.WRIST["n"])]
    screws = [csk_screw(*screw_xy(a)) for a in angles]
    locks = [lock_screw(1), lock_screw(-1)]
    nuts = [lock_nut(1), lock_nut(-1)]

    report = [
        "motion: the wrist plate bolts to the forearm wrist block, the hollow shell sits on the plate collar, and the hand does not move",
        f"hand length target {HAND_L:.1f} mm from the mating face to the middle fingertip (arm L_HAND)",
        f"knuckle plane z {KNUCKLE_Z:.1f} mm, palm/hand {KNUCKLE_Z / HAND_L:.3f} (Greiner band 0.556 to 0.573)",
        "material PETG, showcase shell, no load through the fingers",
        "bed: plate proximal face down, collar up; shell wrist rim and tabs down, fingers up",
        f"depth/breadth {DEPTH_K:.2f} is an assumption",
    ]

    # seats and clearances
    report.append(want(problems, "plate on wrist block", gap(flange, block), 0.0, 0.20))
    buried = vol(flange.intersect(block))
    report.append(f"plate inside block: {buried:.1f} mm3")
    if buried > 8:
        problems.append(f"plate inside block: {buried:.1f}, wanted 0 to 8")
    report.append(want(problems, "spigot to pocket", gap(spigot, plate), 0.22, 0.40))
    report.append(want(problems, "collar to shell", gap(collar, shell), 0.22, 0.42))
    report.append(want(problems, "shell on plate", gap(shell, flange), 0.0, 0.20))
    shell_in_plate = vol(shell.intersect(plate))
    report.append(f"shell inside plate: {shell_in_plate:.1f} mm3")
    if shell_in_plate > 8:
        problems.append(f"shell inside plate: {shell_in_plate:.1f}, wanted 0 to 8")

    # screws: 4 into the existing inserts, 2 locking the shell
    for i, screw in enumerate(screws):
        g = gap(screw, plate)
        report.append(want(problems, f"csk screw {i + 1} to plate", g, 0.0, 0.35))
        hit = vol(screw.intersect(shell))
        if hit > 5:
            problems.append(f"csk screw {i + 1} hits the shell: {hit:.1f} mm3")
        hit_b = vol(screw.intersect(block))
        report.append(f"csk screw {i + 1} in block: {hit_b:.1f} mm3")
        if hit_b > 5:
            problems.append(f"csk screw {i + 1} misses the insert bore: {hit_b:.1f} mm3 in block material")
    if len(screws) != 4:
        problems.append(f"wrist screws: {len(screws)}, wanted 4")
    report.append("screws: 4 x M3x12 countersunk, wrist plate to the existing wrist-block inserts")
    report.append("screws: 2 x M3x8 button, shell tabs to plate lugs, each with one M3 nut")
    for i, screw in enumerate(locks):
        report.append(want(problems, f"lock screw {i + 1} to shell", gap(screw, shell), 0.0, 0.35))
        report.append(want(problems, f"lock screw {i + 1} to plate", gap(screw, plate), 0.05, 0.40))
        hit_b = vol(screw.intersect(block))
        if hit_b > 1:
            problems.append(f"lock screw {i + 1} hits the wrist block: {hit_b:.1f} mm3")
    for i, nut in enumerate(nuts):
        report.append(want(problems, f"nut {i + 1} to plate", gap(nut, plate), 0.05, 0.45))

    # size of the hand, measured on the solids
    bb = shell.val().BoundingBox()
    length = bb.zmax  # mating face is z = 0 on the plate; the shell starts at the flange
    # middle fingertip is the max z of the whole assembly
    length = max(bb.zmax, plate.val().BoundingBox().zmax)
    report.append(want(problems, "middle fingertip", length, HAND_L - 1.5, HAND_L + 1.5))
    # y -5 to 3 keeps the finger centerline and leaves out the thumb
    slab = shell.intersect(box(0, -1.0, KNUCKLE_Z + 2.0, 160, 8, 5))
    sbb = slab.val().BoundingBox()
    breadth = sbb.xmax - sbb.xmin
    report.append(want(problems, "knuckle breadth", breadth, 78.0, 90.0))
    report.append(f"knuckle slab y {sbb.ymax - sbb.ymin:.2f} mm")

    wall_finger = span_along(shell, (centers["middle"] + 8.0, FINGER_Y, 130.0), (14, 1.0, 2.0), 0)
    wall_palm = span_along(shell, (0.0, 16.0, 22.0), (4, 10, 3), 1)
    report.append(want(problems, "shell wall at middle finger", wall_finger, 1.00, 1.50))
    report.append(want(problems, "shell wall at palm", wall_palm, 1.00, 1.55))
    flange_t = span_along(plate, (20.0, 0.0, 3.0), (4, 4, 16), 2)
    report.append(want(problems, "flange thickness", flange_t, 5.6, 6.4))
    collar_w = span_along(plate, (0, WRIST_RY - SHELL - CLEAR - COLLAR_WALL / 2, 10.0), (3, 12, 3), 1)
    report.append(want(problems, "collar wall", collar_w, LOAD_WALL, 4.0))
    # plastic between the spigot pocket and the nearest screw shaft, below the countersink
    sx, sy = screw_xy(45.0)
    pocket_pin = cyl_z(0, 0, 2.4, SPIGOT_R + CLEAR, 1.2)
    shaft_pin = cyl_z(sx, sy, 2.4, M3_CLEAR / 2, 1.2)
    report.append(want(problems, "wall between pocket and screw", gap(pocket_pin, shaft_pin), LOAD_WALL, 6.0))

    for name, shape in (("wrist plate", plate), ("hand shell", shell)):
        if vol(shape) < 10:
            problems.append(f"{name} has no volume")
        count = solid_count(shape)
        report.append(f"solids {name}: {count}")
        if count != 1:
            problems.append(f"{name} is {count} separate pieces")

    plate_bed = on_bed(plate, flip=False)
    shell_bed = on_bed(shell, flip=False)
    for name, shape in (("wrist plate", plate_bed), ("hand shell", shell_bed)):
        bb = shape.val().BoundingBox()
        sides = (bb.xmax - bb.xmin, bb.ymax - bb.ymin, bb.zmax - bb.zmin)
        report.append(f"bed {name}: {sides[0]:.0f} x {sides[1]:.0f} x {sides[2]:.0f} mm")
        if max(sides) > BED or min(bb.zmin, 0) < -0.05:
            problems.append(f"{name} bed: {max(sides):.0f} mm, limit {BED:.0f}")
        if abs(bb.zmin) > 0.05:
            problems.append(f"{name} not on z=0: {bb.zmin:.2f}")

    # plate already sits on z = 0, so the bridge test uses model coordinates
    over_p, worst_p = face_area(plate, True, 0.8, allow_plate)
    named, _ = face_area(plate, True, 0.8, lambda x, y, z: False)
    over_s, worst_s = face_area(shell_bed, True, 0.8, lambda x, y, z: False)
    bridge, _ = face_area(shell_bed, False, 8.0, lambda x, y, z: False)
    report.append(f"plate overhang area {over_p:.0f} mm2")
    report.append(f"spigot pocket bridge {named - over_p:.0f} mm2, span {2 * (SPIGOT_R + CLEAR):.1f} mm")
    report.append(f"shell overhang area {over_s:.0f} mm2")
    report.append(f"shell upward bridge area {bridge:.0f} mm2 (fingertip caps and webs)")
    if over_p > 20:
        problems.append(f"plate overhang: {over_p:.0f} mm2, wanted under 20, near {worst_p}")
    if over_s > 25:
        problems.append(f"shell overhang: {over_s:.0f} mm2, wanted under 25, near {worst_s}")
    report.append("fingertips are open so the hollow vents; those holes are not a bridge")

    plate_g = vol(plate) * PETG
    shell_g = vol(shell) * PETG
    solid_g = plate_g + shell_g
    # 3 perimeters eat most of the 6 mm plate. 5% infill fills the little core.
    # The 1.2 mm shell is perimeters only, so its printed mass is the solid mass.
    plate_print = plate_g * 0.55
    printed = plate_print + shell_g
    report.append(f"solid PETG plate {plate_g:.1f} g, shell {shell_g:.1f} g, total {solid_g:.1f} g")
    report.append(f"about 5 percent infill, printed guess {printed:.0f} g (shell counted solid)")
    report.append(f"dummy-hand load used by the arm {MASS_LIMIT:.0f} g")
    if solid_g > MASS_LIMIT:
        problems.append(f"solid mass: {solid_g:.1f}, wanted under {MASS_LIMIT:.0f}")
    report.append(f"showcase shell {SHELL:.2f} mm, decorative minimum {DECOR:.2f}, load wall {LOAD_WALL:.2f}")
    report.append("not run: finite element, a print on the P2S, a fit on the real spigot")

    # forearm plates end 6 mm before this face (v -228 vs v -234). Ears must stay distal of that.
    report.append(f"wrist center world Y {yc:.2f} mm (arm frame, for placing the step)")

    text = "\n".join(report + problems)
    with open(os.path.join(HERE, "checks.txt"), "w", encoding="utf-8") as handle:
        handle.write(text + "\n")
    print(text)
    draw_preview(shell, plate, os.path.join(HERE, "hand_preview.png"))
    if problems:
        raise SystemExit(1)

    assy = cq.Assembly(name="dummy_hand")
    assy.add(shell, name="hand_shell", color=cq.Color(0.86, 0.55, 0.32))
    assy.add(plate, name="wrist_plate", color=cq.Color(0.75, 0.62, 0.45))
    assy.add(block, name="wrist_block_existing", color=cq.Color(0.45, 0.48, 0.52))
    assy.add(spigot, name="spigot_existing", color=cq.Color(0.45, 0.48, 0.52))
    for i, screw in enumerate(screws):
        assy.add(screw, name=f"m3x12_csk_{i + 1}", color=cq.Color(0.55, 0.56, 0.58))
    for i, screw in enumerate(locks):
        assy.add(screw, name=f"m3x8_button_{i + 1}", color=cq.Color(0.55, 0.56, 0.58))
    for i, nut in enumerate(nuts):
        assy.add(nut, name=f"m3_nut_{i + 1}", color=cq.Color(0.35, 0.36, 0.38))
    step_path = os.path.join(HERE, "hand.step")
    assy.save(step_path)

    bed_parts = [("wrist_plate", plate_bed), ("hand_shell", shell_bed)]
    write_3mf(bed_parts, os.path.join(HERE, "hand.3mf"))
    zip_path = os.path.join(HERE, "hand_print.zip")
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, shape in bed_parts:
            archive.write(export_stl(shape, name), name + ".stl")
    print("wrote", step_path)


if __name__ == "__main__":
    main()
