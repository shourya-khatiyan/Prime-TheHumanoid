"""Light cover for the wooden stand that is already built.

The wood plate is 340 x 190 mm and the stick is 27 x 18 mm. These prints
do not hold the arm. They clip around that wood. Every piece fits a Bambu
P2S, and the print zip has one file for each physical piece.

Run:
  D:\\VAYN-CAD-env\\venv\\Scripts\\python.exe gen_stand_lite.py
"""

import math
import os
import zipfile

import cadquery as cq
import lib3mf
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
from mpl_toolkits.mplot3d.art3d import Poly3DCollection  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
BED = 246.0
RHO = 1.27  # g/cm3, PETG, solid bars with no infill

# wood that already exists
PLATE_X, PLATE_Y = 340.0, 190.0
STICK_X, STICK_Y, STICK_Z = 27.0, 18.0, 620.0
GAP = 0.8  # per side, so the painted plate still drops in

RIM = 8.0
RIM_H = 8.0
BAR = 2.6
INNER_X = PLATE_X + 2 * GAP
INNER_Y = PLATE_Y + 2 * GAP
OUTER_X = INNER_X + 2 * RIM
OUTER_Y = INNER_Y + 2 * RIM
MID = OUTER_X / 2
TONGUE = 12.0

SEG_L = 200.0
SEG_N = 3
WALL = 2.6
PIN_D = 3.0
PIN_HOLE = 3.6

BLUE = "#3F6FB5"
WOOD = "#C4A574"


def box(sx, sy, sz, cx, cy, cz):
    """Centered box."""
    return cq.Workplane("XY").box(sx, sy, sz).val().translate(cq.Vector(cx, cy, cz))


def fuse(parts):
    """Join solids."""
    acc = parts[0]
    for part in parts[1:]:
        acc = acc.fuse(part)
    return acc


def drill(shape, diameter, x, y, z):
    """Vertical hole centered on the point."""
    tool = cq.Solid.makeCylinder(diameter / 2, 40, cq.Vector(x, y, z - 20), cq.Vector(0, 0, 1))
    return shape.cut(tool)


def bar_xy(x0, y0, x1, y1, z=BAR / 2, thick=BAR):
    """Flat bar in the plan, ends at the two points."""
    dx, dy = x1 - x0, y1 - y0
    span = (dx * dx + dy * dy) ** 0.5
    angle = math.degrees(math.atan2(dy, dx))
    bar = cq.Workplane("XY").box(span, thick, thick).val()
    bar = bar.rotate((0, 0, 0), (0, 0, 1), angle)
    return bar.translate(cq.Vector((x0 + x1) / 2, (y0 + y1) / 2, z))


def bar_xz(x0, z0, x1, z1, y, thick=BAR):
    """Bar on a vertical face."""
    dx, dz = x1 - x0, z1 - z0
    span = (dx * dx + dz * dz) ** 0.5
    angle = math.degrees(math.atan2(dz, dx))
    bar = cq.Workplane("XY").box(span, thick, thick).val()
    bar = bar.rotate((0, 0, 0), (0, 1, 0), -angle)
    return bar.translate(cq.Vector((x0 + x1) / 2, y, (z0 + z1) / 2))


def vol(shape):
    """Volume in mm3."""
    try:
        solids = shape.Solids()
    except Exception:
        return 0.0
    return sum(item.Volume() for item in solids)


def size_of(shape):
    """Overall size."""
    bb = shape.BoundingBox()
    return (bb.xlen, bb.ylen, bb.zlen)


def rim_rect(x0, x1, y0, y1):
    """Four sides of a frame between the two corners. Open in the middle."""
    return [
        box(x1 - x0, RIM, RIM_H, (x0 + x1) / 2, y0 + RIM / 2, RIM_H / 2),
        box(x1 - x0, RIM, RIM_H, (x0 + x1) / 2, y1 - RIM / 2, RIM_H / 2),
        box(RIM, y1 - y0 - 2 * RIM, RIM_H, x0 + RIM / 2, (y0 + y1) / 2, RIM_H / 2),
        box(RIM, y1 - y0 - 2 * RIM, RIM_H, x1 - RIM / 2, (y0 + y1) / 2, RIM_H / 2),
    ]


def base_a():
    """Left half of the base frame. The tongue sticks out past the middle."""
    parts = rim_rect(0, MID, 0, OUTER_Y)
    # triangles under the plate, ends buried in the rim
    parts.append(bar_xy(RIM, RIM, MID - 4, OUTER_Y / 2))
    parts.append(bar_xy(RIM, OUTER_Y - RIM, MID - 4, OUTER_Y / 2))
    parts.append(bar_xy(RIM, OUTER_Y / 2, MID - 4, RIM))
    cy = OUTER_Y / 2
    parts.append(box(TONGUE, 36, 2.2, MID + TONGUE / 2, cy, 1.1))
    shape = fuse(parts)
    # screws down into the existing wood, one at each left corner
    for x, y in ((14, 14), (14, OUTER_Y - 14)):
        shape = drill(shape, 4.5, x, y, RIM_H / 2)
    for y in (cy - 10, cy + 10):
        shape = drill(shape, 3.4, MID + 6, y, 1.1)
    return shape


def base_b():
    """Right half. A slot takes the tongue from the left half."""
    parts = rim_rect(MID + TONGUE, OUTER_X, 0, OUTER_Y)
    parts.append(bar_xy(MID + TONGUE + 4, RIM, OUTER_X - RIM, OUTER_Y / 2))
    parts.append(bar_xy(MID + TONGUE + 4, OUTER_Y - RIM, OUTER_X - RIM, OUTER_Y / 2))
    parts.append(bar_xy(MID + TONGUE + 4, OUTER_Y / 2, OUTER_X - RIM, OUTER_Y - RIM))
    cy = OUTER_Y / 2
    # block around the slot, then the slot itself
    parts.append(box(TONGUE, 48, 5, MID + TONGUE / 2, cy, 2.5))
    shape = fuse(parts)
    shape = shape.cut(box(TONGUE + 0.8, 36 + 0.8, 2.8, MID + TONGUE / 2, cy, 1.2))
    for x, y in ((OUTER_X - 14, 14), (OUTER_X - 14, OUTER_Y - 14)):
        shape = drill(shape, 4.5, x, y, RIM_H / 2)
    for y in (cy - 10, cy + 10):
        shape = drill(shape, 3.4, MID + 6, y, 1.1)
    return shape


def stick_half(pins):
    """Open cage for one side of the stick. pins True adds the two locating pins."""
    hy = STICK_Y / 2 + 0.4
    hx = STICK_X / 2 + 0.4
    y_bar = hy + BAR / 2
    x_bar = hx + BAR / 2
    parts = [
        box(BAR, BAR, SEG_L, -x_bar, y_bar, SEG_L / 2),
        box(BAR, BAR, SEG_L, x_bar, y_bar, SEG_L / 2),
    ]
    # three clips hold the stick. they stop at the split so the halves do not collide
    clip_h = hy + BAR - 0.3
    for zc in (8.0, SEG_L / 2, SEG_L - 8):
        parts.append(box(2 * x_bar + BAR, BAR, 8, 0, y_bar, zc))
        parts.append(box(BAR, clip_h, 8, -x_bar, 0.3 + clip_h / 2, zc))
        parts.append(box(BAR, clip_h, 8, x_bar, 0.3 + clip_h / 2, zc))
    parts.append(bar_xz(-x_bar, 20, x_bar, SEG_L / 2, y_bar))
    parts.append(bar_xz(x_bar, 20, -x_bar, SEG_L / 2, y_bar))
    parts.append(bar_xz(-x_bar, SEG_L - 20, x_bar, SEG_L / 2, y_bar))
    parts.append(bar_xz(x_bar, SEG_L - 20, -x_bar, SEG_L / 2, y_bar))
    if pins:
        for z in (SEG_L / 2 - 30, SEG_L / 2 + 30):
            parts.append(box(PIN_D, 4, PIN_D, 0, -1.7, z))
    shape = fuse(parts)
    for z in (36.0, SEG_L - 36):
        shape = fuse([shape, box(10, 5, 8, x_bar + 4, y_bar, z)])
        shape = shape.cut(box(3.4, 8, 3.4, x_bar + 4, y_bar, z))
    return shape


def grams(shape):
    """Filament if the bars are printed solid."""
    return vol(shape) / 1000.0 * RHO


def assert_bed(name, shape, lines):
    """Refuse a part the P2S cannot print."""
    dims = size_of(shape)
    ok = max(dims) <= BED
    lines.append(f"{'ok' if ok else 'FAIL'}  {name}: {dims[0]:.0f} x {dims[1]:.0f} x {dims[2]:.0f} mm, {grams(shape):.0f} g")
    if not ok:
        raise SystemExit(lines[-1])
    return dims


def lay_down(shape):
    """Put the long axis on the bed."""
    return shape.rotate((0, 0, 0), (1, 0, 0), 90)


def write_3mf(items, path):
    """One named mesh per piece."""
    wrapper = lib3mf.get_wrapper()
    model = wrapper.CreateModel()
    model.SetUnit(lib3mf.ModelUnit.MilliMeter)
    for name, shape, _color in items:
        verts, tris = shape.tessellate(0.25)
        obj = model.AddMeshObject()
        obj.SetName(name)
        obj.SetGeometry(
            [lib3mf.Position((float(point.x), float(point.y), float(point.z))) for point in verts],
            [lib3mf.Triangle((int(tri[0]), int(tri[1]), int(tri[2]))) for tri in tris],
        )
        model.AddBuildItem(obj, wrapper.GetIdentityTransform())
    model.QueryWriter("3mf").WriteToFile(path)


def draw(items, path):
    """Four views."""
    fig = plt.figure(figsize=(11, 8), facecolor="white")
    views = [("front", 18, -70), ("side", 18, 10), ("top", 90, -90), ("back", 18, 110)]
    meshes = []
    for _name, shape, color in items:
        verts, tris = shape.tessellate(1.2)
        points = np.array([(v.x, v.y, v.z) for v in verts])
        faces = points[np.array(tris)]
        rgb = tuple(int(color[i:i + 2], 16) / 255 for i in (1, 3, 5))
        meshes.append((faces, rgb))
    for i, (title, elev, azim) in enumerate(views, start=1):
        ax = fig.add_subplot(2, 2, i, projection="3d")
        for faces, rgb in meshes:
            ax.add_collection3d(Poly3DCollection(faces, facecolor=rgb, edgecolor="none", alpha=0.95))
        ax.view_init(elev=elev, azim=azim)
        ax.set_xlim(-10, OUTER_X + 10)
        ax.set_ylim(-10, OUTER_Y + 10)
        ax.set_zlim(0, 700)
        ax.set_box_aspect((OUTER_X, OUTER_Y, 700))
        ax.set_title(title)
        ax.set_axis_off()
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)


def main():
    """Build the cover, check the bed and the mass, write the files."""
    os.makedirs(HERE, exist_ok=True)
    left = base_a()
    right = base_b()
    front = stick_half(True)
    back = stick_half(False).mirror("XZ")
    for z in (SEG_L / 2 - 30, SEG_L / 2 + 30):
        back = back.cut(box(PIN_HOLE, 6, PIN_HOLE, 0, -2.0, z))
    lines = ["stand-lite check", ""]
    assert_bed("base_a", left, lines)
    assert_bed("base_b", right, lines)
    posed_front = lay_down(front)
    posed_back = lay_down(back)
    assert_bed("stick_front", posed_front, lines)
    assert_bed("stick_back", posed_back, lines)
    clash = vol(left.intersect(right))
    lines.append(f"{'ok' if clash < 5 else 'FAIL'}  base halves overlap {clash:.1f} mm3")
    if clash >= 5:
        raise SystemExit(lines[-1])
    tongue = box(TONGUE, 36, 2.2, MID + TONGUE / 2, OUTER_Y / 2, 1.1)
    slot = box(TONGUE + 0.8, 36.8, 2.8, MID + TONGUE / 2, OUTER_Y / 2, 1.2)
    extra = vol(tongue.cut(slot))
    lines.append(f"{'ok' if extra < 5 else 'FAIL'}  tongue sticks out of the slot by {extra:.1f} mm3")
    if extra >= 5:
        raise SystemExit(lines[-1])

    one_seg = grams(front) + grams(back)
    total = grams(left) + grams(right) + one_seg * SEG_N
    lines.append("")
    lines.append(f"base {grams(left) + grams(right):.0f} g")
    lines.append(f"one stick segment {one_seg:.0f} g, three segments {one_seg * SEG_N:.0f} g")
    lines.append(f"all printed plastic {total:.0f} g")
    print("\n".join(lines))

    stl_dir = os.path.join(HERE, "stl")
    os.makedirs(stl_dir, exist_ok=True)
    copies = {
        "base_a": left,
        "base_b": right,
    }
    for index in range(1, SEG_N + 1):
        copies[f"stick_front_{index}"] = posed_front
        copies[f"stick_back_{index}"] = posed_back
    for name, shape in copies.items():
        cq.exporters.export(shape, os.path.join(stl_dir, f"{name}.stl"), tolerance=0.08, angularTolerance=0.2)
    zip_path = os.path.join(HERE, "stand_lite_print.zip")
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
        for name in copies:
            archive.write(os.path.join(stl_dir, f"{name}.stl"), f"{name}.stl")

    # assembly for the step and the 3mf. wood is shown, not printed.
    plate = box(PLATE_X, PLATE_Y, 12, OUTER_X / 2, OUTER_Y / 2, 3 + 6)
    stick = box(STICK_X, STICK_Y, STICK_Z, OUTER_X / 2, OUTER_Y / 2, STICK_Z / 2)
    view = [("base_a", left, BLUE), ("base_b", right, BLUE), ("plate", plate, WOOD), ("stick", stick, WOOD)]
    for index in range(SEG_N):
        z0 = 40 + index * SEG_L
        view.append((f"stick_front_{index + 1}", front.translate(cq.Vector(OUTER_X / 2, OUTER_Y / 2, z0)), BLUE))
        view.append((f"stick_back_{index + 1}", back.translate(cq.Vector(OUTER_X / 2, OUTER_Y / 2, z0)), BLUE))
    assy = cq.Assembly(name="stand-lite")
    for name, shape, color in view:
        assy.add(shape, name=name, color=cq.Color(color))
    assy.save(os.path.join(HERE, "stand_lite.step"))
    write_3mf(view, os.path.join(HERE, "stand_lite.3mf"))
    draw(view, os.path.join(HERE, "stand_lite_preview.png"))
    with open(os.path.join(HERE, "checks.txt"), "w", encoding="utf-8") as handle:
        handle.write("\n".join(lines) + "\n")
    print(f"print zip has {len(copies)} stl files")


if __name__ == "__main__":
    main()
