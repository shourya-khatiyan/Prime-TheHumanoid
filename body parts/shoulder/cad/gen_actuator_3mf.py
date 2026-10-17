"""Build the VAYN shoulder actuator Rev 1.4 as a multi-object 3MF.

Every part is a separate named, watertight mesh placed in its assembled
position (Z = 0 at the rear outer face, axis = Z). Geometry follows shoulder/parts.md. Motor, encoder PCB and
purchased bearings are envelope models only. Tapped holes are modelled at
thread major diameter, threads are not modelled.

Run:  python gen_actuator_3mf.py   (needs numpy + manifold3d + lib3mf)
Output, beside this script: actuator.3mf, actuator_stl.zip,
and actuator_print.zip (machined stand-ins and gears; no bought parts),
plus an interference / mass report printed to the console.
"""

import ctypes
import math
import os
import re
import struct
import zipfile
from itertools import combinations

import lib3mf
import numpy as np
from manifold3d import CrossSection, Manifold, OpType

REV = "1.4"
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "actuator.3mf")
PA = math.radians(20.0)
BACKLASH_HALF = 0.025  # circular thinning per gear at pitch (0.05 per mesh)

# material name -> (display colour, density g/cm3)
MATERIALS = {
    "7075-T6": ("#B8BEC6", 2.81),
    "6061-T6": ("#C9CED4", 2.70),  # elbow and arm still use this key
    "16MnCr5 carburized": ("#8A6F4E", 7.85),
    "42CrMo4 nitrided": ("#6E5A44", 7.85),
    "42CrMo4 Q&T": ("#7D8590", 7.85),
    "Spring steel": ("#4F6D7A", 7.80),
    "52100 bearing steel": ("#9AA3AD", 7.81),
    "Steel 12.9 fastener": ("#2B2B2B", 7.85),
    "Bearing (purchased)": ("#D9B54A", 7.80),
    "Motor envelope": ("#5B7DB1", 0.0),
    "Electronics": ("#2E8B57", 0.0),
    "NdFeB magnet": ("#B03030", 7.50),
}


# ---------------------------------------------------------------- primitives
def segs(r):
    """Return a circle segment count for radius r (same r -> same count)."""
    return max(24, int(math.ceil(2 * math.pi * r / 0.7 / 4)) * 4)


def cyl(r, z0, z1, x=0.0, y=0.0):
    """Solid cylinder of radius r between z0 and z1, centred at (x, y)."""
    return Manifold.cylinder(z1 - z0, r, r, segs(r)).translate((x, y, z0))


def tube(ro, ri, z0, z1):
    """Hollow cylinder (ro outer, ri inner) between z0 and z1."""
    return cyl(ro, z0, z1) - cyl(ri, z0 - 1, z1 + 1)


def box(x0, x1, y0, y1, z0, z1):
    """Axis-aligned box from min/max corners."""
    return Manifold.cube((x1 - x0, y1 - y0, z1 - z0)).translate((x0, y0, z0))


def polar(r, deg):
    """Return (x, y) for radius r at angle deg."""
    a = math.radians(deg)
    return r * math.cos(a), r * math.sin(a)


def pattern(fn, angles):
    """Union of fn(angle) over all angles."""
    return Manifold.batch_boolean([fn(a) for a in angles], OpType.Add)


def holes(r_pcd, d, z0, z1, angles):
    """Union of axial round holes of diameter d on a pitch circle."""
    return pattern(lambda a: cyl(d / 2, z0, z1, *polar(r_pcd, a)), angles)


def every(n, start=0.0):
    """List of n equally spaced angles starting at start (deg)."""
    return [start + 360.0 * i / n for i in range(n)]


# ---------------------------------------------------------------- gears
def inv(a):
    """Involute function tan(a) - a."""
    return math.tan(a) - a


def tooth_outline(n, m, r_root, r_tip, half_angle_pitch):
    """Closed involute outline of n teeth (tooth centred on +X).

    r_root/r_tip are the inner/outer radii of the outline and
    half_angle_pitch is the half tooth angle at the pitch circle.
    for an internal ring this is the outline of the tooth *spaces*.
    returns an (k, 2) numpy array, counter-clockwise.
    """
    rp = n * m / 2
    rb = rp * math.cos(PA)

    def theta(r):
        # half tooth angle at radius r (radial below the base circle)
        a = math.acos(rb / max(r, rb))
        return max(half_angle_pitch + inv(PA) - inv(a), 0.002)

    pitch = 2 * math.pi / n
    t_root = theta(r_root)
    r_flank0 = max(r_root, rb)
    one = []
    one += [(r_root, a) for a in np.linspace(-pitch / 2, -t_root, 3)]
    one += [(r, -theta(r)) for r in np.linspace(r_flank0, r_tip, 7)[(0 if r_root < rb else 1):]]
    one += [(r_tip, a) for a in np.linspace(-theta(r_tip), theta(r_tip), 4)[1:-1]]
    one += [(r, theta(r)) for r in np.linspace(r_tip, r_flank0, 7)[:(None if r_root < rb else -1)]]
    one += [(r_root, a) for a in np.linspace(t_root, pitch / 2, 3)[:-1]]
    pts = [(r * math.cos(a + i * pitch), r * math.sin(a + i * pitch)) for i in range(n) for r, a in one]
    return np.array(pts)


def ext_gear(n, m, z0, z1, rot_deg=0.0):
    """External spur gear (ISO 53 basic rack, x = 0, thinned for backlash)."""
    rp = n * m / 2
    half = (math.pi * m / 2 - BACKLASH_HALF) / (2 * rp)
    pts = tooth_outline(n, m, rp - 1.25 * m, rp + m, half)
    return Manifold.extrude(CrossSection([pts]), z1 - z0).rotate((0, 0, rot_deg)).translate((0, 0, z0))


def ring_gear(n, m, r_od, z0, z1, rot_deg=0.0):
    """Internal ring gear with outer diameter 2*r_od (space widened for backlash)."""
    rp = n * m / 2
    half = (math.pi * m / 2 + BACKLASH_HALF) / (2 * rp)
    spaces = tooth_outline(n, m, rp - m, rp + 1.25 * m, half)
    cut = Manifold.extrude(CrossSection([spaces]), z1 - z0 + 2).translate((0, 0, z0 - 1))
    return cyl(r_od, z0, z1) - cut.rotate((0, 0, rot_deg))


def planet_rot(phi_deg, ns, np_):
    """Planet self-rotation (deg) so it meshes with a sun whose tooth is on +X."""
    return phi_deg + 180.0 + 180.0 / np_ + phi_deg * ns / np_


# ---------------------------------------------------------------- fasteners
def shcs(x, y, z_face, length, d, direction=1):
    """Socket head cap screw; head sits on z_face, shank goes along direction."""
    hd, hh = 1.67 * d, d
    head = cyl(hd / 2, z_face - direction * hh, z_face, x, y) if direction > 0 else cyl(hd / 2, z_face, z_face + hh, x, y)
    shank = cyl(d / 2, z_face, z_face + direction * length, x, y) if direction > 0 else cyl(d / 2, z_face - length, z_face, x, y)
    return head + shank


def csk(x, y, z_face, length, d, direction=1):
    """90 deg countersunk screw flush with z_face; length is overall."""
    hd, hh = 2 * d, d / 2
    if direction > 0:
        head = Manifold.cylinder(hh, hd / 2, d / 2, segs(hd / 2)).translate((x, y, z_face))
        return head + cyl(d / 2, z_face + hh - 0.01, z_face + length, x, y)
    head = Manifold.cylinder(hh, d / 2, hd / 2, segs(hd / 2)).translate((x, y, z_face - hh))
    return head + cyl(d / 2, z_face - length, z_face - hh + 0.01, x, y)


def csk_hole(x, y, z_face, depth, d, direction=1):
    """Countersunk clearance hole matching csk()."""
    return csk(x, y, z_face - direction * 0.01, depth + 0.02, d + 0.2, direction)


# ---------------------------------------------------------------- bearings
def ball_bearing(d, D, B, z0, d1, D1, nballs, dball, seals=False):
    """Deep-groove ball bearing as inner ring, outer ring, ball set (+ seals)."""
    zc = z0 + B / 2
    rpitch = (d1 + D1) / 4
    groove = Manifold.revolve(CrossSection.circle(dball / 2 + 0.1, 32).translate((rpitch, 0)), segs(rpitch))
    groove = groove.translate((0, 0, zc))
    inner = tube(d1 / 2, d / 2, z0, z0 + B) - groove
    outer = tube(D / 2, D1 / 2, z0, z0 + B) - groove
    ball = Manifold.sphere(dball / 2, 20)
    balls = Manifold.compose([ball.translate((*polar(rpitch, a), zc)) for a in every(nballs)])
    parts = {"inner ring": inner, "outer ring": outer, "ball set": balls}
    if seals:
        parts["seal rear"] = tube(D1 / 2 - 0.15, d1 / 2 + 0.15, z0 + 0.3, z0 + 0.9)
        parts["seal front"] = tube(D1 / 2 - 0.15, d1 / 2 + 0.15, z0 + B - 0.9, z0 + B - 0.3)
    return parts


# ---------------------------------------------------------------- assembly
def build():
    """Return list of (name, material, manifold) for the whole actuator."""
    p = []

    def add(name, mat, solid):
        p.append((name, mat, solid))

    # gear data (spec section 7)
    s1, p1, r1, m1 = 18, 36, 90, 0.8
    s2, p2, r2, m2 = 18, 27, 72, 1.0
    a1 = (s1 + p1) * m1 / 2  # 21.6
    a2 = (s2 + p2) * m2 / 2  # 22.5
    planet_angles = every(3)
    post_angles = every(3, 60)

    # interface patterns (spec section 6 + 12)
    stator_pcd, stator_ang = 20.0, every(4, 45)  # 4 x m4 on pcd 40 (83xx family default)
    rotor_pcd, rotor_ang = 15.5, every(4)  # 4 x m3 on pcd 31 (eaglepower 83xx default)
    rotor_alt = (12.5, every(4, 45))  # 4 x m3 on pcd 25 (8308 alternate), cut in sun-1 only
    rear_ang = every(6, 30)  # plate->housing m3 and torso m4
    flange_ang, cover_ang = every(8), every(8, 22.5)
    cart_dowel_ang = [11.25, 191.25]
    hall_ang = 270.0

    # motor as measured with a vernier: mount face -> rotor hub face 32.5, od 92, front shaft stub d2.9 x 8.9,
    # rear cap d17.4 turns with the rotor (plain centre hole), flexible phase leads leave the rear face at r 32 (13 bundle)
    motor_r, motor_h = 46.0, 32.5
    stub_r, stub_h, cap_r = 1.45, 8.9, 8.7
    lead_ang = 180.0  # phase lead exit angle
    shim_t = 1.0  # fitted pack, 0.5..1.5; moves only the motor and sun-1
    z_mount = 10.0 + shim_t
    z_hub = z_mount + motor_h
    z_hub0 = 10.0 + 1.0 + motor_h  # hub face at the nominal 1.0 pack; housing and gearbox are drawn against it
    ds = z_hub - z_hub0  # motor + sun-1 offset from nominal
    dz = z_hub0 - 38.5  # gearbox shift against rev 1.3
    plug_r, z_plug, rad_z, rad_ang = 47.25, 2.0, 6.0, every(8, 22.5)  # plate plug in the housing bore, radial m3 ring
    z_ic = 5.0  # ic top face

    def radial(s, a, z):
        """Turn a part drawn along +z from z = -50 into one pointing inward from r 50 at angle a, height z."""
        return s.rotate((0, -90, 0)).translate((0, 0, z)).rotate((0, 0, a))

    # ---- rear plate, encoder, lid (Z 0-10)
    lid = cyl(29.9, 0, 2) - holes(17, 5.6, 0.5, 2.1, every(4)) - box(24, 31, -2, 2, -1, 3)
    lid = lid - box(25.5, 31, -7.5, 7.5, -1, 3).rotate((0, 0, lead_ang))  # notch beside the phase lead slot
    for a in every(4, 45):
        lid = lid - csk_hole(*polar(27, a), 0.0, 2.0, 2.0, 1)
    add("01 Encoder lid 7075-T651 D59.8x2", "7075-T6", lid)
    for i, a in enumerate(every(4, 45)):
        add(f"02.{i + 1} Screw M2x4 CSK lid", "Steel 12.9 fastener", csk(*polar(27, a), 0.0, 4.0, 2.0, 1))
    pcb = (box(-15, 15, -15, 15, 2.5, 4.1).rotate((0, 0, 45))) - holes(17, 2.7, 2, 5, every(4))  # m2.5 fine clearance: +/-0.1 centring
    add("03 Motor encoder PCB 30x30x1.6 (AS5047P)", "Electronics", pcb)
    add("04 AS5047P IC (TSSOP-14 envelope)", "Electronics", box(-2.5, 2.5, -2.2, 2.2, 4.1, z_ic))
    for i, a in enumerate(every(4)):
        x, y = polar(17, a)
        add(f"05.{i + 1} Screw M2.5x5 pan PCB", "Steel 12.9 fastener", cyl(2.5, 0.75, 2.5, x, y) + cyl(1.25, 2.49, 7.5, x, y))
    z_mag = z_mount - 4.75  # holder length 4.75: magnet-ic gap 1.25 at the nominal pack, 0.75..1.75 over the shim range
    holder = cyl(5, z_mag, z_mount) - cyl(3, z_mag - 0.1, z_mag + 2.5) + cyl(1.4, z_mount - 0.01, z_mount + 2.0)
    add("06 Magnet holder 7075-T651 D10, pin D2.8 into the rotor cap", "7075-T6", holder)
    add("07 Encoder magnet D6x2.5 diametric", "NdFeB magnet", cyl(3, z_mag, z_mag + 2.5))
    plate = cyl(50, 0, z_plug) + cyl(plug_r, z_plug - 0.01, 10)  # d100 seat rim + d94.5 k6 plug
    plate = plate - cyl(30.05, -1, 2) - cyl(25, 1.9, 6.0) - cyl(7, 5.9, 11)
    plate = plate - cyl(9.75, 8.5, 10.1)  # relief for the rotating d17.4 cap
    plate = plate + holes(17, 5.0, 4.1, 6.05, every(4)) - holes(17, 2.5, 4.0, 8.0, every(4))  # pcb bosses m2.5
    plate = plate - holes(27, 2.0, 1.9, 6.0, every(4, 45))  # lid m2 tapped
    plate = plate - holes(38, 5.0, -1, 7.0, rear_ang) - holes(38, 4.0, -1, 6.0, [120, 300])  # torso helicoil m4 + dowel
    plate = plate - pattern(lambda a: radial(cyl(1.5, -plug_r - 1, -41.25), a, rad_z), rad_ang)  # radial m3 tapped 6 deep
    grooves = [box(24, 57, -2, 2, -1, 3.0),  # encoder cable groove
               box(25, 57, -7.5, 7.5, -1, 5).rotate((0, 0, lead_ang))]  # phase lead rear groove
    plate = plate - grooves[0] - grooves[1] - box(25, 39, -7.5, 7.5, -1, 11).rotate((0, 0, lead_ang))  # lead slot through
    plate = plate - tube(40, 26, 7.5, 10.1)  # front lightening pocket
    for a in stator_ang:
        plate = plate - csk_hole(*polar(stator_pcd, a), 6.0, 4.0, 4.0, 1)
    add("08 Rear mount plate 7075-T6 (D100 rim + D94.5 plug)", "7075-T6", plate)
    for i, a in enumerate(rad_ang):
        add(f"09.{i + 1} Screw M3x8 CSK radial housing->plate", "Steel 12.9 fastener", radial(csk(0, 0, -50, 8.0, 3.0, 1), a, rad_z))
    for i, a in enumerate(stator_ang):
        add(f"11.{i + 1} Screw M4x10 CSK stator", "Steel 12.9 fastener", csk(*polar(stator_pcd, a), 6.0, 10.0, 4.0, 1))
    shim = tube(25, 9.75, 10.0, z_mount) - holes(stator_pcd, 4.5, 9.9, z_mount + 0.1, stator_ang)
    add("48 Motor shim pack 2x0.5 D50/D19.5", "Spring steel", shim)

    # ---- motor envelope (mount face z_mount, hub face z_hub)
    stator = cyl(motor_r, z_mount, z_mount + 3) + cyl(43, z_mount + 3, z_hub - 3)
    stator = stator - cyl(cap_r + 0.3, z_mount - 1, z_hub) - holes(stator_pcd, 4.0, z_mount - 0.1, z_mount + 6, stator_ang)
    add("12 LA8308 stator + base (envelope, measured)", "Motor envelope", stator)
    bell = tube(motor_r, 44.5, z_mount + 3.5, z_hub - 2) + cyl(motor_r, z_hub - 2, z_hub) - holes(rotor_pcd, 3.0, z_hub - 2.1, z_hub + 0.1, rotor_ang)
    bell = bell + cyl(stub_r, z_hub - 0.1, z_hub + stub_h) + cyl(cap_r, z_mount, z_mount + 3) - cyl(1.5, z_mount - 1, z_mount + 2.1)
    add("13 LA8308 rotor bell + front stub + rear cap (envelope, measured)", "Motor envelope", bell)
    add("14 LA8308 shaft D6", "52100 bearing steel", cyl(3, z_mount + 3, z_hub - 2))

    # ---- housing (Z 2-84+dz): d100 tube, d94.5 bore open at the rear over the plate plug
    zp = z_hub0 + 1.5  # partition rear face: 1.5 axial gap to the rotor hub face
    h = cyl(50, z_plug, 84 + dz) - cyl(plug_r, z_plug - 1, zp) - cyl(20.5, zp - 1, 43 + dz)
    h = h - cyl(42.5, 42.5 + dz, 59.7 + dz) - cyl(44.5, 59.7 + dz, 84.1 + dz)
    h = h - pattern(lambda a: box(44, 51, -1.5, 1.5, 19, 39).rotate((0, 0, a)), every(12, 15))
    # csk centres 0.1 forward of the plate threads so tightening draws the housing onto the plate rim
    h = h - pattern(lambda a: radial(csk_hole(0, 0, -50, 2.8, 3.0, 1), a, rad_z + 0.1), rad_ang) - grooves[0] - grooves[1]
    h = h - pattern(lambda a: box(37.5, 42.6, -1.5, 1.5, 41.0 + dz, 42.6 + dz).rotate((0, 0, a)), [45, 225])  # ring-1 dowel radial slots
    h = h - holes(46.5, 3.0, 76.0 + dz, 84.1 + dz, flange_ang)  # cartridge flange m3 tapped
    h = h - pattern(lambda a: box(44.4, 49.5, -2.0, 2.0, 79.5 + dz, 84.1 + dz).rotate((0, 0, a)), cart_dowel_ang)
    add("15 Housing one-piece 7075-T6", "7075-T6", h)

    # gearbox parts below are drawn at their rev 1.3 z and moved forward by dz as one block
    n_gear = len(p)

    # ---- stage 1 (6:1, m0.8)
    ring1 = ring_gear(r1, m1, 42.5, 42.5, 57.85, 180.0 / r1) - holes(39.75, 3.0, 42.4, 49.5, [45, 225])
    add("16 Ring-1 90T m0.8 (42CrMo4 nitrided)", "42CrMo4 nitrided", ring1)
    for i, a in enumerate([45, 225]):
        add(f"17.{i + 1} Dowel D3x8 ring-1 axial", "52100 bearing steel", cyl(1.5, 41.0, 49.0, *polar(39.75, a)))
    sun1 = cyl(20, 38.5, 41.5) + cyl(6, 41.4, 46.4) + ext_gear(s1, m1, 46.3, 56.7)
    sun1 = sun1 - cyl(9, 38.4, 39.0) - cyl(1.75, 38.4, 38.5 + stub_h + 1.6)  # hub-disc relief + bore over the shaft stub
    for pcd, angs in ((rotor_pcd, rotor_ang), rotor_alt):
        for a in angs:
            sun1 = sun1 - csk_hole(*polar(pcd, a), 41.5, 3.0, 3.0, -1)
    add("18 Sun-1 18T m0.8 flanged pinion (16MnCr5)", "16MnCr5 carburized", sun1.translate((0, 0, ds)))
    for i, a in enumerate(rotor_ang):
        add(f"19.{i + 1} Screw M3x5 CSK sun-1->rotor", "Steel 12.9 fastener", csk(*polar(rotor_pcd, a), 41.5 + ds, 5.0, 3.0, -1))
    add("20 Thrust washer C1 rear D48/42x0.3", "52100 bearing steel", tube(24, 21, 42.5, 42.8))
    c1r = cyl(30, 43, 46) + pattern(lambda a: cyl(5, 45.9, 57.0, *polar(22, a)), post_angles)
    c1r = c1r - cyl(9, 42, 47) - holes(a1, 8.0, 42.9, 46.1, planet_angles) - holes(22, 3.0, 49.0, 57.1, post_angles)
    add("21 Carrier-1 rear plate + posts (42CrMo4 Q&T)", "42CrMo4 Q&T", c1r)
    c1f = cyl(30, 57, 60) + cyl(7, 59.9, 71.1) + ext_gear(s2, m2, 71.0, 81.0)
    c1f = c1f - holes(a1, 8.0, 56.9, 60.1, planet_angles) - cyl(9.5, 56.9, 58.2)  # recess: 1.5 axial gap over the sun-1 tips
    for a in post_angles:
        c1f = c1f - csk_hole(*polar(22, a), 60.0, 3.0, 3.0, -1)
    add("22 Carrier-1 front plate + Sun-2 18T m1 (16MnCr5)", "16MnCr5 carburized", c1f)
    for i, a in enumerate(post_angles):
        add(f"23.{i + 1} Screw M3x10 CSK carrier-1", "Steel 12.9 fastener", csk(*polar(22, a), 60.0, 10.0, 3.0, -1))
    for i, phi in enumerate(planet_angles):
        x, y = polar(a1, phi)
        g = (ext_gear(p1, m1, 46.5, 56.5, planet_rot(phi, s1, p1)) - cyl(6, 46, 57)).translate((x, y, 0))
        add(f"24.{i + 1} Planet-1 36T m0.8 (16MnCr5)", "16MnCr5 carburized", g)
        add(f"25.{i + 1} HK0810 needle bearing", "Bearing (purchased)", tube(6, 4, 46.5, 56.5).translate((x, y, 0)))
        add(f"26.{i + 1} Planet pin-1 D8x17 h6 52100", "52100 bearing steel", cyl(4, 43.0, 60.0, x, y))
        add(f"27.{i + 1} Thrust washer D14/8.2x0.3 rear", "52100 bearing steel", (tube(7, 4.1, 46.2, 46.5)).translate((x, y, 0)))
        add(f"28.{i + 1} Thrust washer D14/8.2x0.3 front", "52100 bearing steel", (tube(7, 4.1, 56.5, 56.8)).translate((x, y, 0)))

    # ---- preload spring, output bearings, cartridge + stage 2 (5:1, m1)
    wave = tube(42.4, 36.58, 0, 0.76).warp(lambda v: (v[0], v[1], v[2] + 0.945 * (1 - math.cos(4 * math.atan2(v[1], v[0])))))
    add("29 Wave spring Smalley SSB-0335 (2.65 at nominal geometry)", "Spring steel", wave.translate((0, 0, 57.85)))
    add("30 Thrust washer C1 front D40/24x0.3", "52100 bearing steel", tube(20, 12, 60.2, 60.5))
    brg = dict(d=65, D=85, B=10, d1=70.0, D1=79.6, nballs=24, dball=4.6)
    for k, v in ball_bearing(z0=60.5, seals=True, **brg).items():
        add(f"31 Rear 61813-2Z (floating outer ring) {k}", "Bearing (purchased)", v)
    c2r = cyl(32.5, 60.5, 70.5) + pattern(lambda a: cyl(7.5, 70.4, 81.5, *polar(27, a)), post_angles)
    c2r = c2r - cyl(11.5, 60, 71) - holes(a2, 8.0, 64.5, 70.6, planet_angles) - holes(27, 4.0, 73.5, 81.6, post_angles)
    c2r = c2r - holes(a2, 3.0, 60.4, 64.6, planet_angles)  # pin seat shoulder, d3 vent + punch-out
    c2r = c2r - tube(40, 32.5, 60, 70.5) - tube(29.5, 21, 60.4, 63.5)  # inner-ring zone clear + lightening groove
    add("32 Carrier-2 rear half (hub D65 + posts, 42CrMo4 Q&T)", "42CrMo4 Q&T", c2r)
    cart = cyl(44.5, 60.0, 84.0) + cyl(50, 84.0, 91.5) - cyl(42.5, 59.9, 91.6)
    cart = cart + ring_gear(r2, m2, 42.5, 70.8, 81.2)
    cart = cart - holes(46.5, 3.4, 83.9, 91.6, flange_ang) - holes(46.5, 5.8, 88.3, 91.6, flange_ang)
    cart = cart - holes(46.6, 2.5, 86.5, 91.6, cover_ang) - holes(47, 4.0, 83.9, 88.0, cart_dowel_ang)
    add("33 Bearing cartridge + Ring-2 72T m1 (42CrMo4 nitrided)", "42CrMo4 nitrided", cart)
    for i, a in enumerate(flange_ang):
        add(f"34.{i + 1} Screw M3x10 SHCS cartridge->housing", "Steel 12.9 fastener", shcs(*polar(46.5, a), 88.3, 10.0, 3.0, -1))
    for i, a in enumerate(cart_dowel_ang):
        add(f"35.{i + 1} Dowel D4x8 cartridge anti-rotation", "52100 bearing steel", cyl(2, 80.0, 88.0, *polar(47, a)))
    for i, phi in enumerate(planet_angles):
        x, y = polar(a2, phi)
        g = (ext_gear(p2, m2, 71.0, 81.0, planet_rot(phi, s2, p2)) - cyl(6, 70, 82)).translate((x, y, 0))
        add(f"36.{i + 1} Planet-2 27T m1 (16MnCr5)", "16MnCr5 carburized", g)
        add(f"37.{i + 1} HK0810 needle bearing", "Bearing (purchased)", tube(6, 4, 71.0, 81.0).translate((x, y, 0)))
        add(f"38.{i + 1} Planet pin-2 D8x23 h6 52100", "52100 bearing steel", cyl(4, 64.5, 87.5, x, y))
        add(f"39.{i + 1} Thrust washer D14/8.2x0.3 rear", "52100 bearing steel", tube(7, 4.1, 70.7, 71.0).translate((x, y, 0)))
        add(f"40.{i + 1} Thrust washer D14/8.2x0.3 front", "52100 bearing steel", tube(7, 4.1, 81.0, 81.3).translate((x, y, 0)))
    for k, v in ball_bearing(z0=81.5, seals=True, **brg).items():
        add(f"41 Front 61813-2RS1 (located outer ring) {k}", "Bearing (purchased)", v)
    c2f = cyl(32.5, 81.5, 92.0) + cyl(39, 92.0, 95.5) - cyl(9, 81.4, 87.5) - cyl(18, 89.0, 95.6) - cyl(20, 93.5, 95.6)
    c2f = c2f - holes(26, 5.0, 87.5, 95.6, every(6, 30))  # m5 tapped in steel
    c2f = c2f - holes(a2, 8.0, 81.4, 87.8, planet_angles) - holes(27, 4.5, 81.4, 95.6, post_angles) - holes(27, 8.0, 91.5, 95.6, post_angles)
    mag = Manifold.cylinder(2.3, 1.5, 1.5, segs(1.5)).rotate((0, 90, 0)).translate((36.8, 0, 93.75))
    add("42 Carrier-2 front half + output flange D78 (42CrMo4 Q&T)", "42CrMo4 Q&T", c2f - mag)
    for i, a in enumerate(post_angles):
        add(f"43.{i + 1} Screw M4x16 SHCS carrier-2 halves", "Steel 12.9 fastener", shcs(*polar(27, a), 91.5, 16.0, 4.0, -1))
    add("44 Homing magnet D3x2 radial (in flange rim)", "NdFeB magnet", Manifold.cylinder(2.0, 1.5, 1.5, segs(1.5)).rotate((0, 90, 0)).translate((36.8, 0, 93.75)))

    # ---- front cover / bearing retainer (Z 91.5-94.5)
    cov = tube(50, 40, 91.5, 94.5)
    for a in cover_ang:
        cov = cov - csk_hole(*polar(46.6, a), 94.5, 3.0, 2.5, -1)
    hall_pocket = box(39.9, 41.6, -2.0, 2.0, 92.0, 94.6) + box(41.5, 50.1, -0.6, 0.6, 93.3, 94.6)
    add("45 Front cover / bearing retainer 7075-T6", "7075-T6", cov - hall_pocket.rotate((0, 0, hall_ang)))
    add("46 Hall homing sensor DRV5033FA SOT-23 (envelope)", "Electronics", box(40.2, 41.4, -1.45, 1.45, 92.6, 94.2).rotate((0, 0, hall_ang)))
    for i, a in enumerate(cover_ang):
        add(f"47.{i + 1} Screw M2.5x6 CSK cover->cartridge", "Steel 12.9 fastener", csk(*polar(46.6, a), 94.5, 6.0, 2.5, -1))
    p[n_gear:] = [(n, m, s.translate((0, 0, dz))) for n, m, s in p[n_gear:]]
    return p


# ---------------------------------------------------------------- checks
SHOULDER_MESHES = [("18 Sun-1", "24.1 Planet-1"), ("24.1 Planet-1", "16 Ring-1"),
                   ("22 Carrier-1 front", "36.1 Planet-2"), ("36.1 Planet-2", "33 Bearing cartridge"),
                   ("13 LA8308 rotor", "15 Housing"), ("18 Sun-1", "15 Housing"), ("18 Sun-1", "21 Carrier-1 rear"),
                   ("18 Sun-1", "22 Carrier-1 front"), ("13 LA8308 rotor", "08 Rear"),
                   ("06 Magnet holder", "08 Rear"), ("07 Encoder magnet", "04 AS5047P")]


def check(parts, meshes=SHOULDER_MESHES, motor_g=336):
    """Print watertight status, min gaps of the named pairs, overlaps between parts and mass totals."""
    bad = [n for n, _, s in parts if s.is_empty() or s.status().name != "NoError" or s.volume() <= 0]
    print(f"objects: {len(parts)}   invalid meshes: {bad or 'none'}")
    named = {n: s for n, _, s in parts}
    for a, b in meshes:
        sa = next(s for n, s in named.items() if n.startswith(a))
        sb = next(s for n, s in named.items() if n.startswith(b))
        print(f"min gap {a} <-> {b}: {sa.min_gap(sb, 3.0):.3f} mm")  # 3.0 = search cap
    boxes = [s.bounding_box() for _, _, s in parts]
    hits = []
    for i, j in combinations(range(len(parts)), 2):
        bi, bj = boxes[i], boxes[j]
        if any(bi[k] >= bj[k + 3] or bj[k] >= bi[k + 3] for k in range(3)):
            continue
        v = (parts[i][2] ^ parts[j][2]).volume()
        if v > 0.05:
            hits.append((v, parts[i][0], parts[j][0]))
    print(f"interferences > 0.05 mm3: {len(hits)}")
    for v, a, b in sorted(hits, reverse=True):
        print(f"  {v:9.2f} mm3  {a}  <->  {b}")
    mass = sum(s.volume() / 1000 * MATERIALS[m][1] for _, m, s in parts)
    print(f"modelled mass (excl. motor/electronics): {mass:.0f} g   + motor {motor_g} g = {mass + motor_g:.0f} g")
    lo = np.min([b[:3] for b in boxes], axis=0)
    hi = np.max([b[3:] for b in boxes], axis=0)
    print(f"envelope: X {lo[0]:.1f}..{hi[0]:.1f}  Y {lo[1]:.1f}..{hi[1]:.1f}  Z {lo[2]:.1f}..{hi[2]:.1f} mm")
    return hits


# ---------------------------------------------------------------- 3mf writer
def mesh_arrays(solid):
    """Return (vertices float32 (n,3), triangles uint32 (m,3)) of a manifold."""
    mesh = solid.to_mesh()
    return np.asarray(mesh.vert_properties, dtype=np.float32)[:, :3], np.asarray(mesh.tri_verts, dtype=np.uint32)


def write_3mf(parts, path, title=f"VAYN Shoulder Actuator Rev {REV}"):
    """Write parts as separate named, coloured mesh objects using lib3mf (reference 3MF writer)."""
    w = lib3mf.get_wrapper()
    model = w.CreateModel()
    model.SetUnit(lib3mf.ModelUnit.MilliMeter)
    model.GetMetaDataGroup().AddMetaData("", "Title", title, "string", False)
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


# object numbers printed as stand-ins, gears included. bought parts stay out.
PRINT_PARTS = {1, 6, 8, 15, 16, 18, 21, 22, 24, 32, 33, 36, 42, 45}


def part_no(name):
    """Return the leading object number of a part name."""
    return int(name.split()[0].split(".")[0])


def print_parts(parts):
    """Return the parts to 3d-print: machined stand-ins and gears."""
    return [p for p in parts if part_no(p[0]) in PRINT_PARTS]


def write_stl_zip(parts, path):
    """Write every given part as a binary STL (assembled position) into one zip."""
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
    write_stl_zip(print_parts(model), OUT.replace(".3mf", "_print.zip"))
