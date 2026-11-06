"""Sleeves for the two K 20x24x10 cages.

The cage walks with the crank journal inside the disc bore. These sleeves
fill the gap the caliper showed. Z = 0 is the end that sits on the bed.

Bought cage, SKF K 20x24x10. The user measured the free cage: 20 mm inside,
23 mm outside. The catalog roller set is 20 mm under the rollers and 24 mm
over the rollers, width 10 mm.
https://www.skf.com/group/products/rolling-bearings/roller-bearings/needle-roller-bearings/needle-roller-and-cage-assemblies/productid-K%2020X24X10

Caliper on the parts in hand: shaft 19.00 mm, disc hole 24.00 mm.
The inner sleeve is PETG. One end sits on the bed. The wall is one
perimeter. It locates the cage. It is not a needle race.

Run: python gen_sleeves.py
"""

import math
import os
import struct

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from manifold3d import Manifold

HERE = os.path.dirname(os.path.abspath(__file__))

# user caliper, mm
SHAFT_D = 19.00
DISC_D = 24.00
CAGE_ID = 20.00
CAGE_OD_MEASURED = 23.00
# catalog roller set. the rollers, not the cage steel.
FW = 20.00
EW = 24.00
WIDTH = 10.00
PETG = 1.27
# one perimeter on a 0.4 mm nozzle is about 0.45 mm
# https://help.prusa3d.com/article/layers-and-perimeters_1748
PERIMETER = 0.45
SEGS = 256


def cyl(r, z0, z1):
    """Cylinder of radius r from z0 to z1."""
    return Manifold.cylinder(z1 - z0, r, r, SEGS).translate((0, 0, z0))


def sleeve():
    """Inner sleeve. Bore fits the 19 mm shaft. Outside is the 20 mm roller bore."""
    return cyl(FW / 2, 0, WIDTH) - cyl(SHAFT_D / 2, -0.2, WIDTH + 0.2)


def radii(solid, z):
    """Min and max radius of the slice at height z."""
    rs = [math.hypot(x, y) for poly in solid.slice(z).to_polygons() for x, y in poly]
    return min(rs), max(rs)


def write_stl(solid, path):
    """Binary STL of one sleeve, bed end at z = 0."""
    mesh = solid.to_mesh()
    v = mesh.vert_properties
    t = mesh.tri_verts
    with open(path, "wb") as f:
        f.write(b"\0" * 80)
        f.write(struct.pack("<I", len(t)))
        for tri in t:
            p = [tuple(float(x) for x in v[i][:3]) for i in tri]
            ax = [p[1][k] - p[0][k] for k in range(3)]
            bx = [p[2][k] - p[0][k] for k in range(3)]
            n = (
                ax[1] * bx[2] - ax[2] * bx[1],
                ax[2] * bx[0] - ax[0] * bx[2],
                ax[0] * bx[1] - ax[1] * bx[0],
            )
            ln = math.sqrt(sum(c * c for c in n)) or 1.0
            f.write(struct.pack("<12fH", *(c / ln for c in n), *p[0], *p[1], *p[2], 0))


def main():
    """Measure the sleeve and write two STL files, one for each cage."""
    part = sleeve()
    r_in, _ = radii(part, 1.0)
    _, r_out = radii(part, WIDTH / 2)
    # the bore slice also carries the outside edge, so split by radius
    rs = [math.hypot(x, y) for poly in part.slice(WIDTH / 2).to_polygons() for x, y in poly]
    bore = min(rs)
    outside = max(rs)
    wall = outside - bore
    problems = []
    report = [
        "motion: the sleeve sits on the crank journal and gives the K 20x24x10 rollers a 20 mm bore",
        f"shaft caliper {SHAFT_D:.2f} mm, cage inner {CAGE_ID:.2f} mm, catalog under rollers {FW:.2f} mm",
        f"disc hole caliper {DISC_D:.2f} mm, cage measured outside {CAGE_OD_MEASURED:.2f} mm, catalog over rollers {EW:.2f} mm",
        f"inner sleeve bore {2 * bore:.3f} mm, outside {2 * outside:.3f} mm, wall {wall:.3f} mm, width {WIDTH:.2f} mm",
        f"diametral gap filled, inner {CAGE_ID - SHAFT_D:.2f} mm",
        f"outer gap the caliper sees {DISC_D - CAGE_OD_MEASURED:.2f} mm. catalog roller outside is {EW:.2f} mm, same as the disc hole, so no outer sleeve",
        f"wall {wall:.2f} mm, one perimeter is {PERIMETER:.2f} mm. fit sleeve, not a load wall",
        f"solid PETG {part.volume() / 1000 * PETG:.2f} g each, two sleeves {2 * part.volume() / 1000 * PETG:.2f} g",
    ]
    if abs(2 * bore - SHAFT_D) > 0.02:
        problems.append(f"bore: {2 * bore:.3f}, wanted {SHAFT_D:.2f} to {SHAFT_D:.2f}")
    if abs(2 * outside - FW) > 0.02:
        problems.append(f"outside: {2 * outside:.3f}, wanted {FW:.2f} to {FW:.2f}")
    if abs(wall - (FW - SHAFT_D) / 2) > 0.02:
        problems.append(f"wall: {wall:.3f}, wanted {(FW - SHAFT_D) / 2:.2f} to {(FW - SHAFT_D) / 2:.2f}")
    text = "\n".join(report + problems)
    with open(os.path.join(HERE, "checks.txt"), "w", encoding="utf-8") as f:
        f.write(text + "\n")
    print(text)
    fig, ax = plt.subplots(figsize=(4, 4))
    for poly in part.rotate((90, 0, 0)).slice(0).to_polygons():
        ax.fill([p[0] for p in poly], [-p[1] for p in poly], facecolor="#c4a574", edgecolor="black", lw=0.4)
    ax.set_aspect("equal")
    ax.set_title("inner sleeve, 19.00 x 20.00 x 10")
    ax.set_xlabel("x mm")
    ax.set_ylabel("z mm")
    fig.tight_layout()
    fig.savefig(os.path.join(HERE, "sleeve_section.png"), dpi=120)
    plt.close(fig)
    if problems:
        raise SystemExit(1)
    for name in ("inner_sleeve_A.stl", "inner_sleeve_B.stl"):
        write_stl(part, os.path.join(HERE, name))
        print("wrote", name)


if __name__ == "__main__":
    main()
