"""Single source of truth for every arm Rev 2 dimension (mm, deg).

Rev 2 is a twin-plate arm with a direct-drive elbow: the Eaglepower LA8308
KV90 sits between the two upper-arm plates and its rotor drives the forearm.

World frame: origin on the shoulder axis at the shoulder output-flange face.
+Y is the shoulder axis pointing outboard (away from the torso), +X forward,
+Z up. At zero shoulder angle the arm hangs along -Z; the elbow axis is
parallel to Y at x = 0, z = Z_ELBOW.

Arm-plane coordinates (u, v): u = world x (forward), v = world z - Z_ELBOW
(up from the elbow axis). Every plate is a 2D outline in (u, v) extruded
between two world-y faces. Flexion turns the forearm about +y by theta:
the hanging forearm (pointing -v) swings toward +u.
"""

import math

# ---------------------------------------------------------------- geometry (arm/research.md s2, 160 cm)
L_UPPER = 298.0  # shoulder axis -> elbow axis
L_FOREARM = 234.0  # elbow axis -> wrist flange face
L_HAND = 173.0  # future hand: load point only
Z_ELBOW = -L_UPPER
THETA_MIN, THETA_MAX = -5.0, 140.0  # rubber-sleeve stop contacts (gen_arm sweep: heel at -5, front edge at ~140)
SOFT_MIN, SOFT_MAX = -3.0, 135.0  # odesc software limits
SWEEP = [-5.0, 0.0, 15.0, 30.0, 45.0, 60.0, 75.0, 90.0, 105.0, 120.0, 130.0, 135.0, 138.0, 140.0]
G = 9.81

# ---------------------------------------------------------------- materials (bambu petg hf tds: 34 +- 4 / 23 +- 4 mpa, 1.28 g/cm3, hdt 62 c)
SIG_PETG_XY, SIG_PETG_Z = 34.0 - 4.0, 23.0 - 4.0  # mean - 1 sd
E_PETG = 1810.0 - 190.0
SF_PRINT = 2.0
RHO_PETG = 1.28
MU_PRINT = 0.30

# ---------------------------------------------------------------- shoulder interface (shoulder parts.md 42, 43, 45)
SH_FLANGE_Z = 100.5  # flange face in shoulder z
SH_M5_R, SH_M5_ANG = 26.0, [30.0 + 60.0 * k for k in range(6)]  # 6 x m5, tapped 8 deep
SH_M5_TAP = 8.0
SH_M4_HEAD_R, SH_M4_HEAD_ANG = 27.0, [60.0, 180.0, 300.0]  # carrier-2 screw heads flush with the face
SH_PILOT_R, SH_PILOT_DEPTH = 20.0, 2.0  # d40 h7 recess in the flange
SH_COVER_Y = -1.0  # stationary cover front face (world y)
SH_R = 50.0
SPIGOT = dict(r=20.0 - 0.10, h=1.8)  # printed d40 spigot (clearance set by the coupon), 0.2 short of the recess floor
M4_HEAD_RELIEF = dict(r=4.5, depth=0.4)
M5 = dict(hole_r=5.15 / 2, washer=dict(od=10.0, id=5.3, t=1.0), screw_l=14.0, torque=2.0)  # iso 7089 washer; 14 mm keeps 6 mm in the 8 mm tap through the 7 mm plate

# ---------------------------------------------------------------- elbow motor (eaglepower la8308 kv90; shoulder parts.md rev 1.4 measurements)
MOTOR = dict(r=46.0, h=32.5, mass=336.0, kv=90.0, r_phase=0.0846, l=37e-6, pp=20, i_cont=22.0, i_peak=40.0)
MOTOR_BASE = dict(pcd_r=20.0, ang=[0.0, 90.0, 180.0, 270.0], d=4.0, thread=6.0)  # 4 x m4 on d40 (angles vs the lead exit: measure)
ROTOR = dict(pcd_r=15.5, ang=[45.0, 135.0, 225.0, 315.0], d=3.0, thread=5.0, stub_r=1.75, stub_l=10.5, cap_r=8.7)
LEAD = dict(r=32.0, ang=135.0, hole_r=8.5)  # phase-lead bundle (13 across) leaves the rear face here: up and back, never swept
STANDOFF = dict(ro=5.5, ri=2.25, h=5.0)  # printed tubes on the motor screws: 5 mm air gap, keeps the petg away from the stator
NTC = "10k NTC (B3950) bonded to a stator coil through a base window, wired to the ODESC motor thermistor input"

# ---------------------------------------------------------------- elbow stack (world y)
# measured: magnet face to the old hub face is 47.5-48 mm. that stack already
# matched the old model, and the tube then stuck out of 203 by only 1 mm.
# the new hub is longer so the end flange stands clear of 203.
Y_UI = (0.0, 7.0)  # was 5. the extra 2 mm holds the encoder nuts inside the plate, off the magnet
Y_MOUNT = Y_UI[1] + STANDOFF["h"]  # motor mounting face
Y_ROTOR = Y_MOUNT + MOTOR["h"]  # rotor hub face
HUB = dict(flange_r=21.0, flange_t=4.0, journal_d=19.20, spacer_l=2.40,
           end_r=14.0, end_t=6.0, end_pcd_r=10.0, end_ang=(90.0, 210.0, 330.0))
# sleeve drops into the big hole in 203. body od under the hole, bore over the 26.5 bearing.
SLEEVE = dict(hole_r=17.3, od_r=16.4, flange_r=19.0, flange_t=1.2,
              bore_r=13.45, lip_r=11.0, lip_t=1.2, proud=2.2)
_HUB_FLANGE_END = Y_ROTOR + HUB["flange_t"]
Y_SLEEVE = (_HUB_FLANGE_END + 0.5, _HUB_FLANGE_END + 0.5 + SLEEVE["flange_t"] + 5.0 + SLEEVE["proud"])
Y_UO = (Y_SLEEVE[0] + SLEEVE["flange_t"], Y_SLEEVE[0] + SLEEVE["flange_t"] + 5.0)  # upper outer plate, 5 thick
Y_HUB_END = (Y_SLEEVE[1] + 0.30, Y_SLEEVE[1] + 0.30 + HUB["end_t"])  # flange that bolts to the forearm
Y_FO = (Y_HUB_END[1], Y_HUB_END[1] + 4.0)  # forearm outer plate
Y_FI = (-5.0, -1.0)  # forearm inner plate

# ---------------------------------------------------------------- motor encoder (meukron board, not the shoulder p12 square)
# user calipers: diagonals 24 mm and 19 mm, centre to centre. the photo shows the
# 24 mm pair running corner to corner of the board, the 19 mm pair the other way.
_S2 = math.sqrt(2.0)
PCB = dict(w=30.0, t=1.6, hole_d=3.2,
           holes=[(12.0 / _S2, 12.0 / _S2), (-12.0 / _S2, -12.0 / _S2),
                  (9.5 / _S2, -9.5 / _S2), (-9.5 / _S2, 9.5 / _S2)])
Y_PCB = (2.6, 4.2)  # board sits in the pocket; m2.5 nuts (2.0) stay below the y 7 face
Y_IC_TOP = Y_PCB[1] + 1.1  # tssop-14, under the 1.20 mm max
Y_MAG = Y_MOUNT - 4.75  # magnet face on the rear-cap holder (shoulder part 8 geometry)
POCKET_CLEAR = 0.3
CABLE_GROOVE = dict(w=6.0, d=2.0, ang=135.0, r1=58.0)  # encoder cable groove on the outboard face of the inner plate

# ---------------------------------------------------------------- bearings
# 6804Z catalog is 20 x 32 x 7 (skf / iso 15). the diameters below are the ones measured on this bearing.
PIVOT_BRG = dict(d=19.5, D=31.5, B=7.0, d1=23.5, D1=27.5, nballs=8, dball=3.5)
PIVOT_FACE_Y = -2.15  # outboard face of the pivot bearing
PIVOT_BORE_R = PIVOT_BRG["D"] / 2 + 0.25  # slip, not a press: the motor bearings still set the axis
PIVOT_LIP_Y = PIVOT_FACE_Y + 0.10
PIVOT_LIP_R = 13.2  # keeps the outer ring, clears the stub shoulder
FI_BOSS_Y0 = PIVOT_FACE_Y - PIVOT_BRG["B"] - 1.7
STUB = dict(r=PIVOT_BRG["d"] / 2, journal_clear=0.15, shoulder_r=11.0, shoulder_t=0.45, neck_r=6.5)
# hub bearing: measured id 19.5, od 26.5. width was not measured; the model uses 5 mm.
# the sleeve lip is 7.2 mm deep, so a 4 mm or a 7 mm bearing still seats. shorten part 214 if it is wider than 5.
HUB_BRG = dict(d=19.5, D=26.5, B=5.0, d1=22.0, D1=24.2, nballs=8, dball=2.0)
# ---------------------------------------------------------------- upper-arm plates (petg, 5 thick, printed flat)
UPPER = dict(r_sh=44.0, r_el=52.0,
             front=[(48.9, 17.8), (18.0, 95.0), (18.0, 215.0), (41.3, 283.0)],
             back=[(-41.3, 283.0), (-20.0, 215.0), (-20.0, 95.0), (-48.9, 17.8)],
             heel=[(-53.5, -48.2), (-35.7, -62.5)], heel_a=(222.0, 240.3))  # heel face radial at 240.3 deg, carries the rubber pad
HEEL_PAD = dict(t=3.0, r=(52.0, 72.0))  # 3 mm rubber glued on the heel face of both plates: extension stop at -5 deg, unpowered fall ~200 N
SLOTS = [(62.0, 98.0, 6.0), (194.0, 232.0, 6.0)]  # (v0, v1, half width): solid band between them carries the laps
SPLIT = dict(inner=120.0, outer=155.0, lap=30.0, screw_u=10.0, screw_dv=9.0)  # staggered half-laps, epoxy + 4 x m3 csk; pieces <= 235 long
UPPER_SPACER = dict(inset=7.5, every=4, r=4.5, r_el_min=58.0, r_sh_min=50.0,
                    shoulder=[(36.0, L_UPPER), (-36.0, L_UPPER), (0.0, L_UPPER - 40.0)])
SPACER_INSERT = dict(d_hole=4.0, depth=6.7)  # ruthex-type m3 x 5.7 heat-set insert in each sleeve end

# ---------------------------------------------------------------- forearm plates (petg, 4 thick truss)
FORE = dict(r_lobe=26.0, rim=7.0, bar=6.0,
            back=[(-24.4, -8.9), (-30.0, -60.0), (-21.0, -165.0), (-20.0, -228.0)],
            front=[(20.0, -228.0), (21.0, -165.0), (30.0, -60.0), (24.4, -8.9)],
            lobe_a=(-20.0, 200.0))
FORE_NODES = [("back", -60.0), ("front", -85.0), ("back", -110.0), ("front", -135.0), ("back", -160.0), ("front", -205.0), ("back", -205.0)]
STOP_EXT, STOP_FLEX = 0, 1  # indices in FORE_NODES that carry rubber sleeves
FORE_SPACER = dict(r=4.0, sleeve_r=5.0)  # d8 printed sleeve; silicone tube 8 x 10 on the two stop spacers
WRIST = dict(v=(-L_FOREARM, -216.0), u=20.0, pcd_r=15.0, n=4, ang0=45.0, spigot_r=10.0 - 0.01, spigot_h=1.8)

# ---------------------------------------------------------------- fasteners
M3 = dict(clear_r=3.4 / 2, csk_d=6.3, csk_depth=1.7)
M4 = dict(clear_r=4.5 / 2, csk_d=8.4, csk_depth=2.2)

# ---------------------------------------------------------------- print bed (bambu p2s 256 x 256 x 256, 5 mm margin)
BED = 246.0
PRINT_SKIN = 1.7  # 4 walls; thin truss bars print solid anyway


def polar(r, deg):
    """(x, y) for radius r at angle deg."""
    a = math.radians(deg)
    return r * math.cos(a), r * math.sin(a)


def bezier(P, n=24):
    """Points on the cubic bezier with control points P (4 x (u, v))."""
    out = []
    for i in range(n + 1):
        t = i / n
        k = ((1 - t) ** 3, 3 * (1 - t) ** 2 * t, 3 * (1 - t) * t * t, t ** 3)
        out.append((sum(k[j] * P[j][0] for j in range(4)), sum(k[j] * P[j][1] for j in range(4))))
    return out


def inset(curve, d):
    """Offset the interior points of a curve by d to its left (into a ccw outline)."""
    out = []
    for i in range(1, len(curve) - 1):
        (u0, v0), (u1, v1) = curve[i - 1], curve[i + 1]
        length = math.hypot(u1 - u0, v1 - v0)
        out.append((curve[i][0] - d * (v1 - v0) / length, curve[i][1] + d * (u1 - u0) / length))
    return out


def upper_spacers():
    """Spacer sleeve centres (u, v) between the upper-arm plates."""
    q = UPPER_SPACER
    pts = inset(bezier(UPPER["front"]), q["inset"]) + inset(bezier(UPPER["back"]), q["inset"])
    pts = [p for i, p in enumerate(pts) if i % q["every"] == 2]
    keep = [p for p in pts if math.hypot(*p) > q["r_el_min"] and math.hypot(p[0], p[1] - L_UPPER) > q["r_sh_min"]]
    laps = [lap_screws("inner"), lap_screws("outer")]
    keep = [p for p in keep if all(math.hypot(p[0] - s[0], p[1] - s[1]) > 9.0 for ls in laps for s in ls)]
    return keep + q["shoulder"]


def lap_screws(which):
    """The four m3 screw centres (u, v) of one half-lap."""
    v0, du, dv = SPLIT[which], SPLIT["screw_u"], SPLIT["screw_dv"]
    return [(su * du, v0 + sv * dv) for su in (-1, 1) for sv in (-1, 1)]


def fore_rims():
    """(back curve, front curve, back inset, front inset) of the forearm truss plates."""
    b, f = bezier(FORE["back"], 22), bezier(FORE["front"], 22)
    return b, f, inset(b, FORE["rim"]), inset(f, FORE["rim"])


def fore_nodes():
    """Truss node / spacer centres (u, v) on the forearm rims, in FORE_NODES order."""
    _, _, bi, fi = fore_rims()
    side = {"back": bi, "front": fi}
    return [min(side[s], key=lambda p: abs(p[1] - v)) for s, v in FORE_NODES]
