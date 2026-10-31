"""Torque and speed for the shoulder v3 cycloid. Run: python calc.py"""

import math

KT = 0.0919  # N*m/A, same motor constant as shoulder/cad/calc.py
I_CONT = 12.09  # A, the old 30 N*m planetary current
I_PROOF = 20.15
RATIO = 45
ETA = 0.85  # between a measured 81% peak and a 93% single-stage catalogue figure
N_MOTOR = 90 * 24  # rpm, KV 90 at 24 V, no-load ceiling


def torque(amps):
    """Output torque (N*m) at this phase current."""
    return KT * amps * RATIO * ETA


def main():
    """Print the continuous and proof numbers."""
    print(f"motor torque at {I_CONT:.2f} A: {KT * I_CONT:.3f} N*m")
    print(f"continuous output: {torque(I_CONT):.1f} N*m at {N_MOTOR / RATIO:.1f} rpm")
    print(f"proof output: {torque(I_PROOF):.1f} N*m")
    print(f"eccentricity: {0.65 * 38 / 46:.3f} mm, pins 46 x D4 on R38")
    w = N_MOTOR * 2 * math.pi / 60
    p_in = KT * I_CONT * w
    print(f"gearbox heat at continuous, eta {ETA}: {p_in * (1 - ETA):.0f} W")


if __name__ == "__main__":
    main()
