> **Revision note (2026-10-20, VAYN-6.2.1):** corrected in place to match the built hardware and live measurements:  
> gearbox 80:1 (4:1 planetary + 20:1 cycloidal) → **30:1 two-stage planetary (6:1 × 5:1)**  
> motor → **EaglePower LA8308 KV90** (20 pole pairs, counted)  
> torque target 80+ N·m → **30 N·m continuous / 50 N·m proof, theoretical and untested**  
> ODESC firmware **0.5.1** (read live)  
> the old system name "RHEI" replaced by **VAYN** throughout  
> The architecture decisions are in [VAYN-6.2.1](../VAYN - 6.2.1.md) and the build plan is in the [RT Core implementation spec](RT Core Implementation - VAYN 6.2.1.md).

> **We are not going to make VAYN directly control the BLDC phases. ODrive will do the low-level FOC/current control. VAYN will command the actuator at the joint/torque level.**  
> That is actually a good fit for VAYN-6.2.

---

# 1. Your actual actuator

Your current actuator (VAYN shoulder, `Prime-TheHumanoid/body parts/shoulder`) is:

```text
EaglePower LA8308 KV90 BLDC (20 pole pairs)
      ↓
Planetary stage 1
6:1  (sun 18 / planet 36 / ring 90)
      ↓
Planetary stage 2
5:1  (sun 18 / planet 27 / ring 72)
      ↓
Output joint
```

Total:

```text
6 × 5 = 30:1
```

And:

```text
Flipsky ODESC3.6 (ODrive v3.6 clone, firmware 0.5.1)
       +
AS5047P encoder (motor side, SPI)
       +
DRV5033 hall homing sensor (output flange)
```

Your target is:

> **30 N·m continuous / 50 N·m proof output torque at the shoulder joint, after real losses (theoretical, from** **`shoulder/cad/calc.txt`****; not yet tested).**

Right now that is still a **theoretical target** because we don't yet know measured motor current capability, winding resistance, actual gearbox efficiency, thermal behavior, backlash, bearing losses, etc.

That distinction is important.

---

# 2. First: how all of this fits into VAYN

The complete actuator/control architecture should look like this:

```text
                    VAYN SYSTEM
                         │
                         │
                  ┌──────▼──────┐
                  │   Orin NX   │
                  │             │
                  │ AI / Vision │
                  │ Policy      │
                  │ Planning    │
                  └──────┬──────┘
                         │
                    motion/torque
                      reference
                         │
                         ▼
              ┌────────────────────┐
              │   RT MOTION CORE   │
              │                    │
              │ State estimation   │
              │ Impedance control  │
              │ Whole-body control │
              │ Safety validation  │
              │ Command arbitration│
              └─────────┬──────────┘
                        │
                     CAN bus
                        │
                        ▼
              ┌────────────────────┐
              │   ODRIVE 3.6       │
              │                    │
              │ Position/velocity  │
              │ / torque interface │
              │                    │
              │     FOC            │
              │ Current control    │
              │ Motor commutation  │
              └─────────┬──────────┘
                        │
                   3-phase PWM
                        │
                        ▼
                 ┌────────────┐
                 │ 90 KV BLDC │
                 └─────┬──────┘
                       │
                     6:1
                       │
                       ▼
                  Planetary 1
                       │
                     5:1
                       │
                       ▼
                  Planetary 2
                       │
                       ▼
                 SHOULDER JOINT
```

And separately:

```text
                 SAFETY MCU
                     │
          ┌──────────┼──────────┐
          │          │          │
       current    encoder    temperature
          │          │          │
          └──────────┼──────────┘
                     │
               watchdog/fault
                     │
              safety mechanism
```

This is exactly the type of separation VAYN-6.2 is trying to establish: AI generates capability, the RT domain owns physical control, and independent hardware supervises safety.

---

# 3. What ODrive actually does

This is the first big concept you need to understand.

ODrive is **not just a dumb motor driver**.

It already contains the low-level machinery for:

```text
BLDC commutation
FOC
phase-current measurement
current regulation
motor calibration
encoder processing
motor protection
```

The ODrive architecture therefore becomes approximately:

```text
VAYN
  ↓
"Give the joint approximately 5 Nm"
  ↓
ODrive
  ↓
"How much q-axis current produces that?"
  ↓
FOC
  ↓
phase currents
  ↓
BLDC
```

This is good because **we absolutely do not want to write a BLDC FOC implementation from scratch as our first step.**

ODrive's firmware already exposes torque/current control modes, including `CONTROL_MODE_TORQUE_CONTROL` and `input_torque`. ([GitHub](https://github.com/odriverobotics/ODrive/blob/master/tools/odrive/enums.py?utm_source=chatgpt.com))

---

# 4. So where does VAYN's impedance control go?

This is an important architectural decision.

For our first VAYN implementation, I recommend:

```text
VAYN RT Core
      ↓
joint-level impedance / torque controller
      ↓
desired motor torque
      ↓
ODrive torque command
      ↓
ODrive FOC/current controller
      ↓
motor
```

So there are **two nested levels**:

### Outer loop — VAYN

```text
joint position
joint velocity
desired position
desired velocity
desired torque
        ↓
impedance controller
        ↓
desired torque
```

### Inner loop — ODrive

```text
desired motor torque
        ↓
Iq target
        ↓
FOC current controller
        ↓
PWM
        ↓
motor phases
```

That is a much cleaner implementation of VAYN than trying to replace ODrive's FOC.

---

# 5. Why this is useful

Suppose VAYN says:

```text
I want the shoulder to produce 40 Nm.
```

We can convert:

```text
joint torque
    ↓
gear ratio
    ↓
motor torque
    ↓
ODrive torque command
```

With your 30:1 gearbox:

```text
T_motor ≈ T_joint / (30 × η_gearbox)
```

So the ODrive only needs to control the motor-side torque.

---

# 6. Your theoretical torque actually looks promising — but there is a big "if"

ODrive documents the motor torque relationship approximately as:

Tmotor=8.27IKVT_{motor} = \\frac{8.27 I}{K_V}

for PM motors. (GitHub)

For your 90 KV motor:

Kt≈8.2790K_t \\approx \\frac{8.27}{90}

so:

Kt≈0.0919 Nm/AK_t \\approx 0.0919\\ Nm/A

Motor torque is therefore approximately:

```text
1 A → 0.092 Nm
10 A → 0.919 Nm
15 A → 1.38 Nm
20 A → 1.84 Nm
```

Ideal 30:1 gearbox:

```text
1 A → 2.76 Nm output
10 A → 27.6 Nm
15 A → 41.4 Nm
```

But this is **ideal**, before gearbox losses.

For example, with an assumed 87% total gearbox efficiency (the value in the GUI actuator profile, unproven):

```text
1 A → 2.40 Nm
10 A → 24.0 Nm
15 A → 36.0 Nm
```

So the theoretical 30 N·m continuous target needs about 12.5 A, and the 50 N·m proof load about 21 A. Both must be proven by the thermal test (`shoulder/cad/calc.txt` uses 12.09 A for 30 N·m at its own efficiency assumption).

But we **cannot conclude that yet**.

We need:

```text
motor continuous current
motor winding resistance
motor thermal limit
ODrive continuous current
gearbox efficiency
gearbox thermal losses
bearing losses
gearbox preload
actual speed
actual duty cycle
```

ODrive's own documentation also makes clear that v3.6 continuous current depends heavily on cooling; the published figures vary with cooling arrangement. Your clone must be treated separately from those official figures. ([GitHub](https://github.com/odriverobotics/ODrive/blob/master/docs/specifications.rst?utm_source=chatgpt.com))

---

# 7. 90 KV + 30:1 also tells us the speed

Motor no-load speed is approximately:

RPM≈KVVRPM \\approx K_V V

For example, **if** you eventually use 48 V:

```text
90 × 48 ≈ 4320 rpm
```

After 30:1:

```text
4320 / 30 ≈ 144 rpm
```

At 24 V (Phase 1 uses a bench PSU at about 24 V):

```text
2160 rpm motor
≈ 72 rpm output (432 °/s)
```

Actual loaded speed will be lower.

So the drivetrain choice gives us a sensible path for a relatively high-torque, relatively low-speed shoulder actuator.

---

# 8. But there is one major thing we need to fix in the design

## Your encoder placement matters enormously.

You said:

> AS5047P magnetic encoder.

The AS5047P can provide 14-bit absolute angular information through SPI and also provides programmable ABI incremental outputs. It supports speeds up to 28,000 rpm, so the motor-side rotational speed is within its basic speed capability. ([ams OSRAM](https://look.ams-osram.com/m/96c6ce98dbc085b4/original/AS5047P_FS000140_1-00.pdf?utm_source=chatgpt.com))

But we need to ask:

### Where is the encoder physically located?

There are two possibilities.

### A. Encoder on motor shaft

```text
AS5047P
   ↓
motor shaft
   ↓
6:1
   ↓
5:1
   ↓
shoulder
```

This is excellent for:

```text
FOC commutation
motor position
motor velocity
```

but it does **not directly measure the final shoulder position**.

---

### B. Encoder on gearbox output

```text
motor
 ↓
6:1
 ↓
5:1
 ↓
AS5047P
 ↓
shoulder output
```

Now we know actual joint position much better.

But the ODrive needs rotor electrical position for motor commutation.

---

# 9. For your final shoulder actuator, I strongly recommend two position measurements

Conceptually:

```text
              MOTOR SIDE
                  │
               Encoder 1
               AS5047P
                  │
                  ▼
              ODrive FOC
                  │
               motor
                  │
                gear
                  │
                gear
                  │
                  ▼
              OUTPUT SIDE
                  │
               Encoder 2
                  │
                  ▼
             VAYN RT Core
```

Why?

Because your gearbox is:

```text
planetary stage 1 (6:1)
+
planetary stage 2 (5:1)
```

and the final output can have:

- backlash,
- elastic deformation,
- bearing deformation,
- gearbox compliance,
- manufacturing error.

A motor encoder divided by 30 assumes the gearbox behaves perfectly.

Real gearbox:

```text
motor moves 1°
      ≠
output necessarily moves exactly 1/30°
```

under load. (The CAD backlash estimate is 0.09–0.22° at the output, `shoulder/cad/calc.txt` §3.)

For a shoulder joint targeting **30 N·m continuous** (untested), output-side measurement becomes very valuable.

> **Update (2026-10-20):** the current shoulder CAD has **no output encoder**. It uses a DRV5033 hall homing sensor on the output flange. Because 30:1 is an exact integer ratio, hall (or reference-pose) homing plus the motor AS5047P gives the absolute joint angle at motor-encoder precision. An output absolute encoder remains the recommended later upgrade (homing without motion, two-channel plausibility). See [VAYN-6.2.1 §8](../VAYN - 6.2.1.md).

Current ODrive documentation describes the ideal dual-encoder architecture as using one encoder for motor commutation and another for load position/velocity; however, the current ODrive hardware comparison lists **multiple encoder feedback as unavailable on v3.6**, so we must not assume your v3.6 clone can do this internally. ([ODrive Documentation](https://docs.odriverobotics.com/v/latest/manual/hardware-config.html?utm_source=chatgpt.com))

### Therefore our architecture should be:

```text
AS5047P #1
→ motor-side
→ ODrive

Output encoder
→ RT Motion Core
```

That also fits VAYN very well.

---

# 10. Very important: your current AS5047P is not necessarily your final joint encoder

For the **first actuator prototype**, using one AS5047P on the motor shaft is perfectly reasonable.

We can use it to prove:

```text
motor
+
ODrive
+
FOC
+
encoder
+
gearbox
```

Then add output sensing before calling the actuator fully validated for VAYN.

This lets us proceed without waiting for everything.

---

# 11. How AS5047P connects to ODrive

The AS5047P supports SPI and ODrive supports the AMS AS5047P protocol in appropriate firmware. ODrive's documentation shows the SPI connection as:

```text
AS5047P              ODrive

VCC       ─────────── 3.3V
GND       ─────────── GND
SCK       ─────────── SPI SCK
MISO      ─────────── SPI MISO
MOSI      ─────────── SPI MOSI
CS        ─────────── SPI CS
```

The exact GPIO/connector assignment has to be taken from **your particular ODrive clone**, not blindly copied from the official board. ODrive's official documentation confirms AS5047P support over the AMS SPI protocol. ([GitHub](https://github.com/odriverobotics/odrive/blob/master/docs/encoders.rst?utm_source=chatgpt.com))

The AS5047P itself supports 3.3 V or 5 V operation depending on configuration, so we need to follow the exact encoder board implementation you purchased rather than assume its voltage from the chip alone. ([Infineon](https://www.infineon.com/part/AS5047P?utm_source=chatgpt.com))

---

# 12. Do NOT wire the whole thing immediately

This is the order I want you to follow.

## Stage A — identify ODrive

Before connecting motor power:

```text
ODrive
  ↓
USB
  ↓
computer
```

We inspect:

```text
hardware version
firmware version
serial
configuration
```

ODrive exposes its firmware and hardware versions through:

```text
fw_version_major
fw_version_minor
fw_version_revision

hw_version_major
hw_version_minor
hw_version_revision
```

and `odrivetool` can read them. ([GitHub](https://github.com/odriverobotics/ODrive/blob/master/docs/commands.rst?utm_source=chatgpt.com))

### Do not flash anything yet.

This is especially important because yours is a **clone**.

A clone may have:

- different hardware revision,
- different current-sense circuitry,
- different thermistor implementation,
- modified firmware,
- different pin mapping,
- modified bootloader.

So before we decide firmware commands, **we identify what you actually have**.

---

# 13. Your first software tool is not VAYN

It is:

```text
odrivetool
```

The GUI is useful too.

Think of them as:

```text
ODrive GUI / odrivetool
        ↓
commissioning + diagnostics + configuration
```

not:

```text
ODrive GUI
        ↓
VAYN runtime
```

The GUI is not going to become the robot's brain.

We'll eventually have:

```text
VAYN RT Core
       ↓
CAN
       ↓
ODrive
```

For initial commissioning, we'll use:

```text
PC
 ↓
USB
 ↓
ODrive
```

---

# 14. Why CAN should eventually be our main connection

For development:

```text
USB → ODrive
```

is convenient.

For the robot:

```text
RT Core
   ↓
CAN
   ↓
ODrive
```

is a much better architectural fit.

ODrive v3.6 supports CAN and UART, and the official comparison lists CAN and UART among its interfaces. (ODrive Documentation)

The CAN protocol exposes exactly the sort of commands our architecture wants, including:

```text
Set Axis State
Set Controller Mode
Set Input Torque
Set Input Velocity
Set Input Position
Get Encoder Estimates
Get Iq
Get Temperature
Get Bus Voltage/Current
Get Torque
Get Power
```

and it also has a watchdog mechanism. ([ODrive Documentation](https://docs.odriverobotics.com/v/latest/manual/can-protocol.html?utm_source=chatgpt.com))

> **Update (2026-10-20):** the list above is from the current (0.6.x) ODrive docs. Our ODESC runs **firmware 0.5.1**, whose CANSimple has no temperature, torque or power messages, and no periodic encoder broadcast. Encoder estimates must be polled with RTR frames, and gains cannot be set over CAN. See the [RT Core implementation spec §10](RT Core Implementation - VAYN 6.2.1.md).

That's a very good fit.

---

# 15. Eventually our data flow will be this

Suppose VAYN wants:

```text
Shoulder torque = 30 Nm
```

RT Motion Core:

```text
30 Nm joint torque
        ↓
convert through 30:1
        ↓
motor torque command
        ↓
ODrive
```

ODrive:

```text
motor torque
        ↓
FOC current target
        ↓
PWM
        ↓
BLDC
```

Meanwhile:

```text
AS5047P
   ↓
motor position
   ↓
ODrive
```

and eventually:

```text
output encoder
   ↓
actual shoulder position
   ↓
RT Motion Core
```

This produces a proper feedback loop.

---

# 16. And this is where VAYN's impedance controller comes in

Suppose:

```text
desired shoulder angle = 45°
actual shoulder angle = 43°
```

The RT core calculates:

```text
position error = 2°
```

and perhaps:

```text
velocity error
```

Then:

```text
τ_joint =
Kp × position_error
+
Kd × velocity_error
+
feedforward
```

Then:

```text
τ_joint
   ↓
gear conversion
   ↓
motor torque
   ↓
ODrive
```

This is the real beginning of the VAYN physical brain.

---

# 17. Safety architecture with your particular ODrive

There is an important issue here.

The official current comparison lists the v3.6 as having no dedicated Error/Enable pins. (ODrive Documentation)

Therefore we should **not design our safety architecture around "Safety MCU pulls an ODrive enable pin."**

Instead, the eventual hardware safety architecture needs something like:

```text
Battery
   │
   ▼
Fuse
   │
   ▼
Contactor / power-control stage
   │
   ▼
ODrive
   │
   ▼
Motor
```

with the Safety MCU controlling an appropriate hardware safety mechanism.

But:

> **We must not simply assume that cutting motor power is a safe state.**

Your own VAYN architecture already recognized this: actuator back-drivability, brakes, passive damping, driver behavior, stored energy and contactor behavior determine what happens after a controller fault.

This becomes particularly important for a **30 N·m (target) gravity-loaded shoulder actuator**: on ODESC3.6, a watchdog timeout or any drive fault disarms the motor and the arm falls, so Phase 1 runs on a guarded, tethered rig ([VAYN-6.2.1 §9](../VAYN - 6.2.1.md)).

---

# 18. Another thing we must design: regenerative energy

This actuator isn't just consuming energy.

During:

```text
deceleration
gravity-driven motion
external force
```

the motor can act as a generator.

That energy can go back into the DC bus.

ODrive v3.6 has brake-resistor/regen functionality, and its firmware includes DC bus over-voltage and over-regen protection. (GitHub)

For our actuator, we therefore need to determine:

```text
battery voltage
maximum regenerative power
brake resistor
brake resistance
brake power rating
DC bus capacitance
contactor/precharge
```

This should be part of Phase 1, not an afterthought.

---

# 19. So your real Phase 1 architecture becomes

```text
                    VAYN RT CORE
                         │
                         │ CAN
                         ▼
                 ┌───────────────┐
                 │ ODRIVE 3.6    │
                 │               │
                 │ CAN interface  │
                 │ torque command │
                 │ watchdog       │
                 │ FOC            │
                 │ current loop   │
                 └───────┬───────┘
                         │
                    3-phase
                         │
                         ▼
                LA8308 90 KV BLDC
                         │
                    AS5047P #1
                    motor encoder
                         │
                         ▼
                 6:1 planetary stage 1
                         │
                         ▼
                 5:1 planetary stage 2
                         │
                         ▼
                   SHOULDER OUTPUT
                         │
                         ▼
        DRV5033 hall homing (output encoder #2 later)
                         │
                         ▼
                  VAYN RT Core

              ┌─────────────────────┐
              │     SAFETY MCU      │
              │                     │
              │ ODrive watchdog     │
              │ current             │
              │ temperature         │
              │ encoder/fault       │
              │ E-stop              │
              │ power safety        │
              └─────────────────────┘
```

---

# 20. The software stack we will build

You said you currently have essentially **zero knowledge of the electronics software side**.

That's fine. We'll build it from the bottom.

### Level 1 — ODrive software

We learn:

```text
ODrive firmware
odrivetool
GUI
motor calibration
encoder calibration
torque mode
velocity mode
position mode
CAN
watchdog
faults
```

### Level 2 — Actuator communication

We'll write:

```text
VAYN RT Core
       ↓
CAN driver
       ↓
ODrive CAN protocol
```

### Level 3 — Joint controller

We'll write:

```text
joint state
      ↓
impedance controller
      ↓
desired torque
      ↓
ODrive
```

### Level 4 — State estimator

We'll combine:

```text
joint encoder
+
IMU
+
motor feedback
+
output encoder
```

### Level 5 — Safety

We'll build:

```text
limits
+
watchdogs
+
fault states
+
Safety MCU
```

### Level 6 — Whole body

Only after one actuator works:

```text
1 actuator
 ↓
multiple actuators
 ↓
arm
 ↓
torso
 ↓
legs
 ↓
whole humanoid
```

### Level 7 — AI

Only then:

```text
RT Core
 ↑
Action Policy
 ↑
Prediction
 ↑
Vision
 ↑
VLM
```

That's how we turn the VAYN document into an actual machine.

---

# 21. Simulation path

We also don't need to risk the real actuator while learning.

We'll use three levels:

```text
LEVEL 1
Python actuator simulation

          ↓

LEVEL 2
Motor/ODrive Hardware-in-the-Loop

          ↓

LEVEL 3
Real actuator
```

And then:

```text
LEVEL 4
Single joint robot simulation

          ↓

LEVEL 5
Whole humanoid simulation

          ↓

LEVEL 6
Real humanoid
```

For the first simulation, we don't even need Isaac Sim.

We can make a simple mathematical model:

```text
motor
+
gear ratio
+
inertia
+
friction
+
damping
+
controller
```

and see exactly what happens when we change:

```text
Kp
Kd
motor torque
gear efficiency
load
delay
noise
```

That will make the control theory much easier for you to understand.

---

# 22. What I want us to do right now

**Do not start wiring the motor yet.**

Our first practical task is:

## Step 1 — Identify your ODrive clone

> **Done (2026-10-20, read-only):** hardware 3.6-56V, firmware 0.5.1, serial `0x378635693034`, control loop 8000 Hz. Axis0 motor calibrated (20 pole pairs, R 0.0846 Ω, L 37 µH). CAN at 250 kbit/s. Full readout in [VAYN-6.2.1 §3.2](../VAYN - 6.2.1.md).

Connect **only the USB/logic connection needed to communicate with the board according to its hardware arrangement**. Do not energize the motor power stage.

Install the ODrive Python tools and run:

```bash
odrivetool
```

Then we'll inspect:

```python
odrv0.hw_version_major
odrv0.hw_version_minor
odrv0.hw_version_variant

odrv0.fw_version_major
odrv0.fw_version_minor
odrv0.fw_version_revision

odrv0.serial_number
```

Those are official ODrive diagnostic properties. (GitHub)

Also:

```python
dump_errors(odrv0)
```

**Do not run motor calibration yet.**

---

# 23. After that, we'll establish the exact ODrive path

Once we know the firmware, I'll give you the exact commands for _your version_.

The sequence will be:

```text
ODrive identification
        ↓
firmware identification
        ↓
clone compatibility check
        ↓
motor electrical parameters
        ↓
encoder wiring
        ↓
AS5047P configuration
        ↓
motor calibration
        ↓
encoder calibration
        ↓
very-low-power spin test
        ↓
torque/current test
        ↓
gearbox connection
        ↓
loaded actuator test
        ↓
CAN control
        ↓
VAYN RT Core
```

We won't skip steps.
