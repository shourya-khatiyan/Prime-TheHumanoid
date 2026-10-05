"""Build the VAYN shoulder actuator as exact OpenCascade (B-rep) solids.

Geometry comes from build() in gen_actuator_3mf.py (single source of truth).
This module swaps its mesh kernel (manifold3d) for an OpenCascade kernel
(CadQuery/OCP): true cylinders, cones, tori and involute B-spline tooth
flanks. It then runs the same checks and writes:
  - cad/rev<rev>/<rev>.step       : coloured, named assembly of exact solids (Fusion: File > Open)
  - cad/rev<rev>/<rev>_OCC.3mf    : named, coloured meshes tessellated from the B-rep
  - cad/rev<rev>/<rev>_OCC_STL_parts.zip : one STL per part, assembled position

Run with the D: environment:
  D:\\VAYN-CAD-env\\venv\\Scripts\\python.exe gen_actuator_occ.py
"""

import math
import os
import time
from types import SimpleNamespace

import cadquery as cq
import numpy as np
from OCP.BRepExtrema import BRepExtrema_DistShapeShape

import gen_actuator_3mf as g

TESS_TOL, TESS_ANG = 0.01, 0.15  # mm chord / rad angle used for 3mf + stl
AXES = ((1, 0, 0), (0, 1, 0), (0, 0, 1))


class Solid:
    """Exact B-rep solid with the small manifold3d-style api build() uses."""

    def __init__(self, shape, tube=None):
        """Wrap a cadquery shape; tube=(ro, ri, z0, z1) is kept for warp()."""
        self.s = shape
        self.tube = tube

    def __add__(self, o):
        return Solid(self.s.fuse(o.s).clean())

    def __sub__(self, o):
        return Solid(self.s.cut(o.s).clean())

    def __xor__(self, o):
        return Solid(self.s.intersect(o.s))

    def translate(self, v):
        """Move by vector v (x, y, z)."""
        return Solid(self.s.translate(cq.Vector(*v)))

    def rotate(self, r):
        """Rotate about the origin by (rx, ry, rz) degrees, x first then y then z."""
        s = self.s
        for axis, ang in zip(AXES, r):
            if ang:
                s = s.rotate((0, 0, 0), axis, ang)
        return Solid(s)

    def warp(self, fn):
        """Bend a tube along fn by lofting radial sections (tube-only warp)."""
        ro, ri, z0, z1 = self.tube
        n, quads = 12, []

        def section(k):
            # radial rectangle at angle k, corners moved by fn
            a = 2 * math.pi * k / (4 * n)
            c, s = math.cos(a), math.sin(a)
            pts = [cq.Vector(*fn((r * c, r * s, z))) for r, z in ((ri, z0), (ro, z0), (ro, z1), (ri, z1))]
            return cq.Wire.makePolygon(pts, close=True)

        for q in range(4):
            quads.append(cq.Solid.makeLoft([section(q * n + k) for k in range(n + 1)]))
        return Solid(quads[0].fuse(*quads[1:]).clean())

    def volume(self):
        """Solid volume in mm3."""
        return self.s.Volume()

    def bounding_box(self):
        """(xmin, ymin, zmin, xmax, ymax, zmax)."""
        b = self.s.BoundingBox()
        return (b.xmin, b.ymin, b.zmin, b.xmax, b.ymax, b.zmax)

    def is_empty(self):
        """True when the shape has no solid volume."""
        return self.s.isNull() or self.s.Volume() <= 0

    def status(self):
        """manifold3d-style status: .name == 'NoError' when the b-rep is valid."""
        return SimpleNamespace(name="NoError" if self.s.isValid() else "InvalidBRep")

    def min_gap(self, o, _search):
        """Exact minimum distance to another solid."""
        return BRepExtrema_DistShapeShape(self.s.wrapped, o.s.wrapped).Value()

    def to_mesh(self):
        """Tessellate into shared-vertex triangles (manifold3d Mesh-like)."""
        v, t = self.s.tessellate(TESS_TOL, TESS_ANG)
        v = np.array([p.toTuple() for p in v], dtype=np.float64)
        t = np.array(t, dtype=np.int64)
        # merge face-duplicated vertices so the mesh is one closed shell
        _, first, inv_idx = np.unique(np.round(v, 6), axis=0, return_index=True, return_inverse=True)
        t = inv_idx.reshape(-1)[t]
        t = t[(t[:, 0] != t[:, 1]) & (t[:, 1] != t[:, 2]) & (t[:, 0] != t[:, 2])]
        return SimpleNamespace(vert_properties=v[first], tri_verts=t)


class Kernel:
    """Static constructors matching the manifold3d calls inside build()."""

    @staticmethod
    def cylinder(h, r_low, r_high=-1.0, _segs=0):
        """Cylinder or cone from z = 0 to h on the z axis."""
        r_high = r_low if r_high < 0 else r_high
        if abs(r_high - r_low) < 1e-9:
            return Solid(cq.Solid.makeCylinder(r_low, h))
        return Solid(cq.Solid.makeCone(r_low, r_high, h))


# ---------------------------------------------------------------- primitives
def cyl(r, z0, z1, x=0.0, y=0.0):
    """Exact cylinder of radius r between z0 and z1 at (x, y)."""
    return Solid(cq.Solid.makeCylinder(r, z1 - z0, cq.Vector(x, y, z0)))


def tube(ro, ri, z0, z1):
    """Exact hollow cylinder; remembers its size for warp()."""
    s = cq.Solid.makeCylinder(ro, z1 - z0, cq.Vector(0, 0, z0)).cut(cq.Solid.makeCylinder(ri, z1 - z0 + 2, cq.Vector(0, 0, z0 - 1)))
    return Solid(s, (ro, ri, z0, z1))


def box(x0, x1, y0, y1, z0, z1):
    """Axis-aligned box from min/max corners."""
    return Solid(cq.Solid.makeBox(x1 - x0, y1 - y0, z1 - z0, cq.Vector(x0, y0, z0)))


def pattern(fn, angles):
    """Union of fn(angle) over all angles."""
    shapes = [fn(a).s for a in angles]
    return Solid(shapes[0].fuse(*shapes[1:]).clean() if len(shapes) > 1 else shapes[0])


# ---------------------------------------------------------------- gears
def tooth_wire(n, m, r_root, r_tip, half_angle_pitch):
    """Closed involute wire of n teeth: b-spline flanks, true tip/root arcs.

    same tooth maths as gen_actuator_3mf.tooth_outline (for a ring, pass the
    space outline). returns a cadquery wire in the xy plane.
    """
    rp = n * m / 2
    rb = rp * math.cos(g.PA)

    def theta(r):
        # half tooth angle at radius r
        a = math.acos(rb / max(r, rb))
        return max(half_angle_pitch + g.inv(g.PA) - g.inv(a), 0.002)

    def pt(r, a):
        return cq.Vector(r * math.cos(a), r * math.sin(a), 0)

    pitch = 2 * math.pi / n
    r0 = max(r_root, rb)
    t_root, t_tip = theta(r_root), theta(r_tip)
    radii = np.linspace(r0, r_tip, 9)
    edges = []
    for i in range(n):
        c = i * pitch
        if r_root < rb:
            edges.append(cq.Edge.makeLine(pt(r_root, c - t_root), pt(rb, c - t_root)))
        edges.append(cq.Edge.makeSpline([pt(r, c - theta(r)) for r in radii]))
        edges.append(cq.Edge.makeThreePointArc(pt(r_tip, c - t_tip), pt(r_tip, c), pt(r_tip, c + t_tip)))
        edges.append(cq.Edge.makeSpline([pt(r, c + theta(r)) for r in radii[::-1]]))
        if r_root < rb:
            edges.append(cq.Edge.makeLine(pt(rb, c + t_root), pt(r_root, c + t_root)))
        nxt = (i + 1) * pitch
        edges.append(cq.Edge.makeThreePointArc(pt(r_root, c + t_root), pt(r_root, c + pitch / 2), pt(r_root, nxt - t_root)))
    return cq.Wire.assembleEdges(edges)


def ext_gear(n, m, z0, z1, rot_deg=0.0):
    """Exact external spur gear (ISO 53 rack, x = 0, thinned for backlash)."""
    rp = n * m / 2
    half = (math.pi * m / 2 - g.BACKLASH_HALF) / (2 * rp)
    w = tooth_wire(n, m, rp - 1.25 * m, rp + m, half)
    s = cq.Solid.extrudeLinear(w, [], cq.Vector(0, 0, z1 - z0))
    return Solid(s).rotate((0, 0, rot_deg)).translate((0, 0, z0))


def ring_gear(n, m, r_od, z0, z1, rot_deg=0.0):
    """Exact internal ring gear of outer radius r_od (space widened for backlash)."""
    rp = n * m / 2
    half = (math.pi * m / 2 + g.BACKLASH_HALF) / (2 * rp)
    w = tooth_wire(n, m, rp - m, rp + 1.25 * m, half)
    cut = Solid(cq.Solid.extrudeLinear(w, [], cq.Vector(0, 0, z1 - z0 + 2))).rotate((0, 0, rot_deg))
    return cyl(r_od, z0, z1) - cut.translate((0, 0, z0 - 1))


def ball_bearing(d, D, B, z0, d1, D1, nballs, dball, seals=False):
    """Deep-groove ball bearing: rings with toroidal grooves, ball set, seals."""
    zc = z0 + B / 2
    rpitch = (d1 + D1) / 4
    groove = Solid(cq.Solid.makeTorus(rpitch, dball / 2 + 0.1, cq.Vector(0, 0, zc)))
    balls = [cq.Solid.makeSphere(dball / 2, cq.Vector(*g.polar(rpitch, a), zc), angleDegrees1=-90) for a in g.every(nballs)]
    parts = {"inner ring": tube(d1 / 2, d / 2, z0, z0 + B) - groove,
             "outer ring": tube(D / 2, D1 / 2, z0, z0 + B) - groove,
             "ball set": Solid(cq.Compound.makeCompound(balls))}
    if seals:
        parts["seal rear"] = tube(D1 / 2 - 0.15, d1 / 2 + 0.15, z0 + 0.3, z0 + 0.9)
        parts["seal front"] = tube(D1 / 2 - 0.15, d1 / 2 + 0.15, z0 + B - 0.9, z0 + B - 0.3)
    return parts


# ---------------------------------------------------------------- exports
def write_step(parts, path):
    """Write a named, coloured STEP assembly of the exact solids."""
    assy = cq.Assembly(name=f"VAYN_Shoulder_Actuator_Rev{g.REV}")
    for name, mat, solid in parts:
        r, gg, b = (int(g.MATERIALS[mat][0][i:i + 2], 16) / 255 for i in (1, 3, 5))
        assy.add(solid.s, name=name.replace("/", "-"), color=cq.Color(r, gg, b))
    assy.save(path, exportType="STEP")
    print(f"wrote {path} ({os.path.getsize(path) / 1e6:.1f} MB)")


def use_occ_kernel():
    """Point build() in gen_actuator_3mf at the OpenCascade primitives."""
    for name, fn in dict(cyl=cyl, tube=tube, box=box, pattern=pattern, ext_gear=ext_gear,
                         ring_gear=ring_gear, ball_bearing=ball_bearing, Manifold=Kernel).items():
        setattr(g, name, fn)


if __name__ == "__main__":
    t0 = time.time()
    use_occ_kernel()
    model = g.build()
    print(f"built {len(model)} exact solids in {time.time() - t0:.0f} s")
    g.check(model)
    base = g.OUT[:-4]
    write_step(model, base + ".step")
    g.write_3mf(model, base + "_OCC.3mf")
    g.write_stl_zip(model, base + "_OCC_STL_parts.zip")
    print(f"total {time.time() - t0:.0f} s")
