"""Shoulder v4 coaxial cycloid check. Run: python calc.py

The geometry numbers come from gen_actuator_3mf.py.
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
R_LL = 2.0 * 0.0846
KV, VOLT = 90.0, 24.0
ETA = 0.85
DISC_SHARE = 0.55  # each disc is drawn for a bit more than half, so one disc can lead
C0_NEEDLE = 12900.0  # SKF K 20x24x10, N. the disc covers 7 of the 10 mm
C0_BALL = 2600.0  # SKF 61805, the bearing this needle replaces


def hertz(force, radius):
    """Peak line-contact pressure in MPa. Steel on steel, flank taken as flat."""
    e_star = 1.0 / ((1 - 0.3 ** 2) / 210e3 + (1 - 0.3 ** 2) / 210e3)
    return math.sqrt(force * e_star / (math.pi * 7.0 * radius))


def pin_case(lev, torque_nm, k):
    """Force on the k pins with the longest arms."""
    useful = np.where(lev > 1e-6)[0]
    order = useful[np.argsort(lev[useful])[::-1]][:k]
    arms = lev[order]
    return float(np.max(torque_nm * 1000.0 * arms / np.sum(arms ** 2)))


def main():
    """Print speed, clearance, contact cases and the needle margin."""
    t_cont = KT * I_CONT * g.RATIO * ETA
    t_proof = KT * I_PROOF * g.RATIO * ETA
    n_cont = KV * (VOLT - I_CONT * R_LL)
    print(f"continuous {t_cont:.1f} N*m, proof {t_proof:.1f} N*m, both at efficiency {ETA:.2f}")
    print(f"speed no-load {KV * VOLT / g.RATIO * 6:.0f} deg/s, "
          f"at {I_CONT:.2f} A {n_cont / g.RATIO * 6:.0f} deg/s. 180 deg/s is 30 rpm")
    print(f"e {g.ECC:.3f} mm, relief {g.DR:.2f} mm. "
          f"the relief is {g.DR / g.ECC:.0%} of the offset, so most teeth can still meet")
    red = cy.Reducer(g.ZP, g.PIN_R, g.PIN_RAD, g.ECC, g.DR, g.OUT_R, g.OUT_N, g.OUT_PIN_R,
                     g.OUT_PIN_R + g.ECC + g.OUT_PLAY, n=1600)
    gaps, ogaps = [], []
    for alpha in np.linspace(0.0, 2 * np.pi, 24, endpoint=False):
        for disc in ("A", "B"):
            gaps.append(float(np.min(red.ring_clearance(alpha, disc))))
            ogaps.append(float(np.min(red.out_clearance(alpha, disc))))
    print(f"ring gap min {min(gaps):.3f} mm, after 0.006 mm m6 oversize {min(gaps) - 0.006:.3f}")
    print(f"output gap min {min(ogaps):.3f} mm  self-intersect {cy.self_intersects(red.prof['A'], 2)}")
    print(f"disc sweep radius {red.max_radius(36):.2f} mm")
    worst = {"ideal": 0.0, "brg": 0.0, 1: 0.0, 2: 0.0, 3: 0.0}
    for alpha in np.linspace(0.0, 2 * np.pi, 12, endpoint=False):
        load = red.loads(alpha, "A", t_cont * DISC_SHARE)
        worst["ideal"] = max(worst["ideal"], float(np.max(load["f_ring"])))
        worst["brg"] = max(worst["brg"], load["f_brg"])
        for k in (1, 2, 3):
            worst[k] = max(worst[k], pin_case(load["lev"], t_cont * DISC_SHARE, k))
    scale = t_proof / t_cont
    print(f"ideal share on one disc: pin {worst['ideal']:.0f} N, {hertz(worst['ideal'], g.PIN_RAD):.0f} MPa")
    for k in (1, 2, 3):
        print(f"{k}-pin case: {worst[k]:.0f} N, {hertz(worst[k], g.PIN_RAD):.0f} MPa "
              f"(proof {hertz(worst[k] * scale, g.PIN_RAD):.0f})")
    used = 7.0 / 10.0  # disc face over the 10 mm needle
    c0 = C0_NEEDLE * used
    print(f"needle about {c0:.0f} N static over the 7 mm disc (catalog {C0_NEEDLE:.0f} N for 10 mm)")
    print(f"bearing force {worst['brg']:.0f} N continuous, {worst['brg'] * scale:.0f} N proof")
    print(f"s0 continuous {c0 / worst['brg']:.2f}, proof {c0 / (worst['brg'] * scale):.2f}. "
          f"a 61805 at {C0_BALL:.0f} N would be s0 {C0_BALL / (worst['brg'] * scale):.2f} at proof")
    print(f"flange face z {g.Z_FLANGE1:.1f}, length {g.Z_FLANGE1 - g.LID_OUTER:.1f} mm")


if __name__ == "__main__":
    main()
