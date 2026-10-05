"""Engineering checks for the VAYN shoulder actuator Rev 1.3.

Every number quoted in docs/VAYN_Shoulder_Actuator_CAD_Spec_Rev1_3.md
(sections 3, 9, 10, 11 and appendix A) is printed by this script.
Units: mm, N, N*m, MPa, um, degC. Run: python calc_rev1_3.py
"""

import math

# ---------------------------------------------------------------- inputs
KV, ETA, RATIO = 90.0, 0.90, 30.0
KT = 8.27 / KV  # n*m/a, odrive convention
R_PHASE = 0.186 / 2  # ohm, vendor line-to-line / 2 (measure)

# load cases: (name, output torque, tilt moment, radial n, axial n)
CASES = {
    "L1 continuous": (30.0, 20.0, 50.0, 0.0),
    "L2 torque proof": (50.0, 0.0, 0.0, 0.0),
    "L3 tilt proof": (0.0, 50.0, 150.0, 150.0),
    "L4 combined proof": (50.0, 50.0, 150.0, 150.0),
}

# 61813 (skf): c, c0, f0, ball pitch dia, assumed ball set
C_DYN, C0, F0, DPW, Z_BALLS, DW = 11900.0, 9650.0, 17.0, 75.0, 24, 5.5
Z_REAR_BRG, Z_FRONT_BRG, Z_LOAD = 65.5, 86.5, 95.5  # bearing centres, flange face
SKF_E_Y = [(0.172, 0.19, 2.30), (0.345, 0.22, 1.99), (0.689, 0.26, 1.71), (1.03, 0.28, 1.55),
           (1.38, 0.30, 1.45), (2.07, 0.34, 1.31), (3.45, 0.38, 1.15), (5.17, 0.42, 1.04), (6.89, 0.44, 1.00)]

# wave spring smalley ssb-0335
SPRING_F, SPRING_H, SPRING_K, SPRING_TOL = 231.4, 2.77, 83.0, 0.10

# thermal expansion (um/m/k) and moduli (mpa)
A_AL, A_ST = 23.6, 11.5
E_AL, E_ST = 71.7e3, 210e3

# 12.9 preload per n*m of tightening torque, mu 0.12 (vdi 2230 tables)
PRELOAD_PER_NM = {"M2.5": 1400 / 0.6, "M3": 4240 / 2.14, "M4": 7600 / 5.1, "M5": 12400 / 10.0}


def line(title):
    """Print a section header."""
    print(f"\n=== {title} " + "=" * max(0, 60 - len(title)))


def interp_e_y(x):
    """Return (e, Y) from the skf table for x = f0*Fa/C0 (linear interpolation, clamped)."""
    pts = SKF_E_Y
    if x <= pts[0][0]:
        return pts[0][1], pts[0][2]
    for (x0, e0, y0), (x1, e1, y1) in zip(pts, pts[1:]):
        if x <= x1:
            t = (x - x0) / (x1 - x0)
            return e0 + t * (e1 - e0), y0 + t * (y1 - y0)
    return pts[-1][1], pts[-1][2]


def bearing_loads(tilt_nm, fr_ext, fa_ext, spring_n):
    """Radial and axial loads on (rear, front) 61813 for a tilt moment + radial + axial load.

    the rear outer ring floats on the spring, so the rear axial load is always the
    spring force; the front bearing takes spring + external axial (+ = forward).
    """
    span = Z_FRONT_BRG - Z_REAR_BRG
    a = Z_LOAD - Z_FRONT_BRG
    fr_front = (tilt_nm * 1000 + fr_ext * (span + a)) / span
    fr_rear = fr_front - fr_ext
    return (fr_rear, spring_n), (fr_front, spring_n + fa_ext)


def equivalent_loads(fr, fa):
    """Return (P dynamic, P0 static) for a deep groove ball bearing (skf method)."""
    e, y = interp_e_y(F0 * fa / C0)
    p = fr if fa / max(fr, 1e-9) <= e else 0.56 * fr + y * fa
    p0 = max(fr, 0.6 * fr + 0.5 * fa)
    return p, p0


def ball_deflection(fr):
    """Radial elastic approach (um) of one deep groove bearing under fr (palmgren point contact)."""
    q_max = 5.0 * fr / Z_BALLS
    return 2 * 4.36e-4 * q_max ** (2 / 3) / DW ** (1 / 3) * 1000 / 2


def k_h_beta(ft, b, f_ma_um, crown_um, c_gamma=20.0, n=400):
    """Face load factor from an elastic line-contact model.

    the tooth gap along the face is misalignment (linear, f_ma over b) plus lead
    crowning (parabolic, crown_um at each end). mesh stiffness c_gamma in n/mm/um.
    returns peak / mean load per mm of face.
    """
    xs = [-b / 2 + b * (i + 0.5) / n for i in range(n)]
    gap = [f_ma_um * x / b + crown_um * (2 * x / b) ** 2 for x in xs]
    g0 = min(gap)
    gap = [g - g0 for g in gap]
    lo, hi = 0.0, 1000.0
    for _ in range(60):
        d = (lo + hi) / 2
        load = sum(c_gamma * max(0.0, d - g) for g in gap) * b / n
        lo, hi = (d, hi) if load < ft else (lo, d)
    return c_gamma * lo / (ft / b)


def lewis_y(z):
    """Lewis form factor approximation for 20 deg full depth teeth."""
    return math.pi * (0.154 - 0.912 / z)


def hertz(ft, b, d1, u, k, internal=False):
    """Gear contact stress (mpa) with ZE 189.8, ZH 2.495, Zeps 0.9."""
    uu = (u - 1) / u if internal else (u + 1) / u
    return 189.8 * 2.495 * 0.9 * math.sqrt(ft / (b * d1) * uu * k)


# ---------------------------------------------------------------- 1 motor
line("1 motor, torque, heat")
k_out = KT * RATIO * ETA
print(f"Kt {KT:.4f} N*m/A   output {k_out:.3f} N*m per A")
for t in (20, 30, 37, 50):
    i = t / k_out
    p25 = 1.5 * i ** 2 * R_PHASE
    print(f"  {t:4.0f} N*m -> {i:5.2f} A   Pcu25 {p25:5.1f} W   Pcu90 {p25 * (1 + 0.00393 * 65):5.1f} W")
print(f"  thermal resistance needed at 30 N*m (90C winding, 25C air): {(90 - 25) / (1.5 * (30 / k_out) ** 2 * R_PHASE * 1.2555):.2f} K/W")
print(f"  speeds @24V: motor {KV * 24:.0f} rpm, carrier-1 {KV * 24 / 6:.0f} rpm, output {KV * 24 / RATIO:.0f} rpm")

# ---------------------------------------------------------------- 2 bearings
line("2 output bearings (61813 pair, spring preload)")
print(f"span {Z_FRONT_BRG - Z_REAR_BRG:.1f} mm, load point {Z_LOAD - Z_FRONT_BRG:.1f} mm ahead of front centre")
for name, (tq, tilt, fr, fa) in CASES.items():
    for fa_sign in ((+1, -1) if fa else (+1,)):
        (frr, far), (frf, faf) = bearing_loads(tilt, fr, fa_sign * fa, SPRING_F)
        pr, p0r = equivalent_loads(max(frr, 1), far)
        pf, p0f = equivalent_loads(max(frf, 1), faf)
        tag = f"{name} Fa {fa_sign * fa:+.0f}"
        print(f"{tag:28s} rear Fr {frr:6.0f} Fa {far:4.0f} P {pr:6.0f} s0 {C0 / p0r:5.1f} | "
              f"front Fr {frf:6.0f} Fa {faf:4.0f} P {pf:6.0f} s0 {C0 / p0f:5.1f}")
(frr, far), (frf, faf) = bearing_loads(*CASES["L1 continuous"][1:3], CASES["L1 continuous"][3], SPRING_F)
p_front, _ = equivalent_loads(frf, faf + 150)
l10_mrev = (C_DYN / p_front) ** 3
print(f"L1 life (front, worst Fa {faf + 150:.0f} N): P {p_front:.0f} N  L10 {l10_mrev:.0f} Mrev = {l10_mrev * 1e6 / 72 / 60:,.0f} h @72 rpm")

line("2b tilt stiffness / misalignment")


def tilt_angle(tilt, fr, fa, seat_clear_um):
    """Output tilt (rad) = elastic ball approach of both bearings + outer-ring seat play."""
    (frr, _), (frf, _) = bearing_loads(tilt, fr, fa, SPRING_F)
    return (ball_deflection(frr) + ball_deflection(frf) + seat_clear_um) / 1000 / (Z_FRONT_BRG - Z_REAR_BRG)


SEAT_CLEAR = 10.0  # selective fit: each outer ring 3..10 um diametral, worst case both rings shifted
for name in ("L1 continuous", "L4 combined proof"):
    _, tilt, fr, fa = CASES[name]
    for label, c in (("elastic only", 0.0), ("+ selective seats", SEAT_CLEAR), ("+ plain H6 seats", 35.0)):
        th = tilt_angle(tilt, fr, fa, c)
        print(f"{name:20s} {label:18s} {th * 1e3:4.2f} mrad ({math.degrees(th) * 60:4.1f} arcmin)  tip@670 {th * 670:4.2f} mm")

# ---------------------------------------------------------------- 3 gears
line("3 gears (KA 1.25, KV 1.1, Kgamma 1.2, KHbeta from crowned line-contact model)")
F_HB = 8.0 * 0.85  # um, iso 7 helix slope deviation after case-hardened running-in (y_beta 15 %)
CROWNS = (0.0, 4.0, 6.0, 8.0, 10.0)
CROWN_S2 = 6.0  # um, chosen lead crowning on planet-2 (and sun-2)
CROWN_S1 = 4.0  # um, lead crowning on planet-1 (carrier-1 floats, no tilt)
print("stage-2 KHbeta vs lead crowning (um):", "  ".join(f"C{c:.0f}" for c in CROWNS))
for name, (tq, tilt, fr, fa) in CASES.items():
    if tq == 0:
        continue
    ft2 = 2 * tq / 4.75 / 0.018 / 3 * 1.2
    f_ma = F_HB + tilt_angle(tilt, fr, fa, SEAT_CLEAR) * 10 * 1000 if tilt else F_HB
    print(f"  {name:20s} f_ma {f_ma:4.1f} um:", "  ".join(f"{k_h_beta(ft2, 10, f_ma, c):4.2f}" for c in CROWNS))
c_star, f_star = 2.0 * 20 / 46.8, 1.0 * 20 / 46.8
print(f"  model vs ISO 6336-1 annex C (full face contact, C 2 um, f 1 um, w 46.8): "
      f"{k_h_beta(468, 10, 1.0, 2.0):.3f} vs {1 + c_star / 3 + f_star ** 2 / (16 * c_star):.3f}")
for name, (tq, tilt, fr, fa) in CASES.items():
    if tq == 0:
        continue
    ts2 = tq / (5 * 0.95)
    tm = ts2 / (6 * 0.95)
    ft1 = 2 * tm / 0.0144 / 3 * 1.2
    ft2 = 2 * ts2 / 0.018 / 3 * 1.2
    f_ma2 = F_HB + tilt_angle(tilt, fr, fa, SEAT_CLEAR) * 10 * 1000 if tilt else F_HB
    khb1 = k_h_beta(ft1, 10, F_HB, CROWN_S1)
    khb2 = k_h_beta(ft2, 10, f_ma2, CROWN_S2)
    k1, k2 = 1.25 * 1.1 * khb1, 1.25 * 1.1 * khb2
    print(f"{name}: Tmotor {tm:.3f} N*m, Tsun2 {ts2:.2f} N*m, ring-2 reaction {tq - ts2:.1f} N*m, ring-1 {ts2 - tm:.2f} N*m")
    print(f"  S1 Ft {ft1:4.0f} N  lewis {ft1 / (10 * 0.8 * lewis_y(18)) * khb1:5.0f} MPa  KHbeta {khb1:4.2f}  "
          f"sigH sun {hertz(ft1, 10, 14.4, 2, k1):5.0f}  ring {hertz(ft1, 10, 28.8, 2.5, k1, True):5.0f}")
    print(f"  S2 Ft {ft2:4.0f} N  lewis {ft2 / (10 * lewis_y(18)) * khb2:5.0f} MPa  f_ma {f_ma2:4.1f} um KHbeta {khb2:4.2f}  "
          f"sigH sun {hertz(ft2, 10, 18, 1.5, k2):5.0f}  ring {hertz(ft2, 10, 27, 72 / 27, k2, True):5.0f}")
print("  allowables: 16MnCr5 case-hardened sigHlim 1500 / sigFlim 500 (x ZNT/YNT 1.6/2.5 static);"
      " 42CrMo4 nitrided ring sigHlim 1000-1200")
ts2 = 30 / 4.75
p_hk = 2 * 2 * ts2 / 0.018 / 3 * 1.2
n_rel = (360 - 72) * 18 / 27
print(f"HK0810 stage-2 at L1: P {p_hk:.0f} N, n_rel {n_rel:.0f} rpm, L10h {(3800 / p_hk) ** (10 / 3) * 1e6 / n_rel / 60:,.0f} h")
p_pin = 2 * 2 * (50 / 4.75) / 0.018 / 3 * 1.2
m_pin = p_pin * (21 / 4 - 10 / 8)
print(f"pin-2 bending at L2: {32 * m_pin / (math.pi * 8 ** 3):.0f} MPa (52100 60 HRC)")
for j in (0.03, 0.05, 0.07):
    print(f"backlash {j} mm/mesh -> output {math.degrees(j / 22.5 + j / 21.6 / 5):.3f} deg")

# ---------------------------------------------------------------- 4 preload stack
line("4 spring preload: tolerance + thermal stack")
# H = L_hp + t_f - B_fo/2 - B_fi/2 - L_post - B_ri/2 - B_ro/2 - W_ring1 + (ga_f - ga_r)/2
nominal = dict(L_hp=41.5, t_f=7.5, L_post=11.0, W_ring1=15.35)
tol = dict(L_hp=0.03, t_f=0.02, L_post=0.02, W_ring1=0.02)
h_nom = nominal["L_hp"] + nominal["t_f"] - 20 - nominal["L_post"] - nominal["W_ring1"]
half_width_mean, half_width_tol = 0.0375, 0.0375  # each ring width -0.15/0, enters as half
a_curv = 0.278  # (fi + fo - 1) * Dw, mm
ga = [2 * math.sqrt(a_curv * gr / 1000) for gr in (23, 43)]  # c3 axial play range
ga_tol = (ga[1] - ga[0]) / 2
h_mean = h_nom + 4 * half_width_mean
wc = sum(tol.values()) + 4 * half_width_tol + ga_tol
rss = math.sqrt(sum(v ** 2 for v in tol.values()) + 4 * half_width_tol ** 2 + ga_tol ** 2)
print(f"geometric nominal H {h_nom:.3f}, mean with bearing width tolerance {h_mean:.3f}")
print(f"C3 axial play per bearing {ga[0] * 1000:.0f}-{ga[1] * 1000:.0f} um; worst case +/-{wc:.3f}, RSS +/-{rss:.3f}")
for label, h in (("H min (WC)", h_mean - wc), ("H mean", h_mean), ("H max (WC)", h_mean + wc)):
    f = SPRING_F - SPRING_K * (h - SPRING_H)
    print(f"  {label:11s} {h:.3f} mm -> {f:5.0f} N nominal, {f * (1 - SPRING_TOL):5.0f}..{f * (1 + SPRING_TOL):5.0f} N with spring tol")
f_min = (SPRING_F - SPRING_K * (h_mean + wc - SPRING_H)) * (1 - SPRING_TOL)
f_max = (SPRING_F - SPRING_K * (h_mean - wc - SPRING_H)) * (1 + SPRING_TOL)
print(f"front residual at -150 N: {f_min - 150:.0f} N (min)  front max at +150 N: {f_max + 150:.0f} N")
dh_per_k = (nominal["L_hp"] * A_AL - (20 + nominal["L_post"] + nominal["W_ring1"] - nominal["t_f"]) * A_ST) / 1000
for dt in (-40, -20, 60):
    print(f"  dT {dt:+d} K -> dH {dh_per_k * dt:+.1f} um -> dF {-SPRING_K * dh_per_k * dt / 1000:+.1f} N")
print(f"SKF small-motor guideline F = 0.005..0.01 x d = {0.005 * 65 * 1000:.0f}..{0.01 * 65 * 1000:.0f} N; this spring k = {SPRING_F / 65 / 1000:.4f}")
print(f"rear ring stick-slip: mu 0.15 x Fr_rear(L4) {0.15 * bearing_loads(50, 150, 150, SPRING_F)[0][0]:.0f} N vs spring {SPRING_F:.0f} N")

# ---------------------------------------------------------------- 5 fits vs temperature
line("5 fits vs temperature (um, + = clearance, - = interference)")
fits = [
    # name, dia, hole lo/hi, shaft lo/hi, alpha hole, alpha shaft
    ("ring-1 OD in housing  D85 K6/h5", 85, -18, 4, -15, 0, A_AL, A_ST),
    ("cartridge in housing  D89 G7/h6", 89, 12, 47, -22, 0, A_AL, A_ST),
    ("outer rings, selective D85 OD+3/+10", 85, 3, 10, 0, 0, A_ST, A_ST),
    ("IR on carrier-2       D65 brg/j5", 65, -15, 0, -7, 6, A_ST, A_ST),
    ("labyrinth D40.6H8 over sun-1 D40h8", 40.6, 600, 639, -39, 0, A_AL, A_ST),
]
for name, d, hlo, hhi, slo, shi, ah, as_ in fits:
    row = []
    for dt in (-40, -20, 0, 60):
        g = d * (ah - as_) * dt / 1000
        row.append(f"{hlo - shi + g:+5.0f}..{hhi - slo + g:+5.0f}")
    print(f"{name:36s} -20C {row[0]}  0C {row[1]}  20C {row[2]}  80C {row[3]}")
gr_red = 0.8 * (6 + 15) + A_ST * 5 * DPW / 1000
print(f"radial clearance loss: j5 max interference x0.8 + 5 K ring gradient = {gr_red:.1f} um  "
      f"-> Normal(8-28) min {8 - gr_red:+.1f}  C3(23-43) min {23 - gr_red:+.1f}")

# ---------------------------------------------------------------- 6 joints
line("6 bolted joints and dowels")


def preload(size, torque):
    """Assembly preload (n) for a 12.9 screw at torque (n*m), mu 0.12."""
    return PRELOAD_PER_NM[size] * torque


def joint(name, n, size, torque, r_bolt, r_in, r_out, mu, torque_load, tilt_load):
    """Friction torque and separation moment of a bolted annular flange."""
    fm = preload(size, torque)
    fk = n * fm
    t_slip = fk * mu * r_bolt / 1000
    area = math.pi * (r_out ** 2 - r_in ** 2)
    w = math.pi * (r_out ** 4 - r_in ** 4) / (4 * r_out)
    m_sep = fk * w / area / 1000
    sep = f"separation {m_sep:5.0f} N*m (load {tilt_load:.0f}, SF {m_sep / tilt_load:4.1f})" if tilt_load else ""
    print(f"{name:32s} {n}x{size} @{torque} N*m: FM {fm:5.0f} N  slip {t_slip:5.0f} N*m "
          f"(load {torque_load:.0f}, SF {t_slip / torque_load:4.1f})  {sep}")
    return fm


joint("cartridge flange -> housing", 8, "M3", 1.2, 46.5, 44.5, 50, 0.15, 50 - 50 / 4.75, 50 + 0.15 * 9)
joint("rear plate -> housing lip", 6, "M3", 1.2, 47.0, 44.0, 50, 0.15, 50, 50 + 0.15 * 95.5)
joint("torso bracket -> rear plate", 6, "M4", 3.0, 38.0, 30.0, 50, 0.15, 50, 50 + 0.15 * 95.5)
joint("arm -> output flange", 6, "M5", 8.0, 26.0, 20.0, 39, 0.15, 50, 50 + 0.15 * 0)
joint("carrier-2 halves", 3, "M4", 4.0, 27.0, 19.5, 34.5, 0.15, 50, 0)
joint("sun-1 -> rotor (pcd 25 worst)", 4, "M3", 0.8, 12.5, 10.0, 20.0, 0.15, 50 / (RATIO * ETA), 0)
fm_m3 = preload("M3", 1.2)
tau_al = 331.0  # 7075-t6 shear strength
for name, le in (("housing M3 x6 engage (cartridge)", 6.0), ("housing lip M3 x2.6 engage (plate)", 2.6)):
    a_sh = 0.75 * math.pi * 3.0 * le
    print(f"{name:36s} strip {a_sh * tau_al:5.0f} N vs FM {fm_m3:.0f} N  SF {a_sh * tau_al / fm_m3:.1f}")
for name, torque_nm, r, n, d, le in (("ring-1 dowels 2x D3 (slot 1.5 deep)", 50 / 4.75 - 50 / 28.5, 39.75, 2, 3.0, 1.5),
                                     ("cartridge dowels 2x D4 (backup)", 50 - 50 / 4.75, 47.0, 2, 4.0, 4.0),
                                     ("plate dowels 2x D3 (backup)", 50, 47.0, 2, 3.0, 3.0)):
    f = torque_nm * 1000 / r / n
    print(f"{name:36s} {f:5.0f} N each  shear {f / (math.pi * d ** 2 / 4):5.0f} MPa  bearing(Al) {f / (d * le):4.0f} MPa")
f_post = 50 / 0.027 / 3
print(f"carrier-2 post shear {f_post:.0f} N each, bending {32 * f_post * 5.5 / (math.pi * 15 ** 3):.0f} MPa")
f_lip = f_max + 150
m_lip = f_lip / (2 * math.pi * 41.25) * 3.0
print(f"cover lip: {f_lip:.0f} N -> line {f_lip / (2 * math.pi * 41.25):.2f} N/mm, bending {6 * m_lip / 3.0 ** 2:.0f} MPa")

# ---------------------------------------------------------------- 8 gear inspection
line("8 gear inspection data (x = 0, 20 deg, backlash allowance 0.025 per gear)")
ALPHA = math.radians(20)
INV_A = math.tan(ALPHA) - ALPHA


def inv_inverse(v):
    """Return the pressure angle whose involute function equals v (newton)."""
    a = 0.5
    for _ in range(50):
        a -= (math.tan(a) - a - v) / (math.tan(a) ** 2)
    return a


def span(z, m, k, ds):
    """Base tangent length Wk over k teeth, nominal and with thickness reduction ds."""
    w = m * math.cos(ALPHA) * (math.pi * (k - 0.5) + z * INV_A)
    return w, w - ds * math.cos(ALPHA)


def between_pins(z, m, dp, de):
    """Measurement between two pins (even z) for an internal ring, space widened by de."""
    e = math.pi * m / 2 + de
    a_m = inv_inverse(e / (z * m) + INV_A - dp / (z * m * math.cos(ALPHA)))
    return z * m * math.cos(ALPHA) / math.cos(a_m) - dp, math.degrees(a_m)


for name, z, m, k in (("sun-1", 18, 0.8, 3), ("planet-1", 36, 0.8, 5), ("sun-2", 18, 1.0, 3), ("planet-2", 27, 1.0, 4)):
    w0, w1 = span(z, m, k, 0.025)
    print(f"{name:9s} z{z} m{m}: W{k} nominal {w0:.3f}  with allowance {w1:.3f} (-0.000/-0.015)")
for name, z, m, dp in (("ring-1", 90, 0.8, 1.2), ("ring-2", 72, 1.0, 1.5)):
    mi0, a0 = between_pins(z, m, dp, 0.0)
    mi1, a1 = between_pins(z, m, dp, 0.025)
    print(f"{name:9s} z{z} m{m}: Mi between D{dp} pins nominal {mi0:.3f}  with allowance {mi1:.3f} (+0.015/-0.000), pin contact angle {a1:.1f} deg")

# ---------------------------------------------------------------- 7 housing + homing
line("7 housing and homing magnet")
j_tube = math.pi * (100 ** 4 - 89 ** 4) / 32
print(f"housing torsion at 50 N*m: {50e3 * 50 / j_tube:.1f} MPa; bending at 51.4 N*m: {51.4e3 * 50 / (j_tube / 2):.1f} MPa")
br, rm, lm = 1.43, 1.5, 2.0
for gap in (1.2, 1.4, 2.0):
    b = br / 2 * ((lm + gap) / math.hypot(rm, lm + gap) - gap / math.hypot(rm, gap))
    print(f"homing magnet D3x2 N52 on-axis field at {gap} mm: {b * 1000:.0f} mT (DRV5033FA BOP max 6.8 mT)")
