> **Revision note (2026-10-20, VAYN-6.2.1):** corrected in place:  
> the initial RT computer is now a **Dell Latitude 5490** (Intel i5-8350U, 4 cores, Ubuntu 26.04, PREEMPT_RT kernel 7.0). The Mac Mini plan is dropped; the remaining mentions below were updated to the Dell 5490.  
> ODESC firmware read live: **0.5.1** (hardware 3.6-56V); its CAN is currently 250 kbit/s and will be set to 1 Mbit/s.  
> shoulder actuator: **EaglePower LA8308 KV90, 30:1 two-stage planetary**, DRV5033 hall homing.  
> Architecture: [VAYN-6.2.1](../VAYN - 6.2.1.md). Build plan: [RT Core implementation spec](RT Core Implementation - VAYN 6.2.1.md).

I went through the VAYN architecture files you provided and cross-checked the important hardware/software points against current NVIDIA, ODrive, Flipsky, and AS5047P documentation.
The first thing to do is **separate what is already decided from what is still a design decision**. Right now the confusion is mostly because calibration, ODrive software, CAN, RT Core, Linux RT, Jetson, and ROS2 are being treated as one thing. They are not.
Your VAYN architecture already establishes the key principle: **Orin is the AI computer, RT Core owns physical control, and the Safety MCU is independent protection.** Pasted text (3)

---

# 1. First: LOCK the Phase-1 hardware
For the **initial actuator prototype**, I would lock this:

| Part | Decision | Role |
| ---| ---| --- |
| AS5047P | LOCKED | Motor-side absolute magnetic encoder |
| Flipsky ODESC3.6 Dual Drive | LOCKED for prototype | BLDC motor driver + FOC + current control + encoder processing |
| Dell Latitude 5490 (i5-8350U) | LOCKED as initial RT computer (replaces the Mac Mini, 2026-10-20) | Runs Linux + PREEMPT_RT + our RT Core |
| Jetson Orin NX | AI computer, not RT Core initially | Vision, AI, policy, planning |
| CAN | LOCKED as eventual RT→ODrive actuator bus | Real-time command/feedback network |
| USB | LOCKED for initial ODrive commissioning | PC/Mac → ODESC3.6 during setup/calibration |
| Ethernet | Recommended for Orin ↔ RT Core | High-level motion/reference communication |

The ODESC3.6 vendor listing explicitly gives 8–56 V operation, 50 A continuous / 120 A peak claims, AS5047 support, USB, UART, CAN and other interfaces. [FLIPSKY](https://flipsky.net/collections/special-promotion-products/products/odesc3-6-dual-drive-controller-56v-with-heat-sink-optimizes-high-performance-brushless-motor-high-power-foc-bldc-based-on-odrive?utm_source=chatgpt.com)
There is an important caveat: **ODESC3.6 is an ODrive-derived third-party board, not the official ODrive v3.6.** The official ODrive documentation currently marks v3.6 as NRND/end-of-life, so we should treat the Flipsky board as its own hardware and verify its firmware and electrical behavior before relying on official ODrive assumptions. [ODrive Documentation](https://docs.odriverobotics.com/v/latest/hardware/odrive-comparison.html?utm_source=chatgpt.com)
So:
> **Locked for our prototype ≠ permanently locked for production.**  
> That distinction matters.

---

# 2. The single most important thing: what is the RT Core?
Forget the name "RT Core" for a moment.
Technically, our RT Core is:
> **A C++ real-time control application running as a Linux process on a computer using a PREEMPT_RT Linux kernel.**  
> It is **not**:
- a separate chip
- ROS2 itself
- a neural network
- ODrive firmware
- the Jetson
- the Linux kernel

It is our own software.

Think of the stack like this:

```swift
┌────────────────────────────────────┐
│ Ubuntu Linux                       │
│                                    │
│ PREEMPT_RT kernel                  │
│                                    │
│ ┌────────────────────────────────┐ │
│ │ VAYN RT CORE                   │ │
│ │                                │ │
│ │ State estimation               │ │
│ │ Safety validation              │ │
│ │ Trajectory generation          │ │
│ │ Impedance control              │ │
│ │ Joint control                  │ │
│ │ CAN communication              │ │
│ └────────────────────────────────┘ │
│                                    │
└────────────────────────────────────┘
                 │
                CAN
                 │
                 ▼
             ODESC3.6
                 │
                FOC
                 │
                 ▼
               BLDC
```

Your VAYN documents already define the RT loop around state estimation, validation, trajectory generation, control, limits, actuator commands and timing checks. Pasted text (2)

---

# 3. Then what exactly is PREEMPT_RT?
This is another place where the terminology gets mixed up.
### Linux
Normal Linux is optimized for general-purpose computing.
A normal process can sometimes be delayed because another process, interrupt, driver, kernel task, etc. gets scheduled.
### PREEMPT_RT
PREEMPT_RT modifies the Linux kernel so that important tasks can get **much more deterministic scheduling and latency**.
Very simplified:

```css
Normal Linux

your control loop
      ↓
"wait, something else needs CPU time"
      ↓
delay
```

With PREEMPT_RT:

```verilog
your control thread
      ↓
high-priority real-time scheduling
      ↓
much more predictable execution
```

But one important correction:
> **Installing PREEMPT_RT does NOT automatically make a program real-time.**  
> Our C++ program must also be written appropriately.  
> For example, the RT thread should avoid things such as:

```cs
dynamic memory allocation
blocking I/O
random disk access
slow logging
unbounded locks
garbage collection
```

and should use appropriate real-time scheduling, CPU affinity, memory locking, etc.
So the relationship is:

```perl
PREEMPT_RT
     ↓
makes Linux better suited for deterministic control
     ↓
our C++ RT Core
     ↓
uses that environment correctly
```

---

# 4. Is RT Core ROS2?
## No.
This distinction is important.
ROS2 is a **robotics middleware framework**. It gives us communication, nodes, topics, services, actions, message definitions, etc.
RT Core is **our physical control software**.
We can eventually have:

```markdown
Jetson
│
├── ROS2
├── VLM
├── perception
├── planner
└── policy
      │
      │ motion reference
      ▼
   Ethernet
      │
      ▼
┌─────────────────┐
│ RT Core         │
│ C++             │
│ PREEMPT_RT      │
└────────┬────────┘
         │
        CAN
         │
         ▼
      ODESC
```

ROS2 may eventually be involved in the communication between high-level VAYN components and the RT system.
But I **do not want our first actuator controller to depend on ROS2**.
Our first RT program should simply be:

```swift
C++
↓
CAN
↓
ODrive
```

Later we can integrate ROS2 around it.

---

# 5. Where will we write RT Core?
We will have an ordinary software repository, something like:

```css
vayn/
│
├── rt_core/
│   ├── main.cpp
│   ├── rt_loop.cpp
│   ├── rt_loop.hpp
│   │
│   ├── control/
│   │   ├── impedance.cpp
│   │   └── trajectory.cpp
│   │
│   ├── state/
│   │   ├── estimator.cpp
│   │   └── state.cpp
│   │
│   ├── safety/
│   │   ├── limits.cpp
│   │   └── validator.cpp
│   │
│   └── actuator/
│       ├── odrive.cpp
│       └── actuator.cpp
│
├── simulation/
├── tests/
├── config/
└── docs/
```

The VAYN Phase-1 plan already separates the RT loop, state, control, safety, actuator abstraction, timing and simulation in essentially this way. Pasted text (2)
We compile it into something like:

```text
vayn_rt_core
```

and eventually Linux starts it automatically:

```sql
Linux boot
   ↓
systemd
   ↓
vayn_rt_core
   ↓
real-time control loop
```

So the RT Core is ultimately just a **real software application**, but one designed to run with real-time constraints.

---

# 6. Now the biggest question: which computer runs the RT core (updated 2026-10-20)
My recommendation was originally the Mac Mini. **Decision now: use the Dell Latitude 5490 laptop as the initial physical RT computer**, with Ubuntu 26.04 and the PREEMPT_RT kernel (already installed and verified: `7.0.0-38-realtime`, `CONFIG_PREEMPT_RT=y`).
### Why?
Your VAYN architecture intentionally separates:

```java
Jetson = intelligence
RT computer = physical control
Safety MCU = independent safety
```

Pasted text (3)
Using the Jetson as the RT machine would blur that separation.
NVIDIA does provide a real-time kernel for Jetson Orin NX/Nano, so technically the Jetson is capable of running PREEMPT_RT. NVIDIA documents RT-kernel support for Orin NX/Nano. NVIDIA Docs
But that does **not** mean we should use it as our RT computer.
The Jetson's primary purpose in VAYN is:

```text
vision
AI
policy
planning
GPU computation
```

We don't want our physical control loop competing with those workloads.

---

## Why the Dell 5490 makes sense for Phase 1
It is an x86 machine with 4 physical cores (Intel i5-8350U), so one core can be isolated for the servo loop. The Late-2014 Mac Mini had only two cores Apple Support. Its Intel I219-LM Ethernet supports hardware timestamps (for PTP to the Orin). Laptop-specific risks are firmware SMIs (Dell `dell_smm_hwmon`), deep C-states, and battery power-saving; they are handled in the implementation spec §3.
For our first target:

```sql
one actuator
→
one joint
→
eventually a few joints
```

that is perfectly reasonable.
But I would **not declare the Dell 5490 to be our final humanoid RT computer**. It is the Phase-1 RT host.
We will benchmark it.
The actual test will be something like:

```diff
PREEMPT_RT
+
CPU stress
+
CAN traffic
+
control loop
+
cyclictest
```

Then we measure:

```text
minimum latency
average latency
maximum latency
jitter
missed deadlines
```

That tells us whether the machine is actually suitable rather than assuming it is.

---

# 7. So where does the normal PC fit?
Your normal PC is still useful.
Think:

```bash
Development PC
      │
      │ write / compile / test
      ▼
VAYN source code
      │
      ▼
Dell 5490
      │
      │ runs
      ▼
RT Core
```

So:
### Development computer
Used for:

```text
coding
Git
simulation
plots
documentation
debugging
```

### Dell 5490
Used as:

```kotlin
actual RT host
```

This is much cleaner than trying to turn your development PC into the permanent robot controller.

---

# 8. What about Jetson Orin?
For VAYN:

```markdown
Jetson Orin NX
      │
      ├── Camera
      ├── Vision
      ├── AI
      ├── Policy
      ├── Planning
      └── High-level motion references
                         │
                         ▼
                      Ethernet
                         │
                         ▼
                   Dell 5490 RT Core
                         │
                        CAN
                         │
                         ▼
                    ODESC3.6
```

That is the architecture I want us to build first.
The VAYN design explicitly says the physical-control stack should be able to operate without Orin. Pasted text (2)

---

# 9. Now your second big question: does RT Core do anything during motor calibration?
## Initially: NO.
This is very important.
When we receive the ODESC3.6, we are **not going to immediately involve VAYN RT Core**.
The first phase is ODrive/ODESC commissioning.
The sequence will be:

```text
Computer
   │
  USB
   │
   ▼
ODESC3.6
```

We identify:

```cpp
hardware
firmware
voltage variant
serial
errors
configuration
```

Then configure:

```sql
motor
encoder
current limits
controller
```

Then perform:

```sql
motor calibration
encoder offset calibration
```

ODrive's documentation specifically describes the encoder offset calibration as the step that determines the relationship between electrical motor phase and encoder position. [ODrive Documentation](https://docs.odriverobotics.com/v/latest/guides/odrivetool-setup.html?utm_source=chatgpt.com)
Flipsky itself recommends installing its ODESC environment with the ODrive Python package and using `odrivetool` for this process. Its current setup guide specifically recommends `odrive==0.5.1.post0` for the ODESC3.6 workflow. [FLIPSKY](https://flipsky.net/blogs/vesc-tool/odescv42-environment-installation-guide-for-connected-pcs?utm_source=chatgpt.com)

---

# 10. So when DOES RT Core enter?
This is the key timeline.
## Stage 0 — Hardware bring-up

```text
PC/Mac
  ↓ USB
ODESC
```

RT Core:

```text
NOT involved
```

---

## Stage 1 — ODrive calibration

```text
PC
 ↓
odrivetool
 ↓
ODESC
 ↓
motor
 ↓
AS5047P
```

Still:

```java
RT Core = NOT involved
```

---

## Stage 2 — ODrive-only actuator testing
We test:

```css
current
torque
velocity
position
encoder feedback
temperature
faults
```

Still primarily:

```text
Computer
   ↓ USB
ODESC
```

The ODESC is doing the low-level control itself.

---

## Stage 3 — CAN takeover
This is where RT Core first becomes a real physical component.

```markdown
Dell 5490 RT Core
       │
       │ CAN
       ▼
   ODESC3.6
       │
       ▼
      BLDC
```

The ODrive/ODESC already performs FOC and current regulation.
Our RT Core now sends commands such as:

```text
desired torque
```

and reads back things like:

```css
position
velocity
current
torque
temperature
faults
```

ODrive's CAN protocol supports host-set commands and feedback messages over a standard CAN bus. [ODrive Documentation](https://docs.odriverobotics.com/v/latest/manual/can-protocol.html?utm_source=chatgpt.com)

---

# 11. This is the exact moment RT Core becomes necessary
Suppose we want:
> "Move the shoulder to 40° while behaving like a compliant spring."  
> Now the RT Core does:

```css
desired position
      ↓
actual position
      ↓
position error
      ↓
impedance controller
      ↓
desired joint torque
      ↓
gear ratio conversion
      ↓
motor torque
      ↓
CAN
      ↓
ODESC
```

The ODESC then does:

```markdown
motor torque
      ↓
current target
      ↓
FOC
      ↓
PWM
      ↓
motor
```

That separation is fundamental.

---

# 12. ODrive is already doing a LOT
This is another misconception we need to eliminate.
We are **not** writing:

```text
three-phase BLDC control
```

from scratch.
ODrive/ODESC already handles things such as:

```sql
motor commutation
FOC
phase current measurement
current control
encoder processing
motor calibration
motor protection
```

The RT Core is one level above this.
So:

```bash
RT Core
"Give me 2.5 Nm motor torque"

        ↓

ODESC

"Okay, that requires approximately
this much motor current."

        ↓

FOC

"Generate the required phase currents."

        ↓

Motor
```

That is why using ODESC is valuable.

---

# 13. What is FOC?
Very simply:
**FOC = Field Oriented Control.**
A BLDC motor has three phase currents:

```css
Phase A
Phase B
Phase C
```

FOC mathematically transforms those currents into a rotating reference frame so the controller can independently reason about magnetic flux and torque.
You don't need to implement that yourself.
For us:
> **ODESC owns FOC.**  
> That's the correct abstraction.

---

# 14. Now: what exactly does CAN do?
CAN is not the controller.
CAN is the **communication network**.
Think:

```bash
RT Core
"Give actuator 4 this torque."

        ↓

CAN message

        ↓

ODESC #4
"Got it."
```

Then:

```bash
ODESC #4
"My position is X.
My velocity is Y.
My current is Z."

        ↓

CAN

        ↓

RT Core
```

CAN is therefore the **wire/protocol connecting the controller computer to the motor controllers**.

---

# 15. Does Jetson need CAN?
## In our proposed architecture: NO.
This is very important.
We do **not** want:

```swift
Jetson
   ↓ CAN
ODrive
```

as the primary architecture.
We want:

```swift
Jetson
   ↓
 Ethernet
   ↓
RT Core
   ↓
 CAN
   ↓
ODrive
```

Why?
Because:

```text
Jetson → high-level reference

RT Core → physical control

ODrive → electrical motor control
```

Each system has one clear responsibility.

---

# 16. What happens during calibration then?
During calibration:

```markdown
Dell 5490 / PC
       │
       │ USB
       ▼
   ODESC3.6
       │
       ▼
     Motor
```

No CAN is required.
Later:

```swift
Dell 5490 RT Core
       │
       │ USB-CAN adapter
       │
       ▼
CAN_H ───────────────┐
CAN_L ───────────────┤
                     │
                 ODESC3.6
```

That is when CAN becomes part of the physical control architecture.

---

# 17. What physical wires are we actually talking about?
There are several different types of connections.
## A. AS5047P → ODESC
Your encoder board exposes:

```swift
CS
CLK
MISO
MOSI
5V
3.3V
```

For SPI operation, the important signals are:

```text
VCC
GND
SCK
MISO
CS
```

with MOSI depending on the exact encoder configuration.
The AS5047P provides 14-bit absolute angle data over SPI and supports 5 V or 3.3 V operation at the chip level. ams OSRAM
ODrive officially supports the AMS AS5047P protocol over SPI. ODrive Documentation
For our actuator, **we will use SPI**, not the A/B incremental output, as the primary motor encoder interface.
So conceptually:

```markdown
AS5047P
 ├── VCC
 ├── GND
 ├── SCK
 ├── MISO
 ├── CS
 └── MOSI
        │
        ▼
     ODESC
```

The exact connector/pin mapping must come from the actual Flipsky board revision; we should not blindly assume official ODrive v3.6 pin numbering on the clone.

---

# 18. B. RT Core → ODESC
This is:

```swift
CAN_H
CAN_L
```

using a **twisted pair**.
CAN is a differential bus, meaning the receiver looks at the voltage difference between the two wires rather than treating one wire as an absolute signal.
A typical CAN bus is:

```bash
RT Core
  │
  │ CAN-H
  │ CAN-L
  │
  ├──────────── ODESC #1
  │
  ├──────────── ODESC #2
  │
  ├──────────── ODESC #3
  │
  └──────────── ODESC #N
```

and the physical bus uses:

```text
120 Ω termination
```

at the two ends of the bus.
ODrive's CAN guide describes exactly this standard differential twisted-pair topology with 120 Ω termination. [ODrive Documentation](https://docs.odriverobotics.com/v/latest/guides/can-guide.html?utm_source=chatgpt.com)
For your ODESC clone, we will verify whether the board has onboard termination before finalizing the harness; ODESC users have reported hardware differences from official ODrive boards. [ODrive Community](https://discourse.odriverobotics.com/t/request-for-review-of-my-can-bus-wiring-diagram/12150?utm_source=chatgpt.com)

---

# 19. C. Jetson → RT Core
I recommend:

```text
Ethernet
```

For example:

```markdown
Jetson Orin NX
      │
    Cat6
      │
      ▼
Dell 5490 RT Core
```

This communication is **not part of the fast motor-control loop**.
For example:

```swift
Jetson:

"Walk forward at 0.3 m/s."

        ↓

RT Core:

"Okay. Here's the safe joint motion."

        ↓

CAN

ODrive
```

The RT Core should still be able to control the robot if the Jetson suddenly disappears.
That follows directly from the VAYN architecture. Pasted text (3)

---

# 20. What does the RT Core actually calculate?
Let's take one shoulder joint.
The Jetson might give:

```java
desired shoulder angle
= 45°
```

The RT Core reads:

```java
actual shoulder angle
= 42°
```

and perhaps:

```kotlin
desired velocity
actual velocity
estimated torque
IMU state
joint limits
```

Then it calculates:

```markdown
error = 45° - 42°
      = 3°
```

Then impedance control:

```markdown
τ = Kp(qd - q)
  + Kd(q̇d - q̇)
  + τff
```

Your Phase-1 architecture already defines this as the first baseline controller. Pasted text (2)
Then:

```markdown
joint torque
      ↓
gear ratio
      ↓
motor torque
      ↓
ODESC
```

---

# 21. What is the difference between ODrive control and RT Core control?
This is probably the cleanest distinction:

| Layer | Main question |
| ---| --- |
| Jetson AI | What should the robot do? |
| RT Core | How should the joints move safely? |
| ODESC | What motor current is required right now? |
| FOC | What phase currents/PWM produce that motor torque? |
| BLDC motor | Convert electrical power into mechanical rotation |
| Gearbox | Convert speed/torque |
| Joint | Produce physical movement |

That is the hierarchy.

---

# 22. What exactly is the "ODrive software"?
There are actually **three different things** people casually call "ODrive software."
### 1. ODrive/ODESC firmware
This lives **inside the motor controller**.

```sql
ODESC MCU
   ↓
firmware
   ↓
FOC
current control
encoder processing
control modes
CAN
faults
```

---

### 2. `odrivetool`
This runs on your computer.

```markdown
Linux/Windows PC
       ↓
odrivetool
       ↓
USB
       ↓
ODESC
```

We use this for:

```text
configuration
calibration
diagnostics
testing
reading parameters
clearing faults
```

Flipsky's own ODESC3.6 setup guide uses `odrivetool` and recommends the `0.5.1.post0` ODrive Python package for its ODESC workflow. [FLIPSKY](https://flipsky.net/blogs/vesc-tool/odescv42-environment-installation-guide-for-connected-pcs?utm_source=chatgpt.com)

---

### 3. ODrive CAN protocol
This is what we eventually use for runtime robot control.

```markdown
RT Core
    ↓
CAN message
    ↓
ODESC firmware
```

So:

```java
odrivetool
=
commissioning tool

CAN
=
runtime communication

ODESC firmware
=
actual motor controller
```

This distinction will make the software side much less confusing.

---

# 23. The ODESC firmware should NOT be our first coding target
Initially:

```dpr
WE WRITE

VAYN RT Core

WE DO NOT WRITE

ODrive FOC
```

We use the existing firmware.
The first VAYN code we write is:

```bash
CAN driver
    ↓
ODrive actuator interface
    ↓
joint state
    ↓
safety validator
    ↓
impedance controller
    ↓
torque command
```

This matches the Phase-1 software architecture in your documents. Pasted text (2)

---

# 24. The development timeline I recommend
This is the timeline I would actually follow.

```markdown
PHASE 0
Hardware identification
        │
        ▼
ODESC + AS5047P
        │
        ▼
USB communication
        │
        ▼
ODrive configuration
        │
        ▼
motor calibration
        │
        ▼
encoder calibration
        │
        ▼
low-power motor testing
```

### Then:

```diff
PHASE 1
Actuator validation

ODESC
+
motor
+
encoder
+
gearbox
```

Test:

```css
torque
velocity
position
temperature
faults
limits
```

### Then:

```swift
PHASE 2
CAN

Dell 5490
   ↓
USB-CAN
   ↓
CAN
   ↓
ODESC
```

Now we know the RT computer can actually command the actuator.
### Then:

```diff
PHASE 3
RT Core

C++
+
PREEMPT_RT
+
CAN
+
ODrive driver
```

Now RT Core becomes part of the real actuator loop.
### Then:

```text
PHASE 4
Single-joint impedance control
```

Then:

```text
PHASE 5
Multiple joints
```

Then:

```perl
PHASE 6
IMU + state estimator
```

Then:

```css
PHASE 7
Whole-body stabilization
```

Then:

```text
PHASE 8
Jetson integration
```

Then:

```swift
Jetson
 ↓
motion reference
 ↓
RT Core
 ↓
CAN
 ↓
actuators
```

This follows the development sequence in your VAYN architecture: hardware → actuator interface → safety/RT control → single joint → multi-joint → stabilization → Orin integration → AI. Pasted text (3)

---

# 25. So when does RT Core "start"?
There are actually **two meanings of start**.
### Software development starts now
We can already build:

```diff
RT Core skeleton
+
simulation
+
controller
+
CAN interface
```

without connecting a motor.
Your Phase-1 plan explicitly proposes simulation and failure testing before the real actuator. Pasted text (2)
### Physical RT Core starts later
The first real physical RT loop is:

```swift
Dell 5490
   ↓
RT Core
   ↓
CAN
   ↓
ODESC
   ↓
motor
   ↓
encoder
   ↓
ODESC
   ↓
CAN
   ↓
RT Core
```

That is the moment I would call:
> **"VAYN RT Core is now controlling a real actuator."**

---

# 26. One important correction to our earlier thinking
We should **not** make the first goal:

```text
Jetson + RT + ODrive + ROS2 + AI + humanoid
```

That is far too many moving pieces.
Our first complete system should be:

```markdown
        DELL 5490
     Ubuntu + RT
           │
         CAN
           │
      ODESC3.6
       │      │
       │    AS5047P
       │
     BLDC
       │
    gearbox
       │
     joint
```

That's it.
Then prove:

```css
position
velocity
torque
feedback
safety
timing
```

Only after that do we add Jetson.

---

# 27. One more important issue: AS5047P placement

> **Update (2026-10-20):**  
> At 30:1, one motor turn is 12° at the joint.  
> The shoulder CAD uses a DRV5033 hall homing sensor on the output flange (no output encoder).  
> Because 30:1 is an exact integer ratio, homing selects the 12° sector, and the motor AS5047P then gives the absolute angle (VAYN-6.2.1 §8).

For the **first actuator**, I am comfortable with:

```text
BLDC
 │
AS5047P
 │
ODESC
 │
gearbox
 │
joint
```

But that encoder tells us **motor shaft position**, not necessarily exact final joint position.
Your current VAYN architecture discussion correctly identifies the benefit of having a second output-side encoder eventually. Pasted text
So:
### Prototype 1

```text
1 × AS5047P
→ motor side
→ ODESC
```

### Later production actuator
Potentially:

```css
AS5047P #1
→ motor position
→ ODESC

Output encoder
→ joint position
→ RT Core
```

I would **not delay the first prototype for the second encoder**.

---

# 28. Final architecture we are locking right now
This is the diagram I would put into the VAYN electronics documentation:

```swift
                         VAYN
                          │
              ┌───────────┴───────────┐
              │                       │
              ▼                       ▼
      ┌────────────────┐      ┌─────────────────┐
      │ JETSON ORIN NX │      │   DELL 5490      │
      │                │      │   Intel i5      │
      │ AI             │      │                 │
      │ Vision         │      │ Ubuntu Linux    │
      │ Policy         │      │ PREEMPT_RT      │
      │ Planning       │      │                 │
      └───────┬────────┘      │  VAYN RT CORE   │
              │               └────────┬────────┘
              │                        │
           Ethernet                    │ CAN
              │                        │
              └───────────────────────►│
                                       ▼
                              ┌──────────────────┐
                              │ FLIPSKY ODESC3.6 │
                              │                  │
                              │ CAN              │
                              │ FOC              │
                              │ Current control  │
                              │ Motor control    │
                              │ Encoder input    │
                              └───────┬──────────┘
                                      │
                                   3-phase
                                      │
                                      ▼
                                  BLDC MOTOR
                                      │
                                  GEARBOX
                                      │
                                      ▼
                                  JOINT OUTPUT
```

And:

```text
AS5047P
   │
   │ SPI
   ▼
ODESC3.6
```

while later:

```markdown
Output encoder
      │
      │
      ▼
RT Core
```

---

# 29. The decisions are therefore
### **LOCKED**
**Motor controller:**
Flipsky ODESC3.6 Dual Drive
**Motor encoder:**
AS5047P, motor-side, SPI
**Initial RT computer:**
Dell Latitude 5490 (i5-8350U), running Ubuntu 26.04 + PREEMPT_RT kernel 7.0
**AI computer:**
Jetson Orin NX
**Initial ODESC communication:**
USB
**Runtime actuator communication:**
CAN
**Jetson ↔ RT Core:**
Ethernet
**RT Core implementation:**
C++
**RT Core ≠ ROS2**
**ODrive FOC:**
Leave inside ODESC

---

# 30. What is still NOT locked
These should deliberately remain open for now:

```swift
Exact Ubuntu version
Exact PREEMPT_RT kernel
USB-CAN adapter model
CAN bitrate
CAN message schedule
CAN termination implementation
Safety MCU
Battery voltage
Fuse
Contactor
Precharge circuit
Brake resistor
Final output encoder
IMU
Final RT computer
```

Those are the next engineering decisions.

> **Update (2026-10-20):**  
> Now decided:  
> Ubuntu 26.04  
> PREEMPT_RT kernel `7.0.0-38-realtime`  
> CAN bitrate 1 Mbit/s  
> CAN message schedule: polled CANSimple 0.5.1, 325 µs per joint per cycle  
> Still open:  
> USB-CAN adapter model  
> termination  
> Safety MCU, fuse, contactor, precharge  
> output encoder, IMU  
> final RT computer  
> Brake resistor: 2 Ω, configured and armed; verify it with a multimeter.  
> Battery: not used in Phase 1 (bench PSU).  
> See the [RT Core implementation spec §19](RT Core Implementation - VAYN 6.2.1.md) for the recommended purchases.

Also, because the ODESC is a clone, **we should identify the exact firmware/hardware revision before flashing or trusting any configuration command**. Flipsky's documentation points to the older ODrive toolchain, and there are historical reports of firmware incompatibilities with ODESC3.6, so blindly flashing a current official ODrive firmware would be a bad idea. [FLIPSKY](https://flipsky.net/blogs/vesc-tool/odescv42-environment-installation-guide-for-connected-pcs?utm_source=chatgpt.com)

---

# 31. The entire system in one sentence
The simplest mental model to keep in your head is:
> **Jetson decides what the robot should do → RT Core decides how the body should move safely → CAN carries commands to ODESC → ODESC converts the command into motor current using FOC → encoder feedback closes the loop.**  
> And during commissioning:  
>   
> **PC/Mac → USB → ODESC → calibration/testing; RT Core is not needed yet.**  
> That is the separation we should use for all further VAYN electronics discussions.
