> **Revision note (2026-10-20, VAYN-6.2.1):**  
> The hardware choices that §26 lists as open are now made for Phase 1. RT processor: Dell Latitude 5490 with PREEMPT_RT. Actuator bus: classic CAN at 1 Mbit/s. Motor driver: Flipsky ODESC3.6, firmware 0.5.1. Safety for Phase 1: a guarded, tethered rig. Actuator: EaglePower LA8308 KV90 with a 30:1 two-stage planetary gearbox.  
> The rest of this explainer is still valid.  
> What the RT core is and how it is built: [VAYN-6.2.1](../VAYN - 6.2.1.md), [RT Core implementation spec](RT Core Implementation - VAYN 6.2.1.md), and [RT Core from fundamentals to advanced](RT Core - From Fundamentals to Advanced.md).

# Building VAYN-6.2 — Versatile Arbitrated Embodied Nervous-System

> **VAYN-6.2 is not one AI model. It is a complete robot control system in which different computers and models have different jobs.**

# 1. VAYN-6.2 in very simple language

Think of the robot as having **three main computers**:

```text
             ┌─────────────────────┐
             │   AI COMPUTER       │
             │   Jetson Orin NX    │
             │                     │
             │ "What should I do?" │
             └──────────┬──────────┘
                        │
                 movement reference
                        │
                        ▼
             ┌─────────────────────┐
             │   RT MOTION CORE    │
             │                     │
             │ "How do I move      │
             │  safely right now?" │
             └──────────┬──────────┘
                        │
                   motor commands
                        │
                        ▼
             ┌─────────────────────┐
             │     ACTUATORS       │
             └─────────────────────┘

             ┌─────────────────────┐
             │    SAFETY MCU       │
             │                     │
             │ "Is anything        │
             │  dangerously wrong?"│
             └─────────────────────┘
```

The three computers **do not have equal authority**.

The key rule is:

```text
Orin = intelligence
RT Core = physical control
Safety MCU = independent protection
```

The Orin can disappear and the robot should still have a physical control path. The VAYN-6.2 document explicitly makes the RT Motion Core the owner of stabilization, arbitration, safety validation, fallback and final actuator commands, while the Safety MCU is independent.

---

# 2. The easiest way to understand the four parts

VAYN uses:

```text
THINK → PREDICT → MOVE → SURVIVE
```

## THINK = "What do I want to do?"

This is the intelligent/high-level part.

Example:

You say:

> "Pick up the red bottle."

The robot needs to figure out:

```text
What is the bottle?
Where is it?
Which hand should I use?
What skill should I execute?
```

This is where the VLM, memory and task planner live.

It is **not** controlling motors directly.

Think of it as the robot's **decision maker**.

---

# 3. PREDICT = "What is going to happen?"

Suppose the robot sees:

```text
cup is here
```

But the camera image is already 50 ms old.

The robot has moved during those 50 ms.

So instead of blindly saying:

> "The cup is exactly where the camera saw it."

the predictive system asks:

> "Given how the robot moved, where is the cup/robot likely to be now?"

And similarly:

> "If I move my hand like this, where will my hand/body probably be 30 ms later?"

VAYN-6.2 specifically uses a **hybrid prediction idea**:

```text
Known physics / kinematics
           +
learned residual
           +
contact information
           ↓
     predicted state
```

So we're not asking a neural network to relearn all of physics from zero.

---

# 4. MOVE = "What exact movement should happen?"

Now the robot has:

```text
task
+
vision
+
physical state
+
optional prediction
+
constraints
```

The action policy decides:

> "Move the right hand toward this position."

But this is very important:

### The AI does NOT say:

```text
Motor 1 = 2.37 A
Motor 2 = 1.83 A
Motor 3 = ...
```

Instead it produces a **motion reference**.

For example:

```text
Move right hand here
Move body this way
Put foot here
Maintain this grip force
```

The document calls this a **skill-specific motion reference**.

For example:

```text
GRASP

hand position
hand orientation
joint posture
grip force
contact mode
```

or:

```text
WALK

base velocity
turning velocity
footstep target
timing
body posture
```

---

# 5. SURVIVE = "Can the physical robot actually do this safely?"

This is the most important part of VAYN.

Suppose the AI says:

```text
Move arm here
```

The RT Motion Core asks:

```text
Is this allowed?
Is the joint limit exceeded?
Is the torque too high?
Is the command stale?
Is the robot falling?
Do I need to correct the motion?
```

Then it converts the reference into actual motor control.

Simplified:

```text
AI says:
"Put hand here"

        ↓

RT Motion Core

        ↓

check limits
check state
stabilize body
calculate trajectory
apply impedance/torque control

        ↓

motor driver

        ↓

motor
```

That ownership is explicitly frozen in VAYN-6.2.

---

# 6. Why do we need the RT Motion Core?

This is probably the **single most important concept** to understand before we build anything.

Imagine the Orin runs Linux and your neural model takes:

```text
50 ms
```

or crashes.

You don't want:

```text
AI crashed
   ↓
motors suddenly lose control
   ↓
robot falls
```

Instead:

```text
AI crashed
   ↓
RT Motion Core notices
   ↓
rejects stale command
   ↓
uses fallback behavior
   ↓
keeps controlling the robot
```

That is why VAYN calls it **real-time physical control** rather than simply putting everything inside Python/PyTorch.

---

# 7. Why the Safety MCU exists

Now imagine the RT computer itself crashes.

We don't want:

```text
Orin ──X
RT Core ──X
       ↓
motors continue doing something dangerous
```

The Safety MCU is another independent layer.

It watches things such as:

```text
motor current
encoder status
temperature
driver state
heartbeats
E-stop
```

and can constrain or disable actuation when necessary.

The important part is that it should not depend on:

```text
Linux
CUDA
VLM
Orin software
```

for its basic safety role.

---

# 8. So the robot has two different kinds of "brain"

This distinction is useful:

### AI brain

```text
"I want to pick up the cup."
```

### Physical brain

```text
"Your arm is moving too fast.
Your body is leaning.
Slow down.
Shift COM.
Don't exceed this torque."
```

The first is intelligent and flexible.

The second is **fast, predictable and physically constrained**.

VAYN-6.2 is basically saying:

> Don't force one computer/model to do both jobs.

---

# 9. What actually runs on the Orin?

The baseline assigns the Orin things like:

```text
Camera processing
Visual encoder
Object tracking
World model
Action policy
Cognitive model
Task planner
Event manager
Logging
Model management
```

So the Orin is doing the **expensive AI work**.

It is not the final authority on the motors.

---

# 10. What actually runs on the RT Motion Core?

This is where the real robotics/control engineering happens:

```text
IMU
Encoder
Force/torque
Contact information
       ↓
State estimation
       ↓
Stabilization
       ↓
Command arbitration
       ↓
Safety validation
       ↓
Trajectory generation
       ↓
Impedance / torque control
       ↓
Motor drivers
```

The RT core is the robot's **physical nervous system**.

The document explicitly assigns state estimation, arbitration, validation, fallback, stabilization, trajectory generation and impedance control here.

---

# 11. What is "physical state"?

The RT computer maintains the authoritative physical state.

For example:

```text
q            = joint positions
q_dot        = joint velocities

base pose
base velocity
body orientation

motor torque/current

contact state

COM position
COM velocity
```

Think:

```text
S_phys = "What is physically happening to my body right now?"
```

The Orin can **read** this state.

It doesn't get to create a competing version of physical truth.

---

# 12. Where does vision fit?

Vision is separate from physical state.

For example:

```text
Physical state:
"My right elbow is at 1.2 rad."

Vision:
"There is a red cup 40 cm in front of me."

Task state:
"I need to pick up that cup."

Prediction:
"My hand will probably reach this position in 30 ms."
```

VAYN intentionally keeps these representations separate because visual information contains details that cannot be compressed into simple physical variables.

---

# 13. What is the Reflex Layer?

Imagine the robot is holding a cup.

The high-level policy says:

```text
Hold cup
```

Suddenly:

```text
cup starts slipping
```

We don't want to wait for:

```text
camera
→ vision model
→ planner
→ policy
→ new command
```

Instead fast sensors can react:

```text
tactile / force / IMU / joint feedback
           ↓
        reflex
           ↓
small correction
```

For example:

```text
increase grip force
```

or:

```text
move wrist slightly
```

The important part is that the reflex is **bounded**.

It doesn't get unlimited authority.

---

# 14. What does "bounded" mean?

Suppose the AI says:

```text
move arm normally
```

and the reflex detects something unusual.

It can add:

```text
Δu_reflex
```

but only within a predefined authority.

Conceptually:

```text
final request =
normal AI request
+
limited reflex correction
```

The RT core decides whether that final command is actually allowed.

So:

```text
AI
 │
 ├── "move here"
 │
 ▼
Reflex
 │
 └── "slightly correct"
 │
 ▼
RT Core
 │
 └── "I decide what is physically allowed"
```

This is important because otherwise three systems could fight over the actuator.

---

# 15. What happens if AI stops?

This is where VAYN becomes much easier to understand.

### Normal

```text
Orin
 ↓
RT Core
 ↓
Robot
```

### Orin failure

```text
Orin X

RT Core
 ↓
fallback
 ↓
Robot remains physically controlled
```

### RT Core failure

```text
RT Core X

Safety MCU
 ↓
hardware-defined safety response
```

The exact final behavior depends on your actuator hardware: brakes, passive damping, driver safe-state behavior, etc.

So **we cannot finish the safety architecture without eventually knowing the actuator design**.

---

# 16. What does "stale command" mean?

Suppose the AI says:

```text
Move arm to position X
```

and then the AI freezes for 2 seconds.

We absolutely do not want the robot thinking:

> "This is the newest command, so I'll keep using it."

Every important command therefore contains:

```text
timestamp
sequence_id
valid_until
```

So the RT core can say:

```text
command expired
      ↓
reject
      ↓
fallback
```

This freshness idea is one of the important frozen architectural rules.

---

# 17. The entire robot in one example

Let's say you say:

> **"Pick up the bottle."**

### Step 1 — THINK

VLM:

```text
Task = pick up bottle
Object = bottle_01
Hand = right
Skill = GRASP
```

### Step 2 — PERCEIVE

Camera:

```text
Bottle location
Bottle orientation
Scene geometry
```

### Step 3 — PREDICT

Prediction:

```text
Given robot motion + sensing delay:
expected hand/object state = X
```

### Step 4 — MOVE

Action policy:

```text
Move right hand to X
Approach at this velocity
Use this grip force
```

### Step 5 — REFLEX

Tactile:

```text
Contact detected
Slip probability increasing
```

Reflex:

```text
increase grip slightly
```

### Step 6 — RT CORE

RT controller:

```text
Check joint limits
Check velocity
Check torque
Maintain balance
Combine nominal + reflex
Generate motor commands
```

### Step 7 — SAFETY MCU

Safety MCU:

```text
Everything within limits?
Heartbeat alive?
Motor current safe?
Temperature safe?
```

### Step 8 — ACTUATORS

Motors physically move.

That's VAYN-6.2.

---

# 18. The important part: we are NOT going to build everything at once

This is where your original architecture document is actually very good.

The document explicitly says the development should happen in phases, starting with physical control and only later adding the advanced AI components.

The actual build should look like this:

```text
PHASE 1
Physical control
        ↓
PHASE 2
Basic robot behavior
        ↓
PHASE 3
Vision
        ↓
PHASE 4
Prediction
        ↓
PHASE 5
Reflex
        ↓
PHASE 6
Cognition
        ↓
PHASE 7
Generalist / advanced AI
```

---

# 19. Phase 1 is the REAL beginning

This is where I would start with you.

We build:

```text
ACTUATORS
    ↓
MOTOR DRIVERS
    ↓
RT MOTION CORE
    ↓
STATE ESTIMATOR
    ↓
STABILIZATION
    ↓
IMPEDANCE CONTROL
    ↓
SAFETY MCU
```

And **this must work without the Orin**.

That is explicitly the first development phase in your baseline.

---

# 20. What Phase 1 actually means in practical terms

We don't start by training a VLM.

We don't start by building a world model.

We don't start by training an LNN.

We don't even need the full humanoid intelligence yet.

We first need to make one joint behave correctly.

Something like:

```text
Encoder
   ↓
position estimate
   ↓
controller
   ↓
motor driver
   ↓
motor
   ↓
encoder
   └──────────────┐
                  │
                  └── feedback loop
```

Then:

```text
one joint
↓
one actuator
↓
one limb
↓
multiple joints
↓
whole body
```

---

# 21. Then we build the robot's physical "brain"

Once actuators work:

```text
IMU
+
encoders
+
force sensors
        ↓
state estimator
        ↓
"Where is my body?"
```

Then:

```text
state
+
desired motion
        ↓
stabilization/controller
        ↓
motor commands
```

This becomes the RT Motion Core.

---

# 22. Then we make it move without AI

Before adding the fancy neural system:

```text
STAND
WALK
SIT
REACH
GRASP
```

using conventional/controlled methods.

Why?

Because otherwise, when something fails later, we won't know whether the problem is:

```text
motor
encoder
controller
state estimator
AI
vision
prediction
```

The baseline explicitly requires baseline locomotion and manipulation before research components.

---

# 23. Only then do we add AI

Once the physical robot works:

```text
Physical robot
      +
vision
      ↓
object understanding
```

then:

```text
vision
+
physical state
+
task
      ↓
action policy
```

then:

```text
prediction
```

then:

```text
reflex
```

then:

```text
VLM
```

This keeps debugging manageable.

---

# 24. Minimum VAYN-6.2

You don't actually need the full architecture to say:

> "I have started VAYN."

The minimum functioning version in your document is:

```text
Safety MCU
+
RT Motion Core
+
State Estimator
+
Stabilization
+
Impedance Control
+
Baseline Locomotion
+
Baseline Manipulation
+
Basic Perception
```

The more advanced pieces such as world model, reflex, Flow Matching, VLM, event manager, distillation and free-form policy are optional research additions.

That is extremely important.

---

# 25. So how we'll actually build it

I suggest we treat this as a real engineering project with the following sequence:

```text
VAYN-6.2 IMPLEMENTATION
│
├── 0. Hardware definition
│
├── 1. Actuator interface
│
├── 2. Safety MCU
│
├── 3. RT Motion Core
│     ├── real-time loop
│     ├── encoder reader
│     ├── IMU
│     ├── state estimator
│     ├── limits
│     ├── trajectory generator
│     └── impedance controller
│
├── 4. Single-joint testing
│
├── 5. Multi-joint testing
│
├── 6. Whole-body state estimation
│
├── 7. Stabilization
│
├── 8. Basic locomotion
│
├── 9. Basic manipulation
│
├── 10. Orin communication
│
├── 11. Visual perception
│
├── 12. Action policy
│
├── 13. Prediction
│
├── 14. Reflex
│
├── 15. VLM / task manager
│
└── 16. Full VAYN integration
```

And we should **test every layer before connecting the next one**.

---

# 26. One thing we need to settle before writing code

Your VAYN-6.2 document intentionally leaves some hardware choices open:

```text
RT processor
Actuator communication bus
Actuator safety mechanism
Motor drivers
Sensors
```

Those are not arbitrary software details. They determine how we implement the RT Motion Core.

The document itself says the RT hardware and actuator bus are still engineering parameters rather than frozen choices.

So the next stage should be:

```text
VAYN-6.2
      ↓
PHYSICAL ROBOT HARDWARE
      ↓
RT HARDWARE SELECTION
      ↓
ACTUATOR INTERFACE
      ↓
PHASE 1 IMPLEMENTATION
```

**We can build this with you step-by-step, including the actual code, processes, communication protocol, folder structure, controller mathematics, simulation, testing and eventually the Orin integration.**

The first thing I would build is **Phase 1: one complete actuator control chain** — encoder → RT controller → motor driver → motor → feedback — because everything above it depends on that.
