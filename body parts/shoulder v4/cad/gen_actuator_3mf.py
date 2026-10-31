"""Build the VAYN shoulder v4 coaxial cycloid.

Z = 0 is the bolt face, on the motor hub. Negative Z is the motor and the
encoder. Positive Z is the cycloid and the arm flange. The same cylinder
bolts on as a pitch joint or a yaw joint.

Run: python gen_actuator_3mf.py
"""

import ctypes
import math
import os
import re
import struct
import sys
import zipfile

import lib3mf
import numpy as np
from manifold3d import CrossSection, Manifold, OpType

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "elbow v0", "cad"))
import cycloid as cy

REV = "4.0"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "actuator.3mf")

# cycloid, checked in calc.py
RATIO = 45
ZP = RATIO + 1
PIN_R = 44.0
PIN_RAD = 2.0
LAM = 0.55
ECC = LAM * PIN_R / ZP
DR = 0.12
OUT_R, OUT_N, OUT_PIN_R, OUT_PLAY = 30.0, 8, 3.0, 0.25
HOLE_R = OUT_PIN_R + ECC + OUT_PLAY

# measured LA8308, mm. hub face is z = 0.
MOUNT = -32.5
COVER_FACE = MOUNT - 13.2  # hex 6.7 + glued cover 6.5
LID_OUTER = COVER_FACE - 6.2  # air 1 + chip 1.1 + board 1.6 + air 0.5 + lid 2

# in front of the hub. disc width is the 6005 width.
Z_D1 = (0.8, 12.8)
Z_D2 = (13.4, 25.4)
Z_PINS = (0.5, 34.0)
Z_BRG = ((34.6, 41.6), (48.6, 55.6))
Z_FLANGE = 61.6

MATERIALS = {
    "6082-T6": ("#B8BEC6", 2.70),
    "20MnCr5": ("#8A6F4E", 7.85),
    "52100 bearing steel": ("#9AA3AD", 7.81),
    "Bearing (purchased)": ("#D9B54A", 7.80),
    "Motor envelope": ("#5B7DB1", 0.0),
    "Electronics": ("#2E8B57", 0.0),
}


def segs(r):
    """Circle segment count for radius r."""
    return max(24, int(math.ceil(2 * math.pi * r / 0.8 / 4)) * 4)


def cyl(r, z0, z1, x=0.0, y=0.0):
    """Solid cylinder of radius r from z0 to z1."""
    if z1 < z0:
        z0, z1 = z1, z0
    return Manifold.cylinder(z1 - z0, r, r, segs(r)).translate((x, y, z0))


def tube(ro, ri, z0, z1):
    """Hollow cylinder."""
    return cyl(ro, z0, z1) - cyl(ri, z0 - 1, z1 + 1)


def box(x0, x1, y0, y1, z0, z1):
    """Axis-aligned box."""
    return Manifold.cube((x1 - x0, y1 - y0, z1 - z0)).translate((x0, y0, z0))


def polar(r, deg):
    """Point at radius r and angle deg."""
    a = math.radians(deg)
    return r * math.cos(a), r * math.sin(a)


def pattern(fn, angles):
    """Union of fn(angle)."""
    return Manifold.batch_boolean([fn(a) for a in angles], OpType.Add)


def every(n, start=0.0):
    """n evenly spaced angles in degrees."""
    return [start + 360.0 * i / n for i in range(n)]


def holes(r_pcd, d, z0, z1, angles):
    """Axial holes of diameter d on a pitch circle."""
    return pattern(lambda a: cyl(d / 2, z0, z1, *polar(r_pcd, a)), angles)


def extrude_polygon(pts, z0, z1):
    """Extrude a closed polygon from z0 to z1."""
    arr = np.asarray(pts, dtype=float)
    area = float(np.sum(arr[:, 0] * np.roll(arr[:, 1], -1) - arr[:, 1] * np.roll(arr[:, 0], -1)))
    if area < 0:
        arr = arr[::-1]
    return Manifold.extrude(CrossSection([arr]), z1 - z0).translate((0, 0, z0))


def hex_prism(across_flats, z0, z1):
    """Regular hex prism. across_flats is the flat-to-flat width."""
    radius = across_flats / math.sqrt(3.0)
    pts = [(radius * math.cos(math.radians(60 * i + 30)),
            radius * math.sin(math.radians(60 * i + 30))) for i in range(6)]
    return extrude_polygon(pts, z0, z1)


def disc(z0, z1, shift_x, rot_deg):
    """One cycloid disc on an eccentric journal."""
    pts = cy.disc_profile(PIN_R, ECC, PIN_RAD, RATIO, n=800, dr=DR, rot_deg=rot_deg)
    body = extrude_polygon(pts, z0, z1).translate((shift_x, 0, 0))
    body = body - cyl(23.6, z0 - 0.2, z1 + 0.2, shift_x, 0)  # 6005 outer ring
    for a in every(OUT_N):
        x, y = polar(OUT_R, a)
        body = body - cyl(HOLE_R, z0 - 0.2, z1 + 0.2, x + shift_x, y)
    return body


def build():
    """Return (name, material, solid) for the coaxial actuator."""
    p = []

    def add(name, mat, solid):
        p.append((name, mat, solid))

    # housing. od 100. motor bore clears the measured 92 mm can by 0.2 mm.
    h = cyl(50, LID_OUTER, Z_FLANGE)
    h = h - cyl(46.2, MOUNT, 0.2)  # motor
    h = h - cyl(43.6, 0.4, 34.2)  # cycloid chamber, 0.6 mm over the disc sweep
    h = h - cyl(36, 34.2, Z_FLANGE + 0.2)  # bearing bore 72 mm
    h = h - holes(45, 5.2, -6, 4, every(6, 30))  # bolt face, M5, either pitch or yaw
    for i, a in enumerate(every(ZP)):
        x, y = polar(PIN_R, a)
        h = h - cyl(2.05, 0.2, 6.2, x, y)  # ream H7 in metal; model is 0.05 mm over the pin
        add(f"02.{i + 1} Ring pin D4x32", "52100 bearing steel", cyl(PIN_RAD, 0.4, 32.4, x, y))
    add("01 Housing 6082-T6", "6082-T6", h)

    add("03 Cycloid disc A", "20MnCr5", disc(*Z_D1, ECC, 0.0))
    add("04 Cycloid disc B", "20MnCr5", disc(*Z_D2, -ECC, -180.0 / RATIO))
    add("05 Eccentric bearing A 6005", "Bearing (purchased)", tube(23.5, 12.5, *Z_D1).translate((ECC, 0, 0)))
    add("06 Eccentric bearing B 6005", "Bearing (purchased)", tube(23.5, 12.5, *Z_D2).translate((-ECC, 0, 0)))

    crank = cyl(12.5, 0.2, 26.0)
    crank = crank + cyl(12.5, *Z_D1, ECC, 0) + cyl(12.5, *Z_D2, -ECC, 0)
    crank = crank - cyl(1.6, -0.2, 8.0)  # motor stub clearance, measured d2.9
    crank = crank - holes(19, 2.2, -0.2, 4.0, every(4))  # 4 x M2 on the measured 38 mm circle
    add("07 Crank", "20MnCr5", crank)

    pins = pattern(lambda a: cyl(OUT_PIN_R, 8.0, 34.0, *polar(OUT_R, a)), every(OUT_N))
    carrier = cyl(32, 26.0, 55.6) - cyl(16, 25.5, 56)
    carrier = carrier - holes(OUT_R, OUT_PIN_R * 2, 25.5, 34.2, every(OUT_N))
    flange = cyl(39, 55.6, Z_FLANGE) - cyl(20, Z_FLANGE - 2, Z_FLANGE + 0.2)
    flange = flange - holes(26, 5.0, 55.0, Z_FLANGE + 0.2, every(6, 30))
    add("08 Output and arm flange", "20MnCr5", pins + carrier + flange)
    add("09 Rear output bearing 50x65x7", "Bearing (purchased)", tube(32.5, 25, *Z_BRG[0]))
    add("10 Front output bearing 50x65x7", "Bearing (purchased)", tube(32.5, 25, *Z_BRG[1]))

    stator = cyl(46, MOUNT, 0, ) - cyl(8, MOUNT - 1, 1)
    add("11 LA8308 stator", "Motor envelope", stator)
    bell = cyl(46, -3, 0) + hex_prism(17.3, MOUNT - 6.7, MOUNT) + cyl(5, COVER_FACE, MOUNT - 6.6)
    add("12 LA8308 rotor", "Motor envelope", bell)
    add("13 Encoder lid", "6082-T6", tube(24, 8, LID_OUTER, LID_OUTER + 2))
    add("14 Meukron board", "Electronics", box(-15, 15, -15, 15, COVER_FACE - 2.6, COVER_FACE - 1.0))
    return p


def check(parts):
    """Print mesh health and the envelope."""
    bad = [n for n, _, s in parts if s.is_empty() or s.status().name != "NoError" or s.volume() <= 0]
    print(f"objects {len(parts)}  invalid {bad or 'none'}")
    boxes = [s.bounding_box() for _, _, s in parts]
    lo = np.min([b[:3] for b in boxes], axis=0)
    hi = np.max([b[3:] for b in boxes], axis=0)
    print(f"envelope X {lo[0]:.1f}..{hi[0]:.1f}  Y {lo[1]:.1f}..{hi[1]:.1f}  Z {lo[2]:.1f}..{hi[2]:.1f}")


def mesh_arrays(solid):
    """Vertices and triangles of a manifold."""
    mesh = solid.to_mesh()
    return np.asarray(mesh.vert_properties, dtype=np.float32)[:, :3], np.asarray(mesh.tri_verts, dtype=np.uint32)


def write_3mf(parts, path):
    """Write named coloured meshes."""
    w = lib3mf.get_wrapper()
    model = w.CreateModel()
    model.SetUnit(lib3mf.ModelUnit.MilliMeter)
    group = model.AddBaseMaterialGroup()
    mat_id = {}
    for name, (hexcol, _) in MATERIALS.items():
        r, g, b = (int(hexcol[i:i + 2], 16) for i in (1, 3, 5))
        mat_id[name] = group.AddMaterial(name, w.RGBAToColor(r, g, b, 255))
    for name, mat, solid in parts:
        v, t = mesh_arrays(solid)
        obj = model.AddMeshObject()
        obj.SetName(name)
        obj.SetGeometry([lib3mf.Position((ctypes.c_float * 3)(*p)) for p in v.tolist()],
                        [lib3mf.Triangle((ctypes.c_uint32 * 3)(*f)) for f in t.tolist()])
        obj.SetObjectLevelProperty(group.GetResourceID(), mat_id[mat])
        model.AddBuildItem(obj, w.GetIdentityTransform())
    model.QueryWriter("3mf").WriteToFile(path)
    print(f"wrote {path}")


def write_stl_zip(parts, path):
    """Write one binary STL per part into a zip."""
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for name, _, solid in parts:
            v, t = mesh_arrays(solid)
            tri = v[t]
            n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
            n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
            rec = np.zeros(len(t), dtype=[("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")])
            rec["n"], rec["v"] = n, tri
            fname = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("_") + ".stl"
            z.writestr(fname, b"\0" * 80 + struct.pack("<I", len(t)) + rec.tobytes())
    print(f"wrote {path}")


if __name__ == "__main__":
    model = build()
    check(model)
    write_3mf(model, OUT)
    write_stl_zip(model, OUT.replace(".3mf", "_stl.zip"))
