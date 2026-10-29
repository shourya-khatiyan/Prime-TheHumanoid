> Actuators + motor drivers + Safety MCU + RT Motion Core + state estimator + stabilization + impedance control, operating without the AI computer.

It also deliberately leaves the **RT hardware, actuator bus, and exact actuator architecture open**, so we should not pretend those choices are already finalized.

# Phase 1 — Physical Control Foundation

## 1. What we are building

At the end of Phase 1, we want this:

```text
                    PHASE 1

        ┌─────────────────────────┐
        │      RT MOTION CORE     │
        │                         │
        │  State Estimator        │
        │  Safety Validator       │
        │  Trajectory Generator   │
        │  Stabilization          │
        │  Impedance Controller   │
        └────────────┬────────────┘
                     │
               motor command
                     │
                     ▼
              ┌────────────┐
              │ Motor Driver│
              └──────┬─────┘
                     │
                     ▼
                  MOTOR
                     │
                  gearbox
                     │
                     ▼
                 JOINT
                     │
              encoder / torque
                     │
                     └───────────────┐
                                     │
                                     ▼
                              RT State Estimator


        ┌─────────────────────────┐
        │      SAFETY MCU         │
        │                         │
        │ watchdog                │
        │ current                 │
        │ encoder/fault           │
        │ temperature             │
        │ E-stop                  │
        │ motor enable            │
        └─────────────────────────┘
```

And critically:

```text
Orin = NOT required
```

The physical-control stack must be able to run by itself. That is directly consistent with the frozen architecture.

---

# 2. We should NOT start with the whole humanoid

Our first milestone is:

> **One actuator, one joint, one complete control loop.**

Then:

```text
1 actuator
   ↓
1 joint
   ↓
2–3 joints
   ↓
one limb
   ↓
whole robot
```

This is much easier to debug.

---

# 3. Phase 1 breakdown

We'll divide Phase 1 into eight sub-phases.

### Phase 1A — Development environment

Build the software foundation:

```text
RT Core
Driver abstraction
Controller
State representation
Safety state machine
Logging
Simulation
Tests
```

### Phase 1B — Actuator abstraction

We define a common interface for:

```text
position
velocity
current
torque
temperature
fault state
enable/disable
```

The RT Core should not care whether the physical actuator uses CAN-FD, EtherCAT or another bus.

The VAYN document explicitly leaves the bus choice open and mentions EtherCAT/CAN-FD/deterministic Ethernet as candidates.

---

### Phase 1C — Single-joint control

First controller:

```text
desired position
      ↓
position error
      ↓
velocity error
      ↓
impedance controller
      ↓
torque/current command
      ↓
motor driver
```

The basic impedance equation from VAYN-6.2 is:

```text
τ = Kp(qd - q)
  + Kd(q̇d - q̇)
  + τff
```

where:

```text
q       = actual position
qd      = desired position
q̇       = actual velocity
q̇d      = desired velocity
Kp      = stiffness
Kd      = damping
τff     = feed-forward torque
```

The document also requires torque/current, velocity, thermal and saturation limits around this controller.

---

# 4. The RT control loop

This will eventually be the heart of VAYN.

A simplified loop is:

```text
while robot_enabled:

    read_sensors()

    estimate_state()

    validate_sensor_state()

    receive_latest_reference()

    validate_reference()

    generate_or_update_trajectory()

    calculate_control()

    apply_limits()

    send_motor_commands()

    publish_state()

    check_deadlines()
```

Conceptually:

```text
                 ┌──────────────┐
                 │   Sensors    │
                 └──────┬───────┘
                        ↓
                ┌──────────────┐
                │State Estimator│
                └──────┬───────┘
                       ↓
                ┌──────────────┐
                │   Reference  │
                └──────┬───────┘
                       ↓
                ┌──────────────┐
                │  Controller  │
                └──────┬───────┘
                       ↓
                ┌──────────────┐
                │ Safety Limits│
                └──────┬───────┘
                       ↓
                ┌──────────────┐
                │Motor Driver  │
                └──────┬───────┘
                       ↓
                    Actuator
                       │
                       └──→ sensors
```

The important difference from a normal hobby robot is that **the controller has ownership of the complete loop**, rather than simply sending motor commands from a high-level program.

---

# 5. Our software architecture

I recommend we write the RT Motion Core in **C++**, not Python.

Python can still be used for:

- simulation
    
- plotting
    
- dataset analysis
    
- controller tuning
    
- tests
    
- offline tools
    

But the actual RT loop should be C/C++.

A clean project could start as:

```text
VAYN/
│
├── rt_core/
│   ├── main.cpp
│   ├── rt_loop.cpp
│   ├── rt_loop.hpp
│   │
│   ├── state/
│   │   ├── state.cpp
│   │   ├── state.hpp
│   │   ├── estimator.cpp
│   │   └── estimator.hpp
│   │
│   ├── control/
│   │   ├── impedance.cpp
│   │   ├── impedance.hpp
│   │   ├── trajectory.cpp
│   │   └── trajectory.hpp
│   │
│   ├── safety/
│   │   ├── validator.cpp
│   │   ├── validator.hpp
│   │   ├── limits.cpp
│   │   └── limits.hpp
│   │
│   ├── actuator/
│   │   ├── actuator.hpp
│   │   ├── actuator_state.hpp
│   │   └── actuator_command.hpp
│   │
│   └── timing/
│       ├── clock.hpp
│       └── timing.hpp
│
├── safety_mcu/
│
├── drivers/
│   ├── simulated_actuator/
│   └── real_actuator/
│
├── simulation/
│   ├── actuator_sim.py
│   └── plots.py
│
├── tests/
│   ├── controller_tests/
│   ├── safety_tests/
│   └── timing_tests/
│
├── config/
│   └── joint.yaml
│
└── docs/
```

This gives us one very important property:

```text
RT Core
   ↓
Actuatwe aor Interface
   ↓
     ┌───────────────┐
     │               │
Simulation       Real Driver
```

So we can test almost everything **before connecting the motor**.

---

# 6. First interface: the actuator

We'll define the actuator from the RT Core's point of view.

Something conceptually like:

```cpp
struct ActuatorState
{
    double position;
    double velocity;
    double torque;
    double current;
    double temperature;

    bool enabled;
    bool fault;
};

struct ActuatorCommand
{
    double torque;
    bool enable;
};
```

The RT Core then operates on this abstraction.

That means later:

```text
simulation actuator
```

and:

```text
real motor driver
```

can use the same controller.

---

# 7. State representation

For our first single-joint system:

```cpp
struct JointState
{
    double q;       // position
    double q_dot;   // velocity

    double torque;
    double current;

    double temperature;

    bool valid;
};
```

Later this becomes:

```text
S_phys
```

which in full VAYN includes joint states, base state, contacts, COM, torque estimates, uncertainty, etc.

---

# 8. Safety comes BEFORE the controller

This is something I want to enforce throughout the implementation.

We shouldn't do:

```text
controller
   ↓
motor
```

We do:

```text
controller
   ↓
SAFETY VALIDATOR
   ↓
motor
```

For a single joint:

```text
position limit
velocity limit
torque limit
current limit
temperature limit
command timeout
sensor validity
fault state
```

Example:

```cpp
if (position > max_position)
    torque = 0;

if (temperature > max_temperature)
    disable();

if (command_expired)
    enter_fallback();

if (!encoder_valid)
    disable();
```

This implements the VAYN principle that learned or high-level commands never bypass physical limits.

---

# 9. Command freshness

Even in Phase 1, I want us to implement:

```text
timestamp
sequence_id
valid_until
```

from the beginning.

So later the Orin can plug into the system without changing the control architecture.

Example:

```cpp
struct MotionReference
{
    uint64_t sequence_id;

    double desired_position;
    double desired_velocity;

    uint64_t timestamp;
    uint64_t valid_until;
};
```

If:

```text
now > valid_until
```

the command is stale.

Then:

```text
stale command
    ↓
reject
    ↓
fallback
```

This is one of the architectural rules explicitly frozen in VAYN-6.2.

---

# 10. First controller we build

We should **not** start with MPC, whole-body control or RL.

For one joint:

### Position impedance control

```text
error = desired_position - actual_position

velocity_error =
    desired_velocity - actual_velocity

τ =
    Kp * error
    +
    Kd * velocity_error
    +
    feedforward
```

Then:

```text
τ
 ↓
torque limit
 ↓
current limit
 ↓
driver
```

This gives us a very understandable baseline.

---

# 11. First simulation

Before touching the motor, we'll create a simple simulated actuator.

Something like:

```text
desired position = 1 rad

             ↓

controller

             ↓

simulated motor dynamics

             ↓

position / velocity

             ↓

feedback
```

Then test:

```text
step response
position tracking
overshoot
settling time
oscillation
disturbance
command timeout
sensor noise
```

For example:

```text
0 rad
  │
  │
  │             ┌──────── desired
  │             │
  │             │
  └─────────────┴──────────────
```

We want the actual position to approach the target smoothly without instability.

---

# 12. Then add a simulated disturbance

Suppose:

```text
robot wants:
q = 1.0 rad
```

At time:

```text
t = 2 seconds
```

we apply an external disturbance.

The controller should bring the joint back toward its desired state.

This is the first primitive version of **physical robustness**.

---

# 13. Then test failure

We intentionally break things.

### Encoder failure

```text
encoder invalid
    ↓
controller rejects state
    ↓
safe mode
```

### Command timeout

```text
command expires
    ↓
fallback
```

### Over-temperature

```text
temperature > limit
    ↓
constraint / disable
```

### Communication failure

```text
driver heartbeat lost
    ↓
safe actuator response
```

### RT loop slowdown

```text
deadline missed
    ↓
fault/event logged
```

These tests are important because VAYN's development process explicitly requires sensor dropout, communication loss, stale actions, encoder faults, current anomalies, E-stop, etc. before autonomous operation.

---

# 14. Safety MCU

After our simulated RT controller works, we build the **independent safety layer**.

It doesn't need to run the entire robot.

Its job is approximately:

```text
                SAFETY MCU

            RT heartbeat
                 │
         Motor driver state
                 │
            Motor current
                 │
            Temperature
                 │
             Encoder
                 │
              E-stop
                 ↓
          ┌─────────────┐
          │   SAFETY    │
          │   STATE     │
          └──────┬──────┘
                 │
          ┌──────┴───────┐
          │              │
        NORMAL         FAULT
          │              │
      enable        constrain/disable
```

The architecture explicitly separates the Safety MCU from the RT Motion Core.

---

# 15. What we should NOT do yet

For Phase 1, I don't want us touching:

```text
VLM
GR00T
Flow Matching
A2A
RTC
world model
LNN
tactile ML
visual encoder
event manager
```

Those are later.

Right now the robot has one job:

> **Move one joint safely and predictably under feedback control.**

---

# 16. Phase 1 milestones

We'll use these actual milestones:

|Milestone|Goal|
|---|---|
|**P1.0**|Software project + simulator|
|**P1.1**|Single-joint state model|
|**P1.2**|Impedance controller|
|**P1.3**|Safety validator|
|**P1.4**|Fixed-rate RT loop|
|**P1.5**|Simulated actuator|
|**P1.6**|Failure injection|
|**P1.7**|Real motor driver interface|
|**P1.8**|Real single actuator|
|**P1.9**|IMU + multi-joint state|
|**P1.10**|Multi-joint stabilization|
|**P1.11**|Independent Safety MCU|
|**P1.12**|Phase 1 complete|

---

# 17. The first thing we'll actually code

I recommend we start with **P1.0 + P1.1**:

```text
VAYN-6.2 Phase 1
        │
        ▼
Create repository
        │
        ▼
C++ RT-Core skeleton
        │
        ▼
JointState
ActuatorCommand
MotionReference
SafetyState
        │
        ▼
Simple simulated actuator
        │
        ▼
Run first control loop
```

Then we'll progressively replace the simulated pieces with real hardware.

### One important point

I don't want to choose the physical motor driver, RT computer, or actuator bus blindly. Your VAYN-6.2 document intentionally leaves those as engineering decisions, and the correct choice depends on the actual actuator electronics.

So **software P1.0 can begin immediately**, while the physical P1.7/P1.8 interface will be mapped to your actual motor/driver/encoder hardware.

## Our first build target

We'll build this first:

```text
           Motion Reference
                 │
                 ▼
        ┌─────────────────┐
        │  Safety Check   │
        └────────┬────────┘
                 ▼
        ┌─────────────────┐
        │ Impedance Ctrl  │
        └────────┬────────┘
                 ▼
        ┌─────────────────┐
        │ Simulated Motor │
        └────────┬────────┘
                 ▼
           Joint State
                 │
                 └──────────────► feedback
```

**Next, we should write the actual P1.0 codebase and a one-joint simulator in C++ + Python so you can run it on your machine and see the controller working before we connect a real actuator.**