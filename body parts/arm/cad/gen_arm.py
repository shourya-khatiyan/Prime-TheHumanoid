"""Build the VAYN arm Rev 2 (twin plates, direct-drive LA8308 elbow) as exact OpenCascade solids and check it.

Upper arm = two shaped PETG plates (each printed in two pieces joined by a
glued, screwed half-lap) held apart by printed spacer sleeves; the LA8308
sits between them on four standoffs. The rotor drives a printed hub. A
sleeve in the outer plate carries the hub bearing, and the hub end flange
stands proud of that plate and bolts to the forearm outer plate. The
forearm inner plate pivots on a printed stub through a 6804Z. The forearm
is two PETG truss plates with spacer sleeves and a wrist block. Two
forearm spacers wear silicone sleeves and are the hard stops. All
dimensions come from arm_params.py. Writes, beside this script:
  arm.step          coloured, named assembly (shoulder + arm)
  arm.3mf           named, coloured meshes
  arm_stl.zip       every arm part, assembled position
  arm_print.zip     printed arm parts in print orientation + the fit coupon
  arm_preview.png   rendered views at 0, 90 and 138 deg flexion
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

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from mpl_toolkits.mplot3d.art3d import Poly3DCollection  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "..", "shoulder", "cad"))
import gen_actuator_3mf as g  # noqa: E402  (shoulder module, path set above)
import gen_actuator_occ as occ  # noqa: E402

OUT = os.path.join(HERE, "arm")
REV = "2.1"
BIG = 1000.0

g.MATERIALS.update({
    "PETG": ("#3F6FB5", p.RHO_PETG),
    "PETG forearm": ("#8A5FBF", p.RHO_PETG),
    "Resin": ("#D8D8D8", 1.15),
    "Brass insert": ("#C8A24A", 8.50),
    "Silicone": ("#D9603B", 1.20),
    "NBR O-ring": ("#1E1E1E", 1.30),
})

# print orientation (rx, ry, rz) in world; +y up = (90, 0, 0), +y down = (-90, 0, 0)
PRINT = {201: (-90, 0, 0), 202: (-90, 0, 0), 203: (90, 0, 0), 204: (90, 0, 0), 205: (90, 0, 0), 206: (90, 0, 0),
         207: (90, 0, 0), 208: (90, 0, 0), 209: (-90, 0, 0), 210: (90, 0, 0), 211: (180, 0, 0),
         213: (90, 0, 0), 214: (90, 0, 0)}
MOVING = {207, 208, 209, 210, 211, 214, 217, 220, 221, 222, 223, 224, 225}  # turn with the forearm (218 pads stay on the upper plates)


# ---------------------------------------------------------------- frames and primitives (local frame: x = u, y = v, z = -world y)
def to_world(s):
    """Local (u, v, -y) -> world (x, y, z)."""
    return s.rotate((90, 0, 0)).translate((0, 0, p.Z_ELBOW))


def flex(s, th):
    """Turn a world solid about the elbow axis by flexion th (deg): the hanging forearm swings forward."""
    return s.translate((0, 0, -p.Z_ELBOW)).rotate((0, -th, 0)).translate((0, 0, p.Z_ELBOW))


def V(q):
    """Local vector from a (u, v) pair."""
    return cq.Vector(q[0], q[1], 0)


def arc(c, r, a0, a1):
    """Circular arc edge round c from a0 to a1 (deg, ccw)."""
    pts = [V((c[0] + r * math.cos(math.radians(a)), c[1] + r * math.sin(math.radians(a)))) for a in (a0, (a0 + a1) / 2, a1)]
    return cq.Edge.makeThreePointArc(*pts)


def slab(wire, y0, y1):
    """Extrude a closed (u, v) wire between world faces y0 < y1."""
    face = cq.Face.makeFromWires(wire)
    return occ.Solid(cq.Solid.extrudeLinear(face, cq.Vector(0, 0, y1 - y0)).translate(cq.Vector(0, 0, -y1)))


def poly(pts, y0, y1):
    """Prism of a (u, v) polygon between world faces y0 < y1."""
    return slab(cq.Wire.makePolygon([V(q) for q in pts], close=True), y0, y1)


def ycyl(r, y0, y1, u=0.0, v=0.0):
    """Cylinder along world y between y0 < y1 at (u, v)."""
    return occ.cyl(r, -y1, -y0, u, v)


def ytube(ro, ri, y0, y1, u=0.0, v=0.0):
    """Tube along world y."""
    return ycyl(ro, y0, y1, u, v) - ycyl(ri, y0 - 1, y1 + 1, u, v)


def ybox(u0, u1, v0, v1, y0, y1):
    """Box in (u, v, world y)."""
    return occ.box(u0, u1, v0, v1, -y1, -y0)


def vcyl(r, v0, v1, u, y):
    """Cylinder along v (arm length) at (u, world y)."""
    return occ.Solid(cq.Solid.makeCylinder(r, v1 - v0, cq.Vector(u, v0, -y), cq.Vector(0, 1, 0)))


def csk(u, v, y_face, length, d, into):
    """Countersunk screw flush with world face y_face, shank going into = +1 (+y) or -1."""
    return g.csk(u, v, -y_face, length, d, -into)


def csk_hole(u, v, y_face, depth, d, into):
    """Countersunk clearance hole matching csk()."""
    return g.csk_hole(u, v, -y_face, depth, d, -into)


def shcs(u, v, y_face, length, d, into):
    """Socket head cap screw, head on world face y_face, shank going into."""
    return g.shcs(u, v, -y_face, length, d, -into)


def insert(u, v, y_face, into, length=5.7):
    """Brass m3 heat-set insert from world face y_face going into."""
    y0, y1 = (y_face, y_face + length) if into > 0 else (y_face - length, y_face)
    return ytube(p.SPACER_INSERT["d_hole"] / 2, 1.5, y0, y1, u, v)


def union(parts):
    """Fuse a list of solids."""
    out = parts[0]
    for s in parts[1:]:
        out = out + s
    return out


# ---------------------------------------------------------------- outlines
def upper_wire():
    """Closed wire of the upper-arm plate outline (both plates)."""
    U, sh = p.UPPER, (0.0, p.L_UPPER)
    f0, b3 = p.polar(U["r_el"], 20.0), p.polar(U["r_el"], 160.0)
    f3 = (sh[0] + p.polar(U["r_sh"], -20.0)[0], sh[1] + p.polar(U["r_sh"], -20.0)[1])
    b0 = (sh[0] + p.polar(U["r_sh"], 200.0)[0], sh[1] + p.polar(U["r_sh"], 200.0)[1])
    ha0, ha1 = U["heel_a"]
    h0, h1 = p.polar(U["r_el"], ha0), p.polar(U["r_el"], ha1)
    edges = [cq.Edge.makeBezier([V(q) for q in [f0, U["front"][1], U["front"][2], f3]]),
             arc(sh, U["r_sh"], -20.0, 200.0),
             cq.Edge.makeBezier([V(q) for q in [b0, U["back"][1], U["back"][2], b3]]),
             arc((0.0, 0.0), U["r_el"], 160.0, ha0),
             cq.Edge.makeLine(V(h0), V(U["heel"][0])), cq.Edge.makeLine(V(U["heel"][0]), V(U["heel"][1])),
             cq.Edge.makeLine(V(U["heel"][1]), V(h1)),
             arc((0.0, 0.0), U["r_el"], ha1, 380.0)]
    return cq.Wire.assembleEdges(edges)


def fore_wire():
    """Closed wire of the forearm plate outline (both plates)."""
    F = p.FORE
    a0, a1 = F["lobe_a"]
    edges = [arc((0.0, 0.0), F["r_lobe"], a0, a1),
             cq.Edge.makeBezier([V(q) for q in [p.polar(F["r_lobe"], a1)] + F["back"][1:]]),
             cq.Edge.makeLine(V(F["back"][3]), V(F["front"][0])),
             cq.Edge.makeBezier([V(q) for q in F["front"][:3] + [p.polar(F["r_lobe"], a0)]])]
    return cq.Wire.assembleEdges(edges)


def stadium(v0, v1, hw, y0, y1):
    """Rounded slot along v."""
    return ybox(-hw, hw, v0 + hw, v1 - hw, y0, y1) + ycyl(hw, y0, y1, 0, v0 + hw) + ycyl(hw, y0, y1, 0, v1 - hw)


def bar(a, b, w, y0, y1):
    """Straight truss bar of width w from (u, v) a to b."""
    du, dv = b[0] - a[0], b[1] - a[1]
    n = math.hypot(du, dv)
    ou, ov = -dv / n * w / 2, du / n * w / 2
    return poly([(a[0] + ou, a[1] + ov), (b[0] + ou, b[1] + ov), (b[0] - ou, b[1] - ov), (a[0] - ou, a[1] - ov)], y0, y1)


# ---------------------------------------------------------------- upper arm
def upper_plate(y0, y1):
    """Full upper-arm plate between world faces y0, y1 with its slots (holes added per piece)."""
    s = slab(upper_wire(), y0, y1)
    for v0, v1, hw in p.SLOTS:
        s = s - stadium(v0, v1, hw, y0 - 1, y1 + 1)
    return s


def split(plate, y0, y1, v_split, gap_high):
    """Return (lower, upper) pieces of a plate cut by a half-lap at v_split; the lower piece keeps the gap-side half."""
    lap, c, ym = p.SPLIT["lap"], 0.1, (y0 + y1) / 2
    gap = (ym, y1 + 1) if gap_high else (y0 - 1, ym)
    out = (y0 - 1, ym) if gap_high else (ym, y1 + 1)
    lo = ybox(-BIG, BIG, -BIG, v_split - lap / 2, -BIG, BIG) + ybox(-BIG, BIG, v_split - lap / 2 - 0.01, v_split + lap / 2 - c, *gap)
    hi = ybox(-BIG, BIG, v_split + lap / 2, BIG, -BIG, BIG) + ybox(-BIG, BIG, v_split - lap / 2 + c, v_split + lap / 2 + 0.01, *out)
    return plate ^ lo, plate ^ hi


def inner_plate():
    """Upper inner plate as (lower piece 201, upper piece 202)."""
    y0, y1 = p.Y_UI
    s = upper_plate(y0, y1)
    cut = []
    for u, v in p.upper_spacers():
        cut.append(csk_hole(u, v, y0, y1 - y0, 3.0, 1))
    for u, v in p.lap_screws("inner"):
        cut.append(csk_hole(u, v, y0, y1 - y0, 3.0, 1))
    for a in p.MOTOR_BASE["ang"]:
        cut.append(csk_hole(*p.polar(p.MOTOR_BASE["pcd_r"], a), y0, y1 - y0, 4.0, 1))
    cut.append(ycyl(p.LEAD["hole_r"], y0 - 1, y1 + 1, *p.polar(p.LEAD["r"], p.LEAD["ang"])))
    w = p.PCB["w"] / 2 + p.POCKET_CLEAR
    cut.append(ybox(-w, w, -w, w, p.Y_PCB[0], y1 + 1))
    gq = p.CABLE_GROOVE
    cut.append(occ.Solid(cq.Solid.makeBox(gq["r1"], gq["w"], gq["d"] + 1, cq.Vector(0, -gq["w"] / 2, -(y1 + 1)))
                         .rotate((0, 0, 0), (0, 0, 1), gq["ang"])))
    sh = (0.0, p.L_UPPER)
    for a in p.SH_M5_ANG:
        u, v = p.polar(p.SH_M5_R, a)
        cut.append(ycyl(p.M5["hole_r"], y0 - 1, y1 + 1, u, sh[1] + v))
    for a in p.SH_M4_HEAD_ANG:
        u, v = p.polar(p.SH_M4_HEAD_R, a)
        cut.append(ycyl(p.M4_HEAD_RELIEF["r"], y0 - 1, y0 + p.M4_HEAD_RELIEF["depth"], u, sh[1] + v))
    s = s - union(cut)
    s = s + ycyl(p.SPIGOT["r"], -p.SPIGOT["h"], y0 + 0.01, 0, sh[1])
    # stub: journal for the 6804, a shoulder the inner ring stops on, a thin neck so the encoder heads stay clear
    face, pb, st = p.PIVOT_FACE_Y, p.PIVOT_BRG, p.STUB
    y_in = face - pb["B"]
    stub = ycyl(st["r"] - st["journal_clear"], y_in, face + 0.01)
    stub = stub + ycyl(st["shoulder_r"], face + 0.10, face + 0.10 + st["shoulder_t"])
    stub = stub + ycyl(st["neck_r"], face + 0.10 + st["shoulder_t"] - 0.01, y0 + 0.01)
    stub = stub - ycyl(p.SPACER_INSERT["d_hole"] / 2, y_in - 0.01, y_in + p.SPACER_INSERT["depth"])
    s = s + stub
    # cut after the stub so the neck cannot fill a countersink
    holes = [csk_hole(u, v, y0, p.Y_PCB[0] - y0, 2.5, 1) for u, v in p.PCB["holes"]]
    return split(s - union(holes), y0, y1, p.SPLIT["inner"], True)


def outer_plate():
    """Upper outer plate as (lower piece 203, upper piece 204)."""
    y0, y1 = p.Y_UO
    s = upper_plate(y0, y1)
    cut = [ycyl(p.SLEEVE["hole_r"], y0 - 1, y1 + 1)]
    for u, v in p.upper_spacers() + p.lap_screws("outer"):
        cut.append(csk_hole(u, v, y1, y1 - y0, 3.0, -1))
    for a in p.SH_M5_ANG:
        u, v = p.polar(p.SH_M5_R, a)
        cut.append(ycyl(5.5, y0 - 1, y1 + 1, u, p.L_UPPER + v))  # hex-key access to the shoulder m5 heads
    return split(s - union(cut), y0, y1, p.SPLIT["outer"], False)


# ---------------------------------------------------------------- forearm
def fore_plate(y0, y1):
    """Forearm truss plate between world faces y0, y1."""
    F = p.FORE
    s = slab(fore_wire(), y0, y1)
    _, _, bi, fi = p.fore_rims()
    window = poly(bi + fi, y0 - 1, y1 + 1)
    keep = [ycyl(F["r_lobe"], y0 - 2, y1 + 2), ybox(-BIG, BIG, -BIG, -228.0 + F["rim"], y0 - 2, y1 + 2)]
    nodes = p.fore_nodes()
    for a, b in zip(nodes[:-2], nodes[1:-1]):
        keep.append(bar(a, b, F["bar"], y0 - 2, y1 + 2))
    keep.append(bar(nodes[-2], nodes[-1], F["bar"], y0 - 2, y1 + 2))
    for q in nodes:
        keep.append(ycyl(p.FORE_SPACER["r"] + 2.0, y0 - 2, y1 + 2, *q))
    return s - (window - union(keep))


def wrist_screws():
    """(u, v) of the two m3 screws per forearm plate into the wrist block."""
    return [(-10.0, -225.0), (10.0, -225.0)]


def fore_outer():
    """Forearm outer plate 208 (bolted to the hub end flange)."""
    y0, y1 = p.Y_FO
    s = fore_plate(y0, y1)
    cut = [csk_hole(*p.polar(p.HUB["end_pcd_r"], a), y1, y1 - y0, 3.0, -1) for a in p.HUB["end_ang"]]
    cut += [csk_hole(u, v, y1, y1 - y0, 3.0, -1) for u, v in p.fore_nodes() + wrist_screws()]
    return s - union(cut)


def fore_inner():
    """Forearm inner plate 209: boss and a slip bore for the 6804, with a lip that keeps the outer ring in."""
    y0, y1 = p.Y_FI
    s = fore_plate(y0, y1) + ycyl(p.FORE["r_lobe"] - 0.5, p.FI_BOSS_Y0, y0 + 0.5)
    cut = [ycyl(p.PIVOT_BORE_R, p.FI_BOSS_Y0 - 1, p.PIVOT_LIP_Y),
           ycyl(p.PIVOT_LIP_R, p.PIVOT_LIP_Y - 0.01, y1 + 1)]
    cut += [csk_hole(u, v, y0, y1 - y0, 3.0, 1) for u, v in p.fore_nodes() + wrist_screws()]
    return s - union(cut)


def hub():
    """Rotor hub 207: flange on the rotor, Ø19.2 journal through the bearing, end flange proud of 203."""
    y_r = p.Y_ROTOR
    yf = y_r + p.HUB["flange_t"]
    ye0, ye1 = p.Y_HUB_END
    jr = p.HUB["journal_d"] / 2
    s = ycyl(p.HUB["flange_r"], y_r, yf) + ycyl(jr, yf - 0.01, ye0) + ycyl(p.HUB["end_r"], ye0 - 0.01, ye1)
    cut = [ycyl(p.ROTOR["stub_r"], y_r - 1, ye1 + 1)]
    cut += [csk_hole(*p.polar(p.ROTOR["pcd_r"], a), yf, p.HUB["flange_t"], 3.0, -1) for a in p.ROTOR["ang"]]
    cut += [ycyl(p.SPACER_INSERT["d_hole"] / 2, ye1 - p.SPACER_INSERT["depth"], ye1 + 1,
                 *p.polar(p.HUB["end_pcd_r"], a)) for a in p.HUB["end_ang"]]
    return s - union(cut)


def sleeve():
    """Sleeve 213: flange against the inboard face of 203, bore for the hub bearing, lip on the outboard end."""
    S = p.SLEEVE
    y0, y1 = p.Y_SLEEVE
    yf = y0 + S["flange_t"]
    lip = y1 - S["lip_t"]
    s = ycyl(S["flange_r"], y0, yf) + ycyl(S["od_r"], yf - 0.01, y1)
    s = s - ycyl(S["bore_r"], y0 - 1, lip)
    s = s - ycyl(S["lip_r"], lip - 0.01, y1 + 1)
    return s


def wrist_block():
    """Wrist block 211 between the forearm plates; d20 spigot + 4 x m3 inserts for the future hand."""
    W = p.WRIST
    yc = (p.Y_FI[1] + p.Y_FO[0]) / 2
    s = ybox(-W["u"], W["u"], W["v"][0], W["v"][1], p.Y_FI[1], p.Y_FO[0])
    s = s + vcyl(W["spigot_r"], W["v"][0] - W["spigot_h"], W["v"][0] + 0.01, 0.0, yc)
    cut = []
    for u, v in wrist_screws():
        cut.append(ycyl(2.0, p.Y_FI[1] - 1, p.Y_FI[1] + 6.7, u, v))
        cut.append(ycyl(2.0, p.Y_FO[0] - 6.7, p.Y_FO[0] + 1, u, v))
    for a in g.every(W["n"], W["ang0"]):
        du, dy = p.polar(W["pcd_r"], a)
        cut.append(vcyl(2.0, W["v"][0] - 1, W["v"][0] + 6.7, du, yc + dy))
    return s - union(cut)


def coupon():
    """Fit coupon (own frame, z up).

    Row y 16: journals for both 19.5 bores, radius clearance 0.15 / 0.25 / 0.35.
    Row y 46: 6804 seats, radial float 0.15 / 0.25 / 0.35 over the measured 31.5 od.
    Row y 78: hub-bearing seats, same three floats over the measured 26.5 od.
    Right side: sleeve outside diameters 32.4 / 32.8 / 33.2, screw holes, spacer stubs, spigot ring.
    """
    bore = p.PIVOT_BRG["d"] / 2
    s = occ.box(0, 236, 0, 116, 0, 4)
    for k, clear in enumerate((0.15, 0.25, 0.35)):
        x = 24 + 46 * k
        s = s + occ.cyl(bore - clear, 4, 16, x, 16)
        s = s + occ.cyl(20.0, 4, 11, x, 50) - occ.cyl(p.PIVOT_BRG["D"] / 2 + clear, -1, 12, x, 50)
        s = s + occ.cyl(17.0, 4, 11, x, 84) - occ.cyl(p.HUB_BRG["D"] / 2 + clear, -1, 12, x, 84)
    for k, r in enumerate((16.2, 16.4, 16.6)):
        s = s + occ.cyl(r, 4, 12, 168, 20 + 38 * k)
    for x, y, r in [(206, 16, 1.6), (220, 16, p.M3["clear_r"]), (206, 32, p.M4["clear_r"]), (220, 32, p.M5["hole_r"])]:
        s = s - occ.cyl(r, -1, 6, x, y)
    for k, r in enumerate((p.UPPER_SPACER["r"], p.FORE_SPACER["r"])):
        x = 208 + 16 * k
        s = s + occ.cyl(r, 4, 16, x, 58) - occ.cyl(p.SPACER_INSERT["d_hole"] / 2, 16 - p.SPACER_INSERT["depth"], 17, x, 58)
    s = s + occ.tube(p.SPIGOT["r"], p.SPIGOT["r"] - 3.0, 4, 4 + p.SPIGOT["h"]).translate((210, 92, 0))
    return s


# ---------------------------------------------------------------- assembly
def build_arm():
    """Return list of (name, material, world solid) for every arm part, forearm at 0 deg."""
    parts = []

    def add(name, mat, solid):
        parts.append((name, mat, to_world(solid)))

    lo, hi = inner_plate()
    add("201 Upper inner plate, elbow piece (PETG)", "PETG", lo)
    add("202 Upper inner plate, shoulder piece (PETG)", "PETG", hi)
    lo, hi = outer_plate()
    add("203 Upper outer plate, elbow piece (PETG)", "PETG", lo)
    add("204 Upper outer plate, shoulder piece (PETG)", "PETG", hi)
    a = math.radians(p.UPPER["heel_a"][1])
    n = (-math.sin(a), math.cos(a))
    q1, q2 = p.polar(p.HEEL_PAD["r"][0], p.UPPER["heel_a"][1]), p.polar(p.HEEL_PAD["r"][1], p.UPPER["heel_a"][1])
    pad = [q1, q2, (q2[0] + p.HEEL_PAD["t"] * n[0], q2[1] + p.HEEL_PAD["t"] * n[1]), (q1[0] + p.HEEL_PAD["t"] * n[0], q1[1] + p.HEEL_PAD["t"] * n[1])]
    add("218.1 Rubber pad 3 mm, heel, inner plate", "Silicone", poly(pad, *p.Y_UI))
    add("218.2 Rubber pad 3 mm, heel, outer plate", "Silicone", poly(pad, *p.Y_UO))
    ya, yb = p.Y_UI[1], p.Y_UO[0]
    for i, (u, v) in enumerate(p.upper_spacers()):
        sl = ycyl(p.UPPER_SPACER["r"], ya, yb, u, v) - ycyl(2.0, ya - 1, ya + p.SPACER_INSERT["depth"], u, v) - ycyl(2.0, yb - p.SPACER_INSERT["depth"], yb + 1, u, v)
        add(f"205.{i + 1} Upper spacer sleeve D9 (PETG)", "PETG", sl)
        add(f"230.{i + 1} Insert M3x5.7 upper spacer, inner end", "Brass insert", insert(u, v, ya, 1))
        add(f"231.{i + 1} Insert M3x5.7 upper spacer, outer end", "Brass insert", insert(u, v, yb, -1))
        add(f"232.{i + 1} Screw M3x12 ISO 10642 inner plate->spacer", "Steel 12.9 fastener", csk(u, v, p.Y_UI[0], 12.0, 3.0, 1))
        add(f"233.{i + 1} Screw M3x10 ISO 10642 outer plate->spacer", "Steel 12.9 fastener", csk(u, v, p.Y_UO[1], 10.0, 3.0, -1))
    for i, (u, v) in enumerate(p.lap_screws("inner")):
        add(f"234.{i + 1} Screw M3x12 ISO 10642 inner lap", "Steel 12.9 fastener", csk(u, v, p.Y_UI[0], 12.0, 3.0, 1))
    for i, (u, v) in enumerate(p.lap_screws("outer")):
        add(f"235.{i + 1} Screw M3x10 ISO 10642 outer lap", "Steel 12.9 fastener", csk(u, v, p.Y_UO[1], 10.0, 3.0, -1))
    # motor, standoffs, encoder
    for i, a in enumerate(p.MOTOR_BASE["ang"]):
        u, v = p.polar(p.MOTOR_BASE["pcd_r"], a)
        add(f"206.{i + 1} Motor standoff (PETG)", "PETG", ytube(p.STANDOFF["ro"], p.STANDOFF["ri"], p.Y_UI[1], p.Y_MOUNT, u, v))
        add(f"236.{i + 1} Screw M4x18 ISO 10642 motor->inner plate", "Steel 12.9 fastener", csk(u, v, p.Y_UI[0], 18.0, 4.0, 1))
    motor = ycyl(p.MOTOR["r"], p.Y_MOUNT, p.Y_ROTOR) + ycyl(1.45, p.Y_ROTOR - 0.01, p.Y_ROTOR + 8.9)
    add("240 Motor LA8308 KV90 (envelope)", "Motor envelope", motor)
    add("212 Magnet holder (resin, bonded in the rear cap)", "Resin", ycyl(5.0, p.Y_MAG + 2.5, p.Y_MOUNT))
    add("241 Encoder magnet D6x2.5 diametric", "NdFeB magnet", ycyl(3.0, p.Y_MAG, p.Y_MAG + 2.5))
    pcb = ybox(-15, 15, -15, 15, *p.Y_PCB) - union([ycyl(1.5, p.Y_PCB[0] - 1, p.Y_PCB[1] + 1, u, v) for u, v in p.PCB["holes"]])
    add("242 Encoder PCB 30x30 AS5047P (Meukron)", "Electronics", pcb)
    add("243 AS5047P TSSOP-14 (envelope)", "Electronics", ybox(-2.5, 2.5, -2.2, 2.2, p.Y_PCB[1], p.Y_IC_TOP))
    for i, (u, v) in enumerate(p.PCB["holes"]):
        add(f"244.{i + 1} Screw M2.5x6 ISO 10642 pcb", "Steel 12.9 fastener", csk(u, v, p.Y_UI[0], 6.0, 2.5, 1))
        add(f"245.{i + 1} Nut M2.5 encoder (in the pocket, below the plate face)", "Steel 12.9 fastener",
            ycyl(2.9, p.Y_PCB[1], p.Y_PCB[1] + 2.0, u, v))
    # shoulder bolts
    for i, a in enumerate(p.SH_M5_ANG):
        u, v = p.polar(p.SH_M5_R, a)
        wsh = p.M5["washer"]
        add(f"237.{i + 1} Washer M5 ISO 7089 shoulder", "Steel 12.9 fastener", ytube(wsh["od"] / 2, wsh["id"] / 2, p.Y_UI[1], p.Y_UI[1] + wsh["t"], u, p.L_UPPER + v))
        add(f"238.{i + 1} Screw M5x12 ISO 4762 inner plate->shoulder", "Steel 12.9 fastener", shcs(u, p.L_UPPER + v, p.Y_UI[1] + wsh["t"], p.M5["screw_l"], 5.0, -1))
    # local z = -world y. z0 is the outboard face; the bearing runs inboard from there.
    for k, s in occ.ball_bearing(z0=-p.PIVOT_FACE_Y, seals=True, **p.PIVOT_BRG).items():
        add(f"250 6804Z pivot {k}", "Bearing (purchased)", s)
    y_brg = p.PIVOT_FACE_Y - p.PIVOT_BRG["B"]
    add("252 Insert M3x5.7 stub", "Brass insert", insert(0.0, 0.0, y_brg, 1))
    add("253 Washer 22/3.2x1 stub (PETG)", "PETG", ytube(11.0, 1.7, y_brg - 1.0, y_brg))
    add("254 Screw M3x6 ISO 4762 stub", "Steel 12.9 fastener", shcs(0.0, 0.0, y_brg - 1.0, 6.0, 3.0, 1))
    # forearm group
    add("207 Rotor hub (PETG)", "PETG forearm", hub())
    add("213 Hub bearing sleeve (PETG)", "PETG", sleeve())
    y_sp = p.Y_ROTOR + p.HUB["flange_t"]
    add("214 Hub bearing spacer (PETG)", "PETG forearm", ytube(11.0, p.HUB["journal_d"] / 2 + 0.20, y_sp, y_sp + p.HUB["spacer_l"]))
    y_seat = p.Y_SLEEVE[1] - p.SLEEVE["lip_t"]
    for k, s in occ.ball_bearing(z0=-y_seat, seals=False, **p.HUB_BRG).items():
        add(f"255 Hub bearing 19.5x26.5 {k}", "Bearing (purchased)", s)
    for i, a in enumerate(p.ROTOR["ang"]):
        add(f"220.{i + 1} Screw M3x10 ISO 10642 hub->rotor", "Steel 12.9 fastener", csk(*p.polar(p.ROTOR["pcd_r"], a), p.Y_ROTOR + p.HUB["flange_t"], 10.0, 3.0, -1))
    for i, a in enumerate(p.HUB["end_ang"]):
        u, v = p.polar(p.HUB["end_pcd_r"], a)
        add(f"221.{i + 1} Insert M3x5.7 hub", "Brass insert", insert(u, v, p.Y_HUB_END[1], -1))
        add(f"222.{i + 1} Screw M3x10 ISO 10642 forearm plate->hub", "Steel 12.9 fastener", csk(u, v, p.Y_FO[1], 10.0, 3.0, -1))
    add("208 Forearm outer plate (PETG)", "PETG forearm", fore_outer())
    add("209 Forearm inner plate (PETG)", "PETG forearm", fore_inner())
    ya, yb = p.Y_FI[1], p.Y_FO[0]
    for i, (u, v) in enumerate(p.fore_nodes()):
        sl = ycyl(p.FORE_SPACER["r"], ya, yb, u, v) - ycyl(2.0, ya - 1, ya + p.SPACER_INSERT["depth"], u, v) - ycyl(2.0, yb - p.SPACER_INSERT["depth"], yb + 1, u, v)
        add(f"210.{i + 1} Forearm spacer sleeve D8 (PETG)", "PETG forearm", sl)
        add(f"223.{i + 1} Insert M3x5.7 forearm spacer, ends", "Brass insert", insert(u, v, ya, 1) + insert(u, v, yb, -1))
        add(f"224.{i + 1} Screws 2 x M3x10 ISO 10642 forearm spacer", "Steel 12.9 fastener",
            csk(u, v, p.Y_FI[0], 10.0, 3.0, 1) + csk(u, v, p.Y_FO[1], 10.0, 3.0, -1))
        if i in (p.STOP_EXT, p.STOP_FLEX):
            name = "extension" if i == p.STOP_EXT else "flexion"
            add(f"217.{i + 1} Silicone tube 8x10 stop sleeve, {name}", "Silicone",
                ytube(p.FORE_SPACER["sleeve_r"], p.FORE_SPACER["r"], ya + 0.5, yb - 0.5, u, v))
    add("211 Wrist block (PETG)", "PETG forearm", wrist_block())
    for i, (u, v) in enumerate(wrist_screws()):
        add(f"225.{i + 1} Screws 2 x M3x10 ISO 10642 wrist block (inserts in the block)", "Steel 12.9 fastener",
            csk(u, v, p.Y_FI[0], 10.0, 3.0, 1) + csk(u, v, p.Y_FO[1], 10.0, 3.0, -1))
    return parts


def build_shoulder():
    """Shoulder actuator parts placed with the output-flange face on world y = 0."""
    return [("S" + n, m, s.rotate((-90, 0, 0)).translate((0, -p.SH_FLANGE_Z, 0))) for n, m, s in g.build()]


# ---------------------------------------------------------------- checks
def apart(a, b, margin):
    """True when bounding boxes a and b are further apart than margin."""
    return any(a[k] - margin >= b[k + 3] or b[k] - margin >= a[k + 3] for k in range(3))


def interferences(arm, others):
    """Overlap volume of every arm part against the arm and shoulder parts (forearm at 0 deg)."""
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
    """Closest moving/stationary pairs over the flexion range; stop sleeves reported separately."""
    sb = [s.bounding_box() for _, _, s in stationary]
    worst, stops = {}, []
    for th in p.SWEEP:
        for nm, _, sm in moving:
            m = flex(sm, th)
            bm = m.bounding_box()
            for (ns, _, ss), bs in zip(stationary, sb):
                if apart(bm, bs, 3.0):
                    continue
                v = (m ^ ss).volume()
                gap = -v if v > 1e-3 else m.min_gap(ss, 1.0)
                if nm.startswith("217."):
                    stops.append((th, nm, ns, gap))
                    continue
                if (nm, ns) not in worst or gap < worst[(nm, ns)][0]:
                    worst[(nm, ns)] = (gap, th)
    print(f"flexion sweep {p.SWEEP[0]:.0f}..{p.SWEEP[-1]:.0f} deg, closest moving/stationary pairs (mm, negative = overlap mm3):")
    for (nm, ns), (gap, th) in sorted(worst.items(), key=lambda kv: kv[1][0])[:20]:
        print(f"  {gap:7.3f} at {th:6.1f}  {nm}  <->  {ns}")
    print("stop sleeves (contact expected only at the stops):")
    for th in p.SWEEP:
        row = [(gap, nm, ns) for t, nm, ns, gap in stops if t == th]
        if row:
            gap, nm, ns = min(row)
            print(f"  {th:6.1f} deg  {gap:7.3f}  {nm[:40]}  <->  {ns[:40]}")
    return worst


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
    posed, seen = [], set()
    print(f"print fit (bed {p.BED:.0f} x {p.BED:.0f} x {p.BED:.0f}):")
    for n, m, s in arm:
        num = g.part_no(n)
        rot = PRINT.get(num)
        if rot is None:
            continue
        sp, size, az = print_pose(s, rot)
        ok = max(size) <= p.BED
        if num not in seen or not ok:
            print(f"  {'ok ' if ok else 'BIG'} {size[0]:6.1f} x {size[1]:6.1f} x {size[2]:6.1f}  turn {az:2d}  {n}")
        seen.add(num)
        posed.append((n, m, sp))
    return posed


def masses(arm):
    """Write mass.txt: per-part masses, printed-mass estimates and group centres of mass."""
    lines, groups = [], {"upper": [0.0, np.zeros(3)], "fore": [0.0, np.zeros(3)]}
    for n, m, s in arm:
        rho = g.MATERIALS[m][1]
        mass = s.volume() / 1000 * rho
        c = s.s.Center()
        c = np.array([c.x, c.y, c.z])
        est = ""
        if g.part_no(n) in PRINT:
            shell = min(s.volume(), s.s.Area() * p.PRINT_SKIN)
            printed = (shell + (s.volume() - shell) * 0.40) / 1000 * rho
            est = f"   print est {printed:7.1f} g"
        else:
            printed = mass
        key = "fore" if g.part_no(n) in MOVING else "upper"
        groups[key][0] += printed
        groups[key][1] += printed * c
        lines.append(f"{n:58s} {mass:8.1f} g{est}")
    c_motor = np.array([0.0, (p.Y_MOUNT + p.Y_ROTOR) / 2, p.Z_ELBOW])
    groups["upper"][0] += p.MOTOR["mass"]
    groups["upper"][1] += p.MOTOR["mass"] * c_motor
    out = ["# arm masses, solid material (g); groups use the print estimate for printed parts;",
           "# centres of mass in world mm at 0 deg (y outboard, z up); the motor (336 g) is in the upper group", *lines, ""]
    for k, (mass, mc) in groups.items():
        c = mc / mass
        out += [f"m_{k} = {mass:.1f}", f"com_{k}_x = {c[0]:.1f}", f"com_{k}_y = {c[1]:.1f}", f"com_{k}_z = {c[2]:.1f}"]
    out += [f"m_motor = {p.MOTOR['mass']:.1f}", f"m_arm = {groups['upper'][0] + groups['fore'][0]:.1f}"]
    with open(os.path.join(HERE, "mass.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(out) + "\n")
    print(f"mass: upper arm + motor {groups['upper'][0]:.0f} g, forearm {groups['fore'][0]:.0f} g")


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


def encoder_check():
    """Print the joint stack and refuse a magnet gap outside 0.5..3.0 mm."""
    gap = p.Y_MAG - p.Y_IC_TOP
    d24 = math.dist(p.PCB["holes"][0], p.PCB["holes"][1])
    d19 = math.dist(p.PCB["holes"][2], p.PCB["holes"][3])
    proud = p.Y_HUB_END[1] - p.Y_UO[1]
    print(f"encoder: magnet face y {p.Y_MAG:.2f}, ic top y {p.Y_IC_TOP:.2f} -> gap {gap:.2f} mm (0.5..3.0)")
    print(f"encoder holes: diagonals {d24:.2f} and {d19:.2f} mm")
    print(f"stack y: plate {p.Y_UI[1]:.1f}, mount {p.Y_MOUNT:.1f}, rotor {p.Y_ROTOR:.1f}, "
          f"outer plate {p.Y_UO[0]:.1f}..{p.Y_UO[1]:.1f}, hub end {p.Y_HUB_END[1]:.1f} (proud {proud:.1f})")
    assert 0.5 <= gap <= 3.0
    assert abs(d24 - 24.0) < 0.05 and abs(d19 - 19.0) < 0.05
    assert p.Y_UI[0] + 6.0 < p.Y_MAG  # m2.5x6 tip stays off the magnet
    assert p.Y_PCB[1] + 2.0 < p.Y_UI[1]  # nuts below the plate face
    assert proud > 5.0


if __name__ == "__main__":
    t0 = time.time()
    occ.use_occ_kernel()
    arm = build_arm()
    print(f"built {len(arm)} arm solids in {time.time() - t0:.0f} s")
    shoulder = build_shoulder()
    print(f"placed shoulder ({len(shoulder)}) in {time.time() - t0:.0f} s")
    encoder_check()
    interferences(arm, shoulder)
    num = {n: g.part_no(n) for n, _, _ in arm}
    moving = [q for q in arm if num[q[0]] in MOVING]
    stationary = [q for q in arm if num[q[0]] not in MOVING and num[q[0]] not in (250, 255)]
    sweep([q for q in moving if num[q[0]] not in (207, 214, 220, 221, 222)], stationary)  # hub group is coaxial with the turn
    posed = bed_check(arm)
    masses(arm)
    show_s = [q for q in shoulder if g.part_no(q[0][1:]) in {8, 15, 33, 42, 45}]
    views = [(f"{th:.0f} deg", show_s + [(n, m, flex(s, th) if num[n] in MOVING else s) for n, m, s in arm]) for th in (0.0, 90.0, 138.0)]
    preview(views, OUT + "_preview.png")
    occ.write_step(arm + shoulder, OUT + ".step", f"VAYN_Arm_Rev{REV}")
    g.write_3mf(arm + shoulder, OUT + ".3mf", f"VAYN Arm Rev {REV}")
    g.write_stl_zip(arm, OUT + "_stl.zip")
    g.write_stl_zip(posed + [("299 Fit coupon (PETG)", "PETG", coupon())], OUT + "_print.zip")
    print(f"total {time.time() - t0:.0f} s")
