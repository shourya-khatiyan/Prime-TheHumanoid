"""Shoulder v4 coaxial cycloid check. Run: python calc.py"""

import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "elbow v0", "cad"))
import cycloid as cy

KT = 0.0919
I_CONT, I_PROOF = 12.09, 20.15
RATIO = 45
ETA = 0.85
ZP = RATIO + 1
PIN_R = 44.0
PIN_RAD = 2.0
LAM = 0.55
ECC = LAM * PIN_R / ZP
DR = 0.12
OUT_R, OUT_N, OUT_PIN_R, OUT_PLAY = 30.0, 8, 3.0, 0.25
DISC_L = 7.0
PIN_OVERSIZE = 0.006


def torque(amps):
    """Output torque (N*m) from current, ratio and the 0.85 efficiency allowance."""
    return KT * amps * RATIO * ETA


def main():
    """Print speed, swept clearance and contact stress."""
    t_cont, t_proof = torque(I_CONT), torque(I_PROOF)
    print(f"continuous {t_cont:.1f} N*m at {2160 / RATIO:.1f} rpm ({2160 / RATIO * 6:.0f} deg/s no-load)")
    print(f"proof {t_proof:.1f} N*m")
    print(f"e {ECC:.3f} mm  lambda {LAM:.2f}  180 deg/s is {180 / 6:.0f} rpm")
    red = cy.Reducer(ZP, PIN_R, PIN_RAD, ECC, DR, OUT_R, OUT_N, OUT_PIN_R,
                     OUT_PIN_R + ECC + OUT_PLAY, n=2500)
    gaps, ogaps = [], []
    for alpha in np.linspace(0.0, 2 * np.pi, 36, endpoint=False):
        for disc in ("A", "B"):
            gaps.append(float(np.min(red.ring_clearance(alpha, disc))))
            ogaps.append(float(np.min(red.out_clearance(alpha, disc))))
    print(f"ring gap min {min(gaps):.3f} mm, after m6 oversize {min(gaps) - PIN_OVERSIZE:.3f}")
    print(f"output gap min {min(ogaps):.3f} mm  self-intersect {cy.self_intersects(red.prof['A'], 2)}")
    print(f"disc sweep radius {red.max_radius(72):.2f} mm")
    worst_p, worst_f, worst_b = 0.0, 0.0, 0.0
    for alpha in np.linspace(0.0, 2 * np.pi, 12, endpoint=False):
        for share, tag in ((0.55, t_cont), (0.55 * t_proof / t_cont, t_proof)):
            load = red.loads(alpha, "A", tag * 0.55 if tag == t_cont else t_proof * 0.55)
            force = float(np.max(load["f_ring"]))
            pressure = cy.hertz_line(force, DISC_L, PIN_RAD, 210e3, 0.3, 210e3, 0.3)
            if tag == t_cont:
                worst_p, worst_f = max(worst_p, pressure), max(worst_f, force)
                worst_b = max(worst_b, load["f_brg"])
    proof_b = worst_b * t_proof / t_cont
    print(f"continuous pin {worst_f:.0f} N, p0 {worst_p:.0f} MPa on a flat (limit 1500 case-hardened)")
    print(f"eccentric bearing force {worst_b:.0f} N continuous, {proof_b:.0f} N proof")
    print(f"61805 C0 2600 N: s0 continuous {2600 / worst_b:.2f}, proof {2600 / proof_b:.2f}")


if __name__ == "__main__":
    main()
