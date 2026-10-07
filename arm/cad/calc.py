"""Engineering checks for the VAYN arm Rev 0.

Every number quoted in arm/parts.md is printed by this script. Geometry comes
from arm_params.py, section properties from exact slices of the gen_arm.py
solids, masses from mass.txt (run gen_arm.py first).
Units: mm, N, N*m, MPa. Run: python calc.py > calc.txt
"""

import math
import os

import cadquery as cq

import arm_params as p
import gen_arm as ga
from arm_params import ep
from gen_arm import occ

HERE = os.path.dirname(os.path.abspath(__file__))
PRELOAD_PER_NM = {"M3": 4240 / 2.14, "M4": 7600 / 5.1, "M5": 12400 / 10.0}  # 12.9, mu 0.12 thread (vdi 2230, shoulder calc)
TORQUE = {"M3 elbow": 0.2, "M3": 0.4, "M4": 1.0, "M5": 8.0}  # n*m; "M3 elbow" = screws the elbow already specifies
SIG_XY, SIG_Z = p.SIG_ASA_XY / p.SF_PRINT, p.SIG_ASA_Z / p.SF_PRINT  # printed allowables at the limit loads
TAU_Z = SIG_Z / math.sqrt(3)  # shear across layers (von mises on the z strength)
SIG_6061 = 276.0 / 2.0  # 6061-t6 yield / 2
SIG_PIN = 1000.0  # iso 8734 dowel (hardened, >= 58 hrc) bending allowable, well under its yield
BRG = {"61804-2RS1": (4030.0, 2320.0), "61807-2RS1": (4750.0, 3200.0)}  # c, c0 (n), lower of the sourced values
S0_PROOF = 1.0  # skf static safety, infrequent motion, normal load certainty
PULLOUT = {"M3": 1400.0, "M4": 1400.0 * (5.6 * 8.1) / (4.0 * 5.7)}  # insert pull-out in asa (m4 scaled by hole area)
J_ROTOR = 4e-5  # mn5008 rotor, elbow research estimate (to be measured)
OMEGA_MAX = math.radians(180.0)  # software speed cap
SQUEEZE = 0.25 * p.ORING["cs"]  # usable o-ring squeeze before the rubber goes solid
WASHER_M4_A = math.pi / 4 * (p.WASHER_M4L["od"] ** 2 - p.WASHER_M4L["id"] ** 2)


def line(title):
    """Print a section header."""
    print(f"\n=== {title} " + "=" * max(0, 60 - len(title)))


def read_mass():
    """Return the key = value totals from mass.txt as floats."""
    out = {}
    with open(os.path.join(HERE, "mass.txt"), encoding="utf-8") as f:
        for row in f:
            if " = " in row:
                k, v = row.split(" = ")
                out[k.strip()] = float(v)
    return out


def preload(size, torque=None):
    """Assembly preload (n) for a 12.9 screw of size at torque (default from TORQUE)."""
    return PRELOAD_PER_NM[size[:2]] * (TORQUE[size] if torque is None else torque)


def section(solid, z, h=0.02):
    """Exact section of solid at world z: area, centroid, second moments, extreme fibres.

    a thin slab is cut out of the solid; its volume / h is the area and its
    inertia / h the second moment of area (the slab-thickness term is h^2/12).
    """
    sl = solid ^ occ.box(-400, 400, -400, 400, z - h / 2, z + h / 2)
    c, m, bb = sl.s.Center(), cq.Shape.matrixOfInertia(sl.s), sl.bounding_box()
    return dict(a=sl.volume() / h, xc=c.x, yc=c.y, ixx=m[0][0] / h, iyy=m[1][1] / h, ixy=abs(m[0][1]) / h,
                cx=max(c.x - bb[0], bb[3] - c.x), cy=max(c.y - bb[1], bb[4] - c.y), w=bb[3] - bb[0], t=bb[4] - bb[1])


def bredt(u0, u1, v0, v1, c, t):
    """Thin-wall closed octagon: enclosed midline area and perimeter (mm2, mm)."""
    pts = ga.octagon(u0 + t / 2, u1 - t / 2, v0 + t / 2, v1 - t / 2, c - t / 2 * (2 - math.sqrt(2)))
    area = 0.5 * abs(sum(x0 * y1 - x1 * y0 for (x0, y0), (x1, y1) in zip(pts, pts[1:] + pts[:1])))
    return area, sum(math.dist(a, b) for a, b in zip(pts, pts[1:] + pts[:1]))


def stress(s, m_y, m_x, torque, a_m, t):
    """Bending (about world y and x) + bredt shear: returns sigma, tau, von mises (MPa)."""
    sig = m_y * 1000 * s["cx"] / s["iyy"] + m_x * 1000 * s["cy"] / s["ixx"]
    tau = torque * 1000 / (2 * a_m * t) if a_m else 0.0
    return sig, tau, math.hypot(sig, math.sqrt(3) * tau)


def joint(name, n, size, r_bolt, mu, torque_load, r_in=None, r_out=None, tilt=0.0):
    """Friction torque (and annular separation moment) of n bolts on radius r_bolt."""
    fm = preload(size)
    t_slip = n * fm * mu * r_bolt / 1000
    sep = ""
    if r_out:
        w = math.pi * (r_out ** 4 - r_in ** 4) / (4 * r_out)
        m_sep = n * fm * w / (math.pi * (r_out ** 2 - r_in ** 2)) / 1000
        sep = f"  separation {m_sep:5.1f} N*m (load {tilt:.1f}, SF {m_sep / tilt:4.1f})"
    print(f"{name:34s} {n} x {size[:2]} @ {TORQUE[size]} N*m: FM {fm:5.0f} N  slip {t_slip:6.1f} N*m "
          f"(load {torque_load:.1f}, SF {t_slip / torque_load:4.2f}){sep}")
    return fm, t_slip


# ---------------------------------------------------------------- 0 build the solids that are sliced
occ.use_occ_kernel()
UPPER, LOWER, FORE = ga.upper_shoulder_half(), ga.upper_elbow_half(), ga.elbow_to_world(ga.forearm())
M = read_mass()
S_H = p.L_FOREARM + p.L_HAND / 2  # hand centre from the elbow axis
F3 = p.M_SH_TILT * 1000 / (p.L_UPPER + p.L_FOREARM)  # lateral at the wrist, forearm straight
F4 = p.M_SH_TILT * 1000 / math.hypot(p.L_UPPER, S_H)  # lateral at the hand centre, forearm at 90 deg
Y_BRG_A = p.Y_E0 + ep.Z_BRG0 + ep.BRG_OUT["B"] / 2  # 61807 centre, world y
Y_BRG_B = p.Y_E0 + (p.Z_P_IN0 + p.Z_P_IN1) / 2  # 61804 centre, world y
SPAN = Y_BRG_A - Y_BRG_B
F_COUPLE = F4 * S_H / SPAN  # clevis bearing couple in lc4

# ---------------------------------------------------------------- 1 mass
line("1 mass, gravity, inertia (mass.txt: printed parts at the print estimate)")
m_u, m_f, m_h = M["m_upper"] / 1000, M["m_fore"] / 1000, M["m_hand"] / 1000
r_u, r_f = -M["com_upper_z"] / 1000, -M["com_fore_z"] / 1000
r_fe = r_f - p.L_UPPER / 1000  # forearm group com from the elbow axis
print(f"upper arm + elbow actuator {m_u:.3f} kg at {r_u * 1000:.0f} mm   forearm + hand {m_f:.3f} kg at {r_f * 1000:.0f} mm "
      f"(hand {m_h:.3f} kg)   arm {M['m_arm'] / 1000:.3f} kg vs research budget 1.18 kg ({M['m_arm'] / 1180 - 1:+.0%})")
alpha = OMEGA_MAX / 0.25
t_g = p.G * (m_u * r_u + m_f * r_f)
j_sh = m_u * r_u ** 2 + m_f * r_f ** 2  # point masses: lower bound
print(f"shoulder, arm horizontal: gravity {t_g:.2f} N*m, + {alpha:.2f} rad/s2 (point-mass J {j_sh:.4f}) {t_g + j_sh * alpha:.2f} N*m "
      f"vs 30 N*m continuous (SF {30 / (t_g + j_sh * alpha):.1f})")
t_ge = p.G * m_f * r_fe
j_load = max(m_f * r_fe ** 2, 0.025)  # elbow research s0 load inertia when larger
j_refl = J_ROTOR * ep.RATIO ** 2
print(f"elbow, forearm horizontal: gravity {t_ge:.2f} N*m (com {r_fe * 1000:.0f} mm) vs {ep.T_STATIC} static / {ep.T_CONT} continuous "
      f"rating; load J {j_load:.4f} + reflected rotor {j_refl:.4f} kg*m2")

# ---------------------------------------------------------------- 2 load cases
line("2 load cases (arm never weaker than the shoulder: 50 N*m proof, 50 N*m tilt proof)")
print(f"LC1 shoulder proof as a force at the elbow: {p.T_SH * 1000 / p.L_UPPER:.1f} N")
print(f"LC2 envelope: in-plane moment {p.T_SH:.0f} N*m at the shoulder -> {p.T_EL:.2f} N*m (elbow proof) at the elbow")
print(f"LC3 tilt proof as a lateral force at the wrist (forearm straight, {p.L_UPPER + p.L_FOREARM:.0f} mm): {F3:.1f} N; "
      f"at the palm edge (40 mm) it also twists the forearm {F3 * 0.040:.2f} N*m")
print(f"LC4 tilt proof as a lateral force at the hand centre, forearm at 90 deg ({S_H:.1f} mm out, lever "
      f"{math.hypot(p.L_UPPER, S_H):.1f}): {F4:.1f} N -> upper-arm torsion {F4 * S_H / 1000:.2f} N*m, "
      f"clevis couple {F_COUPLE:.0f} N on {SPAN:.1f} mm bearing span")
print(f"LC5 hard stop: elbow current limit {p.T_EL:.2f} N*m x 1.5 = {1.5 * p.T_EL:.2f} N*m (impact: section 7)")
print(f"allowables (mean - 1 sd / {p.SF_PRINT}): ASA in-layer {SIG_XY:.1f}, across layers {SIG_Z:.1f}, "
      f"interlayer shear {TAU_Z:.1f} MPa; 6061-T6 {SIG_6061:.0f} MPa")

# ---------------------------------------------------------------- 3 upper arm
line("3 upper-arm sections (exact slices; bending sums both axes at the extreme fibres)")
print("    z   part    A mm2   Iy(x2) cm4  Ix(y2) cm4  Ixy/Ixx   LC2 sig  LC3 sig  LC4 sig/tau   LC2+LC4 vm   limit")
for z in (-50.0, -100.0, -140.0, -165.0, -196.0, -220.0, -236.0):
    solid, name = (UPPER, "104") if z > p.Z_JOINT else (LOWER, "110")
    s = section(solid, z)
    xb, xf, y1, c = p.beam_station(z)
    t = p.BEAM_T if z >= -196.0 else p.CROWN_POCKET["inset"]
    a_m, _ = bredt(xb, xf, p.Y_BED, y1, c, t)
    m2 = p.T_EL + (p.T_SH - p.T_EL) * (z - p.Z_ELBOW) / -p.Z_ELBOW
    m3 = F3 * (z - p.Z_ELBOW + p.L_FOREARM) / 1000
    m4 = F4 * (z - p.Z_ELBOW) / 1000
    s2, _, _ = stress(s, m2, 0, 0, 0, t)
    s3, _, _ = stress(s, 0, m3, 0, 0, t)
    s4, t4, _ = stress(s, 0, m4, F4 * S_H / 1000, a_m, t)
    _, _, vm = stress(s, m2, m4, F4 * S_H / 1000, a_m, t)
    ok = "OK" if max(s2, s3, vm) <= SIG_XY and t4 <= TAU_Z else "FAIL"
    print(f"{z:6.0f}   {name}  {s['a']:7.0f}  {s['iyy'] / 1e4:9.2f}  {s['ixx'] / 1e4:9.2f}   {s['ixy'] / s['ixx']:6.3f}  "
          f"{s2:7.2f}  {s3:7.2f}  {s4:6.2f}/{t4:4.2f}   {vm:9.2f}   {ok}")
print("torsion: bredt on the octagon midline (wall 2.5 in the beam, 3.0 pocket inset in the crown); below z -236 the "
      "LC4 couple enters through the ring bolts and the ear (section 6)")

# ---------------------------------------------------------------- 4 forearm
line("4 forearm sections (forearm at 90 deg; LC4 + elbow proof + LC3 palm-edge twist together)")
print("     s    A mm2   Iy(x2) cm4  Ix(y2) cm4   in-plane  lateral  tau    vm    limit")
for sv in (90.0, 100.0, 160.0, 220.0):
    s = section(FORE, p.Z_ELBOW - sv)
    z0, z1 = p.fa_z(sv)
    a_m, _ = bredt(p.FA_POST, p.fa_a(sv), z0, z1, p.FA_C, p.FA_T)
    m_in = p.T_EL * (S_H - sv) / S_H
    m_lat = F4 * (S_H - sv) / 1000
    sig, tau, vm = stress(s, m_in, m_lat, F3 * 0.040, a_m, p.FA_T)
    s_in, _, _ = stress(s, m_in, 0, 0, 0, p.FA_T)
    ok = "OK" if vm <= SIG_XY and tau <= TAU_Z else "FAIL"
    print(f"{sv:6.0f}  {s['a']:7.0f}  {s['iyy'] / 1e4:9.2f}  {s['ixx'] / 1e4:9.2f}   {s_in:7.2f}  {sig - s_in:7.2f}  {tau:5.2f}  {vm:5.2f}   {ok}")

# ---------------------------------------------------------------- 5 joints
line("5 bolted joints (12.9 screws, preload vdi 2230 table mu 0.12; joint friction mu 0.15 metal, 0.30 printed)")
joint("adapter -> shoulder flange", 6, "M5", p.SH_M5_R, p.MU_METAL, p.T_SH, 20.0, 39.0, p.M_SH_TILT)
fm, t_slip = joint("hub plate -> adapter (ASA on 6061)", 6, "M4", p.AD_M4_R, p.MU_PRINT, p.T_SH, 15.0, p.AD_AF / 2, p.M_SH_TILT)
print(f"  DIN 9021 washer on ASA {fm / WASHER_M4_A:.1f} MPa (compression, limit {SIG_XY:.1f}); thread in 6061 "
      f"{p.AD_T:.0f} mm = {p.AD_T / 0.7:.0f} pitches")
flat = p.AD_AF / math.sqrt(3) / 2 - p.AD_CORNER_R * math.tan(math.radians(30))
f_flat = (p.T_SH - 0) * 1000 / (6 * 2 / 3 * flat)
key_d = p.AD_T - p.Y_BED
print(f"  hex key (backup, all 50 N*m, best-case triangular contact over half of each flat): {f_flat:.0f} N per flat, "
      f"peak {2 * f_flat / (flat * key_d):.1f} MPa on {key_d:.0f} mm of pocket (limit {SIG_XY:.1f})")
# mid-span joint: bolt rows in x (in-plane moment) and in y (lateral moment)
bolts, dowels = ga.joint_points()
dx = max(x for x, _ in bolts) - min(x for x, _ in bolts)
dy = max(p.TAB_BOLT_Y) - min(p.TAB_BOLT_Y)
m2j = p.T_EL + (p.T_SH - p.T_EL) * (p.Z_JOINT - p.Z_ELBOW) / -p.Z_ELBOW
m3j = F3 * (p.Z_JOINT - p.Z_ELBOW + p.L_FOREARM) / 1000
fm = preload("M4")
f_b = max(m2j * 1000 / (2 * dx), m3j * 1000 / (2 * dy))
r_j = [math.hypot(x, y - p.TAB_DOWEL_Y) for x, y in bolts]
t_j = sum(fm * p.MU_PRINT * r / 1000 for r in r_j)
f_dw = F4 * S_H / (dowels[1][0] - dowels[0][0])
print(f"mid-span joint 4 x M4 @ {TORQUE['M4']}: in-plane {m2j:.1f} N*m / lateral {m3j:.1f} N*m -> {f_b:.0f} N per bolt "
      f"vs FM {fm:.0f} (no separation, SF {fm / f_b:.1f}); bolt <= FM + load {fm + f_b:.0f} N vs insert pull-out "
      f"~{PULLOUT['M4']:.0f} N (SF {PULLOUT['M4'] / (fm + f_b):.1f})")
print(f"  torsion LC4 {F4 * S_H / 1000:.1f} N*m vs friction {t_j:.1f} N*m (SF {t_j / (F4 * S_H / 1000):.1f}); "
      f"dowels 2 x D4 backup {f_dw:.0f} N each, bearing {f_dw / (p.DOWEL4['d'] * p.DOWEL4['l'] / 2):.1f} MPa (limit {SIG_XY:.1f})")
r_ring = [math.hypot(x, y) for x, y in p.RING_BOLTS]
t_ring = sum(preload("M4") * p.MU_PRINT * r / 1000 for r in r_ring)
t_in = 1.5 * p.T_EL + p.T_EL * (1 + 1 / ep.RATIO)
print(f"front ring -> crown 4 x M4 csk @ {TORQUE['M4']}: friction {t_ring:.0f} N*m vs stop + housing reaction "
      f"{t_in:.1f} N*m (SF {t_ring / t_in:.1f}), plus the {p.RING_POCKET} mm pocket key")
fm3 = preload("M3 elbow")
t_fl = len(ep.ANG_FLANGE) * fm3 * p.MU_PRINT * ep.R_FLANGE_SCREW / 1000
tip = p.RING_Z1 + ep.WASHER_M3["t"] - p.FLANGE_SCREW_L
print(f"ring + cover -> housing {len(ep.ANG_FLANGE)} x M3x{p.FLANGE_SCREW_L:.0f} @ {TORQUE['M3 elbow']}: ring/cover friction "
      f"{t_fl:.1f} N*m vs housing reaction {p.T_EL * (1 + 1 / ep.RATIO):.2f}; insert engagement "
      f"{min(ep.Z_HF - tip, ep.INSERT['length']):.1f} of {ep.INSERT['length']}, tip {tip - (ep.Z_HF - ep.INSERT['depth']):.1f} above the hole floor")
joint("cheek A -> elbow hub (mu 0.20 as elbow)", len(ep.ANG_HUB_INSERT), "M3 elbow", ep.R_HUB_INSERT, 0.20, p.T_EL)
f_dw = p.T_EL * 1000 / ep.R_HUB_INSERT / len(ep.ANG_HUB_DOWEL)
q_dw = f_dw / (p.HUB_DOWEL["d"] * p.HUB_DOWEL["in_boss"])
print(f"  dowels {len(ep.ANG_HUB_DOWEL)} x D{p.HUB_DOWEL['d']:.0f}x{p.HUB_DOWEL['l']:.0f} (backup, full proof): {f_dw:.0f} N each, "
      f"ASA bearing {q_dw:.1f} MPa over {p.HUB_DOWEL['in_boss']:.0f} mm (limit across layers {SIG_Z:.1f}, SF {p.SIG_ASA_Z / q_dw:.1f} on strength)")
tip = p.CHEEK_A_Z[1] - p.HUB_CBORE["depth"] - p.HUB_SCREW_L
print(f"  hub screw M3x{p.HUB_SCREW_L:.0f}: engagement {min(ep.Z_HUB1 - tip, ep.INSERT['length']):.1f} of {ep.INSERT['length']}, "
      f"tip {tip - (ep.Z_HUB1 - ep.INSERT['depth']):.1f} above the hole floor")
fm = preload("M4")
f_cb = len(p.CHEEK_B_JOINT) * fm * p.MU_PRINT
print(f"cheek B -> forearm 4 x M4 @ {TORQUE['M4']}: friction {f_cb:.0f} N vs LC4 bearing force {F_COUPLE:.0f} N "
      f"(SF {f_cb / F_COUPLE:.1f}); holes float {p.CHEEK_B_HOLE_R - 2.0:.1f} mm radial for alignment to the pin")
fm = preload("M3")
z_brg_b = (p.Z_P_IN0 + p.Z_P_IN1) / 2
f_pin = F_COUPLE * (p.EAR_Z[0] - z_brg_b) * p.PIN["screw_r"] / (1.5 * p.PIN["screw_r"] ** 2)
print(f"pin -> ear 3 x M3 csk @ {TORQUE['M3']}: LC4 pin moment -> {f_pin:.0f} N on the worst screw vs FM {fm:.0f} "
      f"(no separation, SF {fm / f_pin:.1f}); insert pull-out ~{PULLOUT['M3']:.0f} N (SF {PULLOUT['M3'] / (fm + f_pin):.1f})")

# ---------------------------------------------------------------- 6 clevis
line("6 clevis: bearings, pin, ear (LC4 couple + LC3 / elbow internal loads)")
c, c0 = BRG["61804-2RS1"]
print(f"61804 passive: Fr {F_COUPLE:.0f} N  s0 {c0 / F_COUPLE:.1f} (need {S0_PROOF})  outer ring slip fit, axial float "
      f"{p.Z_P_IN0 - p.RETAINER['z'][1]:.2f} / {p.CHEEK_B_LIP['z'] - p.Z_P_IN1:.2f} mm")
fr = F_COUPLE + 94.0  # elbow cage net force at proof, share 0.40 (elbow calc.txt)
p0 = max(fr, 0.6 * fr + 0.5 * F4)
print(f"61807 output: Fr {F_COUPLE:.0f} + 94 (elbow internal, proof) = {fr:.0f} N, Fa {F4:.0f} N -> P0 {p0:.0f} N  "
      f"s0 {BRG['61807-2RS1'][1] / p0:.1f} (need {S0_PROOF})")
d_b = 2 * p.PIN["bore_r"]
sig_pin = max(F_COUPLE * (z_end - z_brg_b) * d / 2 / (math.pi * (d ** 4 - d_b ** 4) / 64)
              for d, z_end in ((p.BRG_P["d"], p.Z_P_IN1), (2 * p.PIN["shoulder_r"], p.PIN["z_flange"][0])))
spig = p.PIN["z_spigot"] - p.EAR_Z[0]
print(f"passive pin: bending at the flange {sig_pin:.1f} MPa (6061 limit {SIG_6061:.0f}); spigot D{2 * p.PIN['spigot_r']:.0f} "
      f"x {abs(spig):.0f} in the ear: bearing {F_COUPLE / (2 * p.PIN['spigot_r'] * abs(spig)):.1f} MPa (ASA in-layer {SIG_XY:.1f})")
z_root = p.BEAM_Z_LOW[-1] - 1.0
s = section(LOWER, z_root)
arm_x = z_root - p.Z_ELBOW
off = abs(Y_BRG_B - s["yc"])
sig_e = F_COUPLE * arm_x * s["cx"] / s["iyy"]
tau_e = F_COUPLE * off / ((1 - 0.63 * s["t"] / s["w"]) / 3 * s["w"] * s["t"] ** 2)
print(f"ear below the crown (z {z_root:.0f}, {s['w']:.0f} x {s['t']:.0f}, A {s['a']:.0f}): in-plane bending {sig_e:.1f} MPa, "
      f"twist from the {off:.1f} mm bearing offset {tau_e:.1f} MPa -> vm {math.hypot(sig_e, math.sqrt(3) * tau_e):.1f} "
      f"(limit in-layer {SIG_XY:.1f})")

# ---------------------------------------------------------------- 7 hard stop
line("7 hard stop (pin in the ring, 3 o-rings, slot in cheek A)")
stack = p.ORING["n"] * p.ORING["cs"]
z_face = p.RING_Z1 + p.STOP_BOSS["h"]
a_load = p.RING_Z0 + p.STOP_PIN["l"] - stack / 2 - z_face
l_held = p.RING_T + p.STOP_BOSS["h"]


def stop_caps():
    """Stop force (n) at which each part reaches its allowable."""
    pin = SIG_PIN * math.pi * p.STOP_PIN["d"] ** 3 / 32 / a_load
    boss = SIG_6061 * p.STOP_PIN["d"] * l_held / (1 + 6 * a_load / l_held)
    slot = SIG_Z * p.ORING_OD * stack
    return dict(pin=pin, boss=boss, slot=slot)


caps = stop_caps()
for name, t in (("stall at the current limit", p.T_EL), ("LC5 (x 1.5)", 1.5 * p.T_EL)):
    f = t * 1000 / p.STOP_R
    print(f"{name:28s} {t:5.2f} N*m -> {f:4.0f} N: pin bending {32 * f * a_load / (math.pi * p.STOP_PIN['d'] ** 3):4.0f} MPa, "
          f"ring+boss bearing {f * (1 + 6 * a_load / l_held) / (p.STOP_PIN['d'] * l_held):4.0f} MPa, "
          f"slot (o-ring OD x {stack:.1f}) {f / (p.ORING_OD * stack):4.1f} MPa")
f_cap = min(caps.values())
print("capacity: " + ", ".join(f"{k} {v:.0f} N" for k, v in caps.items()) + f" -> {f_cap * p.STOP_R / 1000:.1f} N*m at the stop")
j_tot = j_load + j_refl
e_kin = 0.5 * j_tot * OMEGA_MAX ** 2
f_gear = ep.T_PROOF * j_tot / j_refl * 1000 / p.STOP_R  # stop force at which the rotor share alone reaches elbow proof
print(f"impact at {math.degrees(OMEGA_MAX):.0f} deg/s: J {j_tot:.4f} kg*m2, energy {e_kin:.3f} J; o-ring squeeze {SQUEEZE:.3f} mm "
      f"(25 % of {p.ORING['cs']}), hardening rubber absorbs F*d/3")
for name, t_m in (("motor at the current limit", p.T_EL), ("motor current cut past the soft limit", 0.0)):
    f_lim = min(f_cap, f_gear) if t_m == 0 else f_cap
    e_abs = f_lim * SQUEEZE / 1000 / 3 - t_m * SQUEEZE / p.STOP_R
    w_ok = math.sqrt(2 * e_abs / j_tot) if e_abs > 0 else 0.0
    print(f"  {name:38s}: stop may absorb {max(e_abs, 0):.3f} J -> safe approach speed {math.degrees(w_ok):5.1f} deg/s")
print(f"  gearbox share of the stop torque = J_rotor / J ({j_refl / j_tot:.2f}); with the motor at the limit any impact "
      f"overloads the gearbox past {ep.T_PROOF} N*m -> firmware: current to 0 beyond {p.THETA_MIN + 5:.0f}/{p.THETA_MAX - 5:.0f} deg")
print(f"slot ends at the stops: o-ring touches at {p.THETA_MIN:.0f} and {p.THETA_MAX:.0f} deg (gen.log sweep); "
      f"slot {p.SLOT_W} wide for a {p.ORING_OD:.1f} o-ring, depth {p.SLOT_DEPTH}, floor {p.CHEEK_A_Z[1] - p.CHEEK_A_Z[0] - p.SLOT_DEPTH:.1f}")

# ---------------------------------------------------------------- 8 encoder
line("8 output encoder")
v_mag = math.pi / 4 * ep.MAG["d"] ** 2 * ep.MAG["h"]
for r in (30.0, 33.1, 35.0):
    b = 1.2 * v_mag / (2 * math.pi * r ** 3) * 1000
    print(f"stray field of the other D{ep.MAG['d']:.0f}x{ep.MAG['h']} N35 magnet at {r:.1f} mm (on-axis dipole, Br 1.2 T): {b:.2f} mT "
          f"vs AS5047P working range 35..70 mT ({b / 35:.1%}), uniform part rejected by the differential hall array")
print(f"output magnet to ic {p.Z_IC_OUT[0] - p.Z_MAG_OUT[1]:.2f} mm (0.5..3.0); magnet turns with the forearm (cover), "
      f"ic on the stationary pin bracket")
