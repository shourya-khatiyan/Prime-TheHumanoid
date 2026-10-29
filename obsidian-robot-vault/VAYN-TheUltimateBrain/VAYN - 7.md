# VAYN-7 — Versatile Arbitrated Embodied Nervous-System

## Real-Time, Predictive and Contact-Aware Humanoid Robot Intelligence Architecture

**Status:** Draft / Research Proposal  
**Predecessor:** VAYN-6.2  
**Purpose:** Research and experimentation  
**Validation Status:** Not yet experimentally validated  
**Hardware Target:** Edge humanoid platform; initial reference target is NVIDIA Jetson Orin NX 16 GB with an independent RT Motion Core and Safety MCU

---

# 1. Executive Summary

VAYN-7 is a proposed evolution of the VAYN-6.2 humanoid robot intelligence architecture.

VAYN-6.2 established the fundamental system structure:

1. **Think** — high-level perception, reasoning and task planning.
    
2. **Predict** — prediction of future physical state and compensation for sensing/control delay.
    
3. **Move** — action generation and execution.
    
4. **Survive** — deterministic stabilization, safety validation and hardware-level protection.
    

VAYN-7 does not replace this structure. Instead, it investigates methods for reducing temporal discontinuities and improving physical interaction.

The primary research areas are:

- asynchronous action generation,
    
- action-history-conditioned flow generation,
    
- motion-aware visual prediction,
    
- delay-conditioned physical prediction,
    
- high-frequency tactile processing,
    
- contact-state estimation,
    
- contact-aware control.
    

The central idea is to make the robot's intelligence more aware of **when information was captured, when an action was generated, when it was actually committed, and when it physically affected the robot**.

However, VAYN-7 is a **research draft**, not a claim that these techniques are automatically superior to VAYN-6.2.

Every proposed component must be validated against a baseline.

---

# 2. Design Philosophy

VAYN-7 follows six principles.

## 2.1 Measure before optimizing

The system must first determine where latency actually occurs.

A reduction in policy inference time is not useful if perception contributes most of the end-to-end delay.

Therefore:

> No major temporal optimization is considered mandatory until the corresponding latency bottleneck has been measured.

---

## 2.2 Physical time is a first-class variable

Every sensor observation and control command should have an explicit temporal identity.

The system distinguishes:

```text
capture time
arrival time
processing time
generation time
commit time
execution time
```

This prevents the architecture from treating a 50 ms old observation as if it represented the current physical state.

---

## 2.3 Intelligence cannot bypass deterministic control

The VAYN-6.2 safety philosophy remains unchanged.

Learned models may propose:

- actions,
    
- trajectories,
    
- residual corrections,
    
- predictions,
    
- contact estimates.
    

They cannot directly bypass:

- joint limits,
    
- torque limits,
    
- velocity limits,
    
- acceleration limits,
    
- actuator constraints,
    
- safety state transitions.
    

---

## 2.4 Experimental components remain replaceable

RTC, A2A, learned prediction, tactile learning and contact-aware MPC are research components.

They must be independently replaceable.

The architecture therefore maintains explicit interfaces between:

```text
perception
prediction
action generation
RT control
safety
```

---

## 2.5 Capability matters more than latency alone

A faster model is not automatically better.

Every optimization should be evaluated using:

```text
task success
+
physical stability
+
reaction time
+
trajectory quality
+
compute
+
power
```

rather than latency alone.

---

## 2.6 VAYN-7 is not assumed to beat VAYN-6.2

The architecture contains hypotheses.

A component should be removed if experiments show that:

```text
benefit < complexity + compute + failure risk
```

---

# 3. System Architecture

The four primary responsibilities remain:

```text
┌──────────────────────────────────────────────┐
│                    THINK                     │
│       VLM / reasoning / task planning       │
└──────────────────────┬───────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────┐
│                   PREDICT                    │
│   physical prediction / temporal alignment   │
└──────────────────────┬───────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────┐
│                    MOVE                      │
│       policy / RTC / A2A / references       │
└──────────────────────┬───────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────┐
│              RT MOTION CORE                  │
│ estimator / stabilization / validation      │
│       impedance / whole-body control         │
└──────────────────────┬───────────────────────┘
                       │
                       ▼
┌──────────────────────────────────────────────┐
│                  ACTUATORS                   │
└──────────────────────────────────────────────┘

              Independent Safety MCU
                       │
          ┌────────────┴────────────┐
          │                         │
     independent sensing       hardware limits
```

The Safety MCU remains independent from the AI compute system.

---

# 4. Hardware Responsibilities

## 4.1 High-level compute

The Orin-class compute platform handles:

- visual perception,
    
- VLM reasoning,
    
- world-state processing,
    
- action policy inference,
    
- optional RTC,
    
- optional A2A,
    
- learned prediction,
    
- learned reflex components.
    

---

## 4.2 RT Motion Core

The RT Motion Core handles:

- physical state estimation,
    
- stabilization,
    
- command arbitration,
    
- deterministic validation,
    
- impedance control,
    
- whole-body control,
    
- actuator command generation,
    
- following-error monitoring,
    
- execution acknowledgement.
    

The RT Motion Core remains operational independently of the Orin.

---

## 4.3 Safety MCU

The Safety MCU provides an independent hardware-level safety layer.

It should have independent access to relevant signals such as:

- joint position,
    
- motor current,
    
- actuator status,
    
- emergency-stop input,
    
- power state,
    
- hardware faults.
    

The MCU can constrain or stop operation but cannot be overridden by learned software.

---

# 5. Temporal Architecture

VAYN-7 introduces explicit temporal contracts.

A command should contain information such as:

```text
command_id
timestamp
source_timestamp
valid_until
reference
mode
priority
```

A sensor observation should contain:

```text
sensor_id
sequence_id
capture_timestamp
arrival_timestamp
processing_timestamp
```

The system should never assume that:

```text
arrival time = capture time
```

---

# 6. Latency Model

The total control latency is represented as:

```text
L_total =
L_capture
+ L_sensor
+ L_transport
+ L_ISP
+ L_visual
+ L_state
+ L_policy
+ L_Orin_RT
+ L_RT
+ L_actuation
```

Not every path uses every component.

For example, a tactile reflex path may bypass visual processing.

The system should record:

- p50,
    
- p90,
    
- p95,
    
- p99,
    
- maximum observed latency,
    
- jitter,
    
- deadline misses.
    

Average latency alone is insufficient.

---

# 7. Executed Action as the Ground Truth

One major change in VAYN-7 is the distinction between:

```text
planned action
```

and:

```text
executed reference
```

The policy may generate:

```text
A_policy
```

but the RT system may modify it because of:

- stabilization,
    
- reflex residuals,
    
- safety limits,
    
- actuator constraints,
    
- trajectory clipping.
    

Therefore:

```text
A_policy ≠ A_executed
```

in general.

A2A and other history-dependent policies should preferentially use the **executed reference history** rather than assuming that the original policy command was physically executed.

---

# 8. ACTION_ACK_V1

The RT Motion Core should provide an acknowledgement interface.

Example:

```text
ACTION_ACK_V1

command_id
generated_at
received_at
committed_at

accepted

committed_reference

residual_applied
safety_clipped

controller_mode

valid_until
```

This provides feedback about what the physical control system actually accepted.

It also enables replay and debugging.

---

# 9. Action Buffer

VAYN-7 uses an explicit future-reference buffer.

```text
Past                Current                  Future

───────┬────────────────────┬────────────────────
       │                    │
       │ committed prefix   │ replannable region
       │                    │
       ▼                    ▼
    immutable            replaceable
```

The committed portion cannot be arbitrarily rewritten.

The future portion can be replanned.

The buffer should account for:

- computation delay,
    
- communication jitter,
    
- actuator latency,
    
- controller requirements.
    

---

# 10. Prediction Horizon vs Execution Horizon

These are deliberately separated.

## Prediction horizon

How far into the future the system predicts:

```text
H_prediction
```

## Execution/commit horizon

How much future behavior becomes committed:

```text
H_execution
```

They do not have to be equal.

For example:

```text
H_prediction = 150 ms
H_execution = 25 ms
```

could be valid.

The actual values must be experimentally determined.

---

# 11. Action Generation

The action policy remains responsible for generating physical references.

Possible outputs include:

### Locomotion

```text
base velocity
footstep targets
body orientation
COM reference
```

### Manipulation

```text
end-effector pose
joint targets
gripper target
grip force
trajectory
```

The RT Motion Core interprets these references according to the skill-specific interface.

---

# 12. Real-Time Chunking

## 12.1 Motivation

Traditional chunked action generation can create a delay between:

```text
current trajectory
```

and:

```text
next generated trajectory
```

Even when chunks are blended, computation and execution remain coupled.

VAYN-7 therefore investigates an asynchronous execution strategy inspired by Real-Time Chunking.

---

## 12.2 Principle

The policy maintains a future action trajectory.

A portion of the trajectory becomes committed while another portion is regenerated.

Conceptually:

```text
CURRENT TIME
     │
     ▼
┌───────────────┬─────────────────────────┐
│ frozen/commit │ continuously regenerated│
│    prefix     │      future region     │
└───────────────┴─────────────────────────┘
```

Generation and execution therefore overlap.

---

## 12.3 Important limitation

RTC does **not** mean:

```text
zero latency
```

It means that computation and execution are overlapped to reduce the effective waiting period.

Actual latency must still be measured.

---

# 13. Trajectory Continuity

VAYN-7 should maintain continuity across regenerated trajectories.

Relevant objectives may include:

```text
position continuity
velocity continuity
acceleration continuity
jerk minimization
```

The blending system should prevent discontinuities at trajectory replacement points.

However:

> mathematical smoothness does not guarantee physical compliance.

Physical compliance remains the responsibility of the RT controller and actuator system.

---

# 14. Action-to-Action Flow Initialization

## 14.1 Concept

Standard generative action policies may begin from a noise distribution.

A2A-style generation instead uses historical action information to initialize generation.

Conceptually:

```text
previous executed action history
             ↓
       initialization
             ↓
       flow generation
             ↓
       new trajectory
```

The objective is to reduce the computational distance between the current action and the required next action.

---

## 14.2 Conditional use

A2A should not always rely blindly on history.

Reset/re-anchoring conditions should include events such as:

- major visual change,
    
- unexpected contact,
    
- action-history corruption,
    
- target movement,
    
- large prediction error,
    
- controller intervention,
    
- recovery transition.
    

---

# 15. A2A Risk: Causal Confusion

Action-history conditioning creates a possible failure mode:

```text
previous action
        ↓
model repeats previous action
        ↓
current observation underused
```

Therefore A2A must be tested for observation sensitivity.

Training experiments may include:

- history dropout,
    
- corrupted action histories,
    
- on-policy data collection,
    
- DAgger-style corrections,
    
- periodic re-anchoring.
    

---

# 16. A2A Evaluation

Compare:

```text
A. noise-initialized flow
B. A2A initialization
C. conventional ACT-style policy
```

under identical conditions.

Measure:

- inference latency,
    
- task success,
    
- reaction time,
    
- trajectory continuity,
    
- observation sensitivity,
    
- recovery after target movement.
    

A critical test is:

```text
robot starts reaching for object
          ↓
object moves unexpectedly
          ↓
measure response
```

A2A must not simply continue reproducing the old action trajectory.

---

# 17. Visual Processing

VAYN-6.2 allows visual features to be cached at lower frequencies than the action policy.

VAYN-7 investigates whether stale visual representations can be compensated without increasing full vision-model inference frequency.

---

# 18. Visual Age

Visual information should be treated as:

```text
feature + capture_timestamp + age
```

rather than simply:

```text
feature
```

Different skills may have different tolerances.

Example:

```text
walking:
larger visual age may be acceptable

fine manipulation:
smaller visual age may be required
```

Therefore a single global visual TTL is not assumed.

---

# 19. Motion-Aware Visual Prediction

Instead of blindly reusing an old visual feature map, VAYN-7 investigates predicting what the observation should look like at execution time.

Possible inputs:

```text
previous visual features
+
camera pose
+
joint state
+
IMU
+
motion history
```

The predictor may produce:

```text
predicted current visual representation
```

This is preferable to treating simple rigid image warping as universally exact.

---

# 20. Visual Feature Transport

Geometric motion compensation may still be useful.

For known camera motion:

```text
camera motion
      ↓
geometric transformation
      ↓
feature transport
```

But geometric transport cannot correctly reconstruct:

- newly visible regions,
    
- occlusions,
    
- independently moving objects,
    
- depth ambiguities.
    

Therefore learned prediction may be required in difficult scenes.

---

# 21. Visual Prediction Baselines

Evaluate:

```text
A. stale features
B. geometric transport
C. motion-aware learned prediction
```

Measure:

- feature prediction error,
    
- object localization,
    
- grasp error,
    
- task success,
    
- compute cost,
    
- latency.
    

A learned predictor should only be retained if it provides measurable benefit.

---

# 22. Physical State Prediction

The predictive system estimates future physical state:

```text
S(t)
+
action
+
delay
        ↓
predicted S(t + Δt)
```

The prediction system should combine:

```text
kinematic / physics prediction
+
learned residual
```

rather than assuming that a neural predictor must replace the physical model.

---

# 23. Delay-Conditioned Prediction

Instead of assuming a fixed latency:

```text
predict 33 ms
```

the predictor should accept a delay estimate:

```text
Δt = estimated execution delay
```

and potentially its uncertainty:

```text
Δt ± uncertainty
```

The predicted state therefore becomes:

```text
S_predicted(Δt)
```

rather than a fixed-time prediction.

---

# 24. Continuous-Time Dynamics

A continuous-time model such as a Neural ODE/CDE may eventually be evaluated.

Conceptually:

```text
dx/dt = f(x,u,t)
```

The model can be queried for:

```text
x(t + Δt)
```

rather than being restricted to a fixed discrete step.

However, continuous-time modeling is an **experimental implementation**, not a requirement.

It must beat simpler baselines such as:

- kinematic extrapolation,
    
- physics rollout,
    
- learned residual dynamics.
    

---

# 25. Prediction Under Contact

Contact events create discontinuities.

Examples:

- foot-ground contact,
    
- hand-object contact,
    
- collision,
    
- slip,
    
- sudden impact.
    

Therefore prediction should represent contact state and uncertainty.

A useful representation may include:

```text
predicted state
+
prediction uncertainty
+
contact probability
```

The system should not assume that a smooth learned trajectory remains valid through arbitrary contact transitions.

---

# 26. Tactile Processing

VAYN-7 expands tactile processing from simple force measurements toward structured contact estimation.

The tactile pipeline is:

```text
Tactile sensors
      ↓
DSP / signal processing
      ↓
force + shear + vibration features
      ↓
contact estimator
      ↓
contact state
      ↓
RT control / reflex
```

---

# 27. Tactile Signal Processing

Possible features include:

- normal force,
    
- shear force,
    
- pressure distribution,
    
- contact centroid,
    
- vibration energy,
    
- spectral features,
    
- temporal derivatives.
    

FFT may be used as a feature-extraction technique.

It is **not** assumed that a universal frequency band defines slip.

---

# 28. Slip Detection

VAYN-7 should output a probabilistic contact state rather than a simplistic binary trigger.

Example:

```text
CONTACT_STATE_V1

contact_probability
normal_force
shear_force
contact_centroid

slip_probability
slip_direction
slip_velocity

signal_quality
confidence

timestamp
```

The frequency characteristics of slip must be measured for the actual sensor, actuator and mechanical system.

---

# 29. Tactile Ground Truth

Slip detection requires real-world labelled data.

A test rig should provide:

```text
object
+
controlled grip
+
controlled pulling force
+
tactile sensor
+
ground-truth object movement
```

Ground truth may come from:

- optical tracking,
    
- motion capture,
    
- instrumented force measurement.
    

Testing should cover:

- different materials,
    
- different grip forces,
    
- different masses,
    
- different surface textures,
    
- actuator vibration,
    
- different temperatures where relevant.
    

---

# 30. Actuator Vibration Characterization

The robot itself produces vibration.

Possible sources include:

- motors,
    
- gearboxes,
    
- harmonic/cycloidal transmissions,
    
- structural resonances,
    
- control-loop oscillations.
    

Therefore tactile frequency features must be measured during:

```text
no motion
low-speed motion
high-speed motion
loaded motion
different actuator configurations
```

Otherwise mechanical vibration could be incorrectly classified as slip.

---

# 31. Contact Estimator

The tactile estimator should infer:

```text
contact
force
shear
slip
confidence
```

rather than simply triggering a reflex.

This allows the RT controller to use tactile information according to physical context.

---

# 32. Contact-Aware Control

VAYN-7 proposes investigating contact-aware MPC.

Conceptually:

```text
tactile state
     +
physical state
     +
object/contact model
          ↓
    contact-aware MPC
          ↓
desired impedance / trajectory
```

The MPC may adapt:

- stiffness,
    
- damping,
    
- contact force,
    
- end-effector motion,
    
- foot placement.
    

---

# 33. Contact MPC Is Experimental

Contact-aware MPC is computationally more expensive than a simple impedance correction.

Therefore evaluate:

```text
A. standard impedance
B. impedance + tactile correction
C. contact controller
D. contact-aware MPC
```

Only retain the complexity if the improvement is measurable.

---

# 34. Reflex Layer

The reflex system remains subordinate to the RT Motion Core.

The learned reflex does not directly command motors.

Instead:

```text
sensor state
     ↓
reflex model
     ↓
bounded residual
     ↓
RT command arbiter
     ↓
validator
     ↓
controller
```

The RT core determines the final allowable command.

---

# 35. Reflex Authority

Reflex residuals must have explicit bounds:

```text
|Δq| ≤ limit
|Δv| ≤ limit
|Δτ| ≤ limit
```

The limits are determined experimentally.

The reflex must never be allowed to destabilize the primary locomotion or manipulation controller.

---

# 36. Locomotion and Manipulation Are Different

RTC and A2A are primarily investigated for continuous manipulation trajectories.

Walking is different because it contains discrete gait events.

For locomotion, VAYN-7 should investigate:

- gait-phase-aware reference updates,
    
- latency randomization during training,
    
- RT stabilization,
    
- footstep timing,
    
- disturbance recovery.
    

RTC/A2A should not automatically be assumed to improve locomotion.

---

# 37. Locomotion Safety Principle

The RT Motion Core always owns physical stabilization.

The learned locomotion policy supplies references.

Conceptually:

```text
Locomotion Policy
       ↓
reference
       ↓
RT Stabilization
       ↓
whole-body control
       ↓
actuators
```

If experimentation demonstrates that a classical stabilizer cannot achieve the required agility, a small real-time RL stabilizer may be evaluated on the RT compute platform.

It must not make survival dependent on the Orin.

---

# 38. Latency-Compensated Control

The RT controller should use known transport and actuator delays.

The objective is:

```text
command generated
       ↓
expected physical execution time
       ↓
state prediction
       ↓
corrected control
```

Avoid unnecessarily converting deterministic hardware delay into a learned prediction problem.

---

# 39. Delay Measurement

The system should measure:

```text
capture delay
processing delay
transport delay
queueing delay
policy delay
RT delay
actuator delay
```

and maintain statistics for each.

Important values include:

```text
p50
p95
p99
maximum
jitter
```

---

# 40. Delay Randomization During Training

Policies should be exposed to realistic timing variation.

Training may randomize:

```text
sensor delay
visual delay
policy delay
communication delay
actuation delay
```

The distribution should be derived from real measured hardware behaviour rather than arbitrary numbers.

This improves robustness to deployment timing variation.

---

# 41. Execution Monitor

The RT validator should continuously monitor:

```text
reference
vs
measured state
```

and calculate following error.

For example:

```text
e(t) = x_reference(t) - x_measured(t)
```

Large errors can indicate:

- actuator saturation,
    
- unexpected contact,
    
- controller failure,
    
- communication problems,
    
- prediction failure.
    

The deterministic following-error check belongs in the RT system.

---

# 42. Prediction Disagreement

The predictive model may provide a soft discrepancy signal:

```text
prediction
vs
observed state
```

Large disagreement may indicate:

- contact,
    
- slip,
    
- unexpected object movement,
    
- sensor failure,
    
- model mismatch.
    

This signal should not independently trigger unsafe learned behaviour.

It can instead:

- trigger logging,
    
- request replanning,
    
- increase safety margins,
    
- initiate a fallback state.
    

---

# 43. Event Manager

VAYN-6.2's semantic event manager remains.

VAYN-7 extends it with temporal information.

Events may include:

```text
target moved
contact detected
slip detected
prediction disagreement
following error exceeded
sensor stale
action buffer underrun
controller intervention
```

Each event has:

```text
timestamp
severity
confidence
source
```

---

# 44. Event-Driven Compute

The event manager may trigger additional computation only when necessary.

For example:

```text
normal operation
      ↓
low compute mode

unexpected contact
      ↓
high-frequency perception/control

stable state
      ↓
return to normal
```

The system should retain a minimum periodic processing rate for safety-critical signals.

---

# 45. Visual Cache and Skill-Specific TTL

Each skill should define its own freshness requirements.

Example concept:

```text
WALK:
visual TTL = relatively relaxed

REACH:
moderate TTL

FINE GRASP:
strict TTL
```

The values must be experimentally determined.

A single universal TTL is not assumed.

---

# 46. Data Architecture

VAYN-7 requires richer logging than VAYN-6.2.

For each trajectory record:

```text
sensor timestamps
camera frames
IMU
joint states
tactile data
policy outputs
executed references
ACTION_ACK
RT modifications
safety clipping
prediction
prediction error
events
latency statistics
```

The system must preserve synchronization information.

---

# 47. Replay System

Every important control episode should be replayable.

A replay should reproduce:

```text
sensor sequence
timestamps
policy inputs
policy outputs
RT modifications
executed commands
```

This allows:

- debugging,
    
- regression testing,
    
- model comparison,
    
- ablation studies.
    

---

# 48. Experimental Baselines

Every VAYN-7 component requires a baseline.

## Action generation

```text
synchronous flow
vs
RTC
```

## Flow initialization

```text
noise initialization
vs
A2A
```

## Vision

```text
stale features
vs
geometric transport
vs
learned prediction
```

## Dynamics

```text
kinematic extrapolation
vs
learned residual
vs
continuous-time model
```

## Tactile

```text
force threshold
vs
signal features
vs
learned contact estimator
```

## Control

```text
impedance
vs
tactile-assisted impedance
vs
contact MPC
```

---

# 49. Primary VAYN-7 Hypotheses

### H1 — Asynchronous action generation

Asynchronous trajectory generation can reduce effective action-generation delay and improve trajectory continuity compared with synchronous chunk generation.

### H2 — Action-history initialization

A2A initialization can reduce action-generation computation while preserving responsiveness to new observations.

### H3 — Motion-aware visual prediction

Execution-time visual prediction can reduce the performance degradation caused by stale visual features.

### H4 — Delay-conditioned prediction

Providing actual execution delay to the physical predictor can improve future-state prediction compared with a fixed prediction horizon.

### H5 — Tactile contact estimation

Structured tactile features can improve contact/slip detection compared with force thresholds alone.

### H6 — Contact-aware control

Tactile-informed control can improve manipulation robustness during uncertain contact.

None of these hypotheses are assumed to be true before experiments.

---

# 50. Critical Failure Modes

VAYN-7 must explicitly test:

## 50.1 A2A action repetition

The model continues the previous trajectory despite an environmental change.

## 50.2 Visual prediction hallucination

The predicted feature representation incorrectly invents or preserves an object.

## 50.3 Tactile false positive

Actuator vibration is interpreted as slip.

## 50.4 Tactile false negative

Actual slip is not detected.

## 50.5 Prediction divergence

Learned dynamics diverge during contact.

## 50.6 Buffer underrun

The action generator fails to provide a new reference before the committed trajectory expires.

## 50.7 Controller conflict

Reflex, policy and stabilization commands interact destructively.

## 50.8 Compute contention

Concurrent perception and policy workloads increase control latency.

## 50.9 Thermal degradation

Sustained compute causes reduced performance or thermal throttling.

---

# 51. Physical Conditions That Must Be Considered

VAYN-7 must be tested under:

- rapid head motion,
    
- torso rotation,
    
- arm motion,
    
- changing lighting,
    
- object occlusion,
    
- moving objects,
    
- unexpected contact,
    
- varying friction,
    
- actuator vibration,
    
- gearbox backlash,
    
- actuator saturation,
    
- sensor noise,
    
- sensor dropout,
    
- communication jitter,
    
- thermal variation,
    
- battery-voltage variation,
    
- external disturbances.
    

Simulation alone is insufficient for validating all of these effects.

---

# 52. Performance Metrics

VAYN-7 should measure:

## Timing

```text
p50 latency
p95 latency
p99 latency
jitter
deadline misses
```

## Motion

```text
trajectory error
velocity discontinuity
acceleration
jerk
```

## Manipulation

```text
grasp success
object displacement
slip rate
force error
```

## Locomotion

```text
fall rate
foot-placement error
COM error
disturbance recovery
energy consumption
```

## Compute

```text
GPU utilization
CPU utilization
memory
bandwidth
temperature
power
```

## Safety

```text
limit violations
validator interventions
fallback events
controller saturation
communication failures
```

---

# 53. Capability per Compute Cost

A useful comparison metric is:

```text
performance improvement
────────────────────────
additional compute cost
```

A more capable model is not automatically better if it consumes excessive compute or increases latency.

---

# 54. Capability per Watt

For an edge humanoid, also evaluate:

```text
task performance
─────────────────
power consumption
```

using sustained power rather than short-duration peak measurements.

---

# 55. VAYN-7 Measurement-First Development Process

The proposed development order is:

```text
VAYN-6.2 baseline
       ↓
instrumentation
       ↓
full latency measurement
       ↓
compute contention measurement
       ↓
visual-age measurement
       ↓
action-history measurement
       ↓
tactile characterization
       ↓
identify bottlenecks
       ↓
select VAYN-7 experiments
       ↓
ablation
       ↓
retain only successful components
```

---

# 56. Gate 0 — Instrumentation

Before modifying the architecture:

- synchronized timestamps,
    
- ACTION_ACK,
    
- executed-action logging,
    
- latency logging,
    
- sensor capture timestamps,
    
- RT following-error monitoring,
    
- replay infrastructure.
    

---

# 57. Gate 1 — Timing Characterization

Measure the complete:

```text
sensor → computation → RT → actuator
```

pipeline.

Produce:

```text
p50
p95
p99
maximum
```

for every major stage.

---

# 58. Gate 2 — Action Generation

If policy inference or chunk-generation delay is significant:

```text
baseline
vs
RTC
vs
A2A
```

is evaluated.

If policy latency is already negligible relative to perception or actuation:

> RTC/A2A should not be prioritized merely because they are newer algorithms.

---

# 59. Gate 3 — Visual Prediction

If visual age significantly affects task performance:

```text
stale
→ geometric transport
→ learned prediction
```

is evaluated.

---

# 60. Gate 4 — Physical Prediction

Evaluate:

```text
kinematic
→ physics
→ learned residual
→ continuous-time
```

only if prediction error is a measured problem.

---

# 61. Gate 5 — Tactile Interaction

Construct a real tactile dataset.

Evaluate:

```text
force baseline
→ signal processing
→ contact estimator
→ tactile-assisted controller
→ contact MPC
```

---

# 62. Gate 6 — Integrated System

Only after individual components demonstrate measurable improvements should they be combined.

This prevents several individually promising components from creating an integrated system that is:

- slower,
    
- harder to debug,
    
- less stable,
    
- more power hungry.
    

---

# 63. VAYN-7 Architecture Status

|Component|Status|
|---|---|
|Four-part architecture|Frozen from VAYN-6.2|
|RT Motion Core|Frozen|
|Independent Safety MCU|Frozen|
|Timestamp contracts|Required|
|ACTION_ACK|Required|
|Executed-action history|Required|
|Action buffer|Required|
|RTC|Experimental|
|A2A|Experimental|
|Motion-aware visual prediction|Experimental|
|Delay-conditioned prediction|Experimental|
|Continuous-time dynamics|Experimental|
|Tactile DSP|Experimental/adoptable baseline|
|Contact estimator|Experimental|
|Contact-aware MPC|Experimental|
|Event manager|Retained|
|Following-error monitor|Required|
|Replay infrastructure|Required|

---

# 64. What VAYN-7 Does Not Claim

VAYN-7 does **not** claim:

- zero latency,
    
- perfect visual alignment,
    
- deterministic slip detection,
    
- universal superiority of RTC,
    
- universal superiority of A2A,
    
- perfect prediction,
    
- human-level dexterity,
    
- human-level locomotion,
    
- that Neural ODEs are inherently better,
    
- that tactile MPC is always necessary,
    
- that a larger model is automatically better,
    
- that any research-paper latency transfers directly to Orin NX hardware.
    

All such claims require experimental validation.

---

# 65. Main Research Questions

VAYN-7 ultimately attempts to answer:

1. Can asynchronous action generation reduce effective control latency?
    
2. Can action-history initialization reduce flow-generation cost without causing action repetition?
    
3. Can visual features be predicted accurately enough to compensate for camera-to-policy delay?
    
4. Does delay-conditioned prediction outperform simpler physical models?
    
5. Can tactile signals detect contact and slip earlier than vision?
    
6. Can tactile information improve physical manipulation without excessive compute?
    
7. Does contact-aware MPC justify its computational complexity?
    
8. Which components provide measurable improvement on the actual robot?
    

---

# 66. VAYN-7 Core Concept

The conceptual evolution is:

```text
VAYN-6.2

THINK
  ↓
PREDICT
  ↓
MOVE
  ↓
RT CONTROL
  ↓
SURVIVE
```

toward:

```text
VAYN-7

THINK
  ↓
TIME-AWARE PREDICT
  ↓
ASYNC MOVE
  ↓
CONTACT-AWARE RT CONTROL
  ↓
SURVIVE
```

The fundamental difference is not simply adding larger models.

It is making the architecture explicitly aware of:

```text
when information existed
when information arrived
what action was planned
what action was actually committed
when the action will physically occur
what the robot physically experienced
```

---

# 67. Final Status

**VAYN-7 is a research draft.**

The architecture should remain open to experimental revision.

The immediate objective is not to prove that VAYN-7 is superior to VAYN-6.2.

The immediate objective is to establish a measured baseline and determine which proposed mechanisms provide enough benefit to justify their computational and engineering cost.

The correct development philosophy is:

```text
MEASURE
   ↓
IDENTIFY BOTTLENECK
   ↓
FORM HYPOTHESIS
   ↓
IMPLEMENT
   ↓
ABLATE
   ↓
MEASURE AGAIN
   ↓
KEEP OR REMOVE
```

A component that does not demonstrate measurable benefit should not remain in VAYN-7 merely because it is theoretically interesting.

**VAYN-7 therefore represents a research direction rather than a finalized architecture.**