# The VAYN RT Core — From Fundamentals to Advanced

**Who this is for:** someone comfortable with software and AI who is newer to electronics, control and real-time systems.
**How to read it:** every term is defined before it is used. Part 1 needs no background. Each part builds on the ones before. The numbers in the examples are the **real VAYN shoulder numbers** (Phase 1, 2026-10-20).
**Related docs:**
- [VAYN-6.2.1](../VAYN - 6.2.1.md): the architecture decisions
- [RT Core implementation spec](RT Core Implementation - VAYN 6.2.1.md): the build plan

**Contents:**
1. What problem the RT core solves
2. Feedback control from zero
3. Time: sampling, latency, jitter and deadlines
4. Motors, gearboxes and sensors
5. Computers that keep time: real-time Linux
6. Talking to the drive: CAN and friends
7. What the VAYN RT core is, exactly
8. Impedance control and stability
9. Trajectories and smooth motion
10. Safety: stopping a robot properly
11. State machines
12. Knowing where the body is: homing and state estimation
13. Advanced: whole-body control, MPC, learned controllers, safety filters
14. Proving it works: verification
15. Glossary
16. References

---

# Part 1 — What problem the RT core solves

## 1.1 A robot is two different kinds of computer problem

VAYN has an AI computer (Jetson Orin NX). It looks at camera images, understands language and decides things like "pick up the red cup". It is smart but **slow and unpredictable in timing**. A model might answer in 40 ms one time and 300 ms the next, or crash.

The body is a physical machine. A motor holding an arm up must be told what to do **hundreds to thousands of times per second**, every time, on time. If it is not, the arm sags, oscillates or falls.

These two jobs have opposite needs:

|  | AI computer | Body controller (RT core) |
| ---| ---| --- |
| Main goal | good decisions | correct timing, every time |
| Typical rate | 0.5–50 Hz | 500–1000 Hz |
| What it fears | wrong answer | late answer |
| If it crashes | robot gets dumber | robot must still be safe |

The **RT core** (real-time motion core) is the program that does the body job. VAYN's central rule is that the AI can make the robot more capable, but **losing the AI must not mean losing control of the body** (VAYN-6.2 §1).

## 1.2 What "real-time" actually means

A real-time system is one where **a correct answer delivered too late is a wrong answer**. It is about _meeting deadlines_, not about being fast.

- **Hard real-time:** missing a deadline is a failure. Example: a servo loop that must produce a new motor command every 1 ms.
- **Firm real-time:** an occasional miss is tolerable, but a late result is useless and is thrown away. Example: a video frame.
- **Soft real-time:** lateness degrades quality gradually. Example: a chat reply.

The RT core's servo loop is treated as hard real-time: we design so that it _never_ misses, and we measure to prove it.

---

# Part 2 — Feedback control from zero

## 2.1 Open loop vs closed loop

- **Open loop:** you send a command and hope. "Apply 1 A to the motor for 0.5 s." If the load is heavier than expected, the arm ends up somewhere else.
- **Closed loop (feedback):** you measure what actually happened and correct. "Where is the arm? It is 3° short, so push a bit more."

```text
  desired ──►(+)──► controller ──► motor ──► arm ──┬──► actual position
             (−)                                   │
              ▲                                    │
              └────────── sensor (encoder) ◄───────┘
```

The difference between desired and actual is the **error**. The controller turns the error into a command.

## 2.2 The P, D and I terms

The simplest useful controllers are built from three ideas:

- **P (proportional):** push in proportion to the error. Bigger error, bigger push. On its own, it behaves like a **spring**.
- **D (derivative):** push against the error's _rate of change_ (in practice, against the velocity). On its own, it behaves like a **damper**, the thing that stops a car bouncing after a bump.
- **I (integral):** add up the error over time and push against the accumulated amount. It removes small steady errors but can cause slow overshoot ("windup").

A PD controller is literally a virtual spring plus damper:

```text
τ = Kp · (q_desired − q) + Kd · (q̇_desired − q̇)
```

where τ (tau) is torque, q is joint angle, q̇ ("q dot") is joint velocity, Kp is stiffness and Kd is damping.

## 2.3 Why damping matters: a feel for the numbers

A spring alone oscillates forever. Damping removes that energy. The **damping ratio** ζ (zeta) says how much:

```text
ζ = Kd / (2 · √(Kp · J))        J = inertia (how hard it is to spin the joint)
```

- ζ < 1: underdamped. It overshoots and rings.
- ζ = 1: critically damped. It is the fastest response with no overshoot.
- ζ > 1: overdamped. It is slow and sluggish, but calm.

For bring-up, slightly overdamped is the safe choice.

## 2.4 Feed-forward: help the controller with what you already know

Feedback only reacts _after_ an error appears. If we already know a force exists, we can cancel it up front. That is **feed-forward**. For the shoulder, gravity pulls the arm down with a torque of about

```text
τ_gravity(q) ≈ 3.26 N·m · sin(q)      (q measured from hanging straight down; v0 arm, no hand)
```

The value 3.26 N·m is from the CAD calculation (`arm/cad/calc.txt`). We add this torque to the command ourselves, so the PD part only has to handle the _remaining_ error. This is why the RT core sends a "torque feed-forward" with every command.

---

# Part 3 — Time: sampling, latency, jitter and deadlines

## 3.1 Computers control in steps (sampling)

A computer cannot react continuously. It works in **cycles**: read the sensors, compute, send the command, wait, repeat. The **sample period** T is the time between cycles; the **rate** is 1/T.

- 1 kHz means T = 1 ms (1000 µs). This is the VAYN servo target.
- 500 Hz means T = 2 ms. This is the accepted fallback.

Between samples the command is held constant (a "zero-order hold"). Holding a stale command for T seconds acts like a small delay, and delay can destabilize a controller (Part 8).

## 3.2 Latency, jitter and WCET

- **Latency:** how long something takes from cause to effect. Example: from "the encoder sampled the angle" to "the motor received a new command".
- **Jitter:** how much that latency _varies_ from cycle to cycle. A loop that is always 300 µs late can be compensated. A loop that is sometimes 50 µs and sometimes 900 µs late is much harder.
- **Deadline:** the latest moment a result is still useful (for the servo loop, the next cycle).
- **WCET (worst-case execution time):** the longest the code can take. Averages hide danger; real-time design looks at the worst case and at high percentiles (p99, p99.9, p99.99).

## 3.3 Total delay is a chain

For a robot, the total delay is a sum of pieces:

```text
sensor sampling → transport (CAN/USB) → OS wake-up → compute → transport back → drive → motor current → torque
```

VAYN-6.2 §94 requires each piece to be measured separately. Saying "the latency is 2 ms" without stating where it was measured is not allowed.

---

# Part 4 — Motors, gearboxes and sensors

## 4.1 The BLDC motor

The shoulder uses a **brushless DC (BLDC) motor**, the EaglePower LA8308 KV90. It has permanent magnets on a spinning outer shell (the rotor; 40 magnets = **20 pole pairs**, counted on our motor) and copper coils on the stationary inside (the stator), connected as three **phases**. Feeding the phases with the right currents at the right moments makes a rotating magnetic field that drags the rotor around.

Two numbers describe it:
- **KV (rpm per volt):** how fast it spins per volt with no load. 90 rpm/V, so at 24 V about 2160 rpm. This value is the seller's figure, not measured.
- **Kt (torque constant, N·m per amp):** how much torque each amp of current produces. For hobby motors whose KV is quoted line-to-line, ODrive uses Kt ≈ 8.27 / KV. The factor comes from 3/2 · 1/√3 · 60/2π [R1][R2]. For our motor, Kt ≈ 0.0919 N·m/A.

**Key idea: torque is proportional to current.** Controlling torque means controlling current.

## 4.2 FOC: how the drive controls current

**Field-oriented control (FOC)** is the maths the motor driver uses. It transforms the three phase currents into two numbers in a frame that rotates with the rotor:
- **I_q**, the current that makes torque
- **I_d**, current that only fights the magnets (kept at 0 here)

The driver runs a fast current loop on these. Our driver, the **Flipsky ODESC3.6** (a clone of ODrive v3.6), does all of this itself; its control loop was measured at **8000 Hz** on our board. The RT core never touches phase currents. It asks for a position, velocity and torque, and the drive turns that into current [R3].

## 4.3 The gearbox

The motor is fast and weak. The joint needs to be slow and strong. A **gearbox** trades speed for torque. The shoulder has a two-stage planetary gearbox:
- stage 1: 6:1 (sun 18 teeth, planets 36, ring 90)
- stage 2: 5:1 (sun 18, planets 27, ring 72)
- total **N = 30**

| Quantity | Motor side | Joint side (× or ÷ 30) |
| ---| ---| --- |
| Speed at 24 V, no load | 2160 rpm | 72 rpm = 432°/s |
| Torque per amp | 0.0919 N·m/A | 2.76 N·m/A ideal, about 2.40 N·m/A with an assumed efficiency η = 0.87 |
| One motor turn | 360° | 12° |

Gearboxes are not perfect:
- **Efficiency η:** some torque is lost to friction. 0.87 is a guess until it is measured.
- **Backlash:** a little free play between teeth. About 0.09–0.22° at the output by the CAD calculation.
- **Reflected inertia:** the motor's rotor inertia appears N² = 900 times larger at the joint. This makes geared joints feel "heavy" and is why stiffness and damping scale with N² (Part 8).

## 4.4 Encoders: resolution is not accuracy

An **encoder** measures angle. The shoulder uses an **AS5047P**: a chip that reads a small magnet glued to the motor shaft and reports the angle over **SPI** (a short-distance digital wire protocol).

- **Resolution:** the smallest step it can report. 14 bits = 16384 steps per turn = 0.022°.
- **Accuracy:** how close the reading is to the truth. The datasheet allows ±0.8° of nonlinearity even with perfect magnet placement [R4][R5].

Never confuse the two. On the motor side, ±0.8° of error becomes only ±0.027° at the joint, because it is divided by 30. That is why the motor encoder is the precise sensor for the joint.

**Absolute vs incremental.** The AS5047P knows the angle _within one motor turn_ as soon as it powers up (absolute single-turn). It does not know how many turns the motor has made. Since one motor turn is 12° of joint motion, the robot does not know which 12° "sector" the joint is in at power-up. Solving this is called **homing** (Part 12).

**Velocity from position.** If you take the difference between two encoder readings 1 ms apart, the smallest non-zero velocity you can see is one count per millisecond. For a 14-bit encoder on the output side that is 0.38 rad/s: far too coarse. Velocity should come from the high-resolution motor encoder through the drive's filter (a PLL estimator), not from differencing a coarse output sensor.

## 4.5 Regeneration: motors are also generators

When an arm is lowered or braked, the motor pushes energy _back_ into the power supply. A battery can absorb it; a **bench power supply usually cannot**, so the voltage rises. The ODESC dumps that energy into a **brake resistor** (2 Ω on our board, armed). If the resistor is missing or broken, the bus voltage can climb until the drive trips or is damaged. This is why the over-voltage trip is lowered to about 28 V for a 24 V supply.

## 4.6 Heat decides the real continuous torque

Current through the copper winding makes heat (power = I² · R). The motor's "22 A" rating assumes a propeller blowing air over it, which a closed actuator does not have. The real continuous current comes only from a **thermal test**: hold a current, measure the temperature, fit a curve. Until then, the RT core runs a **thermal model** (Part 10) and the 30 N·m continuous target stays a target.

---

# Part 5 — Computers that keep time: real-time Linux

## 5.1 Why normal Linux is not enough

A normal operating system shares the CPU between many programs and decides who runs when; this is **scheduling**. Its goal is overall throughput and fairness, not deadlines. A control loop can be delayed by a disk write, a network interrupt, a graphics driver or a background update.

## 5.2 PREEMPT_RT

**PREEMPT_RT** is a set of Linux kernel changes that makes almost all kernel code interruptible ("preemptible") and turns interrupt handlers into schedulable threads. A high-priority task can then take the CPU within microseconds. Since **Linux 6.12** it is part of the mainline kernel [R6][R7]. Our laptop runs `7.0.0-38-realtime` with `CONFIG_PREEMPT_RT=y`.

Installing PREEMPT_RT does **not** make a program real-time. The program must also behave.

## 5.3 How a real-time program must behave

| Rule | Why |
| ---| --- |
| Use `SCHED_FIFO` with a fixed priority (for example 80) | The scheduler always runs the highest-priority ready task [R8] |
| Sleep with `clock_nanosleep(CLOCK_MONOTONIC, TIMER_ABSTIME)` until the next absolute deadline | Relative sleeps drift; the wall clock can jump [R9][R8] |
| Lock memory (`mlockall`) and pre-touch buffers | Avoids page faults (waiting for memory) mid-loop [R8] |
| No memory allocation, file I/O, printing or ordinary mutexes in the loop | Each can block for unbounded time |
| Use priority-inheritance mutexes if any lock is unavoidable | Prevents priority inversion: a low-priority task holding a lock blocks a high-priority one [R9] |
| Pin the loop to an isolated CPU | Other work and interrupts stay off that core [R10][R11] |

**Priority inversion** in one sentence: a high-priority task waits for a lock held by a low-priority task, which is itself pre-empted by a medium-priority task, so the high-priority task waits indefinitely. Priority inheritance temporarily raises the lock holder's priority to fix this.

## 5.4 CPU isolation, C-states and SMIs on our laptop

The Dell Latitude 5490 has 4 cores and 8 hardware threads. The tuning plan (implementation spec §3):

- **Turn off Hyper-Threading.** Two hardware threads share one core's resources and disturb each other.
- **Isolate CPU3** (`isolcpus`, `nohz_full`, `rcu_nocbs`, `irqaffinity`). Only the servo loop runs there, the periodic timer tick stops, and interrupts go to the other cores [R10][R11].
- **C-states** are power-saving sleep levels for idle CPUs. Deeper sleep (our CPU goes down to C10) takes longer to wake. The RT core holds `/dev/cpu_dma_latency` at 0 while running to stay out of deep sleep.
- **SMIs (System Management Interrupts)** are firmware interrupts that freeze the whole CPU while the BIOS does something, such as fan control. Linux cannot see or block them [R12][R13]. On Dell laptops the fan/temperature driver `dell_smm_hwmon` uses this mechanism, and some of its calls can take about 500 ms [R14]. We blacklist that driver and _measure_ the remaining SMIs with `hwlatdetect`.

## 5.5 Measuring timing

| Tool | Measures |
| ---| --- |
| `hwlatdetect` | gaps caused by hardware or firmware (SMIs) with Linux out of the picture [R12] |
| `cyclictest` | how late a high-priority thread wakes up versus its schedule |
| `rtla timerlat` | the same, plus why it was late (a stack trace of the blocker) [R11] |

Targets for our host: firmware gaps < 50 µs; servo wake-up < 100 µs worst case over 24 h under load. Until measured, these are targets.

---

# Part 6 — Talking to the drive: CAN and friends

## 6.1 CAN in one page

**CAN (Controller Area Network)** is a two-wire bus (CAN_H, CAN_L, twisted together) designed for cars and machines. Its key properties:

- **Differential:** the receiver looks at the _difference_ between the two wires, so noise that hits both wires cancels out.
- **Multi-drop:** every node is on the same pair. Only the two physical ends get 120 Ω terminating resistors.
- **Messages, not addresses:** each frame has an 11-bit **identifier**. Lower identifiers win when two nodes talk at once (bitwise **arbitration**), with no collision or retry delay for the winner.
- **Small frames:** classic CAN carries 0–8 data bytes per frame.
- **Bit stuffing:** after five identical bits the sender inserts an opposite bit so receivers stay synchronized. This makes frame length depend on content. The worst case for an 8-byte standard frame is **135 bits**, which is 135 µs at 1 Mbit/s [R15][R16].

## 6.2 Bus load: the budget you cannot exceed

Only one frame is on the wire at a time. Our firmware (ODESC 0.5.1) does not stream position automatically, so every cycle, for every joint, the RT core:

1. sends a position command (8 bytes): **135 µs**
2. sends a "remote request" asking for the encoder (RTR frame, 0 bytes): **55 µs**
3. receives the reply (8 bytes): **135 µs**

That is 325 µs per joint per cycle. At 1000 cycles per second, that is 32.5% of the bus for one joint. Two joints use about 65%. Engineers keep buses below about 70–80% so that error retries and extra messages fit [R17].

The board currently ships at **250 kbit/s**, four times slower: one joint would need 130% of the bus at 1 kHz. This is why the RT plan sets **1 Mbit/s**.

MIT's Mini Cheetah faced the same limit: it used **four** 1 Mbit/s CAN buses, three motors each, to reach 1 kHz [R17][R18]. A 20–30 joint humanoid needs either many buses or a faster bus (CAN-FD or EtherCAT, §6.5).

## 6.3 ODrive "CANSimple" in our firmware

Every ODESC message ID is `node_id × 32 + command` [R19]. The ones the RT core uses:

| Command | What it does |
| ---| --- |
| `Set_Input_Pos` (0x0C) | target position in motor turns, velocity feed-forward and torque feed-forward |
| `Get_Encoder_Estimates` (0x09), via remote request | the drive replies with position (turns) and velocity (turns/s) |
| Heartbeat (0x01), every 10 ms | axis error flags and axis state, sent automatically |
| `Set_Axis_Requested_State` (0x07) | IDLE (1) or CLOSED_LOOP_CONTROL (8) |
| `Get_Vbus_Voltage` (0x17), `Get_Iq` (0x14) | supply voltage, motor current (polled slowly) |

**Watchdog.** The ODESC can disarm itself if it hears nothing for a set time (50 ms in our plan). On firmware 0.5.x, _any_ message to the axis resets this timer, including the polls [R20][R21]. So the RT core sends commands and polls from the same thread: if that thread dies, all traffic stops and the drive disarms.

**Disarm means the arm falls.** The ODESC3.6 has no hardware "safe torque off" input, and disarming removes torque. With the arm attached this is the main Phase-1 hazard, so all Phase-1 tests use a guarded, tethered rig.

## 6.4 USB-CAN adapters and timestamps

The laptop has no CAN port, so a USB-CAN adapter is needed. USB adds latency that varies with host scheduling. The cure is to use the adapter's own **hardware timestamp** of when each frame actually arrived, rather than the time Linux got around to reading it. Software timestamps can be off by milliseconds under load [R22][R23].

## 6.5 Beyond classic CAN

| Bus | Payload per frame | Typical use |
| ---| ---| --- |
| Classic CAN 1 Mbit/s | 8 bytes | our Phase 1 |
| CAN-FD | up to 64 bytes, faster data phase | more joints per bus |
| EtherCAT | one Ethernet frame passes through all drives each cycle; 1–4 kHz cycles common | industrial servo drives; standard drive state machine CiA 402 [R24] |

The bus choice for the full humanoid is an open decision (VAYN-6.2.1 gate G-4).

## 6.6 Ethernet to the AI computer and clock sync

The Orin talks to the RT core over a dedicated Ethernet cable using UDP: small fixed-format messages with a version number and checksum. It is _not_ part of the 1 kHz loop. Each message carries timestamps and a `valid_until`. To compare timestamps between two computers, their clocks are synchronized with **PTP** (Precision Time Protocol). The laptop's Intel I219-LM network chip supports hardware timestamps for this.

---

# Part 7 — What the VAYN RT core is, exactly

## 7.1 Definition

> The VAYN RT core is a C++ real-time program on the RT computer. It is the **only** thing allowed to command the actuators. It continuously turns _references_ (what someone would like the body to do) into _safe actuator commands_, and it keeps the body controlled when every other part of the system fails.

It is not ROS 2, not a neural network, not the drive firmware and not the Linux kernel.

## 7.2 The authority model

```text
Orin (AI)        → suggests references          (may fail, may be wrong, may be late)
RT core          → decides what actually happens (always running, owns the actuators)
ODESC drive      → makes the motor current       (fast inner loops, 8 kHz)
Safety MCU       → can remove power, independently (does not trust the other three)
```

## 7.3 Simplex: the theory behind the design

The **Simplex architecture** [R25][R26] is a classic way to use a clever but unverified controller safely. It has three parts:
- a **high-performance controller**: here, the AI policy
- a simple, verified **safety controller**: here, the RT core's HOLD and controlled-stop fallbacks
- a **decision module** that switches to the safety controller _before_ the system leaves a recoverable state

The RT core is the decision module plus the safety controllers.

## 7.4 The servo pipeline

Each 1 ms cycle runs these stages in order:

```text
read feedback → estimate state → reference gate → arbiter → trajectory → impedance → OUTPUT GUARD → send to drive
```

- **Reference gate:** rejects malformed, stale or out-of-range requests.
- **Arbiter:** picks the active reference (AI, local test, or fallback) and adds any bounded reflex correction of the same type.
- **Trajectory:** turns jumps into smooth motion (Part 9).
- **Impedance:** decides how stiff and damped the joint should be (Part 8).
- **Output guard:** the last check before anything reaches the drive. It covers limits, braking distance, temperature and drive state.

## 7.5 Freshness: every message has an expiry date

Every reference carries `timestamp`, `sequence_id` and `valid_until`. After `valid_until` the RT core may continue smoothly for a short window (50 ms by default), then switches to HOLD. A frozen AI can never keep the robot executing an old command forever (VAYN-6.2 Rule 4).

---

# Part 8 — Impedance control and stability

## 8.1 Impedance: control how the joint _feels_

Position control says "be exactly here". **Impedance control** [R27] says "behave like a spring of stiffness K and a damper D around this target". When the robot touches something, a stiff controller pushes hard, while an impedance-controlled joint gives way gracefully. That is safer for people and objects.

## 8.2 Where the spring is computed matters

The drive runs at 8 kHz, right next to the motor. The RT core runs at 1 kHz on the other side of a CAN bus with a USB adapter in between. That is a 1–3 ms round trip. If the damper is computed across that delay, the "damper" reacts to old velocity and can _add_ energy instead of removing it.

The classic result for sampled controllers [R28][R29] is the passivity condition

```text
b > K·T/2 + |B|
```

Here b is the real physical damping, K and B are the virtual stiffness and damping, and T is the sample period. It says that the longer the delay, the less virtual stiffness and damping you can safely use.

So in Phase 1 the **drive** computes the spring and damper, and the RT core sends the target, the feed-forward and (per session) the gains. MIT's Mini Cheetah does the same: the host sends position, velocity, stiffness, damping and feed-forward, and the motor driver computes the impedance law at 40 kHz [R30][R31].

## 8.3 Turning ODrive gains into joint stiffness

ODrive's position-velocity cascade with the integrator off works out to

```text
τ_motor = vel_gain · (pos_gain · (p_target − p) + v_ff − v) + τ_ff
```

Through a 30:1 gearbox, motor stiffness appears N² = 900 times larger at the joint:

```text
K_joint ≈ 900 · vel_gain · pos_gain / (2π)     D_joint ≈ 900 · vel_gain / (2π)
```

**Worked example (bring-up gains pos_gain 5, vel_gain 0.05):**
- K_joint ≈ 900 · 0.25 / 6.283 ≈ **35.8 N·m/rad** (about 0.62 N·m per degree)
- D_joint ≈ 900 · 0.05 / 6.283 ≈ **7.2 N·m·s/rad**
- With an _assumed_ joint inertia J = 0.2 kg·m², ζ = 7.2 / (2·√(35.8·0.2)) ≈ 1.3: calm and slightly overdamped.

The real inertia must be measured, because the motor rotor's reflected inertia is not yet known.

---

# Part 9 — Trajectories and smooth motion

## 9.1 Why not jump straight to the target

A sudden target change demands infinite acceleration. The controller then saturates (hits its current limit), the gearbox is shocked and the arm overshoots. A **trajectory generator** plans a smooth path that respects:
- velocity limits
- acceleration limits
- **jerk** limits (jerk is the rate of change of acceleration; limiting it removes the "kick")

## 9.2 Online trajectory generation with Ruckig

**Online** means the plan is recomputed every cycle from wherever the joint currently is, so a new target can arrive at any time. **Ruckig** [R32][R33] computes the time-optimal jerk-limited motion from any current state (position, velocity, acceleration) to any target state, fast enough for 1 kHz loops. The RT core uses it for:
- normal motion
- blending a new AI reference into the current motion
- the short coasting window after a reference expires
- controlled stops

## 9.3 Receding horizon

The AI may send a 250 ms plan, but only the first part is executed before a new plan replaces it (VAYN-6.2 §38). The trajectory layer blends each new plan in so that position, velocity and acceleration stay continuous.

---

# Part 10 — Safety: stopping a robot properly

## 10.1 "Stop" has three meanings

Industrial standards define three stop categories (IEC 60204-1), which drives implement as named safety functions (IEC 61800-5-2) [R34][R35][R36]:

| Category | Drive function | What happens | Good for |
| ---| ---| ---| --- |
| 0 | STO (Safe Torque Off) | power removed immediately; the axis coasts | emergencies, when the axis cannot hurt anyone by moving freely |
| 1 | SS1 (Safe Stop 1) | controlled braking, then power removed | fast, controlled stop |
| 2 | SS2 (Safe Stop 2) | controlled braking, then hold position with power on | axes that would fall, such as a raised arm |

For a humanoid, **cutting power is not automatically safe**: a lifted arm or a standing robot falls. VAYN's rule is that the reaction depends on the physical state (VAYN-6.2 §45). The gravity-loaded shoulder prefers SS2 (hold), but the ODESC can only do category 0 by disarming, which is why the rig is required.

## 10.2 Limits that look ahead

A naive rule ("if past the limit, cut torque") acts too late and drops the arm. The RT core instead asks: _at this speed, can I still stop before the limit?_

```text
stopping distance = v² / (2 · a_max)
if  q + v·|v|/(2·a_max)  would pass the limit  →  start braking now and hold at the limit
```

## 10.3 Watchdogs and heartbeats

- A **heartbeat** is a periodic "I am alive" message.
- A **watchdog** is a timer that triggers a safety reaction if it is not reset in time.

VAYN chains them:
- the drive watchdog catches a dead RT core
- the RT core watches drive heartbeats
- the future Safety MCU watches both and controls power through its own wires, never only through CAN

Relying on CAN alone would be a **common-cause failure**: one broken bus would disable both control and safety at once.

## 10.4 Hazard analysis comes first

Safety design starts by listing what can go wrong (hazards), how likely and how bad each is (risk assessment, as in ISO 12100), and which safety functions reduce it. Only then are safety levels chosen (VAYN-6.2 §114). The Phase-1 fault-reaction matrix in VAYN-6.2.1 §9 is the first result of this process.

## 10.5 Thermal protection

The motor has no temperature sensor yet. The RT core runs a two-node thermal model: a winding node that heats from I²R, connected to a housing node, connected to air. It reduces allowed torque as the estimated winding temperature rises. The ODESC protects its own transistors (derating from 70 °C, tripping at 85 °C as configured). Once the 10 kΩ winding thermistor is fitted, the Safety MCU will read it as an independent hard limit.

---

# Part 11 — State machines

## 11.1 What a state machine is

A **state machine** says that the system is always in exactly one named state, and that only listed events can move it to listed other states. It is the opposite of a pile of `if` statements: every situation is explicit and testable.

## 11.2 VAYN uses four small ones

| Machine | States | Question it answers |
| ---| ---| --- |
| RT lifecycle | BOOT, PREFLIGHT, STANDBY, ARMING, ACTIVE, STOPPING, FAULT, ESTOP | Is the RT core allowed to drive motors right now? |
| Reference authority | NONE, HOLD, LOCAL, AI, FALLBACK | Whose reference is being followed? |
| Per joint (modelled on CiA 402 [R24][R37]) | DISABLED, READY, ENABLED, QUICK_STOP, FAULT_REACTION, FAULT | What is this drive doing? |
| Homing | UNHOMED, HOMING, HOMED, LOST | Do we know this joint's absolute angle? |

Keeping them separate avoids one giant, untestable list of modes.

---

# Part 12 — Knowing where the body is: homing and state estimation

## 12.1 Homing a 30:1 joint

At power-up the motor encoder knows the angle inside a motor turn (φ, a fraction from 0 to 1), but not which of the 12° sectors the joint is in. Because 30:1 is an exact integer ratio, each joint angle always pairs with the same φ. So:

1. **Once**, put the joint exactly at a reference pose and remember φ_ref.
2. **Every power-up**, get the joint _roughly_ right, within ±6° (half a sector):
    - Phase 1A: the operator places the arm at a marked pose by hand.
    - Phase 1B: a slow sweep until the hall sensor on the output flange triggers.
3. Snap the reading to the nearest position whose fraction equals φ_ref. Now the joint angle is known to motor-encoder precision (about 0.03°), not to the precision of the rough reference.

The hall sensor will be read by a small CAN "Sensor MCU", because firmware 0.5.1 cannot report it over CAN. An output-side absolute encoder (planned later, as on the elbow) would remove the need to move at power-up.

## 12.2 State estimation

**State estimation** means producing the best guess of the robot's physical state (positions, velocities, body orientation, contacts) from noisy, delayed sensors.

- **One joint (Phase 1):** position from the motor encoder divided by 30, velocity from the drive's filter, torque estimated from current.
- **Whole body (later):** an IMU (accelerometer plus gyroscope) and leg kinematics are fused to estimate the floating base (pelvis) pose and velocity. A common, robust method for legged robots is the contact-aided **invariant extended Kalman filter** [R38][R39].

A **Kalman filter** combines a prediction ("given the last state and the physics, I expect…") with a measurement ("the sensor says…"), weighting each by how much it is trusted.

---

# Part 13 — Advanced topics

## 13.1 Whole-body control (WBC)

With many joints, "where should each joint go?" is solved as an optimization each cycle. The goal is: track the hand target, keep balance, respect joint and torque limits, and keep feet from slipping. It is usually written as a **quadratic program (QP)**, solved at 100–500 Hz in the RT core's slower `motion` thread. It needs a rigid-body dynamics library (for example Pinocchio [R40]). The solver must have a bounded iteration count and a fallback if it does not finish in time. A missed solve must never block the servo loop.

## 13.2 Model predictive control (MPC)

**MPC** plans the next fraction of a second using a model, applies only the first step, then re-plans. It is powerful for balance and contact, but expensive. In VAYN it is deferred until simpler controllers are shown to be insufficient (VAYN-6.3).

## 13.3 Learned controllers inside the RT domain

If a classical stabilizer is not agile enough, a small learned policy may run **inside the RT computer** (never on the Orin), with a measured worst-case run time and the same output guard after it (VAYN-6.2 §9).

## 13.4 Safety filters

A **control barrier function (CBF)** safety filter takes any requested command and finds the closest command that provably keeps the system inside a safe set. It is solved as a tiny QP each cycle [R41]. It is a natural, more general successor to the braking-distance guard.

## 13.5 Latency compensation

If the delay is known and measured, the controller can predict where the joint _will_ be when the command lands, and act on that. This is VAYN's "PREDICT" idea applied at the lowest level. Prediction is a helper, not a replacement for fast feedback.

## 13.6 Scaling to a 20–30 joint humanoid

| Pressure | Answer |
| ---| --- |
| CAN bandwidth | multiple buses, CAN-FD, or EtherCAT (gate G-4) |
| Compute | a dedicated multi-core RT computer with isolated cores |
| Homing without moving | output absolute encoders on every joint |
| Safety | a Safety MCU per limb group, hardwired power control, brakes on gravity-loaded joints |

---

# Part 14 — Proving it works: verification

## 14.1 One code path everywhere

The RT core's control logic is a pure function: the same inputs always give the same outputs. The _same_ code runs:
- in simulation, against a model of the motor, gearbox, arm, drive and CAN timing
- on recorded logs (**replay**)
- in **HIL** (hardware-in-the-loop: real controller, simulated or partial hardware)
- on the real robot

If something goes wrong on the robot, the log can be replayed and the bug reproduced exactly.

## 14.2 Test in layers

1. Unit tests: maths, codec, state machines.
2. Property tests: "for any random input, limits are never exceeded".
3. Timing tests: worst-case execution and wake-up latency over long runs.
4. Fault injection, done on purpose:
    - unplug CAN
    - kill the RT process
    - send stale or invalid references
    - overheat in simulation
    - press the E-stop
5. Check that each reaction matches the fault matrix.
6. Only then, careful hardware steps on the rig, adding one component at a time (VAYN-6.2 §110).

## 14.3 Logs

Every run is logged in **MCAP**, an open, indexed robotics log format and the default for ROS 2 bags [R42][R43]. The log holds timestamps, states, commands, faults, configuration hashes and timing histograms, enough to reconstruct the run.

---

# Part 15 — Glossary

| Term | Meaning |
| ---| --- |
| Actuator | motor + gearbox + sensors + driver that moves a joint |
| Arbitration | choosing which reference is active |
| Backlash | free play between gear teeth |
| BLDC | brushless DC motor |
| CAN / CAN-FD | two-wire robust bus / its faster, bigger-frame successor |
| CiA 402 | standard drive state machine used by CANopen and EtherCAT drives |
| C-state | CPU idle power-saving level; deeper means slower to wake |
| Damping (D, Kd) | resistance proportional to velocity |
| Deadline | latest time a result is still useful |
| EtherCAT | Ethernet-based real-time fieldbus for servo drives |
| Feed-forward | adding a known force to the command up front |
| FOC | field-oriented control of motor currents |
| Following error | difference between commanded and actual position |
| HIL | hardware-in-the-loop testing |
| Homing | finding the absolute joint angle after power-up |
| Impedance control | making a joint behave like a spring and damper |
| Jitter | variation in latency |
| KV / Kt | motor speed constant (rpm/V) / torque constant (N·m/A) |
| Latency | delay from cause to effect |
| MCAP | open log file format for robotics |
| PREEMPT_RT | Linux kernel real-time preemption, mainline since 6.12 |
| Priority inversion | high-priority task blocked by a lower one holding a lock |
| PTP | Precision Time Protocol for clock synchronization |
| Reference | a requested target (position, velocity, torque) |
| RTR frame | CAN "remote request" asking another node to send data |
| Simplex | architecture where a verified controller guards an unverified one |
| SMI | firmware interrupt invisible to the OS; source of latency |
| SS1 / SS2 / STO | safe stop 1 / safe stop 2 / safe torque off |
| Stiffness (K, Kp) | force proportional to position error |
| Watchdog | timer that triggers a safety reaction if not reset |
| WCET | worst-case execution time |

---

# Part 16 — References

- [R1] ODrive docs, "Component Selection" (k_t = 8.27 / k_v). [https://docs.odriverobotics.com/v/latest/articles/component-selection.html](https://docs.odriverobotics.com/v/latest/articles/component-selection.html)
- [R2] ODrive Community, derivation of 8.27 (3/2 · 1/√3 · 60/2π). [https://discourse.odriverobotics.com/t/where-does-the-formula-for-calculating-torque-come-from/1169](https://discourse.odriverobotics.com/t/where-does-the-formula-for-calculating-torque-come-from/1169)
- [R3] ODrive docs, "Controller" (cascaded position/velocity/current loops). [https://docs.odriverobotics.com/v/latest/manual/control.html](https://docs.odriverobotics.com/v/latest/manual/control.html)
- [R4] ams OSRAM, AS5047P datasheet (14-bit, INL ±0.8°). [https://look.ams-osram.com/m/d05ee39221f9857/original/AS5047P-DS000324.pdf](https://look.ams-osram.com/m/d05ee39221f9857/original/AS5047P-DS000324.pdf)
- [R5] Infineon, AS5047P datasheet. [https://www.infineon.com/part/AS5047P](https://www.infineon.com/part/AS5047P)
- [R6] Phoronix, PREEMPT_RT merged for Linux 6.12. [https://www.phoronix.com/news/Linux-6.12-Does-Real-Time](https://www.phoronix.com/news/Linux-6.12-Does-Real-Time)
- [R7] LWN, "The 6.12 merge window begins". [https://lwn.net/Articles/990750/](https://lwn.net/Articles/990750/)
- [R8] [realtime-linux.org](http://realtime-linux.org), "A Checklist for Real-Time Applications in Linux". [https://realtime-linux.org/a-checklist-for-real-time-applications-in-linux/](https://realtime-linux.org/a-checklist-for-real-time-applications-in-linux/)
- [R9] Linux kernel docs, "Real-time application monitors". [https://docs.kernel.org/trace/rv/monitor_rtapp.html](https://docs.kernel.org/trace/rv/monitor_rtapp.html)
- [R10] Intel ECI docs, "Real-Time Scheduling on Linux". [https://eci.intel.com/docs/3.3/development/performance/rt_scheduling.html](https://eci.intel.com/docs/3.3/development/performance/rt_scheduling.html)
- [R11] TechVeda, "SCHED_FIFO and CPU Isolation on Real-Time Linux — Part 3". [https://www.techveda.live/2026/07/05/sched-fifo-cpu-isolation-part-3/](https://www.techveda.live/2026/07/05/sched-fifo-cpu-isolation-part-3/)
- [R12] Linux kernel docs, "Hardware Latency Detector". [https://kernel.org/doc/html/latest/trace/hwlat_detector.html](https://kernel.org/doc/html/latest/trace/hwlat_detector.html)
- [R13] Linux Foundation RT wiki, "SMI latency". [https://wiki.linuxfoundation.org/realtime/documentation/howto/debugging/smi-latency/start](https://wiki.linuxfoundation.org/realtime/documentation/howto/debugging/smi-latency/start)
- [R14] Linux kernel docs, "dell-smm-hwmon". [https://docs.kernel.org/hwmon/dell-smm-hwmon.html](https://docs.kernel.org/hwmon/dell-smm-hwmon.html)
- [R15] Nolte et al., "Using bit-stuffing distributions in CAN analysis". [http://www.es.mdh.se/pdf_publications/298.pdf](http://www.es.mdh.se/pdf_publications/298.pdf)
- [R16] Vector, "CAN bit stuffing". [https://certification.vector.com/mod/page/view.php?id=349](https://certification.vector.com/mod/page/view.php?id=349)
- [R17] D. Kang, "What is CAN?" (robot CAN load, Mini Cheetah 4 × 3 motors). [https://dokkev.github.io/aboutcan/](https://dokkev.github.io/aboutcan/)
- [R18] Robots Guide, "Mini Cheetah". [https://robotsguide.com/robots/minicheetah](https://robotsguide.com/robots/minicheetah)
- [R19] ODrive docs 0.5.6, CAN Protocol. [https://docs.odriverobotics.com/v/0.5.6/can-protocol.html](https://docs.odriverobotics.com/v/0.5.6/can-protocol.html)
- [R20] ODrive docs 0.5.6, Getting Started, watchdog. [https://docs.odriverobotics.com/v/0.5.6/getting-started.html](https://docs.odriverobotics.com/v/0.5.6/getting-started.html)
- [R21] ODrive Changelog 0.6 (older firmware fed the watchdog on all CAN messages). [https://docs.odriverobotics.com/v/latest/changelog.html](https://docs.odriverobotics.com/v/latest/changelog.html)
- [R22] J. Whittington, gs_usb hardware timestamping. [https://engineer.john-whittington.co.uk/programming/2023/01/07/socketcan-gsusb-timestamping.html](https://engineer.john-whittington.co.uk/programming/2023/01/07/socketcan-gsusb-timestamping.html)
- [R23] Linux `gs_usb` driver source. [https://github.com/torvalds/linux/blob/master/drivers/net/can/usb/gs_usb.c](https://github.com/torvalds/linux/blob/master/drivers/net/can/usb/gs_usb.c)
- [R24] CAN in Automation, CiA 402. [https://can-cia.org/can-knowledge/cia-402-series-canopen-device-profile-for-drives-and-motion-control](https://can-cia.org/can-knowledge/cia-402-series-canopen-device-profile-for-drives-and-motion-control)
- [R25] L. Sha, "Using Simplicity to Control Complexity", IEEE Software, 2001. [https://doi.org/10.1109/MS.2001.936213](https://doi.org/10.1109/MS.2001.936213)
- [R26] T. T. Johnson et al., "Real-Time Reachability for Verified Simplex Design", ACM TECS, 2016.
- [R27] N. Hogan, "Impedance Control: An Approach to Manipulation", ASME J. Dyn. Sys. Meas. Control, 1985.
- [R28] J. E. Colgate, G. Schenkel, "Passivity of a class of sampled-data systems", J. Robotic Systems, 1997.
- [R29] J. E. Colgate, J. M. Brown, "Factors Affecting the Z-Width of a Haptic Display", ICRA 1994.
- [R30] B. Katz, MIT thesis, "Low Cost, High Performance Actuators for Dynamic Robots". [https://fab.cba.mit.edu/classes/865.18/motion/papers/katz-thesis.pdf](https://fab.cba.mit.edu/classes/865.18/motion/papers/katz-thesis.pdf)
- [R31] B. Katz, HKC_MiniCheetah firmware (CAN p, v, kp, kd, τ_ff). [https://os.mbed.com/users/benkatz/code/HKC_MiniCheetah/](https://os.mbed.com/users/benkatz/code/HKC_MiniCheetah/)
- [R32] L. Berscheid, T. Kröger, RSS 2021, Ruckig. [https://www.roboticsproceedings.org/rss17/p015.html](https://www.roboticsproceedings.org/rss17/p015.html)
- [R33] Ruckig repository. [https://github.com/pantor/ruckig](https://github.com/pantor/ruckig)
- [R34] Pilz, "EN / IEC 61800-5-2". [https://www.pilz.com/en-US/support/lexicon/articles/200448](https://www.pilz.com/en-US/support/lexicon/articles/200448)
- [R35] GT Engineering, "Stop functions". [https://www.gt-engineering.it/en/insights/machinery-safety/stop-functions/](https://www.gt-engineering.it/en/insights/machinery-safety/stop-functions/)
- [R36] Machinery Safety 101, "Safe Drive Control including STO". [https://machinerysafety101.com/2017/07/03/safe-drive-control-sto/](https://machinerysafety101.com/2017/07/03/safe-drive-control-sto/)
- [R37] Novanta, "CiA 402 State Machine". [https://drives.novantamotion.com/emcl/cia-402-state-machine](https://drives.novantamotion.com/emcl/cia-402-state-machine)
- [R38] R. Hartley et al., "Contact-Aided Invariant Extended Kalman Filtering for Robot State Estimation", IJRR, 2020.
- [R39] M. Bloesch et al., "State Estimation for Legged Robots: Consistent Fusion of Leg Kinematics and IMU", RSS, 2012.
- [R40] J. Carpentier et al., "The Pinocchio C++ library", IEEE/SICE SII, 2019.
- [R41] A. D. Ames et al., "Control Barrier Functions: Theory and Applications", ECC, 2019.
- [R42] MCAP specification. [https://github.com/foxglove/mcap](https://github.com/foxglove/mcap)
- [R43] ros2/rosbag2 (MCAP default storage). [https://github.com/ros2/rosbag2](https://github.com/ros2/rosbag2)
