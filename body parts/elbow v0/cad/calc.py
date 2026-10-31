"""Engineering checks for the VAYN elbow actuator Rev 1.0.

Every number quoted in elbow/parts.md is printed by this script; all
geometry comes from params.py and the exact disc outline from cycloid.py.
Units: mm, N, N*m, MPa. Run: python calc.py > calc.txt
"""

import math

import numpy as np

import cycloid as cy
import params as p

E_STEEL, NU_STEEL = 210e3, 0.30
E_DISC, NU_DISC = 4730.0, 0.35  # bambu pet-cf tds x-y modulus; poisson assumed (p0 moves <3 % for 0.30..0.40)
SIG_Y_DISC = 74.0 - 6.0  # bambu pet-cf tds x-y tensile, mean - 1 sd
SIG_Y_PLA = 35.0 - 4.0  # bambu pla basic tds x-y tensile, mean - 1 sd (cam, cage, carrier)
P_YIELD = 1.67 * SIG_Y_DISC  # hertz line contact first-yield (tresca, tau_max = 0.30 p0)
P_ALLOW_PROOF, P_ALLOW_CONT = P_YIELD, P_YIELD / 1.5
KT = 8.27 / p.KV
R_PHASE = p.R_PHASE_PP / 2
PRELOAD_PER_NM_M3 = 4240 / 2.14  # vdi 2230, mu 0.12 (same table as shoulder calc)
BRG = {  # c, c0 (n), lower of the sourced values
    "6704-2RS": (1010.0, 722.0),
    "6703-2RS": (999.0, 657.0),
    "6701-2RS": (922.0, 530.0),
    "61807-2RS1": (4750.0, 3200.0),
}
S0_PROOF, S0_CONT = 1.0, 1.5  # skf ball-bearing table, low load certainty: infrequent motion / continuous, some deformation
Z_DISC = ((p.Z_D1_0 + p.Z_D1_1) / 2, (p.Z_D2_0 + p.Z_D2_1) / 2)
Z_CAM_BRG = (p.Z_BCR0 + p.BRG_CAM_R["B"] / 2, p.Z_BCF0 + p.BRG_CAM_F["B"] / 2)
Z_OUT_BRG = p.Z_BRG0 + p.BRG_OUT["B"] / 2


def line(title):
    """Print a section header."""
    print(f"\n=== {title} " + "=" * max(0, 60 - len(title)))


def reducer(dr=p.DR, c_out=p.C_OUT):
    """Build the cycloid stage from params (dr / c_out overridable for studies)."""
    return cy.Reducer(p.ZP, p.R_PINS, p.D_PIN / 2, p.E, dr, p.R_OUT, p.N_OUT, p.D_PIN / 2,
                      p.D_PIN / 2 + p.E + c_out, n=p.PROFILE_PTS)


def disc_torque(t_out, share):
    """Ring-side torque (n*m) on one disc for output torque t_out."""
    return t_out * share * (1 + 1 / p.RATIO)


def ring_peaks(r, t_disc, length, n_alpha=48):
    """Worst hertz pressure, pin force and bearing force over one lobe pitch."""
    worst = dict(p=0.0, f=0.0, fb=0.0, pa=0.0, n=99)
    for a in np.linspace(0, 2 * math.pi / p.ZP, n_alpha, endpoint=False):
        d = r.loads(a, "A", t_disc)
        m = d["ring_loaded"]
        for f, kap in zip(d["f_ring"][m], d["kappa"][m]):
            worst["p"] = max(worst["p"], cy.hertz_line(f, length, 1 / (1 / r.rp + kap), E_STEEL, NU_STEEL, E_DISC, NU_DISC))
        # contact normal vs outward radial of the housing groove, housing frame
        _, phi = r.pose(a, "A")
        n_h = d["normal"] @ cy.rot(phi).T
        radial = r.pins / np.linalg.norm(r.pins, axis=1, keepdims=True)
        ang = np.degrees(np.arccos(np.clip(np.sum(n_h * radial, axis=1), -1, 1)))
        worst["pa"] = max(worst["pa"], float(ang[m].max()))
        worst["f"] = max(worst["f"], float(d["f_ring"].max()))
        worst["fb"] = max(worst["fb"], d["f_brg"])
        worst["n"] = min(worst["n"], int(m.sum()))
        worst["fw"] = max(worst.get("fw", 0.0), float(d["f_out"].max()))
    return worst


def free_angle(r, alpha, disc, sign):
    """Disc rotation (rad) about its centre, cam held, until it touches a ring pin (bisection)."""
    c0, phi0 = r.pose(alpha, disc)

    def gap(d):
        q = (r.pins - c0) @ cy.rot(-(phi0 + sign * d)).T
        dist, _, _ = cy.point_to_polyline(q, r.prof[disc])
        return np.min(np.where(cy.inside(q, r.prof[disc]), -dist, dist)) - r.rp

    lo, hi = 0.0, 0.05
    for _ in range(30):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if gap(mid) > 0 else (lo, mid)
    return sign * lo


# ---------------------------------------------------------------- 1 motor
line("1 motor, current, heat (MN5008 KV170, 20:1)")
k_out = KT * p.RATIO * p.ETA
print(f"Kt {KT:.4f} N*m/A   output {k_out:.3f} N*m per A   R_phase {R_PHASE:.3f} ohm")
for name, t in (("static", p.T_STATIC), ("continuous", p.T_CONT), ("proof", p.T_PROOF)):
    i = t / k_out
    print(f"  {name:10s} {t:5.2f} N*m -> {i:5.2f} A   Pcu25 {1.5 * i ** 2 * R_PHASE:5.2f} W")
print(f"  ODESC current_lim {p.I_LIMIT:.0f} A -> {p.I_LIMIT * k_out:.2f} N*m output; motor 180 s peak {p.I_PEAK_MOTOR:.0f} A -> {p.I_PEAK_MOTOR * k_out:.2f} N*m")
print(f"  speed @{p.V_BUS:.0f} V: motor {p.KV * p.V_BUS:.0f} rpm, output {p.KV * p.V_BUS / p.RATIO:.0f} rpm ({p.KV * p.V_BUS / p.RATIO * 6:.0f} deg/s)")
print(f"  motor torque at proof {p.T_PROOF / (p.RATIO * p.ETA):.3f} N*m, at 15 A {p.I_PEAK_MOTOR * KT:.3f} N*m")

# ---------------------------------------------------------------- 2 geometry
line("2 cycloid geometry")
r = reducer()
prof = r.prof["A"]
rad = np.linalg.norm(prof, axis=1)
kap = cy.curvature(prof)
print(f"Zp {p.ZP}  Zc {p.ZC}  R {p.R_PINS}  pin D{p.D_PIN}  e {p.E}  relief {p.DR}  lambda {r.lam:.3f}")
print(f"disc radius (own frame) {rad.min():.3f} .. {rad.max():.3f}   max convex curvature {kap.max():.4f} 1/mm "
      f"(radius {1 / kap.max():.2f})   self-intersection: {cy.self_intersects(prof, 2)}")
hole_r = p.D_OUT_HOLE / 2
bore_r = p.BRG_ECC["D"] / 2
print(f"output holes D{p.D_OUT_HOLE:.2f} on R{p.R_OUT}: outer web {rad.min() - p.R_OUT - hole_r:.2f}  inner web "
      f"{p.R_OUT - hole_r - bore_r:.2f}  between holes {2 * p.R_OUT * math.sin(math.pi / p.N_OUT) - p.D_OUT_HOLE:.2f}")
r_sweep = r.max_radius(720)
print(f"max disc radius in housing {r_sweep:.3f} (formula {p.R_DISC_MAX:.3f}) -> bore R{p.R_BORE_DISC:.2f} gap {p.R_BORE_DISC - r_sweep:.3f}")
cos_psi = (p.R_PINS ** 2 + (p.D_PIN / 2) ** 2 - p.R_BORE_DISC ** 2) / (2 * p.R_PINS * p.D_PIN / 2)
psi = math.degrees(math.acos(cos_psi))
print(f"pin exposure half-angle {psi:.1f} deg (housing backs the other {360 - 2 * psi:.0f} deg)   wall pin->OD {p.R_HOUSING - p.R_PINS - p.D_PIN / 2:.2f}")
psi_m = math.acos((p.R_PINS ** 2 + (p.D_PIN / 2) ** 2 - p.R_MOTOR_BORE ** 2) / (2 * p.R_PINS * p.D_PIN / 2))
print(f"pin capture in the R{p.R_MOTOR_BORE} rear zone ({p.Z_D1_0 - p.GAP - p.Z_PIN0:.1f} long): groove opening "
      f"{p.D_PIN * math.sin(psi_m):.2f} < pin D{p.D_PIN} -> captured; rotor clearance {p.R_MOTOR_BORE - p.M_ROTOR_R:.2f}")
print(f"disc zone bore R{p.R_BORE_DISC:.2f} runs to the front face: discs enter from the front with {p.R_BORE_DISC - r_sweep:.3f} gap "
      f"(an R{p.R_MOTOR_BORE} front zone would block them: disc reaches {r_sweep:.2f})")

line("2b kinematic sweep, one full input turn, both discs")
n_a = 1440
gmin = {"A": 9.0, "B": 9.0}
gmax_min = {"A": 0.0, "B": 0.0}
wmin = {"A": 9.0, "B": 9.0}
for disc in ("A", "B"):
    for a in np.linspace(0, 2 * math.pi, n_a, endpoint=False):
        g = r.ring_clearance(a, disc)
        gmin[disc] = min(gmin[disc], float(g.min()))
        gmax_min[disc] = max(gmax_min[disc], float(np.sort(g)[0]))
        wmin[disc] = min(wmin[disc], float(r.out_clearance(a, disc).min()))
for disc in ("A", "B"):
    print(f"disc {disc}: ring-pin gap min {gmin[disc]:.4f} (target {p.DR})  output-pin gap min {wmin[disc]:.4f} (target {p.C_OUT})"
          f"  with iso 8734 m6 pins (d max {p.D_PIN + 0.012}): {gmin[disc] - 0.006:.4f} / {wmin[disc] - 0.006:.4f}")

line("2c backlash at the output (cam held)")
worst_bl = 0.0
for a in np.linspace(0, 2 * math.pi / p.ZP, 6, endpoint=False):
    lo = max(free_angle(r, a, d, -1) for d in ("A", "B"))
    hi = min(free_angle(r, a, d, +1) for d in ("A", "B"))
    c_rot = p.C_OUT / p.R_OUT
    worst_bl = max(worst_bl, hi - lo + 2 * c_rot)
dog_bl = 2 * (p.DOG_POCKET_D - p.DOG["d"]) / 2 / p.M_ROTOR_HOLES["pcd_r"] / p.RATIO
worst_bl += dog_bl
print(f"profile relief {p.DR}: disc free {math.degrees(hi - lo) * 60:.1f} arcmin; output holes {p.C_OUT}: "
      f"{math.degrees(2 * p.C_OUT / p.R_OUT) * 60:.1f} arcmin; dog play / {p.RATIO}: {math.degrees(dog_bl) * 60:.1f} arcmin")
print(f"total output backlash {worst_bl * 1000:.1f} mrad = {math.degrees(worst_bl):.2f} deg "
      f"(Berkeley Humanoid Lite PLA cycloid <= 23 mrad)   at 0.30 m: {worst_bl * 300:.1f} mm")

# ---------------------------------------------------------------- 3 contact
line("3 ring-pin contact (steel pin on PET-CF lobe, rigid-disc load share)")
print(f"allowables: first yield p0 = 1.67 x {SIG_Y_DISC:.0f} = {P_YIELD:.1f} MPa (proof), /1.5 = {P_ALLOW_CONT:.1f} MPa (continuous)")
res = {}
for name, t, lim in (("continuous", p.T_CONT, P_ALLOW_CONT), ("proof", p.T_PROOF, P_ALLOW_PROOF)):
    w = ring_peaks(r, disc_torque(t, p.DISC_SHARE), p.T_DISC)
    res[name] = w
    print(f"{name:10s} T {t:.2f} share {p.DISC_SHARE:.2f}: p0 {w['p']:5.1f} MPa (limit {lim:.1f}, "
          f"{'OK' if w['p'] <= lim else 'FAIL'})  pin F max {w['f']:.0f} N  loaded pins >= {w['n']}  "
          f"pressure angle max {w['pa']:.1f} deg (< {psi:.1f} exposure)")
print("share sensitivity (one disc carries more after print error, until run-in):")
for s in (0.50, 0.55, 0.60, 0.65, 0.75):
    pc = ring_peaks(r, disc_torque(p.T_CONT, s), p.T_DISC, 12)["p"]
    pp = ring_peaks(r, disc_torque(p.T_PROOF, s), p.T_DISC, 12)["p"]
    print(f"  share {s:.2f}: continuous {pc:5.1f}  proof {pp:5.1f} MPa")

line("3b output pins in disc holes, pin bending")
for name, t in (("continuous", p.T_CONT), ("proof", p.T_PROOF)):
    fw = res[name]["fw"]
    r_eq = (p.D_PIN / 2) * hole_r / (hole_r - p.D_PIN / 2)
    ph = cy.hertz_line(fw, p.T_DISC, r_eq, E_STEEL, NU_STEEL, E_DISC, NU_DISC)
    # pin as a simply supported beam (rear ring centre -> pin-plate face), both disc loads same way
    z_s = (p.Z_OPIN0 + p.Z_RR1) / 2
    span = p.Z_PP0 - z_s
    a1, a2 = Z_DISC[0] - z_s, Z_DISC[1] - z_s
    r_rear = fw * ((span - a1) + (span - a2)) / span
    m_max = max(r_rear * a1, r_rear * a2 - fw * (a2 - a1))
    sig = 32 * m_max / (math.pi * p.D_PIN ** 3)
    bear_ring = r_rear / (p.D_PIN * (p.Z_RR1 - p.Z_OPIN0))
    bear_plate = (2 * fw - r_rear) / (p.D_PIN * p.T_PIN_PLATE)
    print(f"{name:10s} pin F max {fw:5.0f} N  hertz in hole {ph:5.1f} MPa  pin bending <= {sig:5.0f} MPa (iso 8734, >= 1500 MPa)  "
          f"bearing: rear ring {bear_ring:4.1f} / pin plate {bear_plate:4.1f} MPa")

# ---------------------------------------------------------------- 4 bearings
line("4 bearings")
c, c0 = BRG["6704-2RS"]
for name in ("continuous", "proof"):
    fb = res[name]["fb"]
    print(f"6704 eccentric ({name}): Fr {fb:5.0f} N  s0 {c0 / fb:4.2f}  (need {S0_CONT if name == 'continuous' else S0_PROOF})")
fb = res["continuous"]["fb"]
n_rel = p.KV * p.V_BUS * (1 + 1 / p.ZC)
print(f"6704 L10 at continuous load {(c / fb) ** 3:.0f} Mrev = {(c / fb) ** 3 * 1e6 / n_rel / 60:.0f} h at full speed {n_rel:.0f} rpm")


def cam_and_cage(t_out, share_a):
    """Worst loads over one lobe pitch: cam bearings (6703 rear, 6701 front) and cage net force / tilt.

    the cam is a rigid beam on its two cage bearings, loaded by both eccentric
    bearings. the cage gets the sum of the ring-pin forces (net force + moment
    about the 61807 centre); the motor bearings get only dog-coupling torque.
    """
    worst = dict(rear=0.0, front=0.0, f=0.0, m=0.0)
    z_r, z_f = Z_CAM_BRG
    for a in np.linspace(0, 2 * math.pi / p.ZP, 24, endpoint=False):
        cam, ring = [], []
        for disc, s, z in (("A", share_a, Z_DISC[0]), ("B", 1 - share_a, Z_DISC[1])):
            d = r.loads(a, disc, disc_torque(t_out, s))
            rh = cy.rot(r.pose(a, disc)[1])
            cam.append((-(rh @ d["f_brg_vec"]), z))  # force on the cam, housing frame
            ring.append((rh @ d["f_ring_sum"], z))  # ring-pin force on the disc = load the cage reacts
        m = sum(f * (z - z_f) for f, z in cam)
        f_rear = -m / (z_r - z_f)
        f_front = -(sum(f for f, _ in cam) + f_rear)
        f_net = sum(f for f, _ in ring)
        m_cage = sum(f * (z - Z_OUT_BRG) for f, z in ring)
        worst["rear"] = max(worst["rear"], float(np.linalg.norm(f_rear)))
        worst["front"] = max(worst["front"], float(np.linalg.norm(f_front)))
        worst["f"] = max(worst["f"], float(np.linalg.norm(f_net)))
        worst["m"] = max(worst["m"], float(np.linalg.norm(m_cage)) / 1000)
    return worst


z_balls, dm = p.BRG_OUT["nballs"], (p.BRG_OUT["d1"] + p.BRG_OUT["D1"]) / 2
for name, t, need in (("continuous", p.T_CONT, S0_CONT), ("proof", p.T_PROOF, S0_PROOF)):
    for sa in (0.50, 0.40, 0.60):
        w = cam_and_cage(t, sa)
        q = 5 * w["f"] / z_balls + 4.37 * w["m"] * 1000 / (z_balls * dm * math.sin(math.radians(15)))
        s0_out = 5 * BRG["61807-2RS1"][1] / z_balls / q
        print(f"{name:10s} share A {sa:.2f}: 6703 {w['rear']:4.0f} N s0 {BRG['6703-2RS'][1] / w['rear']:4.2f} | "
              f"6701 {w['front']:4.0f} N s0 {BRG['6701-2RS'][1] / w['front']:4.2f} | cage net {w['f']:4.0f} N, "
              f"tilt {w['m']:4.2f} N*m -> 61807 alone s0 {s0_out:4.1f}  (need {need})")
print("61807 ball-load model: Q = 5 Fr / Z + 4.37 M / (Z dm sin 15 deg); clevis forearm shares the tilt in the arm")
f_dog = p.I_PEAK_MOTOR * KT * 1000 / (2 * p.M_ROTOR_HOLES["pcd_r"])  # only 2 of 4 dogs bear (play)
eng = p.Z_TOP + p.DOG["protrude"] - p.Z_CAM0
d_root = 2.39  # m3 minor diameter
print(f"dogs: 2 of 4 bear at 15 A: {f_dog:.0f} N each, PLA pocket {f_dog / (p.DOG['d'] * eng):.1f} MPa, "
      f"set-screw bending {32 * f_dog * (p.DOG['protrude'] - eng / 2) / (math.pi * d_root ** 3):.0f} MPa (45H)")
print(f"motor 696 bearings: no gearbox load (dog play {(p.DOG_POCKET_D - p.DOG['d']) / 2:.2f} mm radial, coupling passes torque only)")

# ---------------------------------------------------------------- 5 joints
line("5 bolted joints, inserts, dowels (preload from vdi 2230 table, mu 0.12 thread)")


def joint(name, n, torque, r_bolt, mu, load, head_area=None):
    """Friction torque of a bolted joint and the preload pressure under the heads."""
    fm = PRELOAD_PER_NM_M3 * torque
    t_slip = n * fm * mu * r_bolt / 1000
    head = f"  head pressure {fm / head_area:4.1f} MPa" if head_area else ""
    print(f"{name:36s} {n} x M3 @ {torque} N*m: FM {fm:4.0f} N  slip {t_slip:5.2f} N*m (load {load:.2f}, SF {t_slip / load:4.2f}){head}")
    return fm


a_washer = math.pi / 4 * (p.WASHER_M3["od"] ** 2 - p.WASHER_M3["id"] ** 2)
eng = p.DOG["length"] - p.DOG["protrude"]
print(f"dog set screws: {eng:.1f} mm in the rotor of {p.M_ROTOR_HOLES['depth']} (bottom gap {p.M_ROTOR_HOLES['depth'] - eng:.1f}); "
      f"tip to pocket floor {p.Z_CAM0 + p.DOG_POCKET_DEPTH - p.Z_TOP - p.DOG['protrude']:.1f} mm axial float")
fm = joint("motor base -> wall (mu 0.20 Al/ASA)", 4, 0.5, p.M_BASE_HOLES["pcd_r"], 0.20, p.I_PEAK_MOTOR * KT)
eng = p.L_MOTOR_SCREW - (p.Z_M0 - p.Z_RING0)
print(f"  motor screw engagement {eng:.1f} mm of {p.M_BASE_HOLES['depth']}   clamp ring on wall {fm * 4 / (math.pi * (p.R_RING_O ** 2 - p.R_RING_I ** 2)):.2f} MPa")
t_housing = p.T_PROOF * (1 + 1 / p.RATIO)
fm = joint("cover + retainer -> housing inserts", 7, 0.2, p.R_FLANGE_SCREW, 0.20, t_housing, a_washer)
eng = p.Z_HF - (p.Z_BRG0 + p.T_FLANGE_COVER + p.WASHER_M3["t"] - p.L_FLANGE_SCREW)
print(f"  insert engagement {eng:.1f} of {p.INSERT['length']} mm; pull-out ~1400 N vs FM {fm:.0f} N (SF {1400 / fm:.1f})")
fm = joint("hub -> forearm inserts", 6, 0.2, p.R_HUB_INSERT, 0.20, p.T_PROOF)
f_dowel = p.T_PROOF * 1000 / p.R_HUB_INSERT / 2
print(f"  hub dowels 2 x D3 carry the full proof torque: {f_dowel:.0f} N each, bearing in PLA (5 deep) {f_dowel / (3 * 5):.1f} MPa "
      f"(yield {SIG_Y_PLA:.0f}, SF {SIG_Y_PLA / (f_dowel / 15):.1f}), shear {f_dowel / (math.pi * 9 / 4):.0f} MPa")
f_dowel = t_housing * 1000 / p.R_FLANGE_SCREW / 2
print(f"flange dowels 2 x D3 (backup): {f_dowel:.0f} N each, bearing in ASA (6 deep) {f_dowel / 18:.1f} MPa")
line("5b insert and screw walls")
d_i = p.INSERT["d_hole"]
w_hub = p.R_HUB - p.R_HUB_INSERT - d_i / 2
w_fl_out = p.R_FLANGE - p.R_FLANGE_SCREW - d_i / 2
x, y = p.R_FLANGE_SCREW * math.cos(math.pi / p.ZP), p.R_FLANGE_SCREW * math.sin(math.pi / p.ZP)
w_fl_pin = math.hypot(x - p.R_PINS, y) - p.D_PIN / 2 - d_i / 2
print(f"hub insert wall {w_hub:.2f}  flange insert wall to OD {w_fl_out:.2f}, to ring pin {w_fl_pin:.2f}  (ruthex min {p.INSERT['wall_min']})")
skin = p.BRG_CAM_R["d"] / 2 - p.M_ROTOR_HOLES["pcd_r"] - p.DOG_POCKET_D / 2
print(f"cam skin outside the dog pockets {skin:.2f} (2 perimeters; dog load is tangential into the solid web)")
rb = p.BRG_ECC["d"] / 2
land = rb - p.SLIDE_CLEAR - p.E - p.BRG_CAM_R["d"] / 2
print(f"slide-over: 6704-A bore r {rb} clears the 6703 journal by {rb - p.BRG_CAM_R['d'] / 2 - p.E:.2f} and the trimmed collar by "
      f"{p.SLIDE_CLEAR:.2f} (6703 inner-ring land {land:.2f}..{p.CAM_R_SHOULDER_R - p.BRG_CAM_R['d'] / 2:.2f}); "
      f"6704-B clears the 6701 shoulder by {rb - p.CAM_F_SHOULDER_R - p.E:.2f}")
print(f"insert hole depth {p.INSERT['depth']} in housing flange: bottom Z {p.Z_HF - p.INSERT['depth']:.1f} (flange from {p.Z_FLANGE0:.1f})")
v, ri, pitch = p.VENT, p.R_MOTOR_BORE, math.radians(360.0 / p.VENT["n"])
rib = ri * (pitch - 2 * math.asin(v["w"] / 2 / ri))
rib_port = ri * (pitch - math.asin(4.0 / ri) - math.asin(v["w"] / 2 / ri))
print(f"vents {v['n']} x {v['w']} wide, Z {v['z0']:.1f}..{v['z1']:.1f}: rib at the bore {rib:.2f} (next to the lead port {rib_port:.2f}), "
      f"roof to ring-pin seat {p.Z_PIN0 - v['z1']:.2f}, open area {v['n'] * v['w'] * (v['z1'] - v['z0']):.0f} mm2")

# ---------------------------------------------------------------- 6 stack
line("6 axial stack (Z from lid rear face)")
for name, z0, z1 in (("lid", p.Z_LID0, p.Z_LID0 + p.T_LID), ("encoder pcb", p.Z_PCB0, p.Z_PCB1), ("AS5047P", p.Z_PCB1, p.Z_IC1),
                     ("magnet", p.Z_MAG, p.Z_MAG + p.MAG["h"]), ("clamp ring 6061", p.Z_RING0, p.Z_RING1),
                     ("housing wall", p.Z_RING1, p.Z_M0), ("motor base..rotor top", p.Z_M0, p.Z_TOP),
                     ("cage rear ring", p.Z_RR0, p.Z_RR1), ("6703 cam rear", p.Z_BCR0, p.Z_RR1),
                     ("disc A", p.Z_D1_0, p.Z_D1_1), ("disc B", p.Z_D2_0, p.Z_D2_1),
                     ("6704 A", p.Z_B1_0, p.Z_B1_0 + 4), ("6704 B", p.Z_B2_0, p.Z_B2_0 + 4), ("cam", p.Z_CAM0, p.Z_CAM_F),
                     ("6701 cam front", p.Z_BCF0, p.Z_CAM_F),
                     ("pin plate", p.Z_PP0, p.Z_PP1), ("retainer", p.Z_HF, p.Z_BRG0), ("61807", p.Z_BRG0, p.Z_BRG1),
                     ("cover lip", p.Z_BRG1, p.Z_FRONT), ("ring pins", p.Z_PIN0, p.Z_PIN1), ("output pins", p.Z_OPIN0, p.Z_OPIN1)):
    print(f"  {name:22s} {z0:6.2f} .. {z1:6.2f}  ({z1 - z0:5.2f})")
print(f"magnet gap to IC {p.Z_MAG - p.Z_IC1:.2f} mm (0.5..3.0)   overall length {p.Z_FRONT:.1f} mm   OD {2 * p.R_FLANGE:.0f} flange / {2 * p.R_HOUSING:.0f} body")
