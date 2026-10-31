"""Loads, gaps and bearing margins for the shoulder v5 cycloid.

Run: python calc.py
The geometry numbers come from gen_actuator_3mf.py so the two files stay together.
"""

import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "elbow v0", "cad"))
import cycloid as cy
import gen_actuator_3mf as g

KT = 0.0919
I_CONT, I_PROOF = 12.09, 20.15
R_LL = 2.0 * 0.0846  # measured phase resistance, wye line value
KV, VOLT = 90.0, 24.0
RATIO = 55
ETA_LO, ETA_HI = 0.85 * 0.85, 0.90 * 0.90  # one mesh, then the second mesh
C0_NEEDLE = 12900.0  # SKF K 20x24x10, N
C0_MID = 10000.0  # SKF K 16x20x10, N
C0_OUT = 4550.0  # SKF 61906, N
SPAN = (g.Z_B1[0] + g.Z_B1[1]) / 2 - ((g.Z_B2[0] + g.Z_B2[1]) / 2)
SPAN = abs(SPAN)


def hertz(force, length, radius):
    """Peak line-contact pressure in MPa. Steel on steel, flank taken as flat."""
    e_star = 1.0 / ((1 - 0.3 ** 2) / 210e3 + (1 - 0.3 ** 2) / 210e3)
    return math.sqrt(force * e_star / (math.pi * length * radius))


def rpm(amps):
    """Loaded motor speed from KV and the line resistance."""
    return KV * (VOLT - amps * R_LL)


def pin_case(lev, torque_nm, k):
    """Force on the k pins with the longest arms. Same share the 2011 paper used."""
    useful = np.where(lev > 1e-6)[0]
    order = useful[np.argsort(lev[useful])[::-1]][:k]
    arms = lev[order]
    return float(np.max(torque_nm * 1000.0 * arms / np.sum(arms ** 2)))


def stage(name, zp, pin_r, torque):
    """Print clearance and contact pressure for one disc."""
    red = cy.Reducer(zp, g.PIN_R, pin_r, g.ECC, g.DR, g.OUT_R, g.OUT_N, g.OUT_PIN,
                     g.HOLE_R, n=1200)
    gaps = [float(np.min(red.ring_clearance(a, d)))
            for a in np.linspace(0, 2 * math.pi, 18, endpoint=False) for d in ("A", "B")]
    worst = {1: 0.0, 2: 0.0, 3: 0.0, "ideal": 0.0, "brg": 0.0}
    for a in np.linspace(0, 2 * math.pi, 12, endpoint=False):
        load = red.loads(a, "A", torque)
        worst["ideal"] = max(worst["ideal"], float(np.max(load["f_ring"])))
        worst["brg"] = max(worst["brg"], load["f_brg"])
        for k in (1, 2, 3):
            worst[k] = max(worst[k], pin_case(load["lev"], torque, k))
    print(f"{name}: gap min {min(gaps):.3f} mm, after 0.006 mm m6 oversize {min(gaps) - 0.006:.3f}")
    print(f"  ideal pin {worst['ideal']:.0f} N, {hertz(worst['ideal'], g.FACE, pin_r):.0f} MPa, "
          f"needle {worst['brg']:.0f} N")
    for k in (1, 2, 3):
        print(f"  {k}-pin {worst[k]:.0f} N, {hertz(worst[k], g.FACE, pin_r):.0f} MPa")
    return worst["brg"]


def main():
    """Print speed, torque, contact stress and bearing margins."""
    t_m = KT * I_CONT
    t_lo, t_hi = t_m * RATIO * ETA_LO, t_m * RATIO * ETA_HI
    scale = I_PROOF / I_CONT
    print(f"ratio {RATIO}:1   lobes {g.ZC1} then {g.ZC2}   e {g.ECC:.2f} mm   pin circle {g.PIN_R:.0f} mm")
    print(f"speed no-load {KV * VOLT / RATIO * 6:.0f} deg/s, "
          f"at {I_CONT:.2f} A {rpm(I_CONT) / RATIO * 6:.0f} deg/s, "
          f"at {I_PROOF:.2f} A {rpm(I_PROOF) / RATIO * 6:.0f} deg/s")
    print(f"torque at {I_CONT:.2f} A: {t_lo:.1f} to {t_hi:.1f} N*m "
          f"(second mesh at 0.85, then at 0.90). proof scales by {scale:.2f}")
    # check the higher torque. if that passes, the lower one does too.
    b1 = stage("stage 1, 12 pins", g.ZP1, g.PIN1, t_hi)
    b2 = stage("stage 2, 10 pins", g.ZP2, g.PIN2, t_hi)
    print(f"needle K20x24x10 C0 {C0_NEEDLE:.0f} N: s0 continuous {C0_NEEDLE / max(b1, b2):.2f}, "
          f"proof {C0_NEEDLE / (max(b1, b2) * scale):.2f}")
    f_mid = t_hi / (g.OUT_R / 1000.0)
    print(f"middle plate roller load about {f_mid:.0f} N at {t_hi:.1f} N*m. "
          f"K16x20x10 s0 continuous {C0_MID / f_mid:.2f}, proof {C0_MID / (f_mid * scale):.2f}")
    tilt = 50.0
    f_tilt = tilt / (SPAN / 1000.0)
    print(f"output bearing span {SPAN:.1f} mm. 50 N*m tilt gives {f_tilt:.0f} N on one 61906, "
          f"s0 {C0_OUT / f_tilt:.2f}")
    print(f"gearbox ends at z {g.Z_FLANGE[1]:.1f}. overall z {g.LID_OUTER:.1f} to {g.Z_FLANGE[1]:.1f}, "
          f"length {g.Z_FLANGE[1] - g.LID_OUTER:.1f} mm")


if __name__ == "__main__":
    main()
