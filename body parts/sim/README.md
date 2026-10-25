# Arm simulation

Rigid-body check of the Rev 2 arm (shoulder pitch + direct-drive elbow pitch, no hand).
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
sim/.venv/Scripts/python sim/check_arm.py --view --mass 0.15
```

## What the model uses

| Item | Value | Source |
|---|---|---|
| Upper arm + elbow motor | 0.741 kg, centre 217 mm from the shoulder | `arm/cad/mass.txt` |
| Forearm | 0.157 kg, centre 122 mm from the elbow | `arm/cad/mass.txt` |
| Payload point | 320.5 mm from the elbow (hand centre) | `arm/parts.md` |
| Shoulder | 10 N·m (printed-arm limit; the actuator itself is 30 N·m continuous) | `arm/cad/calc.txt` §6 |
| Elbow | 0.81 N·m continuous (thermal estimate), 1.84 N·m at the 20 A limit | `arm/cad/calc.txt` §2b, §3 |
| Lift rate | 12.57 rad/s² | `arm/cad/calc.txt` |

Link spin inertia is the point-mass model used in `calc.txt`. Joint friction
is zero until a motor is measured. The elbow is direct drive, so its numbers
are motor torque.
