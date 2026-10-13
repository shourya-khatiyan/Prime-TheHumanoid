# Arm simulation

Rigid-body check of the v0 arm (shoulder pitch + elbow pitch, no hand).
It answers whether the motors can hold or lift a mass. It does not answer
whether a printed part breaks. That stays in `arm/cad/calc.py`.

## Run

```bash
python -m venv sim/.venv
sim/.venv/Scripts/python -m pip install mujoco
sim/.venv/Scripts/python sim/check_arm.py
```

A window of the same model:

```bash
sim/.venv/Scripts/python sim/check_arm.py --view --mass 1.0
```

## What the model uses

| Item | Value | Source |
|---|---|---|
| Upper arm | 1.1535 kg, centre 202 mm from the shoulder | `arm/cad/mass.txt` |
| Forearm | 0.2606 kg, centre 84 mm from the elbow | `arm/cad/mass.txt` |
| Payload point | 320.5 mm from the elbow (future hand centre) | `arm/parts.md` |
| Shoulder | 30 N·m continuous, 50 N·m proof | `shoulder` calc, L1 / L2 |
| Elbow | 4.93 N·m continuous, 8.27 N·m at the 10 A cap | `elbow/cad/params.py` |
| Lift rate | 12.57 rad/s² | `arm/cad/calc.txt` |

Link spin inertia is the point-mass model used in `calc.txt`. Real mesh
inertia comes later, from the STEP file. Joint friction is zero until a
motor is measured. The torque numbers are already gearbox output, so
efficiency is not applied again.
