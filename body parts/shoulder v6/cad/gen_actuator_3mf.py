"""Build the VAYN shoulder v6 coaxial cycloid.

The motor turns the crank. The crank walks two discs around the ring pins.
The discs turn the output pins and the arm.

Z = 0 is the bolt face, on the motor hub. Negative Z is the motor and the
encoder. Positive Z is the cycloid and the arm flange.

Bought parts, as envelopes. The face named is the one that mates.
- LA8308: body 27.5 mm flat to flat, measured. Hub face is z = 0.
- SKF K 20x24x10: Fw 20, Ew 24, width 10. No inner ring. The journal is the
  inner race and the disc bore is the outer race.
  https://www.skf.com/group/products/rolling-bearings/roller-bearings/needle-roller-bearings/needle-roller-and-cage-assemblies/productid-K%2020X24X10
- SKF 61906: 30 x 47 x 9. Shaft abutment da 32 to 34. Housing abutment Da max 45.
  https://www.skf.com/products/rolling-bearings/ball-bearings/deep-groove-ball-bearings/productid-61906-2RS1
- ISO 4762 M2: head diameter 3.8, head height 2.0.
- ISO 10642 M3: 90 degree head, diameter 6.72, height 1.86. Length includes the head.

Every printed part is PETG. The 0.30 mm per side is the stand plug clearance,
so a bought bearing can enter a printed bore.

Bed faces, bore axis up unless noted:
- housing: motor end
- discs, flange, collar, washer, retainer, front plate, cover, arm flange: flat face
- crank: stem end
- rear carrier: plate face, pins up
- rear plate and encoder lid: outer face
- ring pins and cross pin: on the side

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
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from manifold3d import CrossSection, Manifold, OpType

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "elbow v0", "cad"))
import cycloid as cy

REV = "6.0"
HERE = os.path.dirname(os.path.abspath(__file__))
BED = 246.0  # 256 mm bed, 5 mm kept clear on each side
PETG = 1.27  # g/cm3
CLEAR = 0.30  # mm per side, PETG plug, from the stand

# cycloid. pin angle 0 matches disc_profile. v4 used 3.9 deg and the pins
# entered the lobes by about 1 mm at every crank angle.
RATIO = 45
ZP = RATIO + 1
PIN_R = 44.0
PIN_RAD = 2.0
PIN_ANG = 0.0
LAM = 0.55
ECC = LAM * PIN_R / ZP
DR = 0.08
OUT_R, OUT_N, OUT_PIN_R, OUT_PLAY = 30.0, 8, 3.0, 0.25
HOLE_R = OUT_PIN_R + ECC + OUT_PLAY
PIN_HOLE_R = PIN_RAD + CLEAR

# needles and journals. the print journal is 0.30 under Fw so the cage slides on.
# a metal crank is ground to Fw 20.
NEEDLE_FW, NEEDLE_EW, NEEDLE_U = 20.0, 24.0, 10.0
J_R = NEEDLE_FW / 2 - CLEAR
DISC_BORE_R = 12.2  # same bore as the printed v4 discs, so those discs stay

# 61906
BRG_BORE, BRG_OD, BRG_B = 30.0, 47.0, 9.0
SEAT_R = BRG_OD / 2 + CLEAR
HUB_RO = BRG_BORE / 2 - CLEAR  # bearing slides onto the hub
HUB_RI = 13.4
DA_R = 16.5  # shaft abutment 33 mm, inside da 32..34
HSG_ABUT_R = 22.0  # housing abutment 44 mm, under Da max 45

# v4 front stack, shifted +4 mm so the bearing retainer fits behind the plate
DZ = 4.0
Z_D1 = (16.2 + DZ, 23.2 + DZ)
Z_N1 = (14.7 + DZ, 24.7 + DZ)
Z_D2 = (27.4 + DZ, 34.4 + DZ)
Z_N2 = (25.9 + DZ, 35.9 + DZ)
Z_FRONT_PLATE = (34.6 + DZ, 37.4 + DZ)
Z_HOUSING_END = 34.5 + DZ
Z_BRG_FRONT = (37.8 + DZ, 46.8 + DZ)
Z_ARM = (47.0 + DZ, 53.0 + DZ)
Z_FLANGE0, Z_FLANGE1 = Z_ARM  # calc.py still reads these names

Z_BRG_REAR = (4.0, 13.0)
Z_RETAINER = (13.05, 15.65)
Z_REAR_PLATE = (17.3, 19.8)
Z_CRANK_FLANGE = (0.20, 3.30)
Z_SHOULDER = (3.30, 4.00)  # small shoulder the cage can still pass

# measured LA8308. z = 0 is the hub face.
MOUNT = -27.5
COVER_FACE = MOUNT - 13.2
LID_OUTER = COVER_FACE - 6.2
OD_R = 52.0

STEM_R = 8.0
NOSE_R = 6.0
COLLAR_RO = 10.5  # stops the rear cage, and still passes the other disc bore
FLANGE_R = 21.5  # clears the 44 mm abutment hole
M2_R, M2_K, M2_DK = 19.0, 2.0, 3.8
M3_DK = 6.72

MATERIALS = {
    "6082-T6": ("#B8BEC6", 2.70),
    "20MnCr5": ("#8A6F4E", 7.85),
    "52100 bearing steel": ("#9AA3AD", 7.81),
    "Bearing (purchased)": ("#D9B54A", 7.80),
    "Motor envelope": ("#5B7DB1", 0.0),
    "Electronics": ("#2E8B57", 0.0),
    "PETG": ("#C4A574", PETG),
}

# part numbers that are printed. bought bearings, the motor, and screws are not.
PRINT_NOS = {1, 2, 3, 4, 7, 8, 13, 15, 16, 19, 20, 21, 23, 25, 26, 27, 31}


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


def cone(r0, r1, z0, z1, x=0.0, y=0.0):
    """Cone or cylinder from z0 (radius r0) to z1 (radius r1)."""
    if z1 < z0:
        z0, z1, r0, r1 = z1, z0, r1, r0
    return Manifold.cylinder(z1 - z0, r0, r1, segs(max(r0, r1))).translate((x, y, z0))


def csk_hole(x, y, z_face, depth, d):
    """Countersink opening toward -z. Used by the encoder plate."""
    head = cone(d, d / 2 + 0.1, z_face, z_face + d / 2, x, y)
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
    """One cycloid disc on an eccentric journal. Same outline as v4."""
    pts = cy.disc_profile(PIN_R, ECC, PIN_RAD, RATIO, n=1200, dr=DR, rot_deg=rot_deg)
    body = extrude_polygon(pts, z0, z1).translate((shift_x, 0, 0))
    body = body - cyl(DISC_BORE_R, z0 - 0.2, z1 + 0.2, shift_x, 0)
    for a in every(OUT_N):
        x, y = polar(OUT_R, a)
        body = body - cyl(HOLE_R, z0 - 0.2, z1 + 0.2, x + shift_x, y)
    return body


def cage(z0, z1, x):
    """Real K 20x24x10 envelope, bore 20, outside 24."""
    return tube(NEEDLE_EW / 2, NEEDLE_FW / 2, z0, z1).translate((x, 0, 0))


def build():
    """Return (name, material, solid) for the coaxial actuator."""
    p = []

    def add(name, mat, solid):
        p.append((name, mat, solid))

    # the disc bore starts in front of the bearing, so the seat stays.
    # v4 cut the seat away by opening that bore at z = 4.
    h = cyl(OD_R, MOUNT, Z_HOUSING_END)
    h = h - cyl(47.0, MOUNT - 0.2, 0.0)
    h = h - cyl(24.0, -0.2, 3.55)  # flange cavity
    h = h - cyl(HSG_ABUT_R, 3.55, Z_BRG_REAR[0])  # rear shoulder, bearing stops here
    h = h - cyl(SEAT_R, Z_BRG_REAR[0], Z_BRG_REAR[1])
    h = h - cyl(40.30, Z_BRG_REAR[1], Z_RETAINER[1] + 0.2)  # retainer pocket
    h = h - cyl(46.4, Z_RETAINER[1] + 0.2, Z_HOUSING_END + 0.2)
    for i, a in enumerate(every(ZP, PIN_ANG)):
        x, y = polar(PIN_R, a)
        h = h - cyl(PIN_HOLE_R, 0.0, Z_REAR_PLATE[0] - 0.4, x, y)
        add(f"02.{i + 1} Ring pin D4", "52100 bearing steel",
            cyl(PIN_RAD, 0.2, Z_FRONT_PLATE[1], x, y))
    h = h - holes(49.5, 2.5, MOUNT - 0.2, MOUNT + 8, every(8, 22.5))
    h = h - holes(49.5, 2.5, Z_HOUSING_END - 8, Z_HOUSING_END + 0.2, every(8, 22.5))
    h = h - holes(32.0, 2.5, Z_BRG_REAR[1] - 6.0, Z_RETAINER[1] + 0.3, every(4, 22.5))
    add("01 Housing 6082-T6", "6082-T6", h)

    add("03 Cycloid disc A", "20MnCr5", disc(*Z_D1, ECC, 0.0))
    add("04 Cycloid disc B", "20MnCr5", disc(*Z_D2, -ECC, -180.0 / RATIO))
    add("05 Needle K20x24x10 A", "Bearing (purchased)", cage(*Z_N1, ECC))
    add("06 Needle K20x24x10 B", "Bearing (purchased)", cage(*Z_N2, -ECC))

    # one shaft. the Ø16 core runs through both journals. the flange is the
    # only piece that comes off, so the rear cage can slide on from the back.
    shaft = cyl(STEM_R, Z_CRANK_FLANGE[1] - 0.4, Z_N2[1] + 0.3)
    shaft = shaft + cyl(9.0, *Z_SHOULDER)  # cage still clears this step
    shaft = shaft + cyl(J_R, Z_N1[0] - 0.5, Z_N1[1] + 0.3, ECC, 0)
    shaft = shaft + cyl(J_R, Z_N2[0] - 0.5, Z_N2[1] + 0.3, -ECC, 0)
    shaft = shaft + cyl(NOSE_R, Z_N2[1] + 0.3, Z_N2[1] + 8.0)
    shaft = shaft - cyl(1.6, Z_CRANK_FLANGE[0] - 0.4, Z_CRANK_FLANGE[1] + 6.0)  # motor stub
    for a in every(3, 50):
        x, y = polar(4.5, a)
        shaft = shaft - cyl(1.25, Z_CRANK_FLANGE[1] - 0.2, Z_CRANK_FLANGE[1] + 5.0, x, y)
    # M4 thread inside the journal, and a counterbore so the head is not buried in the nose
    shaft = shaft - cyl(1.6, Z_N2[1] - 4.0, Z_N2[1] + 1.7)
    shaft = shaft - cyl(3.6, Z_N2[1] + 1.65, Z_N2[1] + 8.2)
    add("07 Crank shaft", "20MnCr5", shaft)

    collar = tube(COLLAR_RO, STEM_R + CLEAR, Z_SHOULDER[1], Z_N1[0] - 0.5)
    add("20 Collar", "20MnCr5", collar)
    washer = tube(COLLAR_RO, NOSE_R + CLEAR, Z_N2[1] + 0.45, Z_N2[1] + 1.7)
    add("21 Front washer", "20MnCr5", washer)
    add("28 Screw M4 washer", "52100 bearing steel",
        cyl(3.4, Z_N2[1] + 1.7, Z_N2[1] + 5.7) + cyl(1.5, Z_N2[1] - 2.5, Z_N2[1] + 1.7))

    flange = cyl(FLANGE_R, *Z_CRANK_FLANGE) - cyl(STEM_R + CLEAR, Z_CRANK_FLANGE[0] - 0.3, Z_CRANK_FLANGE[1] + 0.3)
    flange = flange - cyl(1.8, Z_CRANK_FLANGE[0] - 0.3, Z_CRANK_FLANGE[1] + 0.3)  # stub
    flange = flange - holes(M2_R, 2.4, Z_CRANK_FLANGE[0] - 0.2, Z_CRANK_FLANGE[1] + 0.2, every(4))
    # head pocket deep enough for a 2.0 mm M2 head, so the head stays inside the face
    flange = flange - holes(M2_R, 4.4, Z_CRANK_FLANGE[1] - 2.25, Z_CRANK_FLANGE[1] + 0.1, every(4))
    for i, a in enumerate(every(4)):
        x, y = polar(M2_R, a)
        head_z0 = Z_CRANK_FLANGE[1] - 2.25
        screw = cyl(0.9, -4.2, head_z0, x, y) + cyl(M2_DK / 2 - 0.15, head_z0, head_z0 + M2_K, x, y)
        add(f"22.{i + 1} Screw M2 crank to rotor", "52100 bearing steel", screw)
    for i, a in enumerate(every(3, 50)):
        x, y = polar(4.5, a)
        flange = flange - cone(M3_DK / 2, 1.5, Z_CRANK_FLANGE[0], Z_CRANK_FLANGE[0] + 1.9, x, y)
        flange = flange - cyl(1.7, Z_CRANK_FLANGE[0] + 1.6, Z_CRANK_FLANGE[1] + 0.2, x, y)
        screw = cone(M3_DK / 2 - 0.2, 1.2, Z_CRANK_FLANGE[0] + 0.05, Z_CRANK_FLANGE[0] + 1.7, x, y)
        screw = screw + cyl(1.05, Z_CRANK_FLANGE[0] + 1.7, Z_CRANK_FLANGE[1] + 4.5, x, y)
        add(f"29.{i + 1} Screw M3 flange to shaft", "52100 bearing steel", screw)
    add("19 Crank flange", "20MnCr5", flange)

    pin_end = Z_FRONT_PLATE[1] - 2.05  # ends before the countersink
    pins = pattern(lambda a: cyl(OUT_PIN_R, Z_REAR_PLATE[0], pin_end, *polar(OUT_R, a)), every(OUT_N))
    plate = tube(36, HUB_RI, *Z_REAR_PLATE)
    hub_j = tube(HUB_RO, HUB_RI, Z_BRG_REAR[0], Z_BRG_REAR[1] + 0.10)
    hub_s = tube(DA_R, HUB_RI, Z_BRG_REAR[1] + 0.10, Z_REAR_PLATE[0])
    carrier = pins + plate + hub_j + hub_s
    for a in every(OUT_N):
        x, y = polar(OUT_R, a)
        carrier = carrier - cyl(1.25, pin_end - 5.2, pin_end + 0.2, x, y)
    add("08 Rear carrier", "20MnCr5", carrier)

    retainer = tube(40.0, HSG_ABUT_R, *Z_RETAINER)
    retainer = retainer - holes(32.0, 3.4, Z_RETAINER[0] - 0.2, Z_RETAINER[1] + 0.2, every(4, 22.5))
    for a in every(4, 22.5):
        retainer = retainer - cone(M3_DK / 2, 1.6, Z_RETAINER[1] - 1.95, Z_RETAINER[1] + 0.05, *polar(32.0, a))
    add("27 Bearing retainer", "6082-T6", retainer)
    for i, a in enumerate(every(4, 22.5)):
        x, y = polar(32.0, a)
        screw = cone(M3_DK / 2 - 0.2, 1.4, Z_RETAINER[1] - 1.8, Z_RETAINER[1] - 0.05, x, y)
        screw = screw + cyl(1.05, Z_BRG_REAR[1] - 5.5, Z_RETAINER[1] - 1.5, x, y)
        add(f"30.{i + 1} Screw M3 retainer", "52100 bearing steel", screw)

    front = tube(36, HUB_RI, *Z_FRONT_PLATE)
    # recess only the band in front of the outer ring. the screws stay in the full thickness.
    front = front - tube(26.0, DA_R, Z_FRONT_PLATE[1] - 1.2, Z_FRONT_PLATE[1] + 0.05)
    front = front + tube(DA_R, HUB_RI, Z_FRONT_PLATE[1] - 1.2, Z_BRG_FRONT[0] - 0.10)
    front = front + tube(HUB_RO, HUB_RI, Z_BRG_FRONT[0] - 0.10, Z_ARM[1])
    front = front - cyl(2.05, -22, 22).rotate((0, -90, 0)).translate((0, 0, (Z_ARM[0] + Z_ARM[1]) / 2))
    for i, a in enumerate(every(OUT_N)):
        x, y = polar(OUT_R, a)
        front = front - cyl(OUT_PIN_R + CLEAR, Z_FRONT_PLATE[0] - 0.2, pin_end, x, y)
        front = front - cyl(1.7, pin_end - 0.2, Z_FRONT_PLATE[1] + 0.2, x, y)
        front = front - cone(M3_DK / 2, 1.6, Z_FRONT_PLATE[1] - 1.95, Z_FRONT_PLATE[1] + 0.05, x, y)
        screw = cone(M3_DK / 2 - 0.2, 1.4, Z_FRONT_PLATE[1] - 1.8, Z_FRONT_PLATE[1] - 0.05, x, y)
        screw = screw + cyl(1.05, pin_end - 4.8, pin_end - 0.15, x, y)
        add(f"24.{i + 1} Screw M3 pin plate", "52100 bearing steel", screw)
    add("23 Front plate and hub", "20MnCr5", front)

    add("09 Rear output bearing 61906", "Bearing (purchased)", tube(BRG_OD / 2, BRG_BORE / 2, *Z_BRG_REAR))
    add("10 Front output bearing 61906", "Bearing (purchased)", tube(BRG_OD / 2, BRG_BORE / 2, *Z_BRG_FRONT))

    cover = cyl(OD_R, Z_HOUSING_END, Z_ARM[0])
    cover = cover - cyl(37.2, Z_HOUSING_END - 0.2, Z_BRG_FRONT[0])
    cover = cover - cyl(SEAT_R, Z_BRG_FRONT[0] - 0.2, Z_BRG_FRONT[1])
    # the hole in front of the bearing is the 44 mm abutment, so it meets the outer ring only
    cover = cover - cyl(HSG_ABUT_R, Z_BRG_FRONT[1], Z_ARM[0] + 0.2)
    for a in every(ZP, PIN_ANG):
        cover = cover - cyl(PIN_HOLE_R, Z_HOUSING_END - 0.2, Z_FRONT_PLATE[1] + 0.3, *polar(PIN_R, a))
    cover = cover - holes(49.5, 3.4, Z_HOUSING_END - 0.2, Z_HOUSING_END + 6, every(8, 22.5))
    add("15 Front cover", "6082-T6", cover)

    arm = cyl(39, *Z_ARM) - cyl(HUB_RO + CLEAR, Z_ARM[0] - 0.2, Z_ARM[1] + 0.2)
    arm = arm - cyl(20, Z_ARM[1] - 2, Z_ARM[1] + 0.2)
    arm = arm - holes(26, 4.2, Z_ARM[0] - 0.2, Z_ARM[1] + 0.2, every(6, 30))
    arm = arm - cyl(2.05, -22, 22).rotate((0, -90, 0)).translate((0, 0, (Z_ARM[0] + Z_ARM[1]) / 2))
    add("25 Arm flange", "20MnCr5", arm)
    add("26 Cross pin D4", "52100 bearing steel",
        cyl(2.0, -18, 18).rotate((0, -90, 0)).translate((0, 0, (Z_ARM[0] + Z_ARM[1]) / 2)))

    stator = cyl(46, MOUNT, 0) - cyl(8, MOUNT - 1, 1)
    add("11 LA8308 stator", "Motor envelope", stator)
    bell = cyl(46, -3, 0) + hex_prism(17.3, MOUNT - 6.7, MOUNT) + cyl(5, COVER_FACE, MOUNT - 6.6)
    bell = bell - holes(M2_R, 2.1, -6.0, 0.3, every(4))
    add("12 LA8308 rotor", "Motor envelope", bell)

    lead = 180.0
    enc = ((12.0, 45.0), (12.0, 225.0), (9.5, 135.0), (9.5, 315.0))
    z_face = MOUNT - LID_OUTER
    lid = cyl(29.9, 0, 2) - cyl(18, 0.5, 2.1)
    lid = lid - box(24, 31, -2, 2, -1, 3) - box(24, 31, -7.5, 7.5, -1, 3).rotate((0, 0, lead))
    lid = lid - holes(27, 2.4, -0.2, 2.2, every(4, 45))
    plate_e = cyl(OD_R, 0, 2) + cyl(OD_R, 1.99, z_face)
    plate_e = plate_e - cyl(30.05, -1, 2)
    plate_e = plate_e - box(-15.3, 15.3, -15.3, 15.3, 1.9, 6.3)
    plate_e = plate_e - cyl(5.5, 6.0, 12.7) - cyl(10.55, 12.2, z_face + 0.1)
    for r, a in enc:
        x, y = polar(r, a)
        plate_e = plate_e + cyl(3.5, 4.1, 6.4, x, y) - cyl(1.7, 4.0, 8.0, x, y)
    plate_e = plate_e - holes(27, 2.0, 1.9, 6.0, every(4, 45))
    plate_e = plate_e - box(24, OD_R + 1, -2, 2, -1, 3)
    plate_e = plate_e - box(24, OD_R + 1, -7.5, 7.5, -1, 5.5).rotate((0, 0, lead))
    plate_e = plate_e - box(24, 36, -7.5, 7.5, -1, z_face + 0.2).rotate((0, 0, lead))
    for a in every(4, 45):
        plate_e = plate_e - csk_hole(*polar(20, a), 8.0, 12.0, 4.0)
    plate_e = plate_e - holes(49.5, 3.4, -0.2, z_face + 0.2, every(8, 22.5))
    shift = (0, 0, LID_OUTER)
    add("13 Rear plate 6082-T6", "6082-T6", plate_e.translate(shift))
    add("16 Encoder lid", "6082-T6", lid.translate(shift))
    board = box(-15, 15, -15, 15, 2.5, 4.1)
    for r, a in enc:
        board = board - cyl(1.7, 2.4, 4.2, *polar(r, a))
    add("14 Meukron board", "Electronics", board.translate(shift))
    add("17 Encoder chip", "Electronics", box(-2.5, 2.5, -2.2, 2.2, 4.1, 5.2).translate(shift))
    return p


def fit_coupon():
    """A bearing bore and a journal, so the 0.30 mm clearance can be tried first."""
    block = box(0, 64, 0, 24, 0, 14) - cyl(SEAT_R, -1, 15, 16, 12)
    return block + cyl(J_R, 0, 10, 48, 12)


def part_no(name):
    """Leading part number, so 02.1 and 02.2 both count as 2."""
    return int(name.split()[0].split(".")[0])


def named(parts):
    """Map part name to solid."""
    return {n: s for n, _, s in parts}


def ix(a, b):
    """Intersection volume in mm3."""
    return Manifold.batch_boolean([a, b], OpType.Intersect).volume()


def radii_at(solid, z):
    """Min and max radius of the slice at z, or None."""
    polys = solid.slice(z).to_polygons()
    rs = [math.hypot(x, y) for poly in polys for x, y in poly]
    if not rs:
        return None
    return min(rs), max(rs)


def bbox(solid):
    """(xmin, ymin, zmin, xmax, ymax, zmax) from a manifold or a wrapper."""
    b = solid.bounding_box()
    if isinstance(b, tuple):
        return b
    return (b.min[0], b.min[1], b.min[2], b.max[0], b.max[1], b.max[2])


def measure(parts):
    """Return (report lines, problem lines). Problems use measured, low to high."""
    g = named(parts)
    housing = g["01 Housing 6082-T6"]
    shaft = g["07 Crank shaft"]
    collar = g["20 Collar"]
    washer = g["21 Front washer"]
    flange = g["19 Crank flange"]
    rear_brg = g["09 Rear output bearing 61906"]
    front_brg = g["10 Front output bearing 61906"]
    carrier = g["08 Rear carrier"]
    retainer = g["27 Bearing retainer"]
    front = g["23 Front plate and hub"]
    cover = g["15 Front cover"]
    disc_a = g["03 Cycloid disc A"]
    disc_b = g["04 Cycloid disc B"]
    report, problems = [], []

    def gap_of(moving, fixed, direction, limit=3.0):
        """How far moving must travel along z before it hits fixed."""
        def hit(dist):
            return ix(moving.translate((0, 0, direction * dist)), fixed) > 1.0
        if hit(0.0):
            return 0.0
        if not hit(limit):
            return None
        lo, hi = 0.0, limit
        for _ in range(16):
            mid = 0.5 * (lo + hi)
            if hit(mid):
                hi = mid
            else:
                lo = mid
        return hi

    # rear cage path. the shaft is open from the back. the collar closes it after.
    rear_cage = cage(0, NEEDLE_U, ECC)
    path_z = (6.0, 10.0, Z_N1[0])
    path_hit = max(ix(rear_cage.translate((0, 0, z)), shaft) for z in path_z)
    report.append(f"rear cage along the shaft: clash {path_hit:.1f} mm3")
    if path_hit > 1.0:
        problems.append(f"rear cage path: {path_hit:.1f} mm3, wanted 0 to 1")
    stop = ix(rear_cage.translate((0, 0, 8.0)), collar)
    report.append(f"collar stops the rear cage: clash {stop:.0f} mm3")
    if stop < 5.0:
        problems.append(f"collar stop: {stop:.0f} mm3, wanted 5 to 400")

    front_cage = cage(0, NEEDLE_U, -ECC)
    front_hit = ix(front_cage.translate((0, 0, Z_N2[0])), shaft)
    nose_hit = ix(front_cage.translate((0, 0, Z_N2[1] + 0.4)), shaft)
    report.append(f"front cage on its journal: clash {front_hit:.1f} mm3, on the nose {nose_hit:.1f} mm3")
    if front_hit > 1.0 or nose_hit > 1.0:
        problems.append(f"front cage path: journal {front_hit:.1f}, nose {nose_hit:.1f}, wanted 0 to 1")
    if ix(front_cage.translate((0, 0, Z_N2[1] - 0.2)), washer) < 5.0:
        problems.append("front washer does not stop the cage")

    seat = radii_at(housing, 8.0)
    report.append(f"housing bore at the rear bearing: r {seat[0]:.2f} to {seat[1]:.2f}")
    if seat[0] < SEAT_R - 0.05 or seat[0] > SEAT_R + 0.05:
        problems.append(f"rear bearing seat radius: {seat[0]:.2f}, wanted {SEAT_R:.2f} to {SEAT_R:.2f}")
    chamber = radii_at(housing, Z_D1[0] + 1.0)
    report.append(f"housing bore at disc A: r {chamber[0]:.2f}")
    if chamber[0] < 46.0:
        problems.append(f"disc bore: r {chamber[0]:.2f}, wanted 46.0 to 46.6")

    report.append(f"rear bearing in the housing: clash {ix(rear_brg, housing):.1f} mm3")
    report.append(f"front bearing in the cover: clash {ix(front_brg, cover):.1f} mm3")
    report.append(f"retainer in the housing: clash {ix(retainer, housing):.1f} mm3")
    if ix(rear_brg, housing) > 1 or ix(front_brg, cover) > 1 or ix(retainer, housing) > 1:
        problems.append("a bearing or the retainer intersects its seat")

    # pins against the discs. v4 at 3.9 deg was about 384 mm3.
    pins = [s for n, s in g.items() if n.startswith("02.")]
    pin_hit = sum(ix(s, disc_a) + ix(s, disc_b) for s in pins)
    red = cy.Reducer(ZP, PIN_R, PIN_RAD, ECC, DR, OUT_R, OUT_N, OUT_PIN_R, HOLE_R, n=1600)
    profile_gap = min(red.ring_clearance(0.0, "A").min(), red.ring_clearance(0.0, "B").min())
    report.append(f"ring pins in the discs: clash {pin_hit:.1f} mm3, profile gap {profile_gap:.3f} mm")
    if pin_hit > 1.0:
        problems.append(f"ring pin clash: {pin_hit:.1f} mm3, wanted 0 to 1")
    if profile_gap < 0.05:
        problems.append(f"ring profile gap: {profile_gap:.3f}, wanted 0.05 to 0.20")

    screw_hit = 0.0
    for n, s in g.items():
        if n.startswith("24."):
            screw_hit += ix(s, carrier) + ix(s, front)
        if n.startswith("29."):
            screw_hit += ix(s, flange) + ix(s, shaft)
        if n.startswith("22."):
            screw_hit += ix(s, flange)
        if n.startswith("28"):
            screw_hit += ix(s, shaft) + ix(s, washer)
        if n.startswith("30."):
            screw_hit += ix(s, retainer) + ix(s, housing)
    report.append(f"screws inside the parts they pass through: clash {screw_hit:.1f} mm3")
    if screw_hit > 8.0:
        problems.append(f"screw clash: {screw_hit:.1f} mm3, wanted 0 to 8")

    head = g["22.1 Screw M2 crank to rotor"]
    head_z = bbox(head)[5]
    face_z = bbox(flange)[5]
    brg_z = bbox(rear_brg)[2]
    report.append(f"M2 head ends z {head_z:.2f}, flange face z {face_z:.2f}, bearing starts z {brg_z:.2f}")
    if head_z > face_z - 0.05:
        problems.append(f"M2 head z {head_z:.2f} is past the flange face {face_z:.2f}")
    if brg_z - head_z < 0.5:
        problems.append(f"M2 head to bearing: {brg_z - head_z:.2f} mm, wanted 0.50 to 2")

    hub_gap = gap_of(carrier, rear_brg, -1)
    report.append(f"hub shoulder to rear bearing: {hub_gap:.2f} mm" if hub_gap is not None else "hub shoulder misses the bearing")
    if hub_gap is None or not 0.05 <= hub_gap <= 0.25:
        problems.append(f"hub shoulder gap: {hub_gap}, wanted 0.05 to 0.25")

    # outer ring band of the front plate should stay well clear of the bearing
    outer = tube(23.5, 21.0, *Z_BRG_FRONT)
    outer_gap = gap_of(front, outer, 1)
    report.append(f"front plate to the outer ring: {outer_gap:.2f} mm" if outer_gap else "front plate misses the outer ring")
    if outer_gap is None or outer_gap < 1.0:
        problems.append(f"front plate to outer ring: {outer_gap}, wanted 1.00 to 3")

    shells = len([s for s in shaft.decompose() if s.volume() > 1])
    report.append(f"crank shaft is {shells} solid")
    if shells != 1:
        problems.append(f"crank shaft solids: {shells}, wanted 1 to 1")
    gap_z = (Z_N1[1] + Z_N2[0]) / 2
    bridge = radii_at(shaft, gap_z)
    report.append(f"shaft between the journals: r {bridge[0]:.2f} to {bridge[1]:.2f}" if bridge else "shaft between the journals: none")
    if bridge is None or bridge[1] < STEM_R - 0.05:
        problems.append("no core between the two journals")
    journal = radii_at(shaft, (Z_N1[0] + Z_N1[1]) / 2)
    # the slice radius about the origin, not the journal axis. report the max.
    report.append(f"crank slice at the rear journal: r {journal[0]:.2f} to {journal[1]:.2f}")

    for n, _, s in parts:
        if part_no(n) in PRINT_NOS and s.volume() < 10:
            problems.append(f"{n} has no volume")
    return report, problems


def mesh_arrays(solid):
    """Vertices and triangles of a manifold."""
    mesh = solid.to_mesh()
    return np.asarray(mesh.vert_properties, dtype=np.float32)[:, :3], np.asarray(mesh.tri_verts, dtype=np.uint32)


def write_3mf(items, path):
    """Write named meshes. items are (name, solid) already placed."""
    w = lib3mf.get_wrapper()
    model = w.CreateModel()
    model.SetUnit(lib3mf.ModelUnit.MilliMeter)
    group = model.AddBaseMaterialGroup()
    color = group.AddMaterial("PETG", w.RGBAToColor(196, 165, 116, 255))
    for name, solid in items:
        v, t = mesh_arrays(solid)
        obj = model.AddMeshObject()
        obj.SetName(name)
        obj.SetGeometry([lib3mf.Position((ctypes_float(p))) for p in v.tolist()],
                        [lib3mf.Triangle((ctypes_uint(f))) for f in t.tolist()])
        obj.SetObjectLevelProperty(group.GetResourceID(), color)
        model.AddBuildItem(obj, w.GetIdentityTransform())
    model.QueryWriter("3mf").WriteToFile(path)


def ctypes_float(p):
    """lib3mf position from a 3-list."""
    return (ctypes.c_float * 3)(*p)


def ctypes_uint(f):
    """lib3mf triangle from a 3-list."""
    return (ctypes.c_uint32 * 3)(*f)


def write_stl_zip(items, path):
    """Write one binary STL per placed solid."""
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        for name, solid in items:
            v, t = mesh_arrays(solid)
            tri = v[t]
            n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
            n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
            rec = np.zeros(len(t), dtype=[("n", "<f4", 3), ("v", "<f4", (3, 3)), ("a", "<u2")])
            rec["n"], rec["v"] = n, tri
            fname = re.sub(r"[^A-Za-z0-9._-]+", "_", name).strip("_") + ".stl"
            z.writestr(fname, b"\0" * 80 + struct.pack("<I", len(t)) + rec.tobytes())


def lay_on_bed(name, solid):
    """Put the part's bed face on z = 0. Pins lie on their side."""
    s = solid
    if name.startswith(("02.", "26 ")):
        s = s.rotate((90, 0, 0))
    b = bbox(s)
    return s.translate((-0.5 * (b[0] + b[3]), -0.5 * (b[1] + b[4]), -b[2]))


def pack(items):
    """Shelf-pack parts onto as many 246 mm plates as they need."""
    gap, margin = 4.0, 5.0
    plates, problems = [], []

    def blank():
        return {"x": margin, "y": margin, "row_h": 0.0, "items": []}

    plates.append(blank())
    order = sorted(items, key=lambda it: -(bbox(it[1])[3] - bbox(it[1])[0]) * (bbox(it[1])[4] - bbox(it[1])[1]))
    for name, solid in order:
        b = bbox(solid)
        w, d, h = b[3] - b[0], b[4] - b[1], b[5] - b[2]
        if max(w, d, h) > BED:
            problems.append(f"{name} is {max(w, d, h):.0f} mm, wanted 0 to {BED:.0f}")
            continue
        home = None
        for plate in plates:
            nx, ny, nh = plate["x"], plate["y"], plate["row_h"]
            if nx + w > margin + BED:
                ny = plate["y"] + plate["row_h"] + gap
                nx, nh = margin, 0.0
            if ny + d <= margin + BED:
                home = plate
                plate["x"], plate["y"], plate["row_h"] = nx, ny, nh
                break
        if home is None:
            home = blank()
            plates.append(home)
        b = bbox(solid)
        home["items"].append((name, solid.translate((home["x"] - b[0], home["y"] - b[1], -b[2]))))
        home["x"] += w + gap
        home["row_h"] = max(home["row_h"], d)
    return [p["items"] for p in plates if p["items"]], problems


def draw_section(parts, path):
    """XZ outline through the axis, plus a zoom on the flange and the bearing."""
    show = (
        ("01 Housing 6082-T6", "#5c6770"),
        ("15 Front cover", "#5c6770"),
        ("07 Crank shaft", "#8a6f4e"),
        ("19 Crank flange", "#c4a574"),
        ("20 Collar", "#d98c4a"),
        ("21 Front washer", "#d98c4a"),
        ("08 Rear carrier", "#6e5a40"),
        ("23 Front plate and hub", "#6e5a40"),
        ("27 Bearing retainer", "#2f6f9f"),
        ("09 Rear output bearing 61906", "#e0c15a"),
        ("10 Front output bearing 61906", "#e0c15a"),
        ("05 Needle K20x24x10 A", "#222222"),
        ("06 Needle K20x24x10 B", "#222222"),
        ("03 Cycloid disc A", "#7d9a62"),
        ("04 Cycloid disc B", "#7d9a62"),
    )
    g = named(parts)
    fig, axes = plt.subplots(1, 2, figsize=(11, 4.4))

    def outlines(solid):
        # 90 deg about x turns the y = 0 plane into z = 0. slice y is -old z.
        turned = solid.rotate((90, 0, 0))
        for poly in turned.slice(0.0).to_polygons():
            yield [p[0] for p in poly], [-p[1] for p in poly]

    for ax, xlim, zlim, title in (
        (axes[0], (-58, 58), (-2, 60), "section at y = 0"),
        (axes[1], (-28, 28), (-1, 22), "flange, collar, bearing seat"),
    ):
        for name, color in show:
            for xs, zs in outlines(g[name]):
                ax.fill(xs, zs, facecolor=color, edgecolor="black", lw=0.3, alpha=0.85, closed=True)
        ax.set_xlim(*xlim)
        ax.set_ylim(*zlim)
        ax.set_aspect("equal")
        ax.set_title(title)
        ax.set_xlabel("x mm")
        ax.set_ylabel("z mm")
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)


def print_items(parts):
    """Printed parts, one bed face each."""
    items = []
    for name, _, solid in parts:
        if part_no(name) not in PRINT_NOS:
            continue
        items.append((name, lay_on_bed(name, solid)))
    items.append(("31 Fit coupon", fit_coupon()))
    return items


def main():
    """Measure, write the report, and export only when the report is clean."""
    parts = build()
    report, problems = measure(parts)
    report.insert(0, "motion: the motor turns the crank, the crank walks two discs around the ring pins, and the discs turn the output pins and the arm")
    # ring pins are modelled as steel. the fit-check print of them is still PETG.
    petg_vol = sum(s.volume() for n, _, s in parts if part_no(n) in PRINT_NOS)
    solid_g = petg_vol / 1000.0 * PETG
    heavy = {}
    for n, _, s in parts:
        key = part_no(n)
        if key in (1, 2, 8, 15, 23):
            heavy[key] = heavy.get(key, 0.0) + s.volume()
    for key in (1, 2, 8, 15, 23):
        report.append(f"solid part {key}: {heavy.get(key, 0.0) / 1000.0 * PETG:.0f} g")
    report.append(f"solid PETG {solid_g:.0f} g")
    report.append("fit-check print is solid. no infill estimate.")
    report.append(f"arm face z {Z_ARM[1]:.1f} mm, was 53.0 on v4")
    text = "\n".join(report + problems)
    with open(os.path.join(HERE, "checks.txt"), "w", encoding="utf-8") as f:
        f.write(text + "\n")
    print(text)
    draw_section(parts, os.path.join(HERE, "section.png"))
    if problems:
        raise SystemExit(1)

    items = print_items(parts)
    plates, bed_problems = pack(items)
    for i, plate in enumerate(plates, 1):
        report.append(f"bed plate {i}: {len(plate)} parts")
    if bed_problems:
        problems.extend(bed_problems)
        with open(os.path.join(HERE, "checks.txt"), "w", encoding="utf-8") as f:
            f.write("\n".join(report + problems) + "\n")
        print("\n".join(bed_problems))
        raise SystemExit(1)
    for i, plate in enumerate(plates):
        fname = "actuator.3mf" if i == 0 else f"actuator_plate{i + 1}.3mf"
        write_3mf(plate, os.path.join(HERE, fname))
    write_stl_zip(items, os.path.join(HERE, "actuator_print.zip"))
    with open(os.path.join(HERE, "checks.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(report) + "\n")
    print("mesh exports written")

    # occ imports this module. when this file is run as __main__, that import is a
    # second copy, so the swapped constructors have to be copied back here.
    import gen_actuator_occ as occ
    import gen_actuator_3mf as model
    occ.use_occ_kernel()
    here = sys.modules[__name__]
    for name in ("cyl", "cone", "tube", "box", "pattern", "extrude_polygon", "hex_prism"):
        setattr(here, name, getattr(model, name))
    solids = build()
    occ.write_step(solids, os.path.join(HERE, "actuator.step"))


if __name__ == "__main__":
    main()
