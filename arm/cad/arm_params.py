"""Single source of truth for every arm dimension (mm, deg).

World frame: origin on the shoulder axis at the shoulder output-flange face.
+Y is the shoulder axis pointing outboard (away from the torso), +X forward,
+Z up. At zero shoulder angle the arm hangs along -Z; the elbow axis is
parallel to Y.

Elbow frame E (used for everything round the elbow): z is the elbow-actuator
axis (lid rear face z = 0, output toward +z = world +Y), y is the distance
below the elbow axis (the forearm length coordinate s when hanging) and x is
forward. A direction at angle psi in E is world (cos psi, 0, -sin psi):
0 = forward, 90 = down, 270 = up.

Shoulder and elbow numbers are read from their own sources (shoulder
parts.md / gen_actuator_3mf.py, elbow params.py) and only re-stated here
where the shoulder code has them inline; gen_arm.py asserts them.
"""

import math
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "elbow", "cad"))
import params as ep  # noqa: E402  (elbow params, path set above)

# ---------------------------------------------------------------- geometry (arm/research.md s2, 160 cm)
L_UPPER = 298.0  # shoulder axis -> elbow axis
L_FOREARM = 234.0  # elbow axis -> wrist flange face
L_HAND = 173.0  # wrist flange face -> fingertip
Z_ELBOW = -L_UPPER
THETA_MIN, THETA_MAX = -5.0, 140.0  # hard stops (software 0..135)
SWEEP = [-5.0, 0.0, 20.0, 40.0, 60.0, 80.0, 100.0, 120.0, 135.0, 140.0]

# ---------------------------------------------------------------- loads (arm never weaker than the shoulder)
T_SH = 50.0  # shoulder current-limit / proof torque (shoulder calc.txt)
M_SH_TILT = 50.0  # shoulder tilt proof
T_EL = ep.T_PROOF  # elbow output at the odesc 10 a current limit
G = 9.81

# ---------------------------------------------------------------- materials
SIG_ASA_XY, SIG_ASA_Z = 37.0 - 3.0, 31.0 - 4.0  # bambu asa tds tensile, mean - 1 sd
SIG_PLA_XY = 35.0 - 4.0  # bambu pla basic tds
SF_PRINT = 2.0  # printed parts against mean - 1 sd at the limit loads
MU_PRINT = 0.30  # asa on asa / asa on 6061 static friction used for printed joints
MU_METAL = 0.15  # steel / aluminium faces (shoulder calc)

# ---------------------------------------------------------------- shoulder interface (shoulder parts.md 42, 43, 45)
SH_FLANGE_Z = 95.5  # flange face in shoulder z
SH_M5_R, SH_M5_ANG = 26.0, [30.0 + 60.0 * k for k in range(6)]  # 6 x m5, tapped 8 deep in en24t
SH_M5_TAP = 8.0
SH_M4_HEAD_R, SH_M4_HEAD_ANG = 27.0, [60.0, 180.0, 300.0]  # carrier-2 screw heads flush with the face
SH_PILOT_R, SH_PILOT_DEPTH = 20.0, 2.0  # d40 h7 pilot
SH_COVER_Y = -1.0  # stationary cover front face (world y)
SH_R = 50.0  # housing and cover radius

# ---------------------------------------------------------------- adapter plate 6061-t6 (cnc, 8 mm stock)
AD_T = 6.0
AD_AF = 76.0  # hexagon across flats, corners at 0 + 60k
AD_CORNER_R = 6.0
AD_SPIGOT_R, AD_SPIGOT_H = 20.0 - 0.009, 1.8  # d40 g6, 0.2 short of the pilot bottom
AD_BORE_R = 14.0
AD_M5_HOLE_R = 5.5 / 2  # iso 273 medium
AD_M4_R, AD_M4_ANG = 34.0, [15.0 + 60.0 * k for k in range(6)]  # m4 tapped through
AD_RELIEF_R, AD_RELIEF_DEPTH = 4.5, 0.3  # over the shoulder m4 heads
WASHER_M5 = dict(od=10.0, id=5.3, t=1.0)  # iso 7089
M5_SCREW_L = 12.0  # iso 4762 12.9 at 8.0 n*m + loctite 243 (shoulder calc)
M5_HEAD = dict(dk=8.5, k=5.0)

# ---------------------------------------------------------------- upper arm, shoulder half (asa)
Y_BED = 1.0  # inboard face of the upper arm = print bed plane, 2.0 from the shoulder cover
DRUM_R, DRUM_T, DRUM_Y1 = SH_R, 2.5, 61.0  # same diameter as the shoulder housing
HUB_Y1 = 16.0  # hub plate outboard face
HUB_RIM = dict(r=40.5, y=8.0)  # outside the m4 washers the drum floor steps down to y 8
HEX_CLEAR = 0.15  # per flat, printed pocket
M5_POCKET_R, M5_POCKET_Y1 = 5.5, AD_T + WASHER_M5["t"] + M5_HEAD["k"] + 0.5
WASHER_M4L = dict(od=12.0, id=4.3, t=1.0)  # din 9021
M4_HUB_L = 16.0  # iso 4762, hub plate -> adapter thread
M4_HEAD = dict(dk=7.0, k=4.0)
CAP_T = 2.5
CAP_SCREW_R, CAP_SCREW_ANG = 46.0, [45.0 + 90.0 * k for k in range(4)]
CAP_GROOVE = (40.0, 41.2, 0.6)  # decorative groove on the cap face: r in, r out, depth
CABLE_EXIT_R, CABLE_EXIT_Y = 7.0, 34.0  # d14 hole, rear of the drum

# ---------------------------------------------------------------- upper arm beam (asa, closed octagon shell)
BEAM_T = 2.5
BEAM_Y1 = 61.0
Z_JOINT = -150.0  # bolted joint between the two upper-arm prints
Z_CAV_TOP = -46.0  # shell cavity opens into the drum here
Z_CAV_BOT = -200.0
CROWN_POCKET = dict(inset=3.0, y=(44.0, 72.0), c=10.0)  # lightening pocket in the crown, clear of channel and ring inserts
RING_POCKET = 1.5  # front ring sits this deep in the crown face (shear key for the housing torque)
CROWN_Y1 = 9.5 + ep.Z_BRG0 + ep.T_FLANGE_COVER + RING_POCKET  # crown outboard face (world y); pocket floor = cover-flange face


def beam_station(z):
    """Outer section (x back, x front, y outboard, chamfer) of the upper arm at world z."""
    xb = -32.0 - 2.0 * min(1.0, (-30.0 - z) / 196.0)
    if z >= -208.0:
        xf = 32.0 - 4.0 * (-30.0 - z) / 178.0
    elif z >= -236.0:
        xf = 28.0 - 16.0 * (-208.0 - z) / 28.0
    else:
        xf = 12.0
    t = min(1.0, max(0.0, (-196.0 - z) / 30.0))  # flare 0..1 between z -196 and -226
    return xb, xf, BEAM_Y1 + t * (CROWN_Y1 - BEAM_Y1), 15.0 - 9.0 * t


BEAM_Z_UP = [-30.0, Z_JOINT]
BEAM_Z_LOW = [Z_JOINT, -196.0, -208.0, -226.0, -236.0, Z_ELBOW + 20.0]
TAB_W, TAB_IN, TAB_C = 14.0, 8.0, 4.0  # joint collar: width outside the shell, overlap into the shell, chamfer
TAB_H_UP, TAB_H_LOW = 8.0, 10.0
TAB_BOLT_Y = [7.0, 55.0]
TAB_DOWEL_Y = 31.0
M4_TAB_L = 16.0
DOWEL4 = dict(d=4.0, l=16.0)  # iso 8734
INSERT_M4 = dict(d_hole=5.6, length=8.1, depth=9.1)  # ruthex rx-m4x8.1
INSERT_M3 = ep.INSERT  # ruthex rx-m3x5.7

# ---------------------------------------------------------------- elbow placement
Y_E0 = Y_BED + 8.0 + 0.5  # lid rear face: 8 mm rear ear + 0.5 air
E_ROT = 36.0  # actuator turned about its axis: lead port 220 -> 256 (up, 14 deg back)
SADDLE_R = ep.R_FLANGE + 1.5
EAR_Z = (-8.5, -0.5)  # rear ear, elbow frame z
EAR_R = 24.0
EAR_BOX = (-30.0, 12.0, -50.0)  # x0, x1, y top (elbow frame y = -up)
CHANNEL = dict(x=(-24.0, 4.0), y=(6.0, 40.0), z_lo=25.0)  # crown cable channel: world x, world y, height above the axis
GROOVE = dict(w=6.0, d=3.0)  # encoder wire groove on the ear inner face

# ---------------------------------------------------------------- front ring 6061-t6 (cnc, 4 mm plate)
RING_Z0 = ep.Z_BRG0 + ep.T_FLANGE_COVER  # 74.3, on the cover flange
RING_T = 4.0
RING_Z1 = RING_Z0 + RING_T
RING_ID_R = ep.R_NECK + 0.1  # pilots on the cover neck d52
RING_R = 44.0
RING_TAB = (-31.0, 9.0, -69.0)  # x0, x1, y top (69 above the axis)
RING_FILLET = 4.0
RING_BOLTS = [(-24.0, -52.0), (2.0, -52.0), (-24.0, -63.0), (2.0, -63.0)]  # elbow frame (x, y)
M4_RING_L = 12.0  # iso 10642, flush in the ring
FLANGE_SCREW_L = 16.0  # din 912 m3: replaces the elbow m3 x 12 (ring under the heads)
Z_FLANGE_HEAD1 = RING_Z1 + ep.WASHER_M3["t"] + ep.M3_SHCS["k"]

# ---------------------------------------------------------------- hard stop (pin in the ring, slot in cheek a)
STOP_R = ep.R_FLANGE_SCREW
STOP_PSI = (ep.ANG_FLANGE[5] + ep.ANG_FLANGE[6]) / 2 + E_ROT - 360.0  # between two flange screws
STOP_PIN = dict(d=5.0, l=14.0)  # iso 8734, pressed through the ring and its boss (7 mm)
STOP_BOSS = dict(r=5.0, h=3.0)  # on the ring front face, between two flange screw heads
ORING = dict(id=4.5, cs=1.5, n=3)  # nbr 70, din 3771
ORING_OD = STOP_PIN["d"] + 2 * ORING["cs"]
SLOT_W = ORING_OD + 0.6

# ---------------------------------------------------------------- forearm (elbow frame: x = x_f, y = s)
CHEEK_A_Z = (Z_FLANGE_HEAD1 + 1.0, Z_FLANGE_HEAD1 + 1.0 + 8.0)
CHEEK_A_R, CHEEK_A_TOP = 44.0, -30.0
CHEEK_A_TIP, CHEEK_B_TIP = (30.0, 80.0), (27.0, 80.0)  # flank end points (x, s); cheek flanks are tangent to the disc
CHEEK_GROOVE = (24.0, 25.2, 0.6)  # decorative groove on the cheek a face: r in, r out, depth
BOSS_R, BOSS_R_MAX = 18.75, ep.BRG_OUT_LIP_ID / 2 - 0.7  # 61807 inner-ring abutment, middle of skf da 37..38; teardrop inside the cover lip
BOSS_Z0 = ep.Z_BRG1  # clamps the 61807 inner ring
BOSS_FACE = 0.5  # round (inside da max 38) for this length at the ring face, teardrop behind it
HUB_SCREW_L = 16.0  # din 912 m3
HUB_CBORE = dict(d=6.2, depth=3.4)
HUB_DOWEL = dict(d=3.0, l=16.0, in_boss=11.0)  # iso 8734; 5 in the elbow hub (as the elbow), 11 in the asa
SLOT_DEPTH = 6.0  # 2 mm floor left in cheek a
FA_POST = -22.0  # posterior face (print bed)
FA_CUT_R = 47.0  # concave clearance round the cradle
FA_T = 2.5  # shell wall
Z_CHEEK_B_IN = -12.5  # forearm inboard face = cheek b inner face
FA_ZC = (Z_CHEEK_B_IN + CHEEK_A_Z[0]) / 2  # forearm centre plane (elbow z)
FA_HALF_WRIST = 22.0
S_FULL = 80.0  # full clevis width down to here; open anterior trough above, closed tube + web below
S_WALL = 100.0  # cheek-side wall tapers 8 -> 2.5 mm by here; anterior face straight to here
S_END = 226.0  # wrist end block start
FA_C = 8.0
FA_ROOF_C = 14.0  # inner chamfer at the anterior corners: keeps every roof bridge of the print under 33 mm
# anterior edge (s, a): straight flank from (46, 10) to (80, 30), then the tube
FA_ANT = [(30.0, 10.0 - 16.0 * 20.0 / 34.0), (S_FULL, 30.0), (S_WALL, 30.0), (S_END, 22.0), (L_FOREARM, 22.0)]


def fa_z(s):
    """Inboard and outboard forearm faces (elbow z) at length s."""
    if s <= S_FULL:
        return Z_CHEEK_B_IN, CHEEK_A_Z[1]
    t = min(1.0, (s - S_FULL) / (S_END - S_FULL))
    return (Z_CHEEK_B_IN + t * (FA_ZC - FA_HALF_WRIST - Z_CHEEK_B_IN),
            CHEEK_A_Z[1] + t * (FA_ZC + FA_HALF_WRIST - CHEEK_A_Z[1]))


def fa_a(s):
    """Anterior face of the forearm at length s (linear between FA_ANT points)."""
    for (s0, a0), (s1, a1) in zip(FA_ANT, FA_ANT[1:]):
        if s <= s1:
            return a0 + (a1 - a0) * (s - s0) / (s1 - s0)
    return FA_ANT[-1][1]


CHEEK_B_JOINT = [(-15.0, 52.0), (-15.0, 70.0), (8.0, 60.0), (14.0, 72.0)]  # m4 bosses, elbow frame (x, y)
CHEEK_B_BOSS_R = 5.5
CHEEK_B_HOLE_R = 4.8 / 2  # 0.4 radial float: cheek b is aligned to the pin before tightening
M4_CHEEK_B_L = 16.0
WRIST = dict(pcd_r=15.0, n=4, ang0=45.0, spigot_r=10.0 - 0.01, spigot_h=1.8, recess_r=10.0 + 0.02, recess_h=2.0,
             bore_r=5.0)  # 4 x m3 on d30; d20 h7 spigot on the forearm, h8 recess in the wrist part

# ---------------------------------------------------------------- passive side (elbow frame z, outward = more negative)
BRG_P = dict(d=20.0, D=32.0, B=7.0, d1=23.85, D1=28.2, nballs=18, dball=3.0)  # skf 61804-2rs1
Z_P_IN0, Z_P_IN1 = -20.6, -13.6  # 61804 inner ring (fixed on the pin)
CHEEK_B_Z = (-21.0, Z_CHEEK_B_IN)
CHEEK_B_R = 34.0
CHEEK_B_LIP = dict(z=-13.25, r=14.5)  # inner lip (printed on the bed side)
BORE_P_R = BRG_P["D"] / 2  # slip fit: outer ring floats 0.35 each way (point load on the outer ring)
PIN = dict(spigot_r=8.0, z_spigot=-2.5, flange_r=19.0, z_flange=(-11.5, -8.5), shoulder_r=11.5,
           z_end=Z_P_IN0 + 0.2, bore_r=5.0, screw_r=15.0, tap_r=7.5)
PIN_SCREW_ANG = [90.0, 210.0, 330.0]
PIN_TAP_ANG = [90.0, 210.0, 330.0]  # m2.5 tapped in the journal end, clear of the wire groove at 270
PIN_TAP_DEPTH = 6.0
L_PIN_SCREW = 8.0  # iso 10642 m3
RETAINER = dict(r0=14.5, r1=30.0, z=(-22.0, -21.0))  # asa washer: outer-ring stop on the cover side
BRACKET = dict(boss_r=11.0, r=20.0, z_boss=(-22.5, Z_P_IN0), z_plate=(-25.5, -22.5), hole_r=5.0, csk_r=7.5,
               groove=(6.0, 13.0, 1.5))  # wire groove under the pcb: width, length, depth
L_BRACKET_SCREW = 10.0  # iso 10642 m2.5
PCB_OUT = dict(w=30.0, t=1.6, hole_r=17.0, ang0=45.0)  # same board as shoulder p12
Z_PCB_OUT = (BRACKET["z_plate"][0] - PCB_OUT["t"], BRACKET["z_plate"][0])
Z_IC_OUT = (Z_PCB_OUT[0] - ep.IC["h"], Z_PCB_OUT[0])
Z_MAG_OUT = (Z_IC_OUT[0] - 1.0 - ep.MAG["h"], Z_IC_OUT[0] - 1.0)
L_PCB_SCREW = 4.0  # din 912 m2.5
COVER = dict(r=25.0, ri=23.5, z_end=Z_MAG_OUT[0] - 2.0, boss_r=3.5, boss_pcd_r=26.5, mag_boss_r=5.0, seat=-28.5)
COVER_ANG = [0.0, 120.0, 240.0]  # forearm frame
L_COVER_SCREW = 12.0  # din 912 m3, head in a counterbore at COVER["seat"]
MAG_SPACING_MIN = 30.0  # stray-field rule between the two encoder magnets / ics

# ---------------------------------------------------------------- dummy hand (pla)
HAND = dict(collar=(L_FOREARM, L_FOREARM + 10.0), neck=(L_FOREARM + 10.0, L_FOREARM + 28.0),
            palm=(L_FOREARM + 48.0, L_FOREARM + 106.0), fingers=L_FOREARM + 106.0)
FINGERS = [(28.5, 61.0), (9.5, 67.0), (-9.5, 63.0), (-28.5, 52.0)]  # x centre, length (index on the thumb side, +x)
HAND_SCREW_L = 12.0  # din 912 m3
HAND_SEAT = L_FOREARM + 6.0  # screw head seat in the collar

# ---------------------------------------------------------------- print bed (bambu p1s 256 x 256 x 256, 5 mm margin)
BED = 246.0


def polar(r, deg):
    """(x, y) for radius r at angle deg."""
    a = math.radians(deg)
    return r * math.cos(a), r * math.sin(a)
