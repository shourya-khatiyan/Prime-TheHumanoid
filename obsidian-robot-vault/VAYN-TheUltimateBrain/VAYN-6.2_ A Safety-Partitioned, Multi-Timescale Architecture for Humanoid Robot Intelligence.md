# VAYN-6.2 — Versatile Arbitrated Embodied Nervous-System

## A Safety-Partitioned, Multi-Timescale Architecture for Humanoid Robot Intelligence on Edge Compute

**Shourya Singh Khatiyan · Avenue Robotics · shauryakhatiyan@gmail.com** 
*Architecture and position paper. No empirical results are reported.*

---

## Abstract

Recent vision-language-action (VLA) models give humanoid robots broad semantic competence, but they are large, run at low rates, and are probabilistic, which makes them poorly suited as the sole source of physical control or safety guarantees. We present VAYN-6.2, a hierarchical architecture that partitions robot intelligence into four responsibilities (think, predict, move, survive) assigned to distinct timescales and hardware domains. Learned components run on an edge AI computer and produce motion *references*. A dedicated real-time (RT) Motion Core permanently owns stabilization, command arbitration, safety validation, fallback and actuator commands, and an independent safety microcontroller supervises both. We contribute (i) an explicit authority and ownership model in which loss of the AI computer degrades capability without removing controllability; (ii) freshness contracts (timestamps, per-skill time-to-live, `valid_until`) that make asynchronous data staleness a first-class quantity; (iii) a hybrid latency-compensating predictor that combines known kinematics/dynamics with a learned residual; (iv) a bounded reflex residual, arbitrated inside the RT domain; and (v) a pre-specified ablation protocol in which each learned component must beat a simpler baseline. Most individual ideas have precedent; the contribution is their integration under explicit contracts and a falsifiable evaluation plan. We state three hypotheses, analyze deployment feasibility on a 16 GB Jetson Orin NX, and identify open risks. All performance targets are design parameters pending measurement.

**Keywords:** humanoid robots, vision-language-action models, real-time control, functional safety, latency compensation, tactile reflexes, edge AI

---

## 1. Introduction

Generalist robot policies have advanced quickly. Dual-system designs pair a slow vision-language model with a fast visuomotor policy (Figure AI, 2025; NVIDIA, 2025), and flow-matching action heads produce smooth multimodal action chunks (Black et al., 2024). Deploying such models on a humanoid raises systems problems that model-centric work often leaves implicit:

1. **Timescale mismatch.** Semantic reasoning tolerates hundreds of milliseconds; balance and contact reaction do not.
2. **Resource contention.** On an edge module with shared memory, a large model's bandwidth demand can starve concurrent workloads, so "the weights fit" is not evidence of feasibility.
3. **Authority ambiguity.** When a policy, a reflex and a safety layer can all write commands, who owns the actuator?
4. **Failure semantics.** For a legged robot, "stop" is not a safe state, since cutting motor power can cause a fall.
5. **Staleness.** Asynchronous modules silently consume outdated inputs unless age is tracked explicitly.

VAYN-6.2 addresses these as architectural concerns. Its guiding principle is that *AI improves capability, but physical controllability must not depend on it*.

**Contributions.** (1) A partitioned architecture with explicit ownership: the RT Motion Core always owns stabilization and final actuator commands (§4.2). (2) An independent safety supervisor with its own sensing path (§4.3). (3) Freshness contracts and versioned interfaces (§4.4, §5). (4) Hybrid prediction with a mandatory five-arm baseline comparison (§4.5). (5) A reflex residual with authority bounds enforced in the RT domain (§4.7). (6) A feasibility methodology and pre-specified hypotheses and ablations (§6–7). We do not claim superiority over existing systems; that requires the comparative evaluation described in §7.

---

## 2. Related Work

**VLA and dual-system policies.** π0 couples a vision-language backbone with a flow-matching action expert (Black et al., 2024). GR00T N1 and its successors use a vision-language module with a diffusion-transformer action head and target humanoids (NVIDIA, 2025); the current N1.7 release is a roughly 3B-parameter model with a Cosmos-Reason2-2B backbone and fine-tuning tooling (NVIDIA, Isaac GR00T repository). Helix runs a slower VLM and a fast visuomotor policy at different rates (Figure AI, 2025). Compact VLAs such as SmolVLA show that sub-billion models can be effective on constrained hardware (Shukor et al., 2025). VAYN-6.2 is compatible with these models: it treats a GR00T-class system as a benchmark, a teacher, or a higher-capacity deployment option, not as a mandatory component.

**Action chunking and latency.** ACT and Diffusion Policy established chunked action prediction (Zhao et al., 2023; Chi et al., 2023). Flow matching (Lipman et al., 2023) offers an efficient generative alternative. Real-time chunking addresses discontinuities between asynchronously generated chunks (Black et al., 2025). We adopt receding-horizon execution with explicit blending and do not treat chunk smoothness as a safety or compliance mechanism.

**Locomotion and whole-body control.** Learned legged locomotion via simulation reinforcement learning with randomization is well established (Hwangbo et al., 2019; Tobin et al., 2017), as is rapid online adaptation (Kumar et al., 2021). Model-based whole-body control and optimization-based stabilization have a long humanoid history (Kuindersma et al., 2016). Impedance control (Hogan, 1985) provides compliance at the joint or task level. VAYN-6.2 does not contest these methods; it specifies where they sit relative to learned high-level policies.

**World models.** Learned latent dynamics models support planning and control (Hafner et al., 2023). We restrict the predictor to short-horizon *physical state* and require it to beat analytic baselines.

**Continuous-time and recurrent reflex models.** Liquid/closed-form continuous-time networks (Hasani et al., 2022) are candidates for fast reflexes. Evidence at humanoid whole-body scale is limited, so we treat them as one arm of a controlled comparison.

**Safety.** ISO 13482:2014 covers personal-care robots, and ISO 13849-1:2023 provides a methodology for safety-related control systems. ISO 25785-1, for industrial mobile robots with actively controlled stability including bipeds, is under development as of our last check, and its scope is industrial environments (ISO, 2024–2026).

---

## 3. Problem Setting and Requirements

We consider a humanoid with *n* actuated joints, proprioceptive sensing (IMU, encoders, current/torque), optional force and tactile sensing, and cameras. Compute comprises an AI module (target: Jetson Orin NX 16 GB), a real-time processor, and a safety MCU. Requirements:

- **R1** Controllability survives AI-module failure.
- **R2** No learned output bypasses limits, validity checks or supervision.
- **R3** Stale data cannot silently drive actuation.
- **R4** Failure behavior depends on physical state, not a single "safe" action.
- **R5** Every learned component has a simpler baseline and a measured benefit.
- **R6** Capability scales with hardware without changing the control hierarchy.

**Table 1. Design-target timescales (parameters, not measured results).**

| Function                         | Target rate               | Domain        |
| -------------------------------- | ------------------------- | ------------- |
| Cognitive reasoning              | \~0.5–3 Hz / event-driven | AI            |
| Visual features, prediction      | \~10–20 Hz                | AI            |
| Action policy                    | \~25–50 Hz                | AI            |
| Learned reflex                   | \~100–250 Hz              | RT or AI CPU  |
| State estimation                 | \~200–500 Hz              | RT            |
| Stabilization                    | \~100–500 Hz              | RT            |
| Joint impedance                  | \~500–1000 Hz             | RT            |
| Current loop, safety supervision | hardware-dependent        | Drivers / MCU |

---

## 4. Architecture

### 4.1 Overview

```
THINK    Cognition (VLM, memory) -> Task/Skill (structured | free-form)

PREDICT  Perception -> Visual Feature Cache; Hybrid predictor -> S_pred

MOVE     Action policy -> nominal reference; reflex -> bounded residual

SURVIVE  RT Motion Core (estimation, arbitration, validation, stabilization,
         fallback, impedance) -> drivers -> actuators
         Independent Safety MCU supervising all of the above
```

The command path is *AI reference → RT Motion Core (arbitration, validation, stabilization, impedance) → driver → actuator*. The AI domain never writes torque or current.

### 4.2 RT Motion Core

The RT Motion Core is active in all modes and owns (a) the authoritative physical state S_phys, (b) stabilization, (c) command arbitration, (d) safety validation, (e) trajectory handling, (f) fallback references, and (g) impedance control. Because it never relinquishes stabilization, mode changes occur at the *reference* level rather than by switching between two independent balance controllers, which removes a major source of transient instability.

**Stabilizer choice.** The primary candidate is a model-based stabilizer (whole-body inverse dynamics or MPC) tracking references such as base velocity, footstep targets or COM targets. This trades some agility, relative to end-to-end RL stabilization, for determinism and fallback simplicity. We pre-declare a contingency: if the classical stabilizer cannot meet agility requirements, a compact learned stabilizer may be used, but it must execute *inside the RT domain*, not on the AI module. This keeps R1 intact.

**Arbitration.** With nominal policy output u_nom and reflex residual Δu_r,

> u_final = Π_safe( u_nom + clip(Δu_r, A(skill, x)) ),

where A is a skill- and state-dependent authority envelope and Π_safe is the RT validator/controller. Authority limits are enforced in the RT core; the AI module is not trusted to enforce its own bounds.

### 4.3 Independent Safety MCU

The MCU supervises (heartbeats of AI module and RT core, driver status, current, temperature, encoders, E-stop) and can constrain or disable actuation. It must not depend on Linux, CUDA, or middleware, and uses its own sensing where hardware permits. It is not expected to perform whole-body balance. If the RT core fails, mitigation is hardware-defined (passive damping, brakes, controlled torque-off, driver safe mode), which makes actuator selection a safety decision, not only a performance one.

### 4.4 State, Vision and Freshness

The system maintains separate, coordinated representations: S_phys (RT-owned), V_scene (visual features, object tracks), G_task, and S_pred. We deliberately avoid compressing vision into S_phys, because dexterous manipulation depends on visual detail that explicit object tracks omit.

Every asynchronous product carries `timestamp`, `sequence_id`, `source_id`, `frame_id` and `valid_until`. A consumer computes age a = t_now − t_stamp and applies a **per-skill** TTL:

> if a > TTL(skill): reject, down-weight, request refresh, or enter a degraded mode.

TTLs differ by task (tolerant for walking, tight for grasping), so no global value is used. Clocks use a common monotonic/hardware timebase within a domain and PTP or equivalent only where devices are distributed; the requirement is a known, measurable temporal relationship.

### 4.5 Hybrid Latency-Compensating Prediction

Total delay is decomposed rather than assumed:

> L_total = L_sensor + L_readout + L_transport + L_perception + L_state + L_prediction + L_policy + L_reference + L_RT + L_actuation.

The predictor targets *physical state*, not video, and uses known structure first:

> ŝ(t+Δ) = f_phys( s(t), a\_{t−d:t} ) + g_θ( s, a, c ),

where f_phys is kinematic or dynamics extrapolation over the known action buffer and actuation delay, g_θ is a learned residual, and c is a contact mode (free, foot, hand, object, impact, slip, recovery). The predictor also outputs uncertainty σ; high σ shortens the horizon, shifts reliance to current measurements, and may reduce motion aggressiveness. Δ is selected from measured L_total and task dynamics: longer horizons compensate more delay but accumulate more error, and contact discontinuities bound useful horizon length. The policy accepts S_pred as an *optional* input and is trained under the degraded configurations it may encounter.

### 4.6 Action Policy and Receding-Horizon Execution

The policy consumes task, V_scene, S_phys, optional S_pred and constraints, and emits a skill-specific **motion reference**: base velocity and footstep targets for walking; end-effector, posture and grip-force targets for manipulation; COM, foot placement and posture for recovery. Each reference declares type, frame, units, priority, constraints and `valid_until`; missing required fields cause rejection. Execution is receding-horizon: a \~250 ms reference is regenerated after executing a short initial window (\~40 ms, a tunable parameter), with blending that preserves position, velocity, acceleration and jerk limits. Flow matching may generate references, but it is not a safety mechanism or a substitute for feedback.

A **hybrid skill pathway** retains structured skills (testable, constrained) and a free-form pathway for long-tail tasks, both under identical lower-level control. This is an acknowledged generality-versus-verifiability tradeoff.

### 4.7 Bounded Reflex

The reflex maps fast proprioceptive, force, tactile and contact signals to a residual Δu_r. Its expected value is task-dependent: modern RL locomotion policies already learn disturbance rejection, so we treat a locomotion residual as an experiment, while contact-rich manipulation (slip, unexpected contact, collision) is the primary target. Candidate models (MLP, GRU, small state-space model, LNN/CfC) are compared under equal parameter budgets, inputs, data and latency. Training uses pushes, slips, impacts, sensor noise and dropout, and delay injection; recovery is considered learned only if demonstrated in evaluation. A fast non-learned layer (filtering, thresholds, impedance adjustment) may sit beneath the learned reflex.

### 4.8 Cognition and Event Management

The VLM outputs structured intent (task, skill, parameters, constraints), never actuator commands, and runs asynchronously. An event manager escalates expensive inference using semantic novelty, object motion, prediction error, physical anomalies and user input, plus **periodic low-cost coverage** so that slow or rare changes are not missed by a change detector alone. We deliberately replace raw pixel-entropy gating with semantic and physical signals, since ego-motion and lighting change every pixel.

### 4.9 Degradation and Fallback

Operating modes: FULL, COGNITIVE-, PREDICTION-, VISION-, POLICY-DEGRADED, AI-OFFLINE, RT-DEGRADED, HARDWARE-FAULT, EMERGENCY, with logged transitions. On AI loss or command expiry the RT core (i) rejects the stale reference, (ii) permits bounded extrapolation (finite, skill-specific window), then (iii) selects a fallback reference according to physical state: maintain posture if stable, decelerate if moving, run recovery if unstable but recoverable, apply fall-mitigation if falling, and use actuator-specific hardware safety on faults. Motor power cut is a last resort. Under compute or thermal pressure, intelligence is shed before control (VLM rate, then visual resolution, then background inference).

---

## 5. Interface Contracts

Interfaces are versioned and classify each field as REQUIRED, OPTIONAL (documented default), DEFAULTED, or FORBIDDEN; the RT core never silently infers missing critical fields.

**Table 2. Interface families.**

| Interface         | Key content                                                                                  |
| ----------------- | -------------------------------------------------------------------------------------------- |
| STATE_V1          | base pose/velocity, joint q/q̇, torque estimate, contact state/probability, COM, uncertainty |
| VISUAL_FEATURE_V1 | features, object info, confidence, `valid_until`                                             |
| TASK_V1           | skill type, target, parameters, constraints, priority, `valid_until`                         |
| ACTION_V1         | reference_type, frame, motion reference, constraints, confidence, `valid_until`              |
| CONTACT_V1        | contact state/probability/location, force estimate, confidence                               |
| SAFETY_V1         | enables, fault state, limits, E-stop, watchdog, heartbeats                                   |

Latent representations shared between models carry versioned contracts (e.g., LATENT_V1) to prevent silent distribution drift after an upstream update; explicit interfaces are preferred over undocumented latent coupling.

---

## 6. Deployment Feasibility Analysis

**Method.** A component is deployable only if memory (weights + activations + buffers + OS), worst-case compute, per-stage latency, communication (transport + queueing + jitter), thermal load and safety independence all pass their budgets. Capacity is necessary but not sufficient.

**Bandwidth.** For an effective working set of W GB read per inference at F Hz, streamed traffic is approximately W × F GB/s, an upper-level estimate since caching, quantization and kernel design change it. The Orin NX 16 GB has about 102 GB/s peak memory bandwidth shared across CPU and GPU (NVIDIA datasheet). A 2 GB model at 200 Hz would require \~400 GB/s, which is infeasible. This is why high-rate functions are assigned to small models (1–100M parameters) or to deterministic controllers, and why the design targets 25–50 Hz for the action policy.

**Planning targets (unmeasured).** Fast perception 10–50M parameters; semantic perception 50–300M; world model 20–100M; action policy 20–100M; reflex 1–10M; cognitive model \~1–3B quantized. Planning memory is \~9–11 GB of working allocation with several GB of headroom. Likely contention risks are VLM prefill, camera/ISP load and thermal throttling, not weights alone.

**Profiles.** The *Edge* profile (Orin NX) uses small specialized models and event-driven cognition. The *Generalist* profile uses a larger platform (e.g., a Jetson Thor-class system) for larger VLA and perception models. The control hierarchy is identical across profiles; only model capacity changes. A GR00T-class model serves as benchmark and teacher; a robot-specific student is trained with demonstrations and DAgger-style corrective rollouts (Ross et al., 2011; Hinton et al., 2015). Distillation success is a hypothesis, and the student is expected to be strongest on structured skills.

---

## 7. Evaluation Plan

We specify the protocol before running experiments.

**Hypotheses.**

- **H1 (contact reflex):** a bounded tactile/force residual improves slip recovery and contact-disturbance success over the same manipulation policy without it.
- **H2 (hybrid prediction):** hybrid prediction improves closed-loop performance under realistic latency over no prediction and physics-only prediction.
- **H3 (event-driven cognition):** event-driven escalation reduces expensive inference with bounded task-performance loss relative to scheduled inference.

**Ablation arms.** Prediction: (A) none, (B) kinematic extrapolation, (C) physics/dynamics, (D) learned residual only, (E) hybrid. Reflex: none, MLP, GRU, LNN/CfC. Cognition: fixed schedule versus event-driven. Baseline: perception + direct policy + RT Motion Core + safety MCU. Components are added incrementally, and any component without measurable benefit is removed without reopening the architecture.

**Metrics.** *Control:* mean, p99 and worst latency, deadline-miss rate, jitter, sensor-to-actuator latency. *Prediction:* position/velocity/COM error, contact classification, multi-step error growth, uncertainty calibration. *Reflex:* recovery success, reaction time, residual magnitude, overshoot, stability impact. *Locomotion:* fall rate, recovery rate, foot-placement error, COM tracking. *Manipulation:* success, slip recovery, contact-force error, placement error. *Hardware:* GPU/CPU use, bandwidth, power, temperature, throttling.

**Procedure.** Stage through simulation, offline replay of recorded streams (preserving timestamps, sequence IDs and data age), hardware-in-the-loop fault injection (sensor dropout, Orin shutdown, RT heartbeat loss, stale/invalid actions, encoder and current anomalies, E-stop), then supervised physical trials. Real-robot comparisons use fixed task setups, many trials per condition, and confidence intervals, since small differences are not detectable with few trials. Training conditions include estimator error, latency, timestamp jitter, dropped frames and stale features, not ground-truth state. Each run records robot, software, model and configuration versions, power mode and thermal state for reproducibility.

---

## 8. Safety and Standards

We assign no safety integrity or performance level before hazard analysis: application → hazard identification → risk assessment → safety functions → required risk reduction → applicable standards → verification. Applicability depends on deployment context: industrial legged robots fall within the scope of the in-development ISO 25785-1, while non-industrial service applications fall under ISO 13482 (whose revision status should be rechecked at submission). The safety path adds secure boot, signed firmware and models, authenticated updates, rollback and network isolation of the safety controller. Collision detection does not rely on vision alone (motor current, torque deviation, encoder error and force sensing contribute). Safe-state design and actuator selection (back-drivability, brakes, damping, contactor behavior) must be finalized together.

---

## 9. Discussion and Limitations

**Tradeoffs accepted.** Generality versus edge efficiency; structured skills versus free-form behavior; prediction horizon versus accuracy; reflex authority versus policy stability; stabilizer determinism versus agility.

**Limitations.**

1. *No empirical validation.* Every rate, latency and size is a target. The paper's claims are architectural and hypothetical.
2. *Engineering scope.* The RT core (estimator, stabilizer, impedance control, validator) plus actuators and safety MCU is a substantial stack that precedes any learned component.
3. *Handover under falling.* If the RT core fails, a biped may fall unless actuator hardware provides mitigation; this cannot be solved in software.
4. *Prediction at contact.* Impacts and slips are the cases where prediction is least reliable and most needed.
5. *Explicit-state bottleneck.* Dexterous manipulation needs visual features beyond S_phys, which increases coupling between perception and policy.
6. *Distillation and skill-library risks.* A small student may lose generality, and discrete skills may mis-handle compositional tasks.
7. *Novelty is modest.* The layers resemble practice at leading groups; the contribution is explicit contracts, authority rules and a falsifiable plan.

**Threats to validity** include simulation-to-real gaps, operator variability in demonstrations, hardware wear, and benchmark selection effects. **Reopening the architecture** is warranted only by structural failures (insufficient RT margin, Orin-to-RT timing, actuator failure behavior, stabilizer agility, physically infeasible interfaces), not by an underperforming learned module.

---

## 10. Conclusion

VAYN-6.2 argues that humanoid intelligence should be organized by timescale and reliability: large models reason, small models adapt quickly, deterministic controllers stabilize, and independent hardware supervises. Its central rule is that the AI stack may raise the robot's capability but must not determine whether the robot is controllable. The architecture's value will be settled by measurement. The next steps are selecting the RT hardware and actuator bus, defining ACTION_V1 and timing budgets, building the RT core and safety MCU, instrumenting the full stack, and running the pre-specified ablations.

---

## References

*(Verify details and add DOIs before submission.)*

- Black, K., et al. (2024). π0: A Vision-Language-Action Flow Model for General Robot Control. arXiv:2410.24164.
- Black, K., Galliker, M. Y., & Levine, S. (2025). Real-Time Execution of Action Chunking Flow Policies. arXiv:2506.07339.
- Chi, C., et al. (2023). Diffusion Policy: Visuomotor Policy Learning via Action Diffusion. RSS.
- Figure AI (2025). Helix: A Vision-Language-Action Model for Generalist Humanoid Control. Technical blog.
- Hafner, D., et al. (2023). Mastering Diverse Domains through World Models. arXiv:2301.04104.
- Hasani, R., et al. (2022). Closed-form continuous-time neural networks. Nature Machine Intelligence, 4.
- Hinton, G., Vinyals, O., & Dean, J. (2015). Distilling the Knowledge in a Neural Network. arXiv:1503.02531.
- Hogan, N. (1985). Impedance control: An approach to manipulation. J. Dynamic Systems, Measurement, and Control, 107(1).
- Hwangbo, J., et al. (2019). Learning agile and dynamic motor skills for legged robots. Science Robotics, 4(26).
- ISO 13482:2014. Robots and robotic devices — Safety requirements for personal care robots.
- ISO 13849-1:2023. Safety of machinery — Safety-related parts of control systems — Part 1.
- ISO/CD 25785-1. Robotics — Safety requirements for dynamically stable industrial mobile robots — Part 1: Robots (under development).
- Kumar, A., et al. (2021). RMA: Rapid Motor Adaptation for Legged Robots. RSS.
- Kuindersma, S., et al. (2016). Optimization-based locomotion planning, estimation, and control design for the Atlas humanoid robot. Autonomous Robots, 40.
- Lipman, Y., et al. (2023). Flow Matching for Generative Modeling. ICLR. arXiv:2210.02747.
- NVIDIA (2025). GR00T N1: An Open Foundation Model for Generalist Humanoid Robots. arXiv:2503.14734.
- NVIDIA. Isaac GR00T (N1.7), GitHub repository: github.com/NVIDIA/Isaac-GR00T.
- NVIDIA. Jetson Orin NX Series Modules Data Sheet.
- Ross, S., Gordon, G., & Bagnell, D. (2011). A reduction of imitation learning and structured prediction to no-regret online learning. AISTATS.
- Shukor, M., et al. (2025). SmolVLA: A Vision-Language-Action Model for Affordable and Efficient Robotics. arXiv:2506.01844.
- Tobin, J., et al. (2017). Domain randomization for transferring deep neural networks from simulation to the real world. IROS.
- Zhao, T. Z., et al. (2023). Learning Fine-Grained Bimanual Manipulation with Low-Cost Hardware. RSS.