"""Build the VAYN shoulder v5 two-stage cycloid.

Z = 0 is the motor hub face. Negative Z is the motor and the encoder.
Positive Z is the cycloid and the arm flange. Pitch and yaw use the same part.

The gear is the Blagojevic layout: one disc on each stage, one crank,
a middle roller plate, a fixed first ring, and a second ring that is the output.
Ratio is 55:1 (11 lobes, then 9).

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

REV = "5.0"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "actuator.3mf")

# 12 pins then 10 pins, one tooth less on each disc. overall ratio 55.
PIN_R = 42.0
ECC = 1.75  # same offset on both journals so the two discs shake against each other
DR = 0.12
ZP1, PIN1 = 12, 4.5  # 11 lobes
ZP2, PIN2 = 10, 5.0  # 9 lobes
ZC1, ZC2 = ZP1 - 1, ZP2 - 1
OUT_R, OUT_N, OUT_PIN, OUT_PLAY = 24.0, 6, 3.5, 0.25
HOLE_R = OUT_PIN + ECC + OUT_PLAY
FACE = 10.0  # matches the K 20x24x10 needle

# measured LA8308. the 27.5 mm length is hub face to rear stator face.
MOUNT = -27.5
COVER_FACE = MOUNT - 13.2  # hex 6.7 plus the glued cover 6.5
LID_OUTER = COVER_FACE - 6.2  # lid, air, board, chip, air to the cover

OD_R = 52.0  # 104 mm, so the cover wall sits outside the 92 mm motor
BORE_R = 47.4  # clears a 10 mm pin on the 42 mm circle (outer radius 47)
Z_D1 = (4.2, 14.2)
Z_WEB = (14.4, 24.4)  # 10 mm, same width as the middle needle
Z_D2 = (24.6, 34.6)
HOUSING_END = 34.8
Z_RING = (35.0, 39.0)
Z_B1 = (40.0, 49.0)  # 61906 pair, centres 16 mm apart
Z_B2 = (56.0, 65.0)
Z_FLANGE = (67.0, 73.0)

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


def csk_hole(x, y, z_face, depth, d):
    """Countersink opening toward -z. The hole runs toward +z."""
    head = Manifold.cylinder(d / 2, d, d / 2 + 0.1, segs(d)).translate((x, y, z_face))
    return head + cyl(d / 2 + 0.1, z_face, z_face + depth, x, y)


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


def make_disc(z0, z1, shift_x, rot_deg, zp, pin_r):
    """One cycloid disc. The outline is rotated; the roller holes stay put."""
    pts = cy.disc_profile(PIN_R, ECC, pin_r, zp - 1, n=900, dr=DR, rot_deg=rot_deg)
    body = extrude_polygon(pts, z0, z1).translate((shift_x, 0, 0))
    body = body - cyl(12.2, z0 - 0.2, z1 + 0.2, shift_x, 0)  # race for the K 20x24x10
    for a in every(OUT_N):
        x, y = polar(OUT_R, a)
        body = body - cyl(HOLE_R, z0 - 0.2, z1 + 0.2, x + shift_x, y)
    return body


def build():
    """Return (name, material, solid) for the whole actuator."""
    p = []

    def add(name, mat, solid):
        p.append((name, mat, solid))

    # housing is open at the back for the motor and open at the front for the discs.
    # the bearings sit in the cover, so the bore never closes down in front of a disc.
    h = cyl(OD_R, MOUNT, HOUSING_END)
    h = h - cyl(47.0, MOUNT - 0.2, 0.0)  # motor, 1 mm radial over the 92 mm can
    h = h - cyl(23.5, -0.2, 4.2)  # crank flange, 22 mm radius, passes the lip
    h = h - cyl(BORE_R, 4.0, HOUSING_END + 0.2)
    for i, a in enumerate(every(ZP1)):
        x, y = polar(PIN_R, a)
        h = h - cyl(PIN1 + 0.05, 0.0, 4.2, x, y)
        add(f"02.{i + 1} Stage-1 pin D9", "52100 bearing steel", cyl(PIN1, 0.2, Z_D1[1], x, y))
    h = h - holes(49, 5.2, MOUNT - 0.2, MOUNT + 8, every(6, 30))
    h = h - holes(49, 4.2, HOUSING_END - 6.0, HOUSING_END + 0.2, every(6, 0))  # m5 for the cover
    add("01 Housing 6082-T6", "6082-T6", h)

    add("03 Disc 11-lobe", "20MnCr5", make_disc(*Z_D1, ECC, 0.0, ZP1, PIN1))
    add("04 Disc 9-lobe", "20MnCr5", make_disc(*Z_D2, -ECC, -180.0 / ZC2, ZP2, PIN2))
    add("05 Needle K20x24x10 A", "Bearing (purchased)", tube(12.0, 10.05, *Z_D1).translate((ECC, 0, 0)))
    add("06 Needle K20x24x10 B", "Bearing (purchased)", tube(12.0, 10.05, *Z_D2).translate((-ECC, 0, 0)))

    # journals stop before the middle needle. the straight bridge joins them.
    crank = cyl(22, 0.2, 3.6) - cyl(1.6, -0.2, 9.0)  # stub clearance, measured d2.9
    crank = crank - holes(19, 2.2, 0.1, 3.7, every(4))  # m2 clearance on the 38 mm circle
    crank = crank + cyl(14, 3.4, 4.0)
    crank = crank + cyl(10, 3.5, 14.3, ECC, 0)
    crank = crank + cyl(8, 14.0, 24.7)
    crank = crank + cyl(10, 24.5, 35.2, -ECC, 0)
    add("07 Crank", "20MnCr5", crank)

    plate = cyl(32, *Z_WEB) - cyl(10.2, Z_WEB[0] - 0.2, Z_WEB[1] + 0.2)
    for a in every(OUT_N):
        x, y = polar(OUT_R, a)
        plate = plate - cyl(OUT_PIN + 0.05, Z_WEB[0] - 0.2, Z_WEB[1] + 0.2, x, y)
    add("08 Central plate", "20MnCr5", plate)
    add("09 Central rollers D7", "52100 bearing steel",
        pattern(lambda a: cyl(OUT_PIN - 0.05, Z_D1[0], Z_D2[1], *polar(OUT_R, a)), every(OUT_N)))
    add("10 Needle K16x20x10", "Bearing (purchased)", tube(10.0, 8.05, 14.5, 24.2))

    ring = cyl(50, *Z_RING) - cyl(13.2, Z_RING[0] - 0.2, Z_RING[1] + 0.2)
    ring = ring - holes(PIN_R, 2 * PIN2 + 0.1, Z_RING[0] - 0.2, Z_RING[1] + 0.2, every(ZP2))
    pins = pattern(lambda a: cyl(PIN2, Z_D2[0], Z_RING[1], *polar(PIN_R, a)), every(ZP2))
    hub = tube(14.9, 13.0, Z_RING[0], Z_FLANGE[1])
    flange = cyl(39, *Z_FLANGE) - cyl(20, Z_FLANGE[1] - 2, Z_FLANGE[1] + 0.2)
    flange = flange - holes(26, 4.2, Z_FLANGE[0] - 0.2, Z_FLANGE[1] + 0.2, every(6, 30))
    add("11 Stage-2 pins D10", "52100 bearing steel", pins)
    add("12 Output ring, hub and arm flange", "20MnCr5", ring + hub + flange)

    add("13 Output bearing 61906 A", "Bearing (purchased)", tube(23.5, 15, *Z_B1))
    add("14 Output bearing 61906 B", "Bearing (purchased)", tube(23.5, 15, *Z_B2))

    cover = cyl(OD_R, HOUSING_END, Z_FLANGE[0] - 0.2)
    cover = cover - cyl(50.4, HOUSING_END - 0.2, Z_RING[1] + 0.2)  # steel ring sits here
    cover = cover - cyl(BORE_R, HOUSING_END - 0.2, Z_B1[0])
    cover = cover - cyl(23.6, Z_B1[0] - 0.2, Z_B1[1])
    cover = cover - cyl(16.0, Z_B1[1], Z_B2[0])  # shoulder between the two bearings
    cover = cover - cyl(23.6, Z_B2[0], Z_B2[1] + 0.2)
    cover = cover - cyl(16.0, Z_B2[1], Z_FLANGE[0] + 0.2)
    cover = cover - holes(49, 5.5, HOUSING_END - 0.2, HOUSING_END + 8, every(6, 0))
    add("15 Front cover", "6082-T6", cover)

    add("16 LA8308 stator", "Motor envelope", cyl(46, MOUNT, 0) - cyl(8, MOUNT - 1, 1))
    bell = cyl(46, -3, 0) + hex_prism(17.3, MOUNT - 6.7, MOUNT) + cyl(5, COVER_FACE, MOUNT - 6.6)
    add("17 LA8308 rotor", "Motor envelope", bell)

    # rear plate matches the measured motor: hex, glued cover, rhombus, cable, phase slot.
    lead = 180.0
    enc = ((12.0, 45.0), (12.0, 225.0), (9.5, 135.0), (9.5, 315.0))
    z_face = MOUNT - LID_OUTER
    lid = cyl(29.9, 0, 2) - cyl(18, 0.5, 2.1)
    lid = lid - box(24, 31, -2, 2, -1, 3) - box(24, 31, -7.5, 7.5, -1, 3).rotate((0, 0, lead))
    lid = lid - holes(27, 2.4, -0.2, 2.2, every(4, 45))
    plate = cyl(OD_R, 0, 2) + cyl(OD_R, 1.99, z_face)
    plate = plate - cyl(30.05, -1, 2)
    plate = plate - box(-15.3, 15.3, -15.3, 15.3, 1.9, 6.3)
    plate = plate - cyl(5.5, 6.0, 12.7) - cyl(10.55, 12.2, z_face + 0.1)
    for r, a in enc:
        x, y = polar(r, a)
        plate = plate + cyl(3.5, 4.1, 6.4, x, y) - cyl(1.7, 4.0, 8.0, x, y)
    plate = plate - holes(27, 2.0, 1.9, 6.0, every(4, 45))
    plate = plate - box(24, OD_R + 1, -2, 2, -1, 3)
    plate = plate - box(24, OD_R + 1, -7.5, 7.5, -1, 5.5).rotate((0, 0, lead))
    plate = plate - box(24, 36, -7.5, 7.5, -1, z_face + 0.2).rotate((0, 0, lead))
    for a in every(4, 45):
        plate = plate - csk_hole(*polar(20, a), 8.0, 12.0, 4.0)
    plate = plate - holes(49, 5.2, -0.2, z_face + 0.2, every(6, 30))
    shift = (0, 0, LID_OUTER)
    add("18 Rear plate 6082-T6", "6082-T6", plate.translate(shift))
    add("19 Encoder lid", "6082-T6", lid.translate(shift))
    board = box(-15, 15, -15, 15, 2.5, 4.1)
    for r, a in enc:
        board = board - cyl(1.7, 2.4, 4.2, *polar(r, a))
    add("20 Meukron board", "Electronics", board.translate(shift))
    add("21 Encoder chip", "Electronics", box(-2.5, 2.5, -2.2, 2.2, 4.1, 5.2).translate(shift))
    return p


def check(parts):
    """Print mesh health, a few gaps, and the envelope."""
    bad = [n for n, _, s in parts if s.is_empty() or s.status().name != "NoError" or s.volume() <= 0]
    print(f"objects {len(parts)}  invalid {bad or 'none'}")
    named = {n: s for n, _, s in parts}

    def gap(a, b):
        sa = next(s for n, s in named.items() if n.startswith(a))
        sb = next(s for n, s in named.items() if n.startswith(b))
        print(f"gap {a} / {b}: {sa.min_gap(sb, 2.0):.3f} mm")

    for pair in (("03", "01"), ("03", "02"), ("04", "11"), ("03", "07"), ("04", "07"),
                 ("08", "07"), ("05", "03"), ("17", "18"), ("12", "15"), ("09", "03")):
        gap(*pair)
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
