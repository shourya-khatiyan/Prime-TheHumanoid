"""Build the VAYN shoulder v3 pitch actuator as a multi-object 3MF.

Folded cycloid. The joint axis is Z. Z = 0 is the torso mounting face.
Positive Z is outboard, toward the arm. The motor axis is parallel, at x = 96.

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
import cycloid as cy  # same curve and clearance math as the elbow

REV = "3.0"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "actuator.3mf")
PA = math.radians(20.0)
BACKLASH_HALF = 0.04

# cycloid. 45 lobes, 46 pins, ratio 45. pin circle R 38, pin diameter 4.
PIN_N = 46
RATIO = PIN_N - 1
PIN_R = 38.0
PIN_RAD = 2.0
ECC = 0.65 * PIN_R / PIN_N
PROFILE_GROW = 0.12  # radial pin clearance. 0.08 was the elbow value that a real pin and a small hole ate up
OUT_R = 22.0
OUT_PIN_R = 3.0
OUT_N = 8
SPUR_M = 1.5
SPUR_Z = 64  # 1:1, centre distance 96 mm
MOTOR_X = SPUR_M * SPUR_Z

MATERIALS = {
    "6082-T6": ("#B8BEC6", 2.70),
    "20MnCr5": ("#8A6F4E", 7.85),
    "52100 bearing steel": ("#9AA3AD", 7.81),
    "Steel 12.9 fastener": ("#2B2B2B", 7.85),
    "Bearing (purchased)": ("#D9B54A", 7.80),
    "Motor envelope": ("#5B7DB1", 0.0),
    "Electronics": ("#2E8B57", 0.0),
}


def segs(r):
    """Circle segment count for radius r."""
    return max(24, int(math.ceil(2 * math.pi * r / 0.8 / 4)) * 4)


def cyl(r, z0, z1, x=0.0, y=0.0):
    """Solid cylinder of radius r from z0 to z1, centred at (x, y)."""
    if z1 < z0:
        z0, z1 = z1, z0
    return Manifold.cylinder(z1 - z0, r, r, segs(r)).translate((x, y, z0))


def tube(ro, ri, z0, z1):
    """Hollow cylinder, outer ro, inner ri."""
    return cyl(ro, z0, z1) - cyl(ri, z0 - 1, z1 + 1)


def box(x0, x1, y0, y1, z0, z1):
    """Axis-aligned box."""
    return Manifold.cube((x1 - x0, y1 - y0, z1 - z0)).translate((x0, y0, z0))


def polar(r, deg):
    """Point (x, y) at radius r and angle deg."""
    a = math.radians(deg)
    return r * math.cos(a), r * math.sin(a)


def pattern(fn, angles):
    """Union of fn(angle) over angles in degrees."""
    return Manifold.batch_boolean([fn(a) for a in angles], OpType.Add)


def every(n, start=0.0):
    """n evenly spaced angles in degrees."""
    return [start + 360.0 * i / n for i in range(n)]


def holes(r_pcd, d, z0, z1, angles):
    """Axial holes of diameter d on a pitch circle."""
    return pattern(lambda a: cyl(d / 2, z0, z1, *polar(r_pcd, a)), angles)


def inv(a):
    """Involute function tan(a) - a."""
    return math.tan(a) - a


def tooth_outline(n, m, r_root, r_tip, half_angle_pitch, pa=None):
    """Closed involute outline of n teeth, centred on +X. Returns an (k, 2) array."""
    pa = PA if pa is None else pa
    rp = n * m / 2
    rb = rp * math.cos(pa)

    def theta(r):
        ang = math.acos(min(1.0, rb / max(r, rb)))
        return max(half_angle_pitch + inv(pa) - inv(ang), 0.002)

    pitch = 2 * math.pi / n
    t_root = theta(r_root)
    r_flank0 = max(r_root, rb)
    one = []
    one += [(r_root, a) for a in np.linspace(-pitch / 2, -t_root, 3)]
    one += [(r, -theta(r)) for r in np.linspace(r_flank0, r_tip, 6)[(0 if r_root < rb else 1):]]
    one += [(r_tip, a) for a in np.linspace(-theta(r_tip), theta(r_tip), 4)[1:-1]]
    one += [(r, theta(r)) for r in np.linspace(r_tip, r_flank0, 6)[:(None if r_root < rb else -1)]]
    one += [(r_root, a) for a in np.linspace(t_root, pitch / 2, 3)[:-1]]
    pts = [(r * math.cos(a + i * pitch), r * math.sin(a + i * pitch)) for i in range(n) for r, a in one]
    return np.array(pts)


def ext_gear(n, m, z0, z1, rot_deg=0.0, pa=None, backlash=None, addendum=1.0):
    """External spur gear, x = 0, thinned for backlash."""
    pa = PA if pa is None else pa
    backlash = BACKLASH_HALF if backlash is None else backlash
    rp = n * m / 2
    half = (math.pi * m / 2 - backlash) / (2 * rp)
    pts = tooth_outline(n, m, rp - 1.25 * m, rp + addendum * m, half, pa)
    return extrude_polygon(pts, z0, z1).rotate((0, 0, rot_deg))


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


def cycloid_points(rot_deg=0.0):
    """Disc outline from the elbow offset curve, in the disc's own centre."""
    pts = cy.disc_profile(PIN_R, ECC, PIN_RAD, RATIO, n=2500, dr=PROFILE_GROW, rot_deg=rot_deg)
    return [tuple(p) for p in pts]


def cycloid_disc(z0, z1, shift_x, rot_deg):
    """One cycloid disc, centre shifted by shift_x, profile rotated by rot_deg.

    Output holes are pin radius + eccentricity + 0.20 mm. That is the orbit
    of the pin in the disc, plus play. An earlier hole added an extra
    R*sin(180/ratio) term and was about 1.7 mm too large in radius.
    """
    pts = cycloid_points(rot_deg)
    body = extrude_polygon(pts, z0, z1).translate((shift_x, 0, 0))
    body = body - cyl(11.0, z0 - 0.2, z1 + 0.2, shift_x, 0)
    hole_r = OUT_PIN_R + ECC + 0.20
    for a in every(OUT_N):
        x, y = polar(OUT_R, a)
        body = body - cyl(hole_r, z0 - 0.2, z1 + 0.2, x + shift_x, y)
    return body


def build():
    """Return (name, material, solid) for the pitch actuator."""
    p = []

    def add(name, mat, solid):
        p.append((name, mat, solid))

    # housing. joint barrel on the origin, motor tunnel at x = 96, inboard of z = 0.
    barrel = cyl(45, 0, 58) + cyl(52, 0, 12)
    tunnel = cyl(50, -36, 12, MOTOR_X, 0)
    web = box(20, MOTOR_X - 20, -28, 28, 0, 12)
    pad = cyl(42, -4, 0) - cyl(30, -5, 1)
    h = barrel + tunnel + web + pad
    h = h - cyl(40.5, 12, 59)  # cycloid chamber
    h = h - cyl(50.5, -1, 12)  # spur chamber on the joint
    h = h - cyl(50.5, -1, 12, MOTOR_X, 0)
    h = h - cyl(46.2, -34, 2, MOTOR_X, 0)  # motor bore, 0.2 mm radial over the 92 mm can
    h = h - box(8, MOTOR_X - 8, -16, 16, -1, 11)  # passage so the two spur gears can meet
    h = h - holes(39, 5.2, -4.1, 8, every(6, 30))  # torso bolts, M5 clearance
    add("01 Housing 6082-T6", "6082-T6", h)

    # fixed ring pins
    for i, a in enumerate(every(PIN_N)):
        x, y = polar(PIN_R, a)
        add(f"02.{i + 1} Ring pin D4", "52100 bearing steel", cyl(PIN_RAD, 16, 36, x, y))

    # two discs, eccentrics opposite, second disc turned by half a turn of the crank
    add("03 Cycloid disc A 45 lobe", "20MnCr5", cycloid_disc(17, 25, ECC, 0.0))
    add("04 Cycloid disc B 45 lobe", "20MnCr5", cycloid_disc(27, 35, -ECC, -180.0 / RATIO))
    for name, z0, sx in (("05 Eccentric bearing A", 17, ECC), ("06 Eccentric bearing B", 27, -ECC)):
        add(name, "Bearing (purchased)", tube(11, 8, z0, z0 + 8).translate((sx, 0, 0)))

    # crank on the joint axis, journals at the disc centres, spur gear on the inboard end
    crank = cyl(8, 2, 46)
    crank = crank + cyl(8, 17, 25, ECC, 0) + cyl(8, 27, 35, -ECC, 0)
    crank = crank - cyl(3, 1.5, 47)
    add("07 Crank shaft", "20MnCr5", crank)
    add("08 Input spur 64T m1.5", "20MnCr5", ext_gear(SPUR_Z, SPUR_M, 2, 10) - cyl(8.2, 1.5, 10.5))

    # output member: pins through the discs, bearings, arm flange
    pins = pattern(lambda a: cyl(OUT_PIN_R, 16, 47, *polar(OUT_R, a)), every(OUT_N))
    flange = cyl(39, 50, 58) - cyl(20, 56, 58.2) - holes(26, 5.0, 49, 58.2, every(6, 30))
    hub = cyl(25, 36, 56) - cyl(12, 35, 57)
    add("09 Output flange and pins", "20MnCr5", pins + flange + hub)

    add("10 Rear output bearing 50x65x7", "Bearing (purchased)", tube(32.5, 25, 36, 43))
    add("11 Front output bearing 50x65x7", "Bearing (purchased)", tube(32.5, 25, 46, 53))

    # motor, inboard of the torso face, axis at x = 96. hub face at z = 1.
    z_hub = 1.0
    z_mount = z_hub - 27.5  # flat face to flat face. the old 32.5 figure is withdrawn.
    stator = cyl(46, z_mount, z_hub, MOTOR_X, 0) - cyl(8, z_mount - 1, z_hub + 1, MOTOR_X, 0)
    add("12 LA8308 envelope", "Motor envelope", stator)
    bell = cyl(46, z_hub - 3, z_hub, MOTOR_X, 0)
    bell = bell + hex_prism(17.3, z_mount - 6.7, z_mount).translate((MOTOR_X, 0, 0))
    bell = bell + cyl(5, z_mount - 13.2, z_mount - 6.6, MOTOR_X, 0)
    add("13 LA8308 rotor cap", "Motor envelope", bell)
    motor_gear = ext_gear(SPUR_Z, SPUR_M, z_hub, z_hub + 8, 180.0 / SPUR_Z) - cyl(6, z_hub - 0.2, z_hub + 8.2)
    add("14 Motor spur 64T m1.5", "20MnCr5", motor_gear.translate((MOTOR_X, 0, 0)))

    # encoder cap over the hex and the cover, M3 rhombus bosses sketched as a lid
    cap = tube(28, 12, z_mount - 22, z_mount - 12).translate((MOTOR_X, 0, 0))
    cap = cap + cyl(28, z_mount - 24, z_mount - 22, MOTOR_X, 0)
    add("15 Encoder cap 6082-T6", "6082-T6", cap)
    board = box(MOTOR_X - 15, MOTOR_X + 15, -15, 15, z_mount - 22, z_mount - 20.4)
    for r, a in ((12.0, 45.0), (12.0, 225.0), (9.5, 135.0), (9.5, 315.0)):
        x, y = polar(r, a)
        board = board - cyl(1.7, z_mount - 22.2, z_mount - 20.2, MOTOR_X + x, y)
    add("16 Meukron board", "Electronics", board)
    return p


def check(parts):
    """Print mesh health, a few gaps, and the envelope."""
    bad = [n for n, _, s in parts if s.is_empty() or s.status().name != "NoError" or s.volume() <= 0]
    print(f"objects: {len(parts)}   invalid: {bad or 'none'}")
    named = {n: s for n, _, s in parts}

    def one(prefix):
        return next(s for n, s in named.items() if n.startswith(prefix))

    pairs = [("03 Cycloid", "02.1 Ring"), ("08 Input", "14 Motor"), ("12 LA8308", "01 Housing"),
             ("09 Output", "03 Cycloid")]
    for a, b in pairs:
        sa, sb = one(a), one(b)
        print(f"gap {a} <-> {b}: {sa.min_gap(sb, 3.0):.3f} mm")
    boxes = [s.bounding_box() for _, _, s in parts]
    lo = np.min([b[:3] for b in boxes], axis=0)
    hi = np.max([b[3:] for b in boxes], axis=0)
    mass = sum(s.volume() / 1000 * MATERIALS[m][1] for _, m, s in parts)
    print(f"mass (motor counted 0): {mass:.0f} g")
    print(f"envelope X {lo[0]:.1f}..{hi[0]:.1f}  Y {lo[1]:.1f}..{hi[1]:.1f}  Z {lo[2]:.1f}..{hi[2]:.1f}")


def mesh_arrays(solid):
    """Vertices and triangles of a manifold solid."""
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
    print(f"wrote {path} ({os.path.getsize(path) / 1e6:.1f} MB)")


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
    print(f"wrote {path} ({os.path.getsize(path) / 1e6:.1f} MB)")


if __name__ == "__main__":
    model = build()
    check(model)
    write_3mf(model, OUT)
    write_stl_zip(model, OUT.replace(".3mf", "_stl.zip"))
