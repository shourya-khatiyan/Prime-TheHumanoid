"""Shoulder v3 cycloid check. Same sweep as elbow v0. Run: python calc.py"""

import os
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "elbow v0", "cad"))
import cycloid as cy

KT = 0.0919
I_CONT, I_PROOF = 12.09, 20.15
RATIO = 45
ETA = 0.85
PIN_N = 46
PIN_R = 38.0
PIN_RAD = 2.0
ECC = 0.65 * PIN_R / PIN_N
DR = 0.12
OUT_R, OUT_PIN_R, OUT_N = 22.0, 3.0, 8
OUT_PLAY = 0.20
PIN_OVERSIZE = 0.006  # radial, ISO 8734 m6 over nominal, same class as the elbow note


def torque(amps):
    """Output torque (N*m) from motor current, ratio and the efficiency allowance."""
    return KT * amps * RATIO * ETA


def main():
    """Print ratio, clearance sweep and a steel contact check."""
    t_cont, t_proof = torque(I_CONT), torque(I_PROOF)
    print(f"continuous {t_cont:.1f} N*m at {2160 / RATIO:.1f} rpm ({2160 / RATIO * 6:.0f} deg/s no-load)")
    print(f"proof {t_proof:.1f} N*m   e {ECC:.3f} mm   lambda {ECC * PIN_N / PIN_R:.2f}")
    print("these torques are motor current x ratio x 0.85. they are not a measured gearbox test.")
    red = cy.Reducer(PIN_N, PIN_R, PIN_RAD, ECC, DR, OUT_R, OUT_N, OUT_PIN_R,
                     OUT_PIN_R + ECC + OUT_PLAY, n=2500)
    gaps, ogaps = [], []
    for alpha in np.linspace(0, 2 * np.pi, 36, endpoint=False):
        for disc in ("A", "B"):
            gaps.append(float(np.min(red.ring_clearance(alpha, disc))))
            ogaps.append(float(np.min(red.out_clearance(alpha, disc))))
    print(f"ring-pin gap min {min(gaps):.3f} mm, after m6 pin oversize {min(gaps) - PIN_OVERSIZE:.3f}")
    print(f"output-hole gap min {min(ogaps):.3f} mm")
    print(f"self-intersection {cy.self_intersects(red.prof['A'], 2)}")
    worst, fmax = 0.0, 0.0
    for alpha in np.linspace(0, 2 * np.pi, 12, endpoint=False):
        load = red.loads(alpha, "A", t_cont * 0.55)
        force = float(np.max(load["f_ring"]))
        pressure = cy.hertz_line(force, 8.0, PIN_RAD, 210e3, 0.3, 210e3, 0.3)
        worst, fmax = max(worst, pressure), max(fmax, force)
    print(f"steel pin on flat, disc face 8 mm, share 0.55: pin force {fmax:.0f} N, p0 {worst:.0f} MPa")


if __name__ == "__main__":
    main()
