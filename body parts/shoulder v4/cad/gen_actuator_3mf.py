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
DR = 0.08  # metal pin is only 0.006 mm over size. 0.12 mm was taking teeth out of contact
OUT_R, OUT_N, OUT_PIN_R, OUT_PLAY = 30.0, 8, 3.0, 0.25
HOLE_R = OUT_PIN_R + ECC + OUT_PLAY

# measured LA8308. z = 0 is the hub face. the body is 27.5 flat to flat.
# the stub and the hex are not inside that 27.5.
MOUNT = -27.5
COVER_FACE = MOUNT - 13.2  # hex 6.7 + glued cover 6.5
LID_OUTER = COVER_FACE - 6.2  # 1 mm air + 1.1 chip + 1.6 board + 0.5 air + 2 lid

# discs stay 7 mm. each needle is 10 mm, with 1.5 mm sticking out of the disc.
# the carrier plates sit outside the discs and clear those ends. flange is at 53.
OD_R = 52.0
Z_D1 = (16.2, 23.2)
Z_N1 = (14.7, 24.7)
Z_D2 = (27.4, 34.4)
Z_N2 = (25.9, 35.9)  # 1.2 mm clear of needle 1, so the journals can overlap
Z_REAR_PLATE = (13.3, 16.0)  # output pins are held here and at the front plate
Z_FRONT_PLATE = (34.6, 37.4)
Z_HOUSING_END = 34.5
Z_BRG = ((4.2, 13.2), (37.8, 46.8))  # 61906, 30 x 47 x 9, C0 4.55 kN
Z_FLANGE0, Z_FLANGE1 = 47.0, 53.0
HUB_RO, HUB_RI = 14.95, 13.4  # 0.05 mm model gap to the 30 mm bearing bore

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
    """Countersink opening toward -z is the head. The hole runs toward +z."""
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


def disc(z0, z1, shift_x, rot_deg):
    """One cycloid disc on an eccentric journal."""
    pts = cy.disc_profile(PIN_R, ECC, PIN_RAD, RATIO, n=1200, dr=DR, rot_deg=rot_deg)
    body = extrude_polygon(pts, z0, z1).translate((shift_x, 0, 0))
    body = body - cyl(12.2, z0 - 0.2, z1 + 0.2, shift_x, 0)  # race for the 24 mm needle
    for a in every(OUT_N):
        x, y = polar(OUT_R, a)
        body = body - cyl(HOLE_R, z0 - 0.2, z1 + 0.2, x + shift_x, y)
    return body


def build():
    """Return (name, material, solid) for the coaxial actuator."""
    p = []

    def add(name, mat, solid):
        p.append((name, mat, solid))

    # housing is open at the rear so the motor slides in, and open at the front
    # so the discs slide in. a lip at z = 0 stops the can. the front bearing
    # lives in a cover, not in a bore smaller than the discs.
    h = cyl(OD_R, MOUNT, Z_HOUSING_END)
    h = h - cyl(47.0, MOUNT - 0.2, 0.0)  # motor entry, 1 mm radial over the 92 mm can
    h = h - cyl(24.0, -0.2, 4.2)  # crank flange, 22 mm radius, passes this hole
    h = h - cyl(23.6, Z_BRG[0][0], Z_BRG[0][1])  # rear 61906 seat
    h = h - cyl(46.4, 4.0, Z_HOUSING_END + 0.2)  # discs enter from the front
    for i, a in enumerate(every(ZP, 3.9)):
        x, y = polar(PIN_R, a)
        h = h - cyl(2.05, 0.0, 4.0, x, y)  # rear support, 0.05 mm radial over the pin
        add(f"02.{i + 1} Ring pin D4", "52100 bearing steel", cyl(PIN_RAD, 0.2, Z_FRONT_PLATE[1], x, y))
    # m3 taps for the rear plate. inner edge stays outside the motor bore.
    h = h - holes(49.5, 2.5, MOUNT - 0.2, MOUNT + 8, every(8, 22.5))
    h = h - holes(49.5, 2.5, Z_HOUSING_END - 8, Z_HOUSING_END + 0.2, every(8, 22.5))
    add("01 Housing 6082-T6", "6082-T6", h)

    add("03 Cycloid disc A", "20MnCr5", disc(*Z_D1, ECC, 0.0))
    add("04 Cycloid disc B", "20MnCr5", disc(*Z_D2, -ECC, -180.0 / RATIO))
    add("05 Needle K20x24x10 A", "Bearing (purchased)", tube(12.0, 10.08, *Z_N1).translate((ECC, 0, 0)))
    add("06 Needle K20x24x10 B", "Bearing (purchased)", tube(12.0, 10.08, *Z_N2).translate((-ECC, 0, 0)))

    # flange reaches the measured m2 circle (radius 19). the old crank was only radius 12.4, so those holes missed it.
    crank = cyl(22, 0.15, 3.4) - cyl(1.6, -0.2, 9.0)
    crank = crank - holes(19, 2.4, 0.05, 3.5, every(4))
    crank = crank - holes(19, 4.4, 2.0, 3.5, every(4))  # head counterbore
    crank = crank + cyl(8, 3.2, Z_N1[0] - 0.1)
    crank = crank + cyl(10.0, Z_N1[0] - 1.0, Z_N2[0] - 0.3, ECC, 0)
    crank = crank + cyl(10.0, Z_N1[1] + 0.2, Z_N2[1] + 0.3, -ECC, 0)
    add("07 Crank", "20MnCr5", crank)
    for i, a in enumerate(every(4)):
        x, y = polar(19, a)
        screw = cyl(0.9, -4.5, 2.0, x, y) + cyl(1.8, 2.0, 3.3, x, y)
        add(f"22.{i + 1} Screw M2 crank to rotor", "52100 bearing steel", screw)

    # rear plate and pins only. the front is open so both discs slide on from the front.
    pins = pattern(lambda a: cyl(OUT_PIN_R, Z_REAR_PLATE[0], Z_FRONT_PLATE[0] + 1.6, *polar(OUT_R, a)), every(OUT_N))
    rear_plate = tube(36, HUB_RI, *Z_REAR_PLATE)
    rear_hub = tube(HUB_RO, HUB_RI, Z_BRG[0][0], Z_REAR_PLATE[1])
    add("08 Rear carrier", "20MnCr5", pins + rear_plate + rear_hub)

    # front plate and hub slide on after the discs. bearing slides on from the arm end, then the flange.
    front = tube(36, HUB_RI, *Z_FRONT_PLATE) + tube(HUB_RO, HUB_RI, Z_FRONT_PLATE[0], Z_FLANGE1)
    front = front - cyl(2.05, -22, 22).rotate((0, -90, 0)).translate((0, 0, 50.0))  # cross pin
    for i, a in enumerate(every(OUT_N)):
        x, y = polar(OUT_R, a)
        front = front - cyl(3.08, Z_FRONT_PLATE[0] - 0.2, Z_FRONT_PLATE[0] + 1.6, x, y)
        front = front - cyl(1.7, Z_FRONT_PLATE[0] + 1.4, Z_FRONT_PLATE[1] + 0.1, x, y)
        front = front - cyl(2.55, Z_FRONT_PLATE[1] - 1.25, Z_FRONT_PLATE[1] + 0.1, x, y)
        shank = cyl(1.2, Z_FRONT_PLATE[0] + 0.4, Z_FRONT_PLATE[1] - 1.2, x, y)
        head = cyl(2.3, Z_FRONT_PLATE[1] - 1.2, Z_FRONT_PLATE[1] - 0.1, x, y)
        add(f"24.{i + 1} Screw M3 pin plate", "52100 bearing steel", shank + head)
    add("23 Front plate and hub", "20MnCr5", front)
    flange = cyl(39, Z_FLANGE0, Z_FLANGE1) - cyl(HUB_RO + 0.12, Z_FLANGE0 - 0.2, Z_FLANGE1 + 0.2)
    flange = flange - cyl(20, Z_FLANGE1 - 2, Z_FLANGE1 + 0.2)
    flange = flange - holes(26, 4.2, Z_FLANGE0 - 0.2, Z_FLANGE1 + 0.2, every(6, 30))
    flange = flange - cyl(2.05, -22, 22).rotate((0, -90, 0)).translate((0, 0, 50.0))
    add("25 Arm flange", "20MnCr5", flange)
    add("26 Cross pin D4", "52100 bearing steel", cyl(2.0, -18, 18).rotate((0, -90, 0)).translate((0, 0, 50.0)))
    add("09 Rear output bearing 61906", "Bearing (purchased)", tube(23.5, 15, *Z_BRG[0]))
    add("10 Front output bearing 61906", "Bearing (purchased)", tube(23.5, 15, *Z_BRG[1]))

    # cover closes the bore, holds the front ends of the ring pins, and the front bearing.
    cover = cyl(OD_R, Z_HOUSING_END, Z_FLANGE0)
    cover = cover - cyl(37.2, Z_HOUSING_END - 0.2, Z_BRG[1][0])
    cover = cover - cyl(23.6, Z_BRG[1][0] - 0.2, Z_BRG[1][1])
    cover = cover - cyl(16.0, Z_BRG[1][1], Z_FLANGE0 + 0.2)
    for a in every(ZP, 3.9):
        cover = cover - cyl(2.05, Z_HOUSING_END - 0.2, Z_FRONT_PLATE[1] + 0.2, *polar(PIN_R, a))
    cover = cover - holes(49.5, 3.4, Z_HOUSING_END - 0.2, Z_HOUSING_END + 6, every(8, 22.5))
    add("15 Front cover", "6082-T6", cover)

    stator = cyl(46, MOUNT, 0) - cyl(8, MOUNT - 1, 1)
    add("11 LA8308 stator", "Motor envelope", stator)
    bell = cyl(46, -3, 0) + hex_prism(17.3, MOUNT - 6.7, MOUNT) + cyl(5, COVER_FACE, MOUNT - 6.6)
    bell = bell - holes(19, 2.1, -6.0, 0.3, every(4))  # m2 clearance in the rotor face; the thread is cut in the metal
    add("12 LA8308 rotor", "Motor envelope", bell)

    # rear plate is the planetary one: lid, encoder pocket, cable groove, phase slot.
    # drawn with the outer face at local z = 0, then shifted so that face is LID_OUTER.
    lead = 180.0
    enc = ((12.0, 45.0), (12.0, 225.0), (9.5, 135.0), (9.5, 315.0))
    z_face = MOUNT - LID_OUTER  # 19.4 mm, motor rear face
    lid = cyl(29.9, 0, 2) - cyl(18, 0.5, 2.1)
    lid = lid - box(24, 31, -2, 2, -1, 3) - box(24, 31, -7.5, 7.5, -1, 3).rotate((0, 0, lead))
    lid = lid - holes(27, 2.4, -0.2, 2.2, every(4, 45))
    plate = cyl(OD_R, 0, 2) + cyl(OD_R, 1.99, z_face)
    plate = plate - cyl(30.05, -1, 2)  # lid sits in this recess
    plate = plate - box(-15.3, 15.3, -15.3, 15.3, 1.9, 6.3)  # encoder pocket
    plate = plate - cyl(5.5, 6.0, 12.7) - cyl(10.55, 12.2, z_face + 0.1)  # cover, then hex
    for r, a in enc:
        x, y = polar(r, a)
        plate = plate + cyl(3.5, 4.1, 6.4, x, y) - cyl(1.7, 4.0, 8.0, x, y)
    plate = plate - holes(27, 2.0, 1.9, 6.0, every(4, 45))
    # encoder cable at 0 deg, phase leads at 180 deg. same paths as the planetary plate.
    plate = plate - box(24, OD_R + 1, -2, 2, -1, 3)
    plate = plate - box(24, OD_R + 1, -7.5, 7.5, -1, 5.5).rotate((0, 0, lead))
    plate = plate - box(24, 36, -7.5, 7.5, -1, z_face + 0.2).rotate((0, 0, lead))
    for a in every(4, 45):
        plate = plate - csk_hole(*polar(20, a), 8.0, 12.0, 4.0)
    plate = plate - holes(49.5, 3.4, -0.2, z_face + 0.2, every(8, 22.5))
    shift = (0, 0, LID_OUTER)
    add("13 Rear plate 6082-T6", "6082-T6", plate.translate(shift))
    add("16 Encoder lid", "6082-T6", lid.translate(shift))
    board = box(-15, 15, -15, 15, 2.5, 4.1)
    for r, a in enc:
        board = board - cyl(1.7, 2.4, 4.2, *polar(r, a))
    add("14 Meukron board", "Electronics", board.translate(shift))
    add("17 Encoder chip", "Electronics", box(-2.5, 2.5, -2.2, 2.2, 4.1, 5.2).translate(shift))
    return p


def check(parts):
    """Print mesh health, disconnected shells, and the envelope."""
    bad = [n for n, _, s in parts if s.is_empty() or s.status().name != "NoError" or s.volume() <= 0]
    print(f"objects {len(parts)}  invalid {bad or 'none'}")
    # the motor envelope omits the can between the hub and the rear cap, so it is two shells on purpose
    split = [f"{n} ({len(s.decompose())})" for n, _, s in parts
             if not n.startswith(("11", "12")) and len(s.decompose()) != 1]
    print(f"disconnected {split or 'none'}")
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
