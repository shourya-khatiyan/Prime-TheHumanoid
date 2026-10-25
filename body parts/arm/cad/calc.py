"""Engineering checks for the VAYN arm Rev 2 (twin plates, direct-drive LA8308 elbow).

Every number quoted in arm/parts.md and elbow/research.md is printed here.
Geometry comes from arm_params.py, masses from mass.txt (run gen_arm.py first).
Units: mm, N, N*m, MPa, A, W. Run: python calc.py > calc.txt
"""

import math
import os

import arm_params as p

HERE = os.path.dirname(os.path.abspath(__file__))
G = p.G
KT = 8.27 / p.MOTOR["kv"]  # n*m/a (odrive convention, peak phase current)
R25 = p.MOTOR["r_phase"]
CU = 0.00393  # copper resistance tempco /k
T_AMB, T_NTC = 35.0, 70.0  # indian summer ambient; odesc motor-thermistor limit (petg hdt 62 c at 1.8 mpa)
R_TH = (2.0, 3.0, 4.0)  # k/w winding -> ambient, still air: unknown until the bench thermal-hold test
C_TH = 0.10 * 900 + 0.15 * 460 + 0.06 * 385 + 0.026 * 440  # j/k lumped estimate (aluminium, steel, copper, magnets)
J_ROTOR = 0.15 * 0.040 ** 2  # kg*m2 estimate: 150 g rotor at r 40 mm (measure)
ALPHA = math.radians(180.0) / 0.25  # 0 -> 180 deg/s in 0.25 s
PROOF = 1.67  # proof / continuous, same factor as the shoulder
HAND = dict(m=0.15, r=(p.L_FOREARM + 0.36 * p.L_HAND) / 1000)  # dummy hand mass, centre of mass from the elbow (winter)
I_LIM = 20.0  # recommended odesc current_lim on the elbow (a)
SIG_XY, SIG_Z = p.SIG_PETG_XY / p.SF_PRINT, p.SIG_PETG_Z / p.SF_PRINT
TAU_GLUE = 2.0  # mpa, epoxy on sanded petg (conservative; petg bonds poorly)


def line(title):
    """Print a section header."""
    print(f"\n=== {title} " + "=" * max(0, 60 - len(title)))


def read_mass():
    """Read mass.txt key = value lines into a dict (g, mm)."""
    out = {}
    with open(os.path.join(HERE, "mass.txt"), encoding="utf-8") as f:
        for ln in f:
            if "=" in ln and not ln.startswith("#"):
                k, v = ln.split("=")
                out[k.strip()] = float(v)
    return out


def pcu(i, t_c=25.0):
    """Copper loss (w) at phase current amplitude i and winding temperature t_c."""
    return 1.5 * i * i * R25 * (1 + CU * (t_c - 25.0))


mass = read_mass()
m_f, r_f = mass["m_fore"] / 1000, math.hypot(mass["com_fore_x"], mass["com_fore_z"] - p.Z_ELBOW) / 1000
m_u = mass["m_upper"] / 1000
r_u = -mass["com_upper_z"] / 1000

# ---------------------------------------------------------------- 1 motor and driver
line("1 motor and driver (LA8308 KV90, ODESC 3.6, 20 V bench)")
km = KT / math.sqrt(1.5 * R25)
print(f"Kt 8.27/KV = {KT:.4f} N*m/A   R_phase {R25 * 1000:.1f} mOhm (measured)   Km {km:.3f} N*m/sqrt(W) cold")
print(f"motor 22 A cont (prop airflow rating) -> {22 * KT:.2f} N*m; 40 A peak -> {40 * KT:.2f} N*m; ODESC 40 A cont still air, 120 A peak")
print(f"no-load joint speed at 20 V x 0.7 modulation: {p.MOTOR['kv'] * 20 * 0.7 * 6:.0f} deg/s -> vel_limit is a safety setting, not a capability limit")
print(f"electrical time constant L/R {p.MOTOR['l'] / R25 * 1000:.2f} ms; lumped heat capacity {C_TH:.0f} J/K (estimate)")

# ---------------------------------------------------------------- 2 elbow loads
line("2 elbow loads, direct drive (joint torque = motor torque)")
print(f"forearm structure (CAD print estimate) {m_f * 1000:.0f} g at {r_f * 1000:.0f} mm; dummy hand {HAND['m'] * 1000:.0f} g at {HAND['r'] * 1000:.0f} mm")
l_f = p.L_FOREARM / 1000
cases = {"no hand": 0.0, "dummy hand": HAND["m"], "dummy hand + 0.10 kg payload": HAND["m"] + 0.10}
loads = {}
for name, mh in cases.items():
    ts = (m_f * r_f + mh * HAND["r"]) * G
    j = m_f * (r_f ** 2 + l_f ** 2 / 12) + mh * HAND["r"] ** 2 + J_ROTOR
    tc = ts + j * ALPHA
    loads[name] = (ts, tc, PROOF * tc, j)
    print(f"\n{name}: static {ts:.2f}  continuous {tc:.2f}  proof {PROOF * tc:.2f} N*m   J {j:.4f} kg*m2 (rotor {100 * J_ROTOR / j:.1f} %)")
    for lab, t in (("hold", ts), ("continuous", tc), ("proof", PROOF * tc)):
        i = t / KT
        pw = pcu(i, 60.0)
        rise = ", ".join(f"{pw * r:.0f}" for r in R_TH)
        extra = ""
        lim = T_NTC - T_AMB
        if pw * 3.0 > lim:
            extra = f"  -> NTC limit in {-3.0 * C_TH * math.log(1 - lim / (pw * 3.0)) / 60:.1f} min (R_th 3)"
        print(f"   {lab:10s} {i:5.1f} A  {pw:5.1f} W   steady rise {rise} K for R_th {R_TH}{extra}")

line("2b continuous rating and payload (stator 70 C at 35 C ambient)")
for rth in R_TH:
    p_ok = (T_NTC - T_AMB) / rth
    t_ok = KT / math.sqrt(1.5 * R25 * (1 + CU * (T_NTC - 25))) * math.sqrt(p_ok)
    ts = loads["dummy hand"][0]
    pay = max(0.0, (t_ok - ts) / (G * (p.L_FOREARM + 0.5 * p.L_HAND) / 1000))
    print(f"R_th {rth:.0f} K/W: {p_ok:4.1f} W -> {t_ok:.2f} N*m continuous ({t_ok / KT:4.1f} A); payload at the hand centre with the dummy hand {pay:.2f} kg")

# ---------------------------------------------------------------- 3 odesc settings
line("3 ODESC axis 1 settings")
print(f"pole_pairs {p.MOTOR['pp']}, torque_constant {KT:.4f}, current_lim {I_LIM:.0f} A ({I_LIM * KT:.2f} N*m, "
      f"{I_LIM / (loads['dummy hand'][2] / KT):.2f} x the dummy-hand proof current)")
print(f"vel_limit 0.5 turn/s (180 deg/s), motor thermistor 10k NTC: limit {T_NTC:.0f} C, abort {T_NTC + 10:.0f} C")
print(f"soft limits {p.SOFT_MIN:.0f} .. {p.SOFT_MAX:.0f} deg (encoder on the motor = joint angle, absolute at power-up, no homing)")
print("direction: set so flexion is positive; output resolution 14 bit = 0.022 deg = 0.12 mm at 0.30 m")

# ---------------------------------------------------------------- 4 stops and falls
line("4 stops and falls")
ts, tc, tp, j = loads["dummy hand"]
e_fall = ts  # forearm horizontal -> straight: work of the gravity torque over 90 deg = static torque x 1 rad equivalent
w_fall = math.sqrt(2 * e_fall / j)
b_short = KT ** 2 / (1.5 * R25)
nodes = p.fore_nodes()
r_ext, r_flex = math.hypot(*nodes[p.STOP_EXT]), math.hypot(*nodes[p.STOP_FLEX])
print(f"unpowered fall horizontal -> straight: {e_fall:.2f} J, {w_fall:.1f} rad/s ({w_fall * HAND['r']:.1f} m/s at the hand); "
      f"ODESC idle = open phases, no braking (shorted phases would give only {b_short:.3f} N*m*s/rad)")
for name, r in (("extension stop (heel tab)", r_ext), ("flexion stop (front edge)", r_flex)):
    for travel in (1.0, 3.0):
        f_avg = e_fall / (travel / 1000)
        print(f"  {name}: sleeve at r {r:.0f} mm; absorbing {e_fall:.2f} J in {travel:.0f} mm -> average {f_avg:.0f} N "
              f"({f_avg / 2:.0f} N per plate edge)")
w_cap = math.radians(180.0)
e_drive = 0.5 * j * w_cap ** 2
f_drive = I_LIM * KT / (r_flex / 1000)
print(f"driven into a stop at the 180 deg/s cap: {e_drive:.3f} J kinetic + current limit {I_LIM * KT:.2f} N*m -> {f_drive:.0f} N static at the flexion sleeve")
print(f"result: a powered stall is harmless; for an unpowered fall the {p.HEEL_PAD['t']:.0f} mm rubber pad on the heel face (part 218) "
      "gives the 3 mm travel (~200 N); keep the arm hanging (0 deg) whenever the ODESC is idle")

# ---------------------------------------------------------------- 5 shoulder
line("5 shoulder")
t_g = (m_u * r_u + m_f * (p.L_UPPER / 1000 + r_f) + HAND["m"] * (p.L_UPPER / 1000 + HAND["r"])) * G
j_sh = m_u * r_u ** 2 + m_f * (p.L_UPPER / 1000 + r_f) ** 2 + HAND["m"] * (p.L_UPPER / 1000 + HAND["r"]) ** 2
print(f"upper arm + motor {m_u * 1000:.0f} g at {r_u * 1000:.0f} mm, forearm {m_f * 1000:.0f} g, dummy hand {HAND['m'] * 1000:.0f} g")
print(f"arm horizontal: gravity {t_g:.2f} N*m, + {ALPHA:.2f} rad/s2 (J {j_sh:.3f}) -> {t_g + j_sh * ALPHA:.2f} N*m vs 30 N*m continuous "
      f"(SF {30 / (t_g + j_sh * ALPHA):.1f})")

# ---------------------------------------------------------------- 6 upper-arm plates and laps
line("6 upper-arm plates and half-laps")


def width_at(v):
    """Plate width at height v (front bezier minus back bezier)."""
    fr = min(p.bezier(p.UPPER["front"], 200), key=lambda q: abs(q[1] - v))[0]
    bk = min(p.bezier(p.UPPER["back"], 200), key=lambda q: abs(q[1] - v))[0]
    return fr - bk


def slot_w(v):
    """Slot width at height v (0 outside the slots)."""
    return next((2 * hw for v0, v1, hw in p.SLOTS if v0 <= v <= v1), 0.0)


t_pl = p.Y_UI[1] - p.Y_UI[0]
lap = p.SPLIT
screws = p.lap_screws("inner")
sum_r2 = sum((u ** 2 + (v - lap["inner"]) ** 2) for u, v in screws)
r_max = max(math.hypot(u, v - lap["inner"]) for u, v in screws)
t_lim_screw = SIG_XY * 3.0 * (t_pl / 2) * sum_r2 / r_max * 2 / 1000  # n*m on the link (each plate half) at bearing = allowable
b_lap = width_at(lap["inner"])
a_glue = b_lap * lap["lap"]
jp = a_glue * (b_lap ** 2 + lap["lap"] ** 2) / 12
c = math.hypot(b_lap, lap["lap"]) / 2
t_lim_glue = TAU_GLUE * jp / c * 2 / 1000
t_sh_lim = 10.0
print(f"half-lap {lap['lap']:.0f} long x {b_lap:.0f} wide, 4 x M3 csk (+-{lap['screw_u']:.0f}, +-{lap['screw_dv']:.0f}), "
      f"half thickness {t_pl / 2:.1f}: screws alone carry {t_lim_screw:.1f} N*m on the link at {SIG_XY:.0f} MPa bearing; "
      f"epoxy alone {t_lim_glue:.1f} N*m at {TAU_GLUE:.0f} MPa")
print(f"-> shoulder current limit for the printed arm: {t_sh_lim:.0f} N*m output (dummy-hand demand {t_g + j_sh * ALPHA:.1f} N*m)")
for v in (40.0, 80.0, lap["inner"], lap["outer"], 220.0, 260.0):
    w = width_at(v)
    sw = slot_w(v)
    i_sec = 2 * t_pl * (w ** 3 - sw ** 3) / 12
    sig = t_sh_lim * 1000 * (w / 2) / i_sec
    print(f"  v {v:5.0f}: plate width {w:5.1f}{f' (slot {sw:.0f})' if sw else ''}: shoulder {t_sh_lim:.0f} N*m on the link -> "
          f"{sig:5.2f} MPa (allow {SIG_XY:.0f})")
f_m5 = t_sh_lim / (6 * p.SH_M5_R / 1000)
print(f"shoulder flange 6 x M5 in close-fit holes: {f_m5:.0f} N each at {t_sh_lim:.0f} N*m -> {f_m5 / (5 * t_pl):.1f} MPa bearing in the plate; "
      f"6 x M5 at {p.M5['torque']:.0f} N*m preload {p.M5['torque'] / (0.2 * 0.005):.0f} N each (petg creep: re-torque after the first week)")

# ---------------------------------------------------------------- 7 elbow joint parts
line("7 elbow joint: hub, pivot, standoffs")
t_el = I_LIM * KT
for name, t in (("current limit", t_el), ("motor 40 A peak", 40 * KT)):
    f_rotor = t / (4 * p.ROTOR["pcd_r"] / 1000)
    f_fore = t / (3 * 0.007)
    tau_tube = t * 1000 * 16 / (math.pi * 22.0 ** 3)
    print(f"{name} {t:.2f} N*m: 4 x M3 hub->rotor {f_rotor:.0f} N each ({f_rotor / (3 * p.HUB['flange_t']):.1f} MPa in the flange); "
          f"3 x M3 plate->hub {f_fore:.0f} N each ({f_fore / (3 * (p.Y_FO[1] - p.Y_FO[0])):.1f} MPa in the 4 mm plate, allow {SIG_XY:.0f}); "
          f"tube shear {tau_tube:.1f} MPa")
span = ((p.Y_FO[0] + p.Y_FO[1]) / 2 - (-2.0 - p.PIVOT_BRG["B"] / 2)) / 1000
for f_side in (20.0, 50.0):
    m_side = f_side * HAND["r"]
    f_pair = m_side / span
    print(f"side push {f_side:.0f} N at the hand: {m_side:.1f} N*m out of plane -> {f_pair:.0f} N couple between the hub (motor bearings) "
          f"and the 6705 pivot ({span * 1000:.0f} mm apart); 6705 static capacity >= 1.0 kN gives s0 >= {1000 / f_pair:.1f}")
f_screw = 0.5 / (0.2 * 0.004)
a_so = math.pi * (p.STANDOFF["ro"] ** 2 - p.STANDOFF["ri"] ** 2)
print(f"motor standoffs: M4 at 0.5 N*m -> {f_screw:.0f} N on {a_so:.0f} mm2 = {f_screw / a_so:.1f} MPa in petg near the stator "
      f"(hdt test 1.8 MPa at 62 C): use 0.5 N*m + Loctite 243, re-check torque after the thermal test")
print(f"motor torque reaction: {40 * KT:.2f} N*m peak on 4 x M4 at r {p.MOTOR_BASE['pcd_r']:.0f} -> "
      f"{40 * KT / (4 * p.MOTOR_BASE['pcd_r'] / 1000):.0f} N each in shear (bearing {40 * KT / (4 * p.MOTOR_BASE['pcd_r'] / 1000) / (4 * t_pl):.1f} MPa)")

# ---------------------------------------------------------------- 8 forearm plates
line("8 forearm truss plates")
bi = p.fore_rims()[2]
fi = p.fore_rims()[3]
for v in (-60.0, -120.0, -200.0):
    ub = min(bi, key=lambda q: abs(q[1] - v))[0]
    uf = min(fi, key=lambda q: abs(q[1] - v))[0]
    d = (uf - ub) / 2 + p.FORE["rim"] / 2
    t = p.Y_FO[1] - p.Y_FO[0]
    i_sec = 2 * 2 * (t * p.FORE["rim"] ** 3 / 12 + t * p.FORE["rim"] * d ** 2)
    sig = t_el * 1000 * (d + p.FORE["rim"] / 2) / i_sec
    print(f"v {v:5.0f}: rims {p.FORE['rim']:.0f} x {t:.0f} at +-{d:.1f} mm, two plates: elbow current limit {t_el:.2f} N*m -> {sig:.2f} MPa")
print(f"stop sleeve load at the current limit: {t_el / (r_flex / 1000):.0f} N on the d8 sleeve near the plates (short lever), "
      f"{t_el / (r_flex / 1000) / 2 / (5 * 3):.1f} MPa edge contact per plate")

# ---------------------------------------------------------------- 9 mass summary
line("9 mass")
print(f"arm total {mass['m_arm']:.0f} g (upper arm + motor {mass['m_upper']:.0f}, forearm {mass['m_fore']:.0f}); "
      f"Rev 1 had a 508 g elbow actuator alone")
