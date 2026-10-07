"""Build the VAYN arm Rev 0 as exact OpenCascade solids and check it.

Upper arm (two ASA prints bolted at a mid-span collar, diamond windows front
and back), elbow clevis (front ring, hard stop, passive pin with an absolute
output encoder), lattice forearm with an integral cheek A, a separate cheek B
and the wrist interface for a future hand (no hand in v0). The shoulder
and the elbow actuator are rebuilt from their own generators and placed in
the arm frame, so every interface is checked against the real parts.
All dimensions come from arm_params.py. Writes, beside this script:
  arm.step          coloured, named assembly (shoulder + elbow + arm)
  arm.3mf           named, coloured meshes
  arm_stl.zip       every arm part, assembled position
  arm_print.zip     printed arm parts, in print orientation on the bed
  arm_preview.png   rendered views at 0, 90 and 140 deg flexion
  mass.txt          part masses and centres of mass (read by calc.py)

Run with the D: environment:
  D:\\VAYN-CAD-env\\venv\\Scripts\\python.exe gen_arm.py
"""

import math
import os
import sys
import time

import cadquery as cq
import matplotlib
import numpy as np

import arm_params as p
from arm_params import ep

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from mpl_toolkits.mplot3d.art3d import Poly3DCollection  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "shoulder", "cad"))
import gen_actuator as el  # noqa: E402  (elbow generator, elbow/cad is on the path via arm_params)
import gen_actuator_3mf as g  # noqa: E402
import gen_actuator_occ as occ  # noqa: E402

OUT = os.path.join(HERE, "arm")
REV = "0"
g.MATERIALS.update({"NBR O-ring": ("#1A1A1A", 1.30)})
# printed part -> rotation (deg, x then y then z) that puts its bed face down
PRINT = {104: (90, 0, 0), 108: (90, 0, 0), 110: (90, 0, 0), 125: (0, -90, 0), 128: (-90, 0, 0),
         133: (90, 0, 0), 140: (90, 0, 0)}
MOVING = {125, 126, 127, 128, 129, 130, 131, 133, 139, 140, 141, 142, 143}  # turn with the forearm
ELBOW_SKIP = ("30.", "31.")  # elbow flange washers + m3 x 12: replaced by arm parts 116/117


# ---------------------------------------------------------------- frames
def flange_to_world(s):
    """Shoulder flange frame (z = world y) -> world."""
    return s.rotate((-90, 0, 0))


def elbow_to_world(s):
    """Elbow frame E (x fwd, y = s down, z = actuator axis) -> world, forearm at 0 deg."""
    return s.rotate((-90, 0, 0)).translate((0, p.Y_E0, p.Z_ELBOW))


def flex(s, theta):
    """Turn a forearm-side solid by theta deg of elbow flexion."""
    return s.translate((0, 0, -p.Z_ELBOW)).rotate((0, -theta, 0)).translate((0, 0, p.Z_ELBOW))


# ---------------------------------------------------------------- primitives
def octagon(u0, u1, v0, v1, c, c1=None):
    """Rectangle u0..u1 x v0..v1 with 45 deg corner chamfers (leg c, or c1 on the u1 side), as 8 (u, v) points."""
    c1 = c if c1 is None else c1
    return [(u0 + c, v0), (u1 - c1, v0), (u1, v0 + c1), (u1, v1 - c1), (u1 - c1, v1), (u0 + c, v1), (u0, v1 - c), (u0, v0 + c)]


def loft(sections):
    """Ruled loft through closed polygon sections given as lists of (x, y, z)."""
    wires = [cq.Wire.makePolygon([cq.Vector(*q) for q in sec], close=True) for sec in sections]
    return occ.Solid(cq.Solid.makeLoft(wires, True))


def prism(pts, z0, z1):
    """Straight extrusion of a closed (x, y) polygon from z0 to z1."""
    w = cq.Wire.makePolygon([cq.Vector(x, y, z0) for x, y in pts], close=True)
    return occ.Solid(cq.Solid.extrudeLinear(w, [], cq.Vector(0, 0, z1 - z0)))


def fillet_box(x0, x1, y0, y1, z0, z1, r, edges="|Z"):
    """Box with the selected edges (all when None) rounded to radius r."""
    s = cq.Workplane("XY").box(x1 - x0, y1 - y0, z1 - z0, centered=False).edges(edges).fillet(r).val()
    return occ.Solid(s).translate((x0, y0, z0))


def rounded_hex(af, r, z0, z1):
    """Hexagon prism across flats af, corners at 0 + 60k deg rounded to r."""
    s = cq.Workplane("XY").polygon(6, 2 * af / math.sqrt(3)).extrude(z1 - z0).edges("|Z").fillet(r).val()
    return occ.Solid(s).translate((0, 0, z0))


def teardrop(r, x, y, z0, z1):
    """Cylinder along z with a 45 deg point toward -x, so it prints with -x down and no support."""
    k = r / math.sqrt(2)
    return occ.cyl(r, z0, z1, x, y) + prism([(x - r * math.sqrt(2), y), (x - k, y - k), (x, y), (x - k, y + k)], z0, z1)


def diamond(au, av, r, w0, w1, origin, x_dir, normal):
    """Diamond window prism: half-diagonals au along x_dir and av across, corners rounded r, from w0 to w1 along normal."""
    wp = cq.Workplane(cq.Plane(origin, x_dir, normal)).workplane(offset=w0)
    s = wp.polyline([(au, 0), (0, av), (-au, 0), (0, -av)]).close().extrude(w1 - w0)
    return occ.Solid(s.edges(cq.selectors.ParallelDirSelector(cq.Vector(*normal))).fillet(r).val())


def tangent_point(px, py, r):
    """Tangent point on the circle r round the origin seen from (px, py), clockwise side."""
    a, b = math.atan2(py, px), math.acos(r / math.hypot(px, py))
    return r * math.cos(a - b), r * math.sin(a - b)


def ycyl(r, y0, y1, x=0.0, z=0.0):
    """Cylinder along +y between y0 and y1, centred at (x, z)."""
    return occ.cyl(r, y0, y1, x, -z).rotate((-90, 0, 0))


def along_y(s, x=0.0, z=0.0):
    """Turn a solid built along +z so it runs along +y, then move it to (x, z)."""
    return s.rotate((-90, 0, 0)).translate((x, 0, z))


def arc_slot(r, w, a0, a1, z0, z1):
    """Round-ended slot of width w on radius r from angle a0 to a1 (deg)."""
    pts = [(0.0, 0.0)] + [p.polar(2 * r, a) for a in np.linspace(a0, a1, 16)]
    s = occ.tube(r + w / 2, r - w / 2, z0, z1) ^ prism(pts, z0 - 1, z1 + 1)
    return s + occ.cyl(w / 2, z0, z1, *p.polar(r, a0)) + occ.cyl(w / 2, z0, z1, *p.polar(r, a1))


def holes(r_hole, z0, z1, r, angles):
    """Union of z cylinders of radius r_hole on radius r at each angle (elbow ring_of)."""
    return el.ring_of(lambda x, y: occ.cyl(r_hole, z0, z1, x, y), r, angles)


def insert(d_hole, d_thread, z_face, length, direction, x=0.0, y=0.0):
    """Heat-set insert envelope from z_face going along direction."""
    z0, z1 = (z_face, z_face + length) if direction > 0 else (z_face - length, z_face)
    return occ.tube(d_hole / 2, d_thread / 2, z0, z1).translate((x, y, 0))


def washer(w, z0, x=0.0, y=0.0):
    """Flat washer dict(od, id, t) lying on z0."""
    return occ.tube(w["od"] / 2, w["id"] / 2, z0, z0 + w["t"]).translate((x, y, 0))


# ---------------------------------------------------------------- upper arm
def beam_section(z, inner=False):
    """Upper-arm octagon section at world z (outer skin, or the cavity when inner)."""
    xb, xf, y1, c = p.beam_station(z)
    y0 = p.Y_BED
    if inner:
        t = p.BEAM_T
        xb, xf, y0, y1, c = xb + t, xf - t, y0 + t, y1 - t, c - t * (2 - math.sqrt(2))
    return [(u, v, z) for u, v in octagon(xb, xf, y0, y1, c)]


def joint_collar(z0, z1):
    """Octagon flange round the beam at the mid-span joint, open in the middle for cables."""
    xb, xf, _, _ = p.beam_station(p.Z_JOINT)
    s = prism(octagon(xb - p.TAB_W, xf + p.TAB_W, p.Y_BED, p.BEAM_Y1, p.TAB_C), z0, z1)
    return s - occ.box(xb + p.TAB_IN, xf - p.TAB_IN, p.Y_BED + p.BEAM_T, p.BEAM_Y1 - p.BEAM_T, z0 - 1, z1 + 1)


def beam_windows(zone):
    """Diamond windows through the front and back beam walls for one (tip z, tip z, count) zone."""
    q = p.UA_WIN
    sides = []
    for z in p.win_centres(*zone[:2], zone[2], q["a"]):
        xb, xf, _, _ = p.beam_station(z)
        sides += [(xf, z, -1.0), (xb, z, 1.0)]
    return occ.pattern(lambda v: diamond(q["a"], q["a"], q["r"], -2.0, 5.0, (v[0], q["y"], v[1]), (0, 0, 1), (v[2], 0, 0)), sides)


def joint_points():
    """World (x, y) of the joint bolts and of the joint dowels."""
    xb, xf, _, _ = p.beam_station(p.Z_JOINT)
    xs = (xb - p.TAB_W / 2, xf + p.TAB_W / 2)
    return [(x, y) for x in xs for y in p.TAB_BOLT_Y], [(x, p.TAB_DOWEL_Y) for x in xs]


def adapter():
    """6061 adapter: hexagon key into the upper arm, d40 spigot in the shoulder pilot, 6 x m5 + 6 x m4."""
    s = rounded_hex(p.AD_AF, p.AD_CORNER_R, 0.0, p.AD_T) + occ.cyl(p.AD_SPIGOT_R, -p.AD_SPIGOT_H, 0.0)
    s = s - occ.cyl(p.AD_BORE_R, -3, p.AD_T + 1) - holes(p.AD_M5_HOLE_R, -3, p.AD_T + 1, p.SH_M5_R, p.SH_M5_ANG)
    s = s - holes(2.0, -1, p.AD_T + 1, p.AD_M4_R, p.AD_M4_ANG)
    q = p.AD_POCKET
    s = s - occ.tube(q["groove"][1], q["groove"][0], p.AD_T - q["depth"], p.AD_T + 1) - holes(q["r"], p.AD_T - q["depth"], p.AD_T + 1, q["pcd_r"], q["ang"])
    return flange_to_world(s - holes(p.AD_RELIEF_R, -0.1, p.AD_RELIEF_DEPTH, p.SH_M4_HEAD_R, p.SH_M4_HEAD_ANG))


def upper_shoulder_half():
    """Upper arm, shoulder half: drum + hub plate (hex pocket), octagon shell beam, joint collar."""
    s = flange_to_world(occ.cyl(p.DRUM_R, p.Y_BED, p.DRUM_Y1)) + loft([beam_section(z) for z in p.BEAM_Z_UP])
    s = s - flange_to_world(occ.cyl(p.DRUM_R - p.DRUM_T, p.HUB_Y1, p.DRUM_Y1 + 1) + occ.tube(p.DRUM_R - p.DRUM_T, p.HUB_RIM["r"], p.HUB_RIM["y"], p.HUB_Y1 + 0.1))
    s = s - loft([beam_section(z, True) for z in (p.Z_CAV_TOP, p.Z_JOINT - 1)])
    s = s + flange_to_world(holes(4.0, p.HUB_RIM["y"], p.DRUM_Y1, p.CAP_SCREW_R, p.CAP_SCREW_ANG))
    s = s + joint_collar(p.Z_JOINT, p.Z_JOINT + p.TAB_H_UP)
    cut = rounded_hex(p.AD_AF + 2 * p.HEX_CLEAR, p.AD_CORNER_R + p.HEX_CLEAR, p.Y_BED - 1, p.AD_T)
    cut = cut + holes(p.M5_POCKET_R, p.AD_T - 0.01, p.M5_POCKET_Y1, p.SH_M5_R, p.SH_M5_ANG)
    cut = cut + holes(2.25, p.AD_T - 0.01, p.HUB_Y1 + 0.1, p.AD_M4_R, p.AD_M4_ANG) + occ.cyl(15.0, p.Y_BED - 1, p.HUB_Y1 + 0.1)
    cut = cut + holes(ep.INSERT["d_hole"] / 2, p.DRUM_Y1 - ep.INSERT["depth"], p.DRUM_Y1 + 1, p.CAP_SCREW_R, p.CAP_SCREW_ANG)
    d = p.DRUM_WIN
    for a in map(math.radians, d["ang"]):
        c, n = math.cos(a), math.sin(a)
        cut = cut + diamond(d["au"], d["av"], d["r"], -2.0, 6.0, (p.DRUM_R * c, p.DRUM_R * n, d["y"]), (-n, c, 0), (-c, -n, 0))
    s = s - flange_to_world(cut) - beam_windows(p.UA_WIN["zones"][0])
    s = s - occ.cyl(p.CABLE_EXIT_R, p.DRUM_R - 4, p.DRUM_R + 1, 0, p.CABLE_EXIT_Y).rotate((0, -90, 0))
    bolts, dowels = joint_points()
    for x, y in bolts:
        s = s - occ.cyl(2.25, p.Z_JOINT - 1, p.Z_JOINT + p.TAB_H_UP + 1, x, y)
    for x, y in dowels:
        s = s - occ.cyl(p.DOWEL4["d"] / 2, p.Z_JOINT - 1, p.Z_JOINT + p.TAB_H_UP + 1, x, y)
    return s


def cap():
    """Shoulder cap: spoked diaphragm over the drum, 4 x m3 countersunk on the spokes, decorative groove."""
    z1 = p.DRUM_Y1 + p.CAP_T
    r0, r1, d = p.CAP_GROOVE
    q = p.CAP_WIN
    spokes = occ.pattern(lambda a: occ.box(-60, 60, -q["spoke"] / 2, q["spoke"] / 2, p.DRUM_Y1 - 2, z1 + 2).rotate((0, 0, a)), p.CAP_SCREW_ANG[:2])
    win = occ.tube(q["r"][1], q["r"][0], p.DRUM_Y1 - 1, z1 + 1) - spokes
    win = occ.Solid(cq.Workplane().add(win.s).edges("|Z").fillet(q["r_fillet"]).val())
    s = occ.cyl(p.DRUM_R, p.DRUM_Y1, z1) - occ.tube(r1, r0, z1 - d, z1 + 1) - win
    for a in p.CAP_SCREW_ANG:
        s = s - g.csk_hole(*p.polar(p.CAP_SCREW_R, a), z1, p.CAP_T, 3.0, -1)
    return flange_to_world(s)


def ring_outline(z0, z1, grow=0.0):
    """Front-ring outline (disc + tab up the arm), grown by grow all round."""
    x0, x1, ytop = p.RING_TAB
    return occ.cyl(p.RING_R + grow, z0, z1) + fillet_box(x0 - grow, x1 + grow, ytop - grow, 0.0, z0, z1, p.RING_FILLET + grow)


def crown_pocket():
    """Lightening pocket in the crown between the cable channel and the ring inserts (world)."""
    q = p.CROWN_POCKET
    secs = []
    for z in (p.Z_CAV_BOT + 1, -208.0, -213.0, -226.0, -236.0, p.Z_ELBOW + 20):
        xb, xf, y1, _ = p.beam_station(z)
        top = min(q["y"][1], y1 - q["inset"])
        c = min(q["c"], (top - q["y"][0]) / 2 - 0.5)
        secs.append([(u, v, z) for u, v in octagon(xb + q["inset"], xf - q["inset"], q["y"][0], top, c)])
    return loft(secs) - elbow_to_world(occ.cyl(p.SADDLE_R + q["inset"], -10, 100))


def upper_elbow_half():
    """Upper arm, elbow half: shell beam flaring into the crown, saddle over the actuator, rear ear for the pin."""
    z0, z1 = p.EAR_Z
    x0, x1, ytop = p.EAR_BOX
    ear = occ.cyl(p.EAR_R, z0, z1) + occ.box(x0, x1, ytop, 0.0, z0, z1)
    s = loft([beam_section(z) for z in p.BEAM_Z_LOW]) + elbow_to_world(ear)
    s = s - loft([beam_section(z, True) for z in (p.Z_JOINT + 1, -196.0, p.Z_CAV_BOT)]) - crown_pocket() - beam_windows(p.UA_WIN["zones"][1])
    ch = p.CHANNEL
    s = s - occ.box(*ch["x"], *ch["y"], p.Z_ELBOW + ch["z_lo"], p.Z_CAV_BOT + 1)
    cut = occ.cyl(p.SADDLE_R, z1, 100.0) + occ.cyl(p.PIN["spigot_r"], z0 - 1, z1 + 1)
    cut = cut + holes(ep.INSERT["d_hole"] / 2, z0 - 0.01, z0 + ep.INSERT["depth"], p.PIN["screw_r"], p.PIN_SCREW_ANG)
    cut = cut + occ.box(-p.GROOVE["w"] / 2, p.GROOVE["w"] / 2, ytop - 10, 0.0, z1 - p.GROOVE["d"], z1 + 0.5)
    cut = cut + ring_outline(p.RING_Z0, p.RING_Z0 + 10, 0.2)
    for x, y in p.RING_BOLTS:
        cut = cut + occ.cyl(p.INSERT_M4["d_hole"] / 2, p.RING_Z0 - p.INSERT_M4["depth"], p.RING_Z0 + 0.1, x, y)
    s = s - elbow_to_world(cut) + joint_collar(p.Z_JOINT - p.TAB_H_LOW, p.Z_JOINT)
    bolts, dowels = joint_points()
    for x, y in bolts:
        s = s - occ.cyl(p.INSERT_M4["d_hole"] / 2, p.Z_JOINT - p.INSERT_M4["depth"], p.Z_JOINT + 1, x, y)
    for x, y in dowels:
        s = s - occ.cyl(p.DOWEL4["d"] / 2, p.Z_JOINT - p.DOWEL4["l"] / 2 - 0.5, p.Z_JOINT + 1, x, y)
    return s


def front_ring():
    """6061 front ring (elbow frame): holds the actuator cover flange to the crown, carries the stop pin."""
    pin = p.polar(p.STOP_R, p.STOP_PSI)
    s = ring_outline(p.RING_Z0, p.RING_Z1) + occ.cyl(p.STOP_BOSS["r"], p.RING_Z1 - 0.1, p.RING_Z1 + p.STOP_BOSS["h"], *pin)
    s = s - occ.cyl(p.RING_ID_R, p.RING_Z0 - 1, p.RING_Z1 + 1)
    s = s - holes(ep.D_M3_CLEAR / 2, p.RING_Z0 - 1, p.RING_Z1 + 1, ep.R_FLANGE_SCREW, flange_angles())
    s = s - occ.cyl(p.STOP_PIN["d"] / 2, p.RING_Z0 - 1, p.RING_Z1 + p.STOP_BOSS["h"] + 1, *pin)
    for x, y in p.RING_BOLTS:
        s = s - g.csk_hole(x, y, p.RING_Z1, p.RING_T, 4.0, -1)
    q, fl = p.RING_WIN, flange_angles()
    for m in [(a + b) / 2 for a, b in zip(fl, fl[1:] + [fl[0] + 360.0])]:
        if q["psi"][0] < m % 360.0 < q["psi"][1]:
            s = s - arc_slot(q["r"], q["w"], m - q["half"], m + q["half"], p.RING_Z0 - 1, p.RING_Z1 + 1)
    return s


def flange_angles():
    """Elbow flange screw angles in the elbow frame (actuator turned by E_ROT)."""
    return [a + p.E_ROT for a in ep.ANG_FLANGE]


def passive_pin():
    """6061 passive pin (elbow frame): spigot in the ear, flange, 61804 journal, wire bore."""
    q = p.PIN
    s = occ.cyl(q["spigot_r"], q["z_flange"][1], q["z_spigot"]) + occ.cyl(q["flange_r"], *q["z_flange"])
    s = s + occ.cyl(q["shoulder_r"], p.Z_P_IN1, q["z_flange"][0]) + occ.cyl(p.BRG_P["d"] / 2, q["z_end"], p.Z_P_IN1)
    s = s - occ.cyl(q["bore_r"], q["z_end"] - 1, q["z_spigot"] + 1)
    for a in p.PIN_SCREW_ANG:
        s = s - g.csk_hole(*p.polar(q["screw_r"], a), q["z_flange"][0], q["z_flange"][1] - q["z_flange"][0], 3.0, 1)
    return s - holes(ep.D_M25_MAJOR / 2, q["z_end"] - 0.01, q["z_end"] + p.PIN_TAP_DEPTH, q["tap_r"], p.PIN_TAP_ANG)


def bracket():
    """6061 encoder bracket (elbow frame): clamps the 61804 inner ring, carries the output pcb."""
    b = p.BRACKET
    zp0, zb1 = b["z_plate"][0], b["z_boss"][1]
    s = occ.cyl(b["boss_r"], *b["z_boss"]) + occ.cyl(b["r"], *b["z_plate"]) - occ.cyl(b["hole_r"], zp0 - 1, zb1 + 1)
    for a in p.PIN_TAP_ANG:
        s = s - g.csk_hole(*p.polar(b["csk_r"], a), zp0, zb1 - zp0, 2.5, 1)
    s = s - holes(ep.D_M25_MAJOR / 2, zp0 - 0.01, b["z_plate"][1] + 0.01, p.PCB_OUT["hole_r"], g.every(4, p.PCB_OUT["ang0"]))
    w, length, d = b["groove"]
    return s - occ.box(-w / 2, w / 2, -length, 0.0, zp0 - 0.01, zp0 + d)


# ---------------------------------------------------------------- forearm (elbow frame)
def fa_section(s, inner=False):
    """Forearm octagon section at length s (outer skin, or the cavity when inner)."""
    z0, z1 = p.fa_z(s)
    x0, x1, c, c1 = p.FA_POST, p.fa_a(s), p.FA_C, p.FA_C
    if inner:
        t, cheek = p.FA_T, p.CHEEK_A_Z[1] - p.CHEEK_A_Z[0]
        w = cheek if s <= p.S_FULL else max(t, cheek - (cheek - t) * (s - p.S_FULL) / (p.S_WALL - p.S_FULL))
        c = c - t * (2 - math.sqrt(2))
        x0, x1, z0, z1, c1 = x0 + t, x1 - t, z0 + t, z1 - w, p.FA_ROOF_C if s <= p.S_NECK else c
    return [(u, s, v) for u, v in octagon(x0, x1, z0, z1, c, c1)]


def fa_windows():
    """Diamond windows through all four walls of the straight forearm tube (elbow frame)."""
    q, zc, h = p.FA_WIN, p.FA_ZC, p.FA_HALF_WRIST
    faces = [((p.FA_POST, zc), (1, 0, 0)), ((p.FA_A_WRIST, zc), (-1, 0, 0)), ((0.0, zc - h), (0, 0, 1)), ((0.0, zc + h), (0, 0, -1))]
    spots = [(x, s, z, nrm) for s in p.win_centres(*q["s"], q["n"], q["a"]) for (x, z), nrm in faces]
    return occ.pattern(lambda v: diamond(q["a"], q["a"], q["r"], -1.0, p.FA_T + 1.0, v[:3], (0, 1, 0), v[3]), spots)


def fa_window(s):
    """Open-trough window at length s: removes the anterior wall between the chamfer lips."""
    z0, z1 = p.fa_z(s)
    x0 = p.fa_a(s) - p.FA_T - 0.5
    return [(x0, s, z0 + p.FA_C), (60.0, s, z0 + p.FA_C), (60.0, s, z1 - p.FA_C), (x0, s, z1 - p.FA_C)]


def cheek_plate(r, tip, z0, z1):
    """Clevis cheek plate: disc r round the axis, flank tangent to the disc up to tip (x, s), flat posterior edge."""
    tx, ty = tangent_point(*tip, r)
    s = occ.cyl(r, z0, z1) + prism([(p.FA_POST, 0.0), (p.FA_POST, tip[1]), tip, (tx, ty), (0.0, 0.0)], z0, z1)
    return s ^ occ.box(p.FA_POST, r + 1, p.CHEEK_A_TOP, tip[1] + 1, z0 - 1, z1 + 1)


def slot_ends():
    """Slot end-centre angles (forearm frame) where the o-rings touch at the hard stops."""
    d = math.degrees((p.SLOT_W - p.ORING_OD) / 2 / p.STOP_R)
    return p.STOP_PSI + p.THETA_MIN + d, p.STOP_PSI + p.THETA_MAX - d


def forearm():
    """Forearm + cheek A in one print: clevis, y-yoke neck, straight lattice tube, wrist block, hub boss, stop slot."""
    neck = list(np.arange(p.S_FULL, p.S_NECK + 0.1, p.FA_STEP))
    outer = loft([fa_section(v) for v in [30.0] + neck + [p.L_FOREARM]])
    za0, za1 = p.CHEEK_A_Z
    s = outer + cheek_plate(p.CHEEK_A_R, p.CHEEK_A_TIP, za0, za1)
    s = s - occ.cyl(p.FA_CUT_R, p.Z_CHEEK_B_IN - 1.5, za0)
    s = s - loft([fa_section(v, True) for v in [40.0] + neck + [p.S_NECK + 6.0, p.S_END]]) - loft([fa_window(v) for v in (30.0, p.S_FULL)])
    s = s + (occ.box(p.FA_POST, 60.0, p.S_FULL, p.S_NECK, p.FA_ZC - 1.25, p.FA_ZC + 1.25) ^ outer) - fa_windows()
    zf = p.BOSS_Z0 + p.BOSS_FACE
    s = s + occ.cyl(p.BOSS_R, p.BOSS_Z0, zf + 0.1) + (teardrop(p.BOSS_R, 0, 0, zf, za0 + 0.5) ^ occ.cyl(p.BOSS_R_MAX, zf, za0 + 0.5))
    bosses = occ.pattern(lambda q: teardrop(p.CHEEK_B_BOSS_R, *q, p.Z_CHEEK_B_IN, -3.0), p.CHEEK_B_JOINT)
    s = s + (bosses ^ outer) + ycyl(p.WRIST["spigot_r"], p.L_FOREARM - 0.5, p.L_FOREARM + p.WRIST["spigot_h"], 0, p.FA_ZC)
    hub_ang = [a + p.E_ROT for a in ep.ANG_HUB_INSERT]
    s = s - holes(ep.D_M3_CLEAR / 2, p.BOSS_Z0 - 0.1, za1 + 0.1, ep.R_HUB_INSERT, hub_ang)
    s = s - holes(p.HUB_CBORE["d"] / 2, za1 - p.HUB_CBORE["depth"], za1 + 0.1, ep.R_HUB_INSERT, hub_ang)
    s = s - holes(ep.DOWEL_D / 2, p.BOSS_Z0 - 0.1, p.BOSS_Z0 + p.HUB_DOWEL["in_boss"], ep.R_HUB_INSERT, [a + p.E_ROT for a in ep.ANG_HUB_DOWEL])
    s = s - arc_slot(p.STOP_R, p.SLOT_W, *slot_ends(), za0 - 0.1, za0 + p.SLOT_DEPTH)
    r0, r1, d = p.CHEEK_GROOVE
    s = s - occ.tube(r1, r0, za1 - d, za1 + 1)
    for x, y in p.CHEEK_B_JOINT:
        s = s - occ.cyl(p.INSERT_M4["d_hole"] / 2, p.Z_CHEEK_B_IN - 0.1, p.Z_CHEEK_B_IN + p.INSERT_M4["depth"], x, y)
    for a in g.every(p.WRIST["n"], p.WRIST["ang0"]):
        x, z = p.polar(p.WRIST["pcd_r"], a)
        s = s - ycyl(ep.INSERT["d_hole"] / 2, p.L_FOREARM - ep.INSERT["depth"], p.L_FOREARM + 0.1, x, p.FA_ZC + z)
    return s - ycyl(p.WRIST["bore_r"], p.S_END - 1, p.L_FOREARM + 3, 0, p.FA_ZC)


def cheek_b():
    """Cheek B (elbow frame): carries the 61804 outer ring (slip fit, floats), bolted to the forearm."""
    z0, z1 = p.CHEEK_B_Z
    s = cheek_plate(p.CHEEK_B_R, p.CHEEK_B_TIP, z0, z1)
    s = s - occ.cyl(p.CHEEK_B_LIP["r"], p.CHEEK_B_LIP["z"] - 0.01, z1 + 0.1) - occ.cyl(p.BORE_P_R, z0 - 0.1, p.CHEEK_B_LIP["z"])
    for x, y in p.CHEEK_B_JOINT:
        s = s - occ.cyl(p.CHEEK_B_HOLE_R, z0 - 0.1, z1 + 0.1, x, y)
    return s - holes(ep.INSERT["d_hole"] / 2, z0 - 0.1, z0 + ep.INSERT["depth"], p.COVER["boss_pcd_r"], p.COVER_ANG)


def cover():
    """Encoder cover (elbow frame): cup over the output pcb, magnet boss, 3 counterbored screw bosses."""
    c = p.COVER
    z0, z1 = c["z_end"], p.RETAINER["z"][0]
    zw = z0 + 2.0
    s = occ.tube(c["r"], c["ri"], zw, z1) + occ.cyl(c["r"], z0, zw) + occ.cyl(c["mag_boss_r"], zw, p.Z_MAG_OUT[1])
    s = s + holes(c["boss_r"], z0, z1, c["boss_pcd_r"], p.COVER_ANG)
    s = s - occ.cyl(ep.MAG["d"] / 2, zw, p.Z_MAG_OUT[1] + 0.1)
    s = s - holes(ep.D_M3_CLEAR / 2, z0 - 0.1, z1 + 0.1, c["boss_pcd_r"], p.COVER_ANG)
    return s - holes(p.HUB_CBORE["d"] / 2, z0 - 0.1, c["seat"], c["boss_pcd_r"], p.COVER_ANG)


# ---------------------------------------------------------------- assembly
def build_arm():
    """Return list of (name, material, solid) for every arm part, in world, forearm at 0 deg."""
    parts = []

    def add(name, mat, solid, frame=None):
        parts.append((name, mat, frame(solid) if frame else solid))

    F, E = flange_to_world, elbow_to_world
    # ---- shoulder interface
    add("101 Adapter plate 6061-T6 (CNC)", "6061-T6", adapter())
    for i, a in enumerate(p.SH_M5_ANG):
        x, y = p.polar(p.SH_M5_R, a)
        add(f"102.{i + 1} Screw M5x12 ISO 4762 12.9 adapter->shoulder", "Steel 12.9 fastener",
            g.shcs(x, y, p.AD_T + p.WASHER_M5["t"], p.M5_SCREW_L, 5.0, -1), F)
        add(f"103.{i + 1} Washer M5 ISO 7089", "Steel 12.9 fastener", washer(p.WASHER_M5, p.AD_T, x, y), F)
    add("104 Upper arm, shoulder half (ASA)", "ASA", upper_shoulder_half())
    for i, a in enumerate(p.AD_M4_ANG):
        x, y = p.polar(p.AD_M4_R, a)
        add(f"105.{i + 1} Screw M4x16 ISO 4762 hub->adapter", "Steel 12.9 fastener",
            g.shcs(x, y, p.HUB_Y1 + p.WASHER_M4L["t"], p.M4_HUB_L, 4.0, -1), F)
        add(f"106.{i + 1} Washer M4 DIN 9021 hub", "Steel 12.9 fastener", washer(p.WASHER_M4L, p.HUB_Y1, x, y), F)
    for i, a in enumerate(p.CAP_SCREW_ANG):
        x, y = p.polar(p.CAP_SCREW_R, a)
        add(f"107.{i + 1} Insert RX-M3x5.7 cap", "Brass insert", insert(ep.INSERT["d_hole"], 3.0, p.DRUM_Y1, ep.INSERT["length"], -1, x, y), F)
        add(f"109.{i + 1} Screw M3x8 ISO 10642 cap", "Steel 12.9 fastener", g.csk(x, y, p.DRUM_Y1 + p.CAP_T, 8.0, 3.0, -1), F)
    add("108 Shoulder cap (ASA)", "ASA", cap())
    # ---- mid-span joint
    add("110 Upper arm, elbow half (ASA)", "ASA", upper_elbow_half())
    bolts, dowels = joint_points()
    z_top = p.Z_JOINT + p.TAB_H_UP
    for i, (x, y) in enumerate(bolts):
        add(f"111.{i + 1} Insert RX-M4x8.1 joint", "Brass insert", insert(p.INSERT_M4["d_hole"], 4.0, p.Z_JOINT, p.INSERT_M4["length"], -1, x, y))
        add(f"112.{i + 1} Screw M4x16 ISO 4762 joint", "Steel 12.9 fastener", g.shcs(x, y, z_top + p.WASHER_M4L["t"], p.M4_TAB_L, 4.0, -1))
        add(f"113.{i + 1} Washer M4 DIN 9021 joint", "Steel 12.9 fastener", washer(p.WASHER_M4L, z_top, x, y))
    for i, (x, y) in enumerate(dowels):
        add(f"114.{i + 1} Dowel D4x16 ISO 8734 joint", "52100 bearing steel", occ.cyl(2.0, p.Z_JOINT - 8.0, p.Z_JOINT + 8.0, x, y))
    # ---- front ring + hard stop
    add("115 Front ring 6061-T6 (CNC 4 mm)", "6061-T6", front_ring(), E)
    for i, a in enumerate(flange_angles()):
        x, y = p.polar(ep.R_FLANGE_SCREW, a)
        add(f"116.{i + 1} Screw M3x16 DIN 912 ring+cover->housing", "Steel 12.9 fastener",
            g.shcs(x, y, p.RING_Z1 + ep.WASHER_M3["t"], p.FLANGE_SCREW_L, 3.0, -1), E)
        add(f"117.{i + 1} Washer M3 ISO 7089 ring", "Steel 12.9 fastener", washer(ep.WASHER_M3, p.RING_Z1, x, y), E)
    for i, (x, y) in enumerate(p.RING_BOLTS):
        add(f"118.{i + 1} Insert RX-M4x8.1 crown", "Brass insert", insert(p.INSERT_M4["d_hole"], 4.0, p.RING_Z0, p.INSERT_M4["length"], -1, x, y), E)
        add(f"119.{i + 1} Screw M4x12 ISO 10642 ring->crown", "Steel 12.9 fastener", g.csk(x, y, p.RING_Z1, p.M4_RING_L, 4.0, -1), E)
    px, py = p.polar(p.STOP_R, p.STOP_PSI)
    add(f"120 Stop pin D5x{p.STOP_PIN['l']:.0f} ISO 8734", "52100 bearing steel", occ.cyl(p.STOP_PIN["d"] / 2, p.RING_Z0, p.RING_Z0 + p.STOP_PIN["l"], px, py), E)
    cs, rc = p.ORING["cs"], p.STOP_PIN["d"] / 2 + p.ORING["cs"] / 2
    for i in range(p.ORING["n"]):
        zc = p.RING_Z0 + p.STOP_PIN["l"] - cs * (i + 0.5)
        add(f"121.{i + 1} O-ring 4.5x1.5 NBR 70 stop", "NBR O-ring",
            occ.Solid(cq.Solid.makeTorus(rc, cs / 2, cq.Vector(px, py, zc), cq.Vector(0, 0, 1))), E)
    # ---- passive pin
    add("122 Passive pin 6061-T6 (turned)", "6061-T6", passive_pin(), E)
    q = p.PIN
    for i, a in enumerate(p.PIN_SCREW_ANG):
        x, y = p.polar(q["screw_r"], a)
        add(f"123.{i + 1} Insert RX-M3x5.7 ear", "Brass insert", insert(ep.INSERT["d_hole"], 3.0, p.EAR_Z[0], ep.INSERT["length"], 1, x, y), E)
        add(f"124.{i + 1} Screw M3x8 ISO 10642 pin->ear", "Steel 12.9 fastener", g.csk(x, y, q["z_flange"][0], p.L_PIN_SCREW, 3.0, 1), E)
    # ---- forearm + cheek A
    add("125 Forearm + cheek A (ASA)", "ASA", forearm(), E)
    za1 = p.CHEEK_A_Z[1]
    for i, a in enumerate(ep.ANG_HUB_INSERT):
        x, y = p.polar(ep.R_HUB_INSERT, a + p.E_ROT)
        add(f"126.{i + 1} Screw M3x16 DIN 912 cheek A->hub", "Steel 12.9 fastener",
            g.shcs(x, y, za1 - p.HUB_CBORE["depth"], p.HUB_SCREW_L, 3.0, -1), E)
    for i, a in enumerate(ep.ANG_HUB_DOWEL):
        z0 = p.BOSS_Z0 + p.HUB_DOWEL["in_boss"] - p.HUB_DOWEL["l"]
        add(f"127.{i + 1} Dowel D3x{p.HUB_DOWEL['l']:.0f} ISO 8734 cheek A/hub", "52100 bearing steel",
            occ.cyl(ep.DOWEL_D / 2, z0, z0 + p.HUB_DOWEL["l"], *p.polar(ep.R_HUB_INSERT, a + p.E_ROT)), E)
    # ---- cheek B + passive bearing
    add("128 Cheek B (ASA)", "ASA", cheek_b(), E)
    zb0 = p.CHEEK_B_Z[0]
    for i, (x, y) in enumerate(p.CHEEK_B_JOINT):
        add(f"129.{i + 1} Insert RX-M4x8.1 forearm", "Brass insert", insert(p.INSERT_M4["d_hole"], 4.0, p.Z_CHEEK_B_IN, p.INSERT_M4["length"], 1, x, y), E)
        add(f"130.{i + 1} Screw M4x16 ISO 4762 cheek B->forearm", "Steel 12.9 fastener",
            g.shcs(x, y, zb0 - p.WASHER_M4L["t"], p.M4_CHEEK_B_L, 4.0, 1), E)
        add(f"131.{i + 1} Washer M4 DIN 9021 cheek B", "Steel 12.9 fastener", washer(p.WASHER_M4L, zb0 - p.WASHER_M4L["t"], x, y), E)
    for k, v in occ.ball_bearing(z0=p.Z_P_IN0, seals=True, **p.BRG_P).items():
        add(f"132 61804-2RS1 passive {k}", "Bearing (purchased)", v, E)
    r = p.RETAINER
    add("133 Bearing retainer (ASA)", "ASA", occ.tube(r["r1"], r["r0"], *r["z"]) - holes(ep.D_M3_CLEAR / 2, r["z"][0] - 0.1, r["z"][1] + 0.1, p.COVER["boss_pcd_r"], p.COVER_ANG), E)
    # ---- output encoder
    add("134 Encoder bracket 6061-T6 (turned)", "6061-T6", bracket(), E)
    b = p.BRACKET
    for i, a in enumerate(p.PIN_TAP_ANG):
        add(f"135.{i + 1} Screw M2.5x10 ISO 10642 bracket->pin", "Steel 12.9 fastener",
            g.csk(*p.polar(b["csk_r"], a), b["z_plate"][0], p.L_BRACKET_SCREW, 2.5, 1), E)
    pcb = occ.box(-15, 15, -15, 15, *p.Z_PCB_OUT) - holes(ep.PCB["hole_d"] / 2, p.Z_PCB_OUT[0] - 1, p.Z_PCB_OUT[1] + 1, p.PCB_OUT["hole_r"], g.every(4, p.PCB_OUT["ang0"]))
    add("136 Output encoder PCB 30x30x1.6 (shoulder P12)", "Electronics", pcb, E)
    add("137 AS5047P TSSOP-14 output (envelope)", "Electronics",
        occ.box(-ep.IC["l"] / 2, ep.IC["l"] / 2, -ep.IC["w"] / 2, ep.IC["w"] / 2, *p.Z_IC_OUT), E)
    for i, a in enumerate(g.every(4, p.PCB_OUT["ang0"])):
        add(f"138.{i + 1} Screw M2.5x4 DIN 912 pcb->bracket", "Steel 12.9 fastener",
            g.shcs(*p.polar(p.PCB_OUT["hole_r"], a), p.Z_PCB_OUT[0], p.L_PCB_SCREW, 2.5, 1), E)
    add("139 Output magnet D6x2.5 diametric", "NdFeB magnet", occ.cyl(ep.MAG["d"] / 2, *p.Z_MAG_OUT), E)
    add("140 Encoder cover (ASA)", "ASA", cover(), E)
    for i, a in enumerate(p.COVER_ANG):
        x, y = p.polar(p.COVER["boss_pcd_r"], a)
        add(f"141.{i + 1} Insert RX-M3x5.7 cheek B", "Brass insert", insert(ep.INSERT["d_hole"], 3.0, zb0, ep.INSERT["length"], 1, x, y), E)
        add(f"142.{i + 1} Screw M3x12 DIN 912 cover->cheek B", "Steel 12.9 fastener", g.shcs(x, y, p.COVER["seat"], p.L_COVER_SCREW, 3.0, 1), E)
    # ---- wrist interface (future hand)
    for i, a in enumerate(g.every(p.WRIST["n"], p.WRIST["ang0"])):
        x, z = p.polar(p.WRIST["pcd_r"], a)
        ins = occ.tube(ep.INSERT["d_hole"] / 2, 1.5, p.L_FOREARM - ep.INSERT["length"], p.L_FOREARM)
        add(f"143.{i + 1} Insert RX-M3x5.7 wrist", "Brass insert", along_y(ins, x, p.FA_ZC + z), E)
    return parts


def build_elbow():
    """Elbow actuator parts placed in the arm (turned by E_ROT), arm-replaced fasteners dropped."""
    return [("E" + n, m, elbow_to_world(s.rotate((0, 0, p.E_ROT)))) for n, m, s in el.build() if not n.startswith(ELBOW_SKIP)]


def build_shoulder():
    """Shoulder actuator parts placed with the output-flange face on world y = 0."""
    return [("S" + n, m, s.rotate((-90, 0, 0)).translate((0, -p.SH_FLANGE_Z, 0))) for n, m, s in g.build()]


# ---------------------------------------------------------------- checks
def apart(a, b, margin):
    """True when bounding boxes a and b are further apart than margin."""
    return any(a[k] - margin >= b[k + 3] or b[k] - margin >= a[k + 3] for k in range(3))


def interferences(arm, others):
    """Overlap volume of every arm part against the arm, elbow and shoulder parts (forearm at 0 deg)."""
    allp = arm + others
    boxes = [s.bounding_box() for _, _, s in allp]
    hits = []
    for i in range(len(arm)):
        for j in range(i + 1, len(allp)):
            if not apart(boxes[i], boxes[j], 0.0):
                v = (allp[i][2] ^ allp[j][2]).volume()
                if v > 0.05:
                    hits.append((v, allp[i][0], allp[j][0]))
    bad = [n for n, _, s in arm if not s.s.isValid() or s.volume() <= 0]
    print(f"arm parts: {len(arm)}   invalid solids: {bad or 'none'}")
    print(f"interferences > 0.05 mm3 at 0 deg: {len(hits)}")
    for v, a, b in sorted(hits, reverse=True):
        print(f"  {v:9.2f} mm3  {a}  <->  {b}")
    return hits


def sweep(moving, stationary):
    """Worst gap of each moving/stationary pair over the flexion range (negative = overlap mm3)."""
    sb = [s.bounding_box() for _, _, s in stationary]
    worst, oring, frame = {}, [], {}
    for th in p.SWEEP:
        for nm, _, sm in moving:
            m = flex(sm, th)
            bm = m.bounding_box()
            for (ns, _, ss), bs in zip(stationary, sb):
                if apart(bm, bs, 10.0 if ns.startswith(("104 ", "110 ", "115 ")) else 3.0):
                    continue
                v = (m ^ ss).volume()
                gap = -v if v > 1e-3 else m.min_gap(ss, 1.0)
                if ns.startswith("121.") and nm.startswith("125 "):
                    oring.append((th, ns, gap))
                    continue
                if (nm, ns) not in worst or gap < worst[(nm, ns)][0]:
                    worst[(nm, ns)] = (gap, th)
                if ns.startswith(("104 ", "110 ", "115 ")) and gap < frame.get(th, (1e9,))[0]:
                    frame[th] = (gap, nm, ns)
    print(f"flexion sweep {p.SWEEP[0]:.0f}..{p.SWEEP[-1]:.0f} deg, closest moving/stationary pairs (mm, deg):")
    for (nm, ns), (gap, th) in sorted(worst.items(), key=lambda kv: kv[1][0])[:25]:
        print(f"  {gap:7.3f} at {th:6.1f}  {nm}  <->  {ns}")
    print("forearm side to upper-arm prints / front ring, closest per angle (10.0 = nothing within 10 mm):")
    for th in p.SWEEP:
        gap, nm, ns = frame.get(th, (10.0, "-", "-"))
        print(f"  {th:6.1f} deg  {gap:7.3f}  {nm}  <->  {ns}")
    print("stop o-ring to cheek A slot (contact expected only at the hard stops):")
    for th in p.SWEEP:
        gaps = [gp for t, _, gp in oring if t == th]
        print(f"  {th:6.1f} deg  {min(gaps) if gaps else float('nan'):7.3f}")
    return worst


def encoder_spacing():
    """Print magnet / ic spacings between the motor encoder and the output encoder (elbow z)."""
    d1 = ep.Z_PCB1 - p.Z_MAG_OUT[1]
    d2 = ep.Z_MAG - p.Z_IC_OUT[1]
    d3 = ep.Z_MAG - p.Z_MAG_OUT[1]
    print(f"encoder spacing: motor ic <-> output magnet {d1:.1f}, output ic <-> motor magnet {d2:.1f}, "
          f"magnet <-> magnet {d3:.1f} mm (min {p.MAG_SPACING_MIN:.0f})")
    assert min(d1, d2, d3) >= p.MAG_SPACING_MIN


def print_pose(solid, rot):
    """Rotate into print orientation and find the z turn that fits the bed; returns (solid on bed, size, z turn)."""
    s = solid.rotate(rot)
    best = None
    for az in range(0, 91, 3):
        b = s.rotate((0, 0, az)).bounding_box()
        size = (b[3] - b[0], b[4] - b[1], b[5] - b[2])
        if best is None or max(size[:2]) < max(best[1][:2]):
            best = (az, size, b)
    az, size, b = best
    return s.rotate((0, 0, az)).translate((-b[0], -b[1], -b[2])), size, az


def bed_check(arm):
    """Print the bed footprint of every printed part and return them posed on the bed."""
    posed = []
    print(f"print fit (bed {p.BED:.0f} x {p.BED:.0f} x {p.BED:.0f}):")
    for n, m, s in arm:
        rot = PRINT.get(g.part_no(n))
        if rot is None:
            continue
        sp, size, az = print_pose(s, rot)
        ok = max(size) <= p.BED
        print(f"  {'ok ' if ok else 'BIG'} {size[0]:6.1f} x {size[1]:6.1f} x {size[2]:6.1f}  turn {az:2d}  {n}")
        posed.append((n, m, sp))
    return posed


def masses(arm, elbow):
    """Write mass.txt: per-part masses, printed-mass estimates and group centres of mass."""
    lines, groups = [], {"upper": [0.0, np.zeros(3)], "fore": [0.0, np.zeros(3)]}
    for n, m, s in arm + elbow:
        rho = g.MATERIALS[m][1]
        mass = s.volume() / 1000 * rho
        c = s.s.Center()
        c = np.array([c.x, c.y, c.z])
        est = ""
        if not n.startswith("E") and g.part_no(n) in PRINT:
            # walls + top/bottom skins solid, the rest at the infill fraction
            shell = min(s.volume(), s.s.Area() * 1.7)
            printed = (shell + (s.volume() - shell) * 0.40) / 1000 * rho
            est = f"   print est {printed:7.1f} g"
        else:
            printed = mass
        key = "fore" if not n.startswith(("E", "S")) and g.part_no(n) in MOVING else "upper"
        groups[key][0] += printed
        groups[key][1] += printed * c
        if not n.startswith("E"):
            lines.append(f"{n:58s} {mass:8.1f} g{est}")
    motor = el.p.MOTOR_MASS_G
    c_motor = np.array([0.0, p.Y_E0 + ep.Z_M0 + 14.0, p.Z_ELBOW])
    groups["upper"][0] += motor
    groups["upper"][1] += motor * c_motor
    m_elbow = sum(s.volume() / 1000 * g.MATERIALS[m][1] for _, m, s in elbow) + motor
    out = ["# arm masses, solid material (g); groups use the print estimate for printed parts;",
           "# centres of mass in world mm at 0 deg (y outboard, z up)", *lines, ""]
    for k, (mass, mc) in groups.items():
        c = mc / mass
        out += [f"m_{k} = {mass:.1f}", f"com_{k}_x = {c[0]:.1f}", f"com_{k}_y = {c[1]:.1f}", f"com_{k}_z = {c[2]:.1f}"]
    out += [f"m_elbow = {m_elbow:.1f}", f"m_arm = {groups['upper'][0] + groups['fore'][0]:.1f}"]
    with open(os.path.join(HERE, "mass.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    print(f"mass: upper arm + elbow {groups['upper'][0]:.0f} g, forearm {groups['fore'][0]:.0f} g, elbow actuator {m_elbow:.0f} g")


def preview(groups, path):
    """Render shaded views (one per flexion angle) of the given parts to a png."""
    light = np.array([0.4, 0.8, 0.45]) / np.linalg.norm([0.4, 0.8, 0.45])
    fig = plt.figure(figsize=(5 * len(groups), 9), dpi=120)
    for k, (title, parts) in enumerate(groups):
        ax = fig.add_subplot(1, len(groups), k + 1, projection="3d")
        polys, cols = [], []
        for _, m, s in parts:
            v, t = s.s.tessellate(0.4, 0.6)
            v = np.array([q.toTuple() for q in v])
            tri = v[np.array(t)]
            n = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
            n /= np.maximum(np.linalg.norm(n, axis=1, keepdims=True), 1e-12)
            base = np.array([int(g.MATERIALS[m][0][i:i + 2], 16) / 255 for i in (1, 3, 5)])
            shade = 0.35 + 0.65 * np.abs(n @ light)
            polys.append(tri)
            cols.append(np.clip(base[None, :] * shade[:, None], 0, 1))
        tris = np.concatenate(polys)
        ax.add_collection3d(Poly3DCollection(tris, facecolors=np.concatenate(cols), linewidths=0))
        lo, hi = tris.reshape(-1, 3).min(axis=0), tris.reshape(-1, 3).max(axis=0)
        ax.set_xlim(lo[0], hi[0])
        ax.set_ylim(lo[1], hi[1])
        ax.set_zlim(lo[2], hi[2])
        ax.set_box_aspect(hi - lo, zoom=1.0)
        ax.view_init(elev=12, azim=35)
        ax.set_axis_off()
        ax.set_title(title)
    fig.subplots_adjust(left=0, right=1, bottom=0, top=0.95, wspace=0)
    fig.savefig(path, bbox_inches="tight", pad_inches=0.1)
    plt.close(fig)
    print(f"wrote {path}")


if __name__ == "__main__":
    t0 = time.time()
    occ.use_occ_kernel()
    arm = build_arm()
    print(f"built {len(arm)} arm solids in {time.time() - t0:.0f} s")
    elbow = build_elbow()
    shoulder = build_shoulder()
    print(f"placed elbow ({len(elbow)}) + shoulder ({len(shoulder)}) in {time.time() - t0:.0f} s")
    encoder_spacing()
    interferences(arm, elbow + shoulder)
    num = {n: g.part_no(n) for n, _, _ in arm}
    moving = [q for q in arm if num[q[0]] in MOVING]
    outside = ("E01 ", "E10 ", "E26 ", "E28 ", "E27 61807-2RS1 output outer ring", "E27 61807-2RS1 output seal")
    stationary = [q for q in arm if num[q[0]] not in MOVING and num[q[0]] != 132] + [q for q in elbow if q[0].startswith(outside)]
    sweep(moving, stationary)
    posed = bed_check(arm)
    masses(arm, elbow)
    show_s = [q for q in shoulder if g.part_no(q[0][1:]) in {8, 15, 33, 42, 45}]
    show_e = [q for q in elbow if q[0].startswith(outside)]
    views = [(f"{th:.0f} deg", show_s + show_e + [(n, m, flex(s, th) if num[n] in MOVING else s) for n, m, s in arm]) for th in (0.0, 90.0, 140.0)]
    preview(views, OUT + "_preview.png")
    occ.write_step(arm + elbow + shoulder, OUT + ".step", f"VAYN_Arm_Rev{REV}")
    g.write_3mf(arm + elbow + shoulder, OUT + ".3mf", f"VAYN Arm Rev {REV}")
    g.write_stl_zip(arm, OUT + "_stl.zip")
    g.write_stl_zip(posed, OUT + "_print.zip")
    print(f"total {time.time() - t0:.0f} s")
