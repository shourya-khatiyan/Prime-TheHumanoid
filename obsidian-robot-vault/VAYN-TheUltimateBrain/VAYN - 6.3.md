# VAYN-6.3 — Versatile Arbitrated Embodied Nervous-System

## Gate-0 Timing & Latency Measurement Specification

**Status:** Engineering Measurement Specification  
**Architecture Status:** VAYN-6.2 architecture remains frozen  
**Purpose:** Baseline instrumentation, timing characterization, bottleneck identification, and evidence generation before adopting VAYN-7 research upgrades  
**Predecessor:** VAYN-6.2  
**Successor Decision:** VAYN-6.3 architecture update only after Gate-0 evidence  
**Primary Principle:** Measure first. Optimize the dominant physical bottleneck, not the most interesting algorithm.

---

# 1. Purpose

VAYN-6.3 Gate-0 is the measurement phase preceding implementation or architectural adoption of the proposed VAYN-7 upgrades.

The objective is to determine:

1. Where end-to-end latency actually occurs.
    
2. How much latency is deterministic versus variable.
    
3. Whether policy inference is a meaningful component of total delay.
    
4. Whether the visual pipeline, transport, RT execution, or actuation dominates.
    
5. How much delay and jitter the robot must tolerate during committed action execution.
    
6. How much disturbance can be survived during the non-replaceable action prefix.
    
7. How much benefit RTC-style asynchronous execution could realistically provide.
    
8. Whether A2A initialization is worth testing on the target hardware.
    
9. Whether visual prediction is more valuable than reducing policy inference.
    
10. Whether tactile processing and contact estimation provide sufficiently reliable information for reflex/control use.
    
11. Whether locomotion and manipulation require different timing strategies.
    

Gate-0 does **not** introduce a new top-level architecture.

The existing VAYN-6.2 structure remains:

```text
THINK
  ↓
PREDICT
  ↓
MOVE
  ↓
SURVIVE
```

Gate-0 determines which internal improvements should subsequently be implemented.

---

# 2. Design Rule

The governing rule is:

```text
VAYN-6.2 baseline
       ↓
Instrument
       ↓
Measure
       ↓
Decompose latency
       ↓
Identify dominant failure/bottleneck
       ↓
Select candidate intervention
       ↓
Run controlled ablation
       ↓
Compare against baseline
       ↓
Keep / modify / defer / reject
```

No proposed technique is considered architecturally adopted merely because:

- it exists in a research paper,
    
- it reports low latency on other hardware,
    
- it improves a small benchmark,
    
- it is theoretically elegant,
    
- or it appears relevant to the problem.
    

The target robot and target compute platform determine whether an optimization is useful.

---

# 3. Architecture Freeze During Gate-0

No new top-level blocks are introduced during Gate-0.

The following remain unchanged from VAYN-6.2:

## 3.1 Think

High-level semantic reasoning, task planning, object understanding, and intent generation.

Typical implementation:

- VLM/VLA
    
- language reasoning
    
- task planning
    
- object reasoning
    

This layer is not responsible for hard real-time stabilization.

---

## 3.2 Predict

Physical and temporal state prediction.

Inputs may include:

- proprioception
    
- IMU
    
- force
    
- tactile
    
- vision
    
- committed action
    
- actuator state
    

The predictive layer may later contain experimental learned prediction modules.

---

## 3.3 Move

Action generation and motion references.

The policy may propose:

- joint targets
    
- end-effector targets
    
- base velocity
    
- footstep targets
    
- grip-force references
    
- manipulation trajectories
    
- task-specific motion references
    

RTC and A2A belong here as **candidate techniques**, not automatically as frozen architecture.

---

## 3.4 Survive

The real-time physical control and safety path.

The RT Motion Core owns:

- state estimation
    
- stabilization
    
- impedance/torque control
    
- whole-body control where applicable
    
- arbitration
    
- validation
    
- following-error checks
    
- command commitment
    
- bounded reflexes
    
- actuator command generation
    

The independent Safety MCU remains outside the learned intelligence path.

AI-generated commands must never bypass:

- joint limits
    
- torque limits
    
- velocity limits
    
- collision constraints
    
- safety state transitions
    
- actuator safety mechanisms
    

---

# 4. Gate-0 Scope

Gate-0 covers five timing domains.

```text
1. Sensor capture
2. Perception/state processing
3. Policy generation
4. RT command execution
5. Physical actuator response
```

The measurement system must connect these domains with synchronized timestamps.

---

# 5. Fundamental Timing Rule

The system must distinguish:

```text
WHEN THE DATA WAS CAPTURED
        ≠
WHEN THE DATA ARRIVED
        ≠
WHEN THE DATA WAS PROCESSED
        ≠
WHEN THE ACTION WAS GENERATED
        ≠
WHEN THE ACTION WAS COMMITTED
        ≠
WHEN THE ACTION BECAME ACTIVE
```

Arrival time must never be treated as capture time when measuring feedback latency.

For visual data, the principal reference timestamp is the **exposure midpoint**.

---

# 6. Global Timing Contract

Every timing-relevant event shall contain, where applicable:

```text
timestamp
sequence_id
source_id
event_type
clock_id
```

Recommended timestamp representation:

```text
64-bit monotonic time
nanosecond or sufficiently high-resolution integer representation
```

Wall-clock time may be logged for diagnostics, but control timing must use a monotonic clock.

---

# 7. Clock Synchronization

All timing-critical components shall operate against a common timing reference or maintain a continuously estimated clock offset.

Potential mechanisms include:

- shared hardware clock,
    
- hardware timestamping,
    
- PTP or equivalent clock synchronization,
    
- deterministic control-cycle synchronization.
    

The exact synchronization mechanism depends on the hardware.

The measurement system must report:

```text
clock_offset_estimate
clock_offset_variance
clock_sync_status
```

A timing result shall be marked invalid when clock synchronization uncertainty becomes larger than the timing resolution required for the experiment.

---

# 8. Camera Timing Contract

Every camera frame shall expose, where supported:

```text
frame_id

exposure_start
exposure_midpoint
exposure_end

readout_complete
transport_departure
arrival_time
feature_generation_time
```

The primary visual capture timestamp is:

```text
t_capture = exposure_midpoint
```

Not:

```text
t_capture = frame arrival time
```

Not:

```text
t_capture = neural feature generation time
```

This distinction is mandatory for visual latency analysis.

---

# 9. Proprioceptive Sensor Timing

For encoders, IMU, force sensors, and other proprioceptive sources:

```text
sample_id
sensor_id
capture_time
arrival_time
processing_time
sequence_id
```

The state estimator must retain the original sensor capture timestamp.

Where sensor hardware supports hardware timestamps, those timestamps are preferred over software arrival timestamps.

---

# 10. Tactile Timing Contract

Tactile samples shall contain:

```text
sample_id
sensor_id
capture_time
arrival_time
feature_time
processing_time
signal_quality
```

The tactile path must preserve sufficient temporal resolution to distinguish:

- contact onset,
    
- sustained contact,
    
- shear,
    
- vibration,
    
- slip-related events,
    
- sensor saturation,
    
- actuator-induced vibration.
    

---

# 11. Action Lifecycle

Every policy action or motion reference shall follow a defined lifecycle.

```text
GENERATED
   ↓
SENT
   ↓
RECEIVED
   ↓
ACCEPTED / REJECTED
   ↓
COMMITTED
   ↓
ACTIVE / EXECUTED
   ↓
EXPIRED
```

Recommended timestamps:

```text
generated_at
sent_at
received_at
accepted_at
committed_at
executed_at
valid_until
```

Not every implementation will be able to directly measure every stage.

Where a physical timestamp is unavailable, the system must clearly distinguish:

```text
measured
estimated
inferred
```

---

# 12. Definition of "Executed Action"

VAYN must distinguish between:

### Planned action

What the policy requested.

### Committed action

What the RT Motion Core accepted as the future reference.

### Executed reference

The reference actually made active by the RT controller after:

- arbitration,
    
- safety validation,
    
- reflex correction,
    
- clipping,
    
- controller modification.
    

### Physical state

What the robot actually did.

Therefore:

```text
planned action
      ≠
committed reference
      ≠
executed reference
      ≠
measured physical state
```

This distinction is critical for learning systems.

A future A2A system must not blindly condition on its own previous plans when those plans may have been altered by the RT stack.

---

# 13. ACTION_ACK_V1

The RT Motion Core shall expose an execution acknowledgment structure.

## 13.1 Required fields

```text
ACTION_ACK_V1

command_id

generated_at
received_at
accepted_at
committed_at

accepted

committed_reference

residual_applied

safety_clipped

controller_mode

valid_until
```

Recommended additional fields:

```text
execution_start
execution_end
following_error
reference_version
state_estimator_version
arbiter_version
validator_status
```

---

# 14. Purpose of ACTION_ACK

`ACTION_ACK` provides the policy layer with a trusted representation of what the RT core actually committed.

It enables:

1. Correct action history.
    
2. Accurate replay.
    
3. Correct A2A conditioning.
    
4. Measurement of arbitration changes.
    
5. Measurement of safety clipping.
    
6. Measurement of reflex intervention.
    
7. Detection of policy/controller disagreement.
    
8. Offline training using actual executed references.
    

---

# 15. Executed Action History

A dedicated:

```text
EXECUTED_ACTION_HISTORY_V1
```

shall be maintained.

Each entry should include:

```text
timestamp
command_id
planned_reference
committed_reference
executed_reference
measured_state
residual
safety_clipping
controller_mode
following_error
```

The history must be aligned to the actual execution timeline.

This dataset becomes the preferred action-history source for any future A2A experiment.

---

# 16. End-to-End Latency

The principal measurement is:

```text
L_total
```

For a visual feedback action:

```text
L_total =
    t_actuator_active
    -
    t_exposure_midpoint
```

For proprioceptive feedback:

```text
L_total =
    t_actuator_active
    -
    t_sensor_capture
```

The exact endpoint must be defined consistently for every experiment.

---

# 17. Latency Decomposition

The primary conceptual decomposition is:

```text
L_total =
    L_capture
  + L_sensor
  + L_transport
  + L_ISP
  + L_visual
  + L_state
  + L_policy
  + L_Orin_to_RT
  + L_RT
  + L_actuation
```

The implementation shall use measurable stage boundaries rather than assuming these values.

For example:

```text
Camera
  ↓
Feature extraction
  ↓
State estimation
  ↓
Policy
  ↓
Orin → RT transfer
  ↓
RT validation/arbitration
  ↓
Controller
  ↓
Actuator
```

Each transition shall be timestamped.

---

# 18. Latency Statistics

Average latency alone is insufficient.

Every experiment shall report at minimum:

```text
mean
p50
p90
p95
p99
maximum
jitter
deadline misses
```

Where useful:

```text
p99.9
minimum
standard deviation
interquartile range
```

The robot shall not be designed around average delay when rare high-latency events can affect safety or stability.

---

# 19. Jitter

Jitter shall be quantified as variation in timing between equivalent pipeline events.

Useful measurements include:

```text
p99 - p50
p99 - p95
maximum - minimum
cycle-to-cycle variation
```

The exact metric used must be reported alongside the result rather than simply reporting the word "jitter."

---

# 20. Deterministic vs Variable Latency

Each latency component should be classified as:

### Deterministic / bounded

Example:

```text
fixed-rate control cycle
```

### Low-variance

Example:

```text
stable sensor transport
```

### Variable

Example:

```text
GPU contention
```

### Unbounded or poorly characterized

Example:

```text
system-level scheduling stalls
```

The optimization strategy should prefer removing variability where possible before adding learned prediction.

---

# 21. Latency Distribution

For each important pipeline:

```text
visual → policy → actuator

IMU → policy → actuator

tactile → reflex → actuator
```

plot the complete latency distribution.

At minimum, collect:

```text
N ≥ sufficient samples to estimate p99
```

The exact sample count must be chosen according to the desired statistical confidence and experiment duration.

No p99 claim should be made from an extremely small sample set.

---

# 22. Amdahl-Based Optimization Decision

After measurement, calculate the contribution of every stage:

```text
Contribution_i =
    L_i / L_total
```

The optimization priority is determined by measured contribution and control impact.

Example:

```text
Stage             Contribution
--------------------------------
Vision            42%
Policy             6%
Transport          8%
RT                  4%
Actuation          17%
Other              23%
```

In this case, reducing policy inference substantially would not eliminate most of the end-to-end latency.

Conversely, if policy computation dominates, RTC/A2A becomes substantially more relevant.

---

# 23. Optimization Decision Heuristic

This is an engineering heuristic, not a fundamental law:

```text
If a stage contributes very little to total latency
and does not determine deadline misses,
do not prioritize optimizing that stage solely for latency.
```

Priority increases when a stage:

- dominates latency,
    
- produces high jitter,
    
- causes deadline misses,
    
- causes instability,
    
- limits control frequency,
    
- or creates a safety-relevant delay.
    

---

# 24. Orin Compute Contention Test

The edge compute platform must be tested under progressively increasing workloads.

Run at least these conditions:

```text
Test A:
Policy only

Test B:
Policy + vision

Test C:
Policy + vision + predictive model

Test D:
Policy + vision + predictive model + VLM

Test E:
Full intended workload

Test F:
Full workload + logging

Test G:
Full workload + thermal steady state
```

Measure:

```text
GPU utilization
GPU memory utilization
GPU memory bandwidth
CPU utilization
CPU scheduling latency
RAM usage
power
temperature
clock frequency
kernel duration
deadline misses
L_total
L_policy
jitter
```

The purpose is to determine whether a technique that looks fast in isolation remains fast under realistic system load.

---

# 25. Thermal Measurement

Latency shall also be measured in:

```text
cold start
normal operating temperature
thermal steady state
high-load condition
low-battery / reduced-power condition where applicable
```

A model that meets timing only before thermal stabilization does not satisfy the same engineering requirement as one that remains deterministic during sustained operation.

---

# 26. Logging Overhead Test

Logging itself can influence timing.

Therefore measure:

```text
no logging
minimal logging
full timing logging
full telemetry logging
```

The timing overhead introduced by instrumentation shall be measured rather than assumed negligible.

---

# 27. Action Buffer Measurement

If RTC-style execution is tested, action references shall be stored in a time-indexed buffer.

Conceptually:

```text
<---- committed / immutable ---->|<--------- replaceable --------->

[t0][t1][t2][t3][t4][t5][t6][t7][t8]...
```

The committed prefix cannot be arbitrarily rewritten after commitment.

The future region may be updated as new observations become available.

---

# 28. Commit Horizon

Define:

```text
H_commit
```

as the temporal duration of the currently committed non-replaceable reference.

For a discrete controller:

```text
H_commit = N_commit / f_control
```

where:

```text
N_commit = number of committed samples
f_control = control frequency
```

The actual system shall use measured timing rather than assuming a fixed value such as 40 ms.

---

# 29. Prediction Horizon vs Execution Horizon

These must remain separate.

### Prediction horizon

How far into the future the model predicts.

```text
H_prediction
```

### Execution/commit horizon

How far into the future the controller has already committed references that cannot be replaced freely.

```text
H_commit
```

It is possible for:

```text
H_prediction > H_commit
```

without requiring:

```text
H_prediction = H_commit
```

They solve different problems.

---

# 30. Reference Buffer Requirement

The reference buffer must tolerate the measured high-percentile pipeline delay.

A first engineering condition is:

```text
H_buffer > L_p99 + safety_margin
```

where the margin depends on:

- skill,
    
- robot dynamics,
    
- fallback authority,
    
- disturbance environment.
    

If the buffer becomes empty before a valid replacement reference arrives:

```text
buffer underrun
      ↓
valid_until policy
      ↓
fallback controller
```

The robot must not continue indefinitely on stale references.

---

# 31. valid_until Contract

Every future motion reference shall contain:

```text
valid_until
```

When the reference expires:

```text
1. New valid reference available
        → continue

2. Temporary valid replacement unavailable
        → bounded fallback

3. Persistent failure
        → state-dependent degraded mode
```

Fallback must be skill-specific.

Examples:

```text
Manipulation:
hold / retract / release / stabilize

Standing:
stabilize / crouch / controlled sit

Walking:
phase-aware halt / controlled stop

Unsafe state:
Safety MCU / hardware safety action
```

---

# 32. Disturbance Survival During the Commit Horizon

The committed prefix is effectively a period during which high-level replanning cannot completely replace the reference.

Therefore define:

```text
T_blind
```

as the period during which the current committed motion cannot be materially replaced by the higher-level policy.

Gate-0 shall measure what disturbances the RT layer can survive during:

```text
T_blind = H_commit + remaining pipeline delay
```

Candidate disturbances:

- external push
    
- unexpected contact
    
- object motion
    
- grip disturbance
    
- foot slip
    
- actuator disturbance
    
- temporary sensor delay
    
- sensor dropout
    
- visual occlusion
    

---

# 33. Reflex Authority Requirement

Reflex authority shall not be selected arbitrarily.

It should be derived from:

```text
disturbance magnitude
+
robot dynamics
+
response latency
+
commit horizon
```

The key question is:

> What disturbance must the RT layer successfully handle before the high-level policy can react?

Gate-0 must answer this experimentally.

---

# 34. Following-Error Monitor

Following-error monitoring belongs in the RT validator.

The RT core should continuously compare:

```text
committed reference
        vs
measured state
```

Compute at least:

```text
position error
velocity error
orientation error
force error where applicable
```

For a trajectory:

```text
e(t) = x_reference(t) - x_measured(t)
```

The monitor must be deterministic.

---

# 35. Learned Prediction Disagreement

Learned model disagreement should remain a **soft signal**.

Example:

```text
Predicted state
      vs
Measured state
```

Large disagreement may indicate:

- unexpected contact
    
- slipping
    
- actuator problem
    
- sensor issue
    
- model failure
    
- environment change
    

But the learned model should not directly determine a safety-critical action solely from prediction error.

The RT validator remains authoritative.

---

# 36. Prediction Discrepancy as Data

Prediction disagreement shall be logged.

Each event may contain:

```text
timestamp
prediction
measurement
prediction_error
contact_state
slip_state
controller_mode
disturbance_event
```

These events become targeted data for offline training and model improvement.

This restores the useful part of the earlier VAYN-5 "error delta" concept without performing uncontrolled online learning.

---

# 37. RTC Evaluation

RTC-style asynchronous action generation becomes an experiment only after measuring:

```text
L_policy
L_total
deadline miss rate
action generation frequency
```

RTC shall be evaluated against:

```text
Baseline:
Synchronous action generation + chunk blending
```

Measure:

```text
end-to-end latency
jitter
trajectory discontinuity
tracking error
reaction time
deadline misses
compute utilization
```

The experiment shall not use "zero latency" as a success criterion.

---

# 38. RTC Research Hypothesis

Candidate hypothesis:

```text
H1:
Asynchronous execution improves responsiveness and/or
trajectory continuity when policy generation occupies a
meaningful fraction of the action pipeline.
```

H1 is considered unsupported if:

- policy latency is already negligible,
    
- the dominant delay exists elsewhere,
    
- or asynchronous execution does not improve measured task performance.
    

---

# 39. A2A Evaluation

A2A initialization shall remain experimental.

Baseline comparisons:

```text
A2A
vs
noise-initialized flow
vs
existing action-chunk policy / ACT-style baseline where appropriate
```

Metrics:

```text
generation latency
reaction latency
task success
action smoothness
observation utilization
intervention recovery
compute consumption
```

---

# 40. A2A Causal Reactivity Test

A major test shall intentionally invalidate the expected continuation.

Examples:

```text
1. Object moves unexpectedly.
2. Object falls.
3. Target location changes.
4. Human moves the target.
5. Robot experiences unexpected contact.
6. Visual observation is temporarily occluded.
```

The intervention should occur during execution of an already generated action sequence.

Measure:

```text
T_reaction =
time from unexpected event
to meaningful policy correction
```

Compare A2A against the baseline.

---

# 41. A2A History-Dependence Test

To determine whether A2A is genuinely using observations, perform:

```text
Normal history
Corrupted action history
Dropped action history
Repeated action history
History dropout during training
```

The purpose is to detect a failure mode where the model repeatedly reproduces previous actions rather than responding to new observations.

---

# 42. Re-Anchoring

A2A should define explicit reset/re-anchor conditions.

Examples:

```text
major visual discontinuity
unexpected contact
large prediction error
target change
task phase transition
reference invalidation
sensor dropout
```

After a re-anchor event, the model must rely more strongly on current observation/state instead of simply extending prior action history.

---

# 43. RTC/A2A Initial Scope

The first implementation target should be:

```text
MANIPULATION
```

not the entire humanoid.

Manipulation generally provides a cleaner environment for testing continuous reference generation and action history.

---

# 44. Locomotion Timing

Locomotion shall be evaluated separately.

Walking contains:

- gait phases,
    
- contact transitions,
    
- foot placement events,
    
- discrete support changes,
    
- balance constraints.
    

Therefore continuous action-chunk inpainting cannot automatically be assumed to transfer from manipulation.

For locomotion, Gate-0 should first investigate:

```text
measured delay
+
delay randomization during training
+
gait-phase-aware reference updates
```

Reference replacement should preferably occur at safe phase boundaries rather than arbitrarily during critical swing/contact transitions.

---

# 45. Visual Age Experiment

Before implementing learned visual prediction, measure the effect of stale observations.

Create controlled visual ages:

```text
0 ms
20 ms
40 ms
60 ms
80 ms
100 ms
150 ms
```

Where feasible.

For each condition measure:

```text
task success
tracking error
object localization error
reaction time
grasp error
trajectory deviation
```

This establishes how sensitive the task is to visual staleness.

---

# 46. Visual Prediction Baselines

Compare:

```text
Baseline A:
Stale visual features

Baseline B:
Stale features + current camera/robot pose

Baseline C:
Geometric/motion-aware feature transport

Candidate D:
Learned visual prediction
```

The learned approach should not be considered useful merely because its predicted image/features look plausible.

The relevant metric is downstream robot performance.

---

# 47. Camera Synchronization First

Before developing sophisticated learned visual prediction, reduce avoidable timing variation.

Preferred direction:

```text
hardware-triggered camera
+
global shutter where appropriate
+
control-clock synchronization
+
exposure-midpoint timestamp
+
deterministic transport
```

The objective is to convert:

```text
variable delay
```

into:

```text
more deterministic delay
```

where physically possible.

Prediction should compensate the remaining uncertainty rather than replace basic timing engineering.

---

# 48. Delay Compensation

The predictive system shall distinguish:

```text
known / bounded delay
```

from:

```text
uncertain delay
```

If delay can be made deterministic, hardware/system design should be preferred.

If a residual uncertainty remains, prediction may compensate for it.

The system should avoid predicting a delay that could have been removed by better synchronization.

---

# 49. Physical State Prediction

Gate-0 shall establish a baseline before Neural ODE or similar continuous-time methods are considered.

Baseline sequence:

```text
1. Measured state
2. Kinematic extrapolation
3. Physics/dynamics model
4. Learned residual model
5. Continuous-time learned dynamics
```

The more complex method must beat the simpler method on:

```text
prediction error
latency
compute
stability
generalization
```

---

# 50. Neural ODE / Continuous-Time Dynamics

Continuous-time latent dynamics remain experimental.

The experiment must answer:

```text
Does continuous-time representation provide
a practical advantage over simpler prediction methods
on the actual robot?
```

It is not assumed that continuous time automatically improves control merely because the physical system is continuous.

---

# 51. Tactile Measurement Phase

Before designing a learned slip classifier, characterize the tactile system.

Measure:

```text
sampling frequency
sensor resolution
force range
shear range
noise floor
frequency response
latency
saturation
temperature dependence
cross-talk
sensor-to-sensor variation
```

Also measure:

```text
motor vibration
gearbox vibration
structural resonance
controller-induced vibration
```

This is necessary because actuator and gearbox vibration can appear in tactile measurements.

---

# 52. Tactile Processing Architecture

The preferred signal path is:

```text
RAW TACTILE SIGNAL
        ↓
LOCAL DSP / SIGNAL PROCESSING
        ↓
FORCE / SHEAR / VIBRATION FEATURES
        ↓
CONTACT ESTIMATOR
        ↓
SLIP ESTIMATION
        ↓
REFLEX / CONTROL
```

A fixed universal FFT band shall not be treated as a universal slip detector.

Frequency features remain useful, but the relevant frequency bands must be characterized on the actual hardware.

---

# 53. Tactile Contact Estimator

A candidate contact state interface:

```text
CONTACT_STATE_V1

timestamp

contact_probability

normal_force
shear_force

contact_centroid

slip_probability
slip_direction
slip_velocity

signal_quality
confidence
```

The interface should explicitly support uncertainty.

---

# 54. Physical Slip Ground Truth

Slip classification requires physical labels.

Construct a controlled test rig capable of producing known slip events.

Possible ground-truth mechanisms:

```text
known pulling force
optical object tracking
motion capture
instrumented displacement
```

Test across:

```text
different object materials
different surfaces
different masses
different grip forces
different contact geometries
different actuator states
different temperatures
different vibration conditions
```

---

# 55. Tactile Evaluation

Baseline:

```text
force threshold
+
vibration energy
```

Candidate:

```text
DSP features
+
learned contact/slip classifier
```

Measure:

```text
precision
recall
false positives
false negatives
detection latency
direction accuracy
velocity estimation error
robustness to actuator vibration
```

The key robotic metric is not classification accuracy alone.

It is:

```text
Did the contact information allow
the robot to correct the physical interaction?
```

---

# 56. Contact-Aware Control

Contact-aware MPC remains deferred until the lower-level baseline is characterized.

Control baselines:

```text
A. Impedance adjustment
B. Tactile-triggered impedance correction
C. Contact controller
D. Contact-aware MPC
```

Compare:

```text
contact stability
force tracking
slip recovery
overshoot
energy
compute load
latency
failure rate
```

Do not introduce MPC complexity without demonstrating that simpler control cannot achieve the required behavior.

---

# 57. Disturbance Observer

A disturbance observer may be evaluated as a separate experimental module.

Candidate inputs:

```text
measured state
expected state
motor torque/current
contact state
prediction discrepancy
```

Candidate outputs:

```text
external disturbance estimate
contact force estimate
model mismatch
```

The observer remains advisory unless explicitly integrated into a validated RT controller.

---

# 58. Manipulation Benchmark

The first VAYN-6.3 timing benchmark should contain manipulation tasks that stress temporal responsiveness.

Suggested task categories:

```text
pick and place
dynamic object interception
grasp stabilization
object handover
moving-target grasp
contact-rich insertion
slip recovery
unexpected object motion
```

Each task must specify:

```text
initial condition
success condition
failure condition
timing requirement
disturbance condition
```

---

# 59. Locomotion Benchmark

Locomotion requires separate measurements.

Include:

```text
standing
walking
turning
start/stop
uneven terrain
push recovery
foot slip
unexpected obstacle/contact
sensor delay
sensor dropout
```

Measure:

```text
fall rate
recovery time
base orientation error
COM error
foot placement error
phase timing
controller deadline misses
```

---

# 60. Delay Randomization

Measured latency distributions should feed simulation/training experiments.

Instead of using only a single fixed artificial delay:

```text
20 ms
```

sample from the measured distribution:

```text
D_measured
```

including realistic variability.

This helps avoid training a policy that works only under idealized timing.

The actual measured distribution must be recorded before defining the randomization range.

---

# 61. Teleoperation Data

When human teleoperation is used for training data, record:

```text
leader command timestamp
leader state timestamp
robot command timestamp
robot received timestamp
robot executed reference timestamp
robot measured state timestamp
```

The leader-follower delay must be measured.

Otherwise temporal delay becomes embedded in the demonstration labels without being visible during training.

---

# 62. Data Model

Gate-0 shall create a unified replayable log containing:

```text
CAMERA
IMU
JOINT ENCODERS
FORCE
TACTILE
POLICY INPUT
POLICY OUTPUT
ACTION_ACK
COMMITTED REFERENCE
EXECUTED REFERENCE
MEASURED STATE
RT CONTROLLER STATE
SAFETY STATE
TIMING EVENTS
SYSTEM LOAD
DISTURBANCE EVENTS
```

All streams must be aligned using timestamps and sequence identifiers.

---

# 63. Replay Requirement

Every important experiment should be replayable offline.

A replay system should allow reconstruction of:

```text
what the robot observed
when it observed it
what the policy produced
what the RT core committed
what the RT core modified
what the robot physically executed
```

The goal is to make timing failures debuggable without requiring repeated physical experiments for every hypothesis.

---

# 64. Benchmark Matrix

Gate-0 shall maintain a benchmark matrix.

|Experiment|Baseline|Candidate|Primary metric|
|---|---|---|---|
|Latency decomposition|VAYN-6.2|—|p99 L_total|
|Policy latency|Existing policy|A2A|L_policy|
|Continuous execution|Sync chunks|RTC|reaction latency|
|Visual freshness|Stale features|Motion-aware prediction|task success|
|State prediction|Kinematic|learned residual|prediction error|
|Tactile slip|Threshold|learned estimator|detection latency|
|Contact control|Impedance|tactile/MPC|recovery/stability|
|Locomotion timing|Existing control|phase-aware timing|fall/recovery|
|Delay robustness|Fixed delay|randomized delay|robustness|

---

# 65. Baseline Requirement

Every candidate module requires a baseline.

Minimum rule:

```text
New method
    must be compared against
existing VAYN implementation
```

Where appropriate:

```text
simple classical method
```

must also be included.

The experiment should answer:

> Does the additional complexity produce a measurable improvement on the robot?

---

# 66. Capability Per Compute

Latency is not the only metric.

Record:

```text
capability / GPU utilization
capability / CPU utilization
capability / watt
capability / model parameter
capability / memory
```

A system that is slightly faster but consumes substantially more power or causes thermal throttling may not be a meaningful improvement for a humanoid.

---

# 67. Power and Thermal Constraints

For each major experiment log:

```text
input power
GPU power
CPU power
temperature
clock rate
thermal throttling
battery state
```

Measure both:

```text
cold performance
```

and:

```text
sustained performance
```

---

# 68. Failure Injection Tests

Timing experiments must include controlled failures.

Examples:

```text
camera frame delay
camera frame drop
tactile packet delay
IMU packet delay
GPU contention
policy timeout
RT packet loss
action buffer underrun
clock offset
sensor dropout
unexpected contact
```

Measure:

```text
detection time
fallback time
recovery time
maximum deviation
whether the robot remains controllable
```

---

# 69. Safety Boundary

The following must never depend on experimental learned modules:

```text
hard joint limits
hard torque limits
emergency stop
actuator-level safety
Safety MCU operation
fundamental state validity checks
```

RTC, A2A, visual prediction, learned prediction, and tactile classifiers cannot override these mechanisms.

---

# 70. Gate-0 Metrics

The main metrics are:

## Timing

```text
L_total
L_capture
L_sensor
L_visual
L_state
L_policy
L_transport
L_RT
L_actuation
```

## Distribution

```text
p50
p90
p95
p99
max
jitter
deadline misses
```

## Control

```text
following error
overshoot
trajectory discontinuity
stability margin
reaction time
recovery time
```

## Perception

```text
visual age
state estimation error
tactile detection latency
contact estimation accuracy
```

## Compute

```text
GPU
CPU
memory
bandwidth
power
temperature
```

## Physical robustness

```text
disturbance tolerance
slip recovery
unexpected-contact recovery
sensor dropout tolerance
```

---

# 71. Gate-0 Decision Outputs

At the end of measurement, every proposed upgrade receives one of four statuses:

```text
ADOPT
```

Evidence shows that the intervention provides a meaningful advantage.

```text
EXPERIMENT FURTHER
```

Initial evidence is promising but insufficient.

```text
DEFER
```

The intervention is technically plausible but not currently relevant to the measured bottleneck.

```text
REJECT
```

The intervention fails to beat the baseline or introduces unacceptable complexity/risk.

````

No upgrade becomes frozen merely because it is technically interesting.

---

# 72. Candidate VAYN-6.3 Status Table

| Module | Location | Initial status | Gate-0 requirement |
|---|---|---|---|
| Async execution / RTC | Move / Action Policy | Candidate | Policy latency must justify it |
| A2A initialization | Move / Action Policy | Experimental | Must beat baseline and pass intervention tests |
| Training-time delay conditioning | Training | Experimental | Requires measured delay distribution |
| Motion-aware visual prediction | Predict | Experimental | Must improve stale-vision performance |
| Delay-conditioned physical prediction | Predict | Experimental | Must beat kinematic baseline |
| Tactile DSP | State / Reflex | Candidate adoption | Physical sensor characterization |
| Learned tactile classifier | State / Reflex | Experimental | Physical slip ground truth |
| Contact-aware MPC | RT Core | Deferred | Must beat simpler control |
| Following-error monitor | RT Validator | Adopt | Deterministic implementation |
| ACTION_ACK | RT → Policy interface | Adopt | Required for correct executed-history semantics |
| Capture timestamps | Sensor interfaces | Adopt | Required for valid timing measurement |
| Clock-offset reporting | Interfaces | Adopt | Required for cross-system timing |
| Delay statistics | Logging | Adopt | Required for engineering decisions |

---

# 73. Proposed VAYN-6.3 Gate-0 Architecture

The conceptual architecture remains:

```text
                         ┌──────────────────────────┐
                         │          THINK           │
                         │ VLM / Planning / Intent  │
                         └────────────┬─────────────┘
                                      │
                                      ▼
                         ┌──────────────────────────┐
                         │         PREDICT          │
                         │ State / Dynamics /       │
                         │ Temporal Prediction      │
                         └────────────┬─────────────┘
                                      │
                                      ▼
                         ┌──────────────────────────┐
                         │          MOVE            │
                         │ Action Policy / References│
                         │ RTC candidate / A2A test │
                         └────────────┬─────────────┘
                                      │
                                      ▼
                  ┌──────────────────────────────────────┐
                  │          REAL-TIME MOTION CORE       │
                  │                                      │
                  │ State Estimator                       │
                  │ Stabilization                         │
                  │ Arbiter                               │
                  │ RT Validator                          │
                  │ Following-Error Monitor               │
                  │ Impedance / Torque / WBC              │
                  │ ACTION_ACK                            │
                  └──────────────────┬───────────────────┘
                                     │
                                     ▼
                              Motor / Actuator
                                     │
                                     ▼
                              Physical Robot

                  ┌──────────────────────────────────────┐
                  │            SAFETY MCU                 │
                  │ Independent supervision               │
                  │ hardware safety limits                │
                  │ emergency handling                    │
                  └──────────────────────────────────────┘
````

No dedicated "temporal alignment layer" is introduced.

Temporal alignment exists primarily through:

```text
timestamps
clock synchronization
ACTION_ACK
valid_until
executed-action history
delay statistics
```

---

# 74. Gate-0 Research Questions

The measurement phase must answer:

### Q1

What is the true p99 end-to-end latency?

### Q2

Which pipeline component dominates it?

### Q3

How much of that latency is variable?

### Q4

How much can be removed through deterministic hardware/system design?

### Q5

Does policy inference materially constrain responsiveness?

### Q6

Would RTC reduce a meaningful portion of the measured delay?

### Q7

Does A2A reduce generation latency enough to matter on the target hardware?

### Q8

Does A2A react to new observations or primarily continue previous behavior?

### Q9

How much visual staleness can each task tolerate?

### Q10

Does motion-aware visual prediction improve downstream robot behavior?

### Q11

How long is the action commit blind window?

### Q12

What disturbances must the RT core survive during that window?

### Q13

What tactile signals reliably indicate contact and slip on the real hardware?

### Q14

Does learned contact estimation outperform a simple DSP/threshold baseline?

### Q15

Does contact-aware control outperform simpler impedance/reflex control?

### Q16

Are locomotion and manipulation best handled with different timing strategies?

---

# 75. Minimum Gate-0 Deliverables

The following artifacts shall exist before VAYN-6.3 architecture decisions are frozen:

```text
1. Latency measurement report
2. Timestamp contract
3. ACTION_ACK_V1 specification
4. Executed-action history specification
5. Clock synchronization report
6. L_total decomposition
7. p50/p95/p99 timing tables
8. GPU/CPU/bandwidth/thermal report
9. Action-buffer and commit-horizon measurements
10. Disturbance-survival results
11. Visual-age benchmark
12. A2A intervention benchmark
13. Tactile physical characterization
14. Slip ground-truth benchmark
15. Failure-injection report
16. Baseline-vs-candidate comparison
17. Adopt/defer/reject decision table
```

---

# 76. Proposed Experiment Order

Do not implement all candidate upgrades simultaneously.

Recommended sequence:

```text
PHASE 1
Instrumentation
    ↓
PHASE 2
Clock synchronization verification
    ↓
PHASE 3
L_total decomposition
    ↓
PHASE 4
Compute contention / thermal characterization
    ↓
PHASE 5
Action commit + buffer measurement
    ↓
PHASE 6
Visual-age experiment
    ↓
PHASE 7
Tactile characterization
    ↓
PHASE 8
Disturbance and failure injection
    ↓
PHASE 9
Select dominant bottlenecks
    ↓
PHASE 10
Run targeted candidate experiments
```

This prevents the project from implementing several new research components before understanding the original problem.

---

# 77. Candidate Intervention Selection

After Gate-0:

```text
IF visual path dominates
    → investigate synchronization / visual prediction

IF policy path dominates
    → investigate RTC / A2A

IF transport dominates
    → investigate RT-side communication/feedforward

IF actuator delay dominates
    → investigate low-level compensation/controller design

IF jitter dominates
    → investigate deterministic scheduling/synchronization

IF disturbance survival dominates
    → investigate RT reflex/control

IF tactile information is unreliable
    → improve sensing/processing before learned control

IF manipulation and locomotion differ substantially
    → maintain separate timing strategies
```

---

# 78. What Gate-0 Does Not Assume

Gate-0 does not assume:

```text
RTC is faster
A2A is better
FutureRTC is necessary
Neural ODE is better
contact MPC is necessary
FFT bands universally detect slip
continuous-time prediction is superior
manipulation and locomotion require the same solution
```

These remain empirical questions.

---

# 79. Research Discipline

VAYN development follows:

```text
BASELINE
   ↓
MEASUREMENT
   ↓
HYPOTHESIS
   ↓
INTERVENTION
   ↓
ABLATION
   ↓
EVALUATION
   ↓
DECISION
```

Not:

```text
NEW PAPER
   ↓
NEW MODULE
   ↓
NEW ARCHITECTURE
```

This prevents architecture inflation and allows each addition to be justified by measured robot behavior.

---

# 80. Gate-0 Acceptance Criteria

Gate-0 is complete when:

### Timing

- All major sensor and action paths are timestamped.
    
- Clock synchronization quality is known.
    
- End-to-end latency is measured.
    
- p99 and jitter are known.
    
- Deadline misses are quantified.
    

### Execution

- Planned, committed, executed, and measured states are distinguishable.
    
- `ACTION_ACK_V1` is implemented or fully specified.
    
- Executed-action history is available.
    
- `valid_until` is enforced.
    
- Commit horizon is measured.
    

### Physical robustness

- Disturbance tolerance is characterized.
    
- Fallback behavior is tested.
    
- Action-buffer underrun behavior is tested.
    
- Failure injection is performed.
    

### Candidate selection

- The dominant bottleneck is identified.
    
- Candidate upgrades are mapped to measured bottlenecks.
    
- At least one baseline exists for each candidate experiment.
    
- RTC/A2A are not adopted merely because of external benchmark results.
    

---

# 81. Final Gate-0 Principle

The objective of Gate-0 is not to make VAYN more complicated.

The objective is to determine:

```text
WHAT IS ACTUALLY SLOW?
WHAT IS ACTUALLY UNSTABLE?
WHAT IS ACTUALLY UNCERTAIN?
WHAT CAN BE MADE DETERMINISTIC?
WHAT MUST BE PREDICTED?
WHAT MUST REMAIN REACTIVE?
```

Only after these questions are answered should VAYN-6.3 selectively incorporate VAYN-7 research techniques.

---

# 82. Current VAYN State

```text
VAYN-6.2
    │
    │ frozen architecture
    ▼
VAYN-6.3 Gate-0
    │
    ├── instrumentation
    ├── timing characterization
    ├── action execution semantics
    ├── visual-age characterization
    ├── tactile characterization
    ├── disturbance testing
    └── baseline measurement
    │
    ▼
Evidence-based candidate selection
    │
    ├── Adopt
    ├── Experimental
    ├── Defer
    └── Reject
    │
    ▼
VAYN-6.3 architecture revision
    │
    ▼
Future VAYN-7 research branch
```

**Gate-0 Status:** Not yet completed  
**VAYN-7 Status:** Research branch only  
**VAYN-6.2 Status:** Architectural baseline  
**Next engineering objective:** Instrument the frozen VAYN-6.2 system and obtain the first complete `L_total` decomposition.