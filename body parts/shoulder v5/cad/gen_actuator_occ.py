"""Build the VAYN shoulder v5 actuator as exact OpenCascade solids.

Geometry comes from build() in gen_actuator_3mf.py. This swaps the mesh
kernel for CadQuery and writes actuator.step beside this script.

Run:
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

TESS_TOL, TESS_ANG = 0.01, 0.15
AXES = ((1, 0, 0), (0, 1, 0), (0, 0, 1))


class Solid:
    """Exact B-rep solid with the small manifold3d-style api build() uses."""

    def __init__(self, shape):
        """Wrap a cadquery shape."""
        self.s = shape

    def __add__(self, o):
        return Solid(self.s.fuse(o.s).clean())

    def __sub__(self, o):
        return Solid(self.s.cut(o.s).clean())

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
        dist = BRepExtrema_DistShapeShape(self.s.wrapped, o.s.wrapped)
        dist.Perform()
        return dist.Value()

    def to_mesh(self):
        """Tessellate into shared-vertex triangles."""
        v, t = self.s.tessellate(TESS_TOL, TESS_ANG)
        v = np.array([p.toTuple() for p in v], dtype=np.float64)
        t = np.array(t, dtype=np.int64)
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


def cyl(r, z0, z1, x=0.0, y=0.0):
    """Exact cylinder of radius r between z0 and z1 at (x, y)."""
    if z1 < z0:
        z0, z1 = z1, z0
    return Solid(cq.Solid.makeCylinder(r, z1 - z0, cq.Vector(x, y, z0)))


def tube(ro, ri, z0, z1):
    """Exact hollow cylinder."""
    if z1 < z0:
        z0, z1 = z1, z0
    outer = cq.Solid.makeCylinder(ro, z1 - z0, cq.Vector(0, 0, z0))
    inner = cq.Solid.makeCylinder(ri, z1 - z0 + 2, cq.Vector(0, 0, z0 - 1))
    return Solid(outer.cut(inner))


def box(x0, x1, y0, y1, z0, z1):
    """Axis-aligned box from min/max corners."""
    return Solid(cq.Solid.makeBox(x1 - x0, y1 - y0, z1 - z0, cq.Vector(x0, y0, z0)))


def pattern(fn, angles):
    """Union of fn(angle) over all angles."""
    shapes = [fn(a).s for a in angles]
    return Solid(shapes[0].fuse(*shapes[1:]).clean() if len(shapes) > 1 else shapes[0])


def extrude_polygon(pts, z0, z1):
    """Extrude a closed polygon into an exact solid from z0 to z1."""
    arr = np.asarray(pts, dtype=float)
    area = float(np.sum(arr[:, 0] * np.roll(arr[:, 1], -1) - arr[:, 1] * np.roll(arr[:, 0], -1)))
    if area < 0:
        arr = arr[::-1]
    wire = cq.Wire.makePolygon([cq.Vector(float(x), float(y), 0) for x, y in arr], close=True)
    solid = cq.Solid.extrudeLinear(wire, [], cq.Vector(0, 0, z1 - z0))
    return Solid(solid).translate((0, 0, z0))


def hex_prism(across_flats, z0, z1):
    """Regular hex prism. across_flats is the flat-to-flat width."""
    radius = across_flats / math.sqrt(3.0)
    pts = [cq.Vector(radius * math.cos(math.radians(60 * i + 30)),
                     radius * math.sin(math.radians(60 * i + 30)), 0) for i in range(6)]
    wire = cq.Wire.makePolygon(pts, close=True)
    solid = cq.Solid.extrudeLinear(wire, [], cq.Vector(0, 0, z1 - z0))
    return Solid(solid).translate((0, 0, z0))


def write_step(parts, path, assy_name=f"VAYN_Shoulder_Actuator_Rev{g.REV}"):
    """Write a named, coloured STEP assembly of the exact solids."""
    assy = cq.Assembly(name=assy_name)
    for name, mat, solid in parts:
        r, gg, b = (int(g.MATERIALS[mat][0][i:i + 2], 16) / 255 for i in (1, 3, 5))
        assy.add(solid.s, name=name.replace("/", "-"), color=cq.Color(r, gg, b))
    assy.save(path, exportType="STEP")
    print(f"wrote {path} ({os.path.getsize(path) / 1e6:.1f} MB)")


def use_occ_kernel():
    """Point build() in gen_actuator_3mf at the OpenCascade primitives."""
    for name, fn in dict(cyl=cyl, tube=tube, box=box, pattern=pattern, hex_prism=hex_prism,
                         extrude_polygon=extrude_polygon, Manifold=Kernel).items():
        setattr(g, name, fn)


if __name__ == "__main__":
    t0 = time.time()
    use_occ_kernel()
    model = g.build()
    print(f"built {len(model)} exact solids in {time.time() - t0:.0f} s")
    bad = [n for n, _, s in model if s.is_empty() or s.status().name != "NoError"]
    print(f"invalid solids: {bad or 'none'}")
    write_step(model, g.OUT[:-4] + ".step")
    print(f"total {time.time() - t0:.0f} s")
