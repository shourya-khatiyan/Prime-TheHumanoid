"""Torque check for the v0 arm.

The links are rigid. This reports the joint torque gravity and a design
acceleration demand, then the heaviest mass those torques can hold.
It does not check whether the plastic or the bolts yield. That is calc.py.
"""

import argparse
from pathlib import Path

import mujoco
import mujoco.viewer
import numpy as np

XML = Path(__file__).with_name("arm.xml")

# output torques, n*m. elbow: params.py. shoulder: calc.txt l1 / l2.
ELBOW_CONTINUOUS = 4.93
ELBOW_LIMIT = 8.27  # odesc 10 a, after the 20:1 cycloid
SHOULDER_CONTINUOUS = 30.0
SHOULDER_PROOF = 50.0
# arm/cad/calc.txt: 180 deg/s in 0.25 s
ALPHA = 12.57  # rad/s^2

# calc.txt gravity, arm horizontal, no hand
EXPECT_SHOULDER = 3.26
EXPECT_ELBOW = 0.21

STRAIGHT = np.array([-np.pi / 2, 0.0])  # both links forward
BENT = np.array([-np.pi / 2, np.pi / 2])  # forearm hanging


def load(mass):
    """Build the arm with a payload mass in kg at the future hand centre."""
    model = mujoco.MjModel.from_xml_path(str(XML))
    body = mujoco.mj_name2id(model, mujoco.mjtObj.mjOBJ_BODY, "payload")
    model.body_mass[body] = mass
    model.body_inertia[body] = np.array([1e-6, 1e-6, 1e-6])
    data = mujoco.MjData(model)
    mujoco.mj_setConst(model, data)
    return model, data


def joint_torque(mass, q, qacc):
    """Torque each motor must apply to hold this pose and acceleration.

    q and qacc are [shoulder, elbow] in rad and rad/s^2.
    """
    model, data = load(mass)
    data.qpos[:] = q
    data.qvel[:] = 0.0
    data.qacc[:] = qacc
    mujoco.mj_inverse(model, data)
    return np.array(data.qfrc_inverse, dtype=float)


def lifting(mass, q):
    """Torque while accelerating the load upward at the design rate.

    Upward is whichever shoulder acceleration adds to gravity.
    """
    base = joint_torque(mass, q, np.zeros(2))
    plus = joint_torque(mass, q, np.array([ALPHA, 0.0]))
    minus = joint_torque(mass, q, np.array([-ALPHA, 0.0]))
    return plus if abs(plus[0]) > abs(minus[0]) else minus


def within(tau, limits):
    """True when each joint torque is inside its limit."""
    return abs(tau[0]) <= limits[0] and abs(tau[1]) <= limits[1]


def max_mass(q, dynamic, limits):
    """Heaviest payload, in kg, that stays inside both torque limits."""
    ask = lifting if dynamic else lambda m, pose: joint_torque(m, pose, np.zeros(2))
    if not within(ask(0.0, q), limits):
        return 0.0
    lo, hi = 0.0, 20.0
    for _ in range(40):
        mid = 0.5 * (lo + hi)
        if within(ask(mid, q), limits):
            lo = mid
        else:
            hi = mid
    return lo


def report_pose(name, q):
    """Print hold and lift capacity for one pose."""
    tau = joint_torque(0.0, q, np.zeros(2))
    print(f"\n{name}")
    print(f"  no payload, hold: shoulder {abs(tau[0]):.2f} n*m, elbow {abs(tau[1]):.2f} n*m")
    cases = (
        ("hold, minutes", False, (SHOULDER_CONTINUOUS, ELBOW_CONTINUOUS)),
        ("hold, short peak", False, (SHOULDER_PROOF, ELBOW_LIMIT)),
        ("lift, minutes", True, (SHOULDER_CONTINUOUS, ELBOW_CONTINUOUS)),
        ("lift, short peak", True, (SHOULDER_PROOF, ELBOW_LIMIT)),
    )
    for label, dynamic, limits in cases:
        mass = max_mass(q, dynamic, limits)
        tau_m = lifting(mass, q) if dynamic else joint_torque(mass, q, np.zeros(2))
        print(
            f"  {label:22s} {mass:5.2f} kg"
            f"   shoulder {abs(tau_m[0]):5.2f} / {limits[0]:.2f}"
            f"   elbow {abs(tau_m[1]):5.2f} / {limits[1]:.2f}"
        )


def check_gravity():
    """Stop if the empty-arm gravity torque does not match calc.txt."""
    tau = joint_torque(0.0, STRAIGHT, np.zeros(2))
    shoulder = abs(tau[0])
    elbow = abs(tau[1])
    print("gravity check, arm straight and horizontal, no hand")
    print(f"  shoulder {shoulder:.2f} n*m  (calc.txt {EXPECT_SHOULDER:.2f})")
    print(f"  elbow    {elbow:.2f} n*m  (calc.txt {EXPECT_ELBOW:.2f})")
    if abs(shoulder - EXPECT_SHOULDER) > 0.05 or abs(elbow - EXPECT_ELBOW) > 0.03:
        raise SystemExit("model does not match calc.txt; do not trust the payload numbers")


def view(mass):
    """Open a window and raise the arm from hanging to straight forward."""
    model, data = load(mass)
    limit = np.array([SHOULDER_CONTINUOUS, ELBOW_CONTINUOUS])
    with mujoco.viewer.launch_passive(model, data) as viewer:
        while viewer.is_running():
            t = data.time
            s = np.clip(t / 3.0, 0.0, 1.0)
            blend = 10 * s**3 - 15 * s**4 + 6 * s**5
            q_des = blend * STRAIGHT
            data.qacc[:] = 40.0 * (q_des - data.qpos) - 8.0 * data.qvel
            mujoco.mj_inverse(model, data)
            data.ctrl[:] = np.clip(data.qfrc_inverse, -limit, limit)
            mujoco.mj_step(model, data)
            viewer.sync()


def main():
    """Run the gravity check and the payload table."""
    parser = argparse.ArgumentParser(description="vayn arm torque and payload check")
    parser.add_argument("--view", action="store_true", help="show the arm lifting a mass")
    parser.add_argument("--mass", type=float, default=1.0, help="payload kg for --view")
    args = parser.parse_args()
    if args.view:
        view(args.mass)
        return
    check_gravity()
    report_pose("straight out (worst lever)", STRAIGHT)
    report_pose("elbow bent 90 deg, forearm down", BENT)


if __name__ == "__main__":
    main()
