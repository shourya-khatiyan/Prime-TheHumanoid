# RT Core Implementation Spec — VAYN 6.2.1

**What this is:** the build-and-test plan for the VAYN RT Motion Core on the real Phase-1 hardware.
**Architecture source:** [VAYN-6.2.1](../VAYN - 6.2.1.md), which defines the improvements I-1 to I-20 referenced here.
**Background:** [RT Core from fundamentals to advanced](RT Core - From Fundamentals to Advanced.md)
**Date:** 2026-10-20

**Rules for this document:**
- Every number is either **measured** (with the date and how), **from a repo file** (with the path), or a **target**, labelled as such.
- Commands that write to the ODESC are **run by you**, not by the agent. They are marked **[YOU RUN]**.
- Commands that change the laptop are reversible and marked **[HOST]**.

---

# 1. Scope

| In scope (Phase 1) | Later |
| ---| --- |
| One shoulder actuator on ODESC axis0, on a guarded, tethered rig | Elbow on ODESC axis1 (the design is ready for it) |
| RT core on the Dell Latitude 5490 | Dedicated RT computer |
| CAN 1 Mbit/s, ODESC firmware 0.5.1 | CAN-FD / EtherCAT / multi-bus (gate G-4) |
| Reference-pose homing (1A), then hall homing through a Sensor MCU (1B) | Output absolute encoder |
| Local (bench) references | Orin `ACTION_V1` over UDP (stub only) |
| Hardware E-stop and PSU current limit | Safety MCU, contactor, brake |

---

# 2. Hardware setup

## 2.1 Topology

```text
 Dell 5490 (RT core)
   │ USB
 USB-CAN adapter (isolated, hardware timestamps)  ── [120 Ω]
   │ CAN_H / CAN_L twisted pair, 1 Mbit/s
   ├── ODESC3.6 (node 0 = axis0 shoulder, node 1 = axis1 unused)
   ├── Sensor MCU (Phase 1B: hall input, later IMU / output encoders)
   └── Safety MCU (later, monitor only on CAN)               ── [120 Ω]

 Bench PSU 24 V (constant-current limit) ── latching E-stop (cuts PSU output) ── DC fuse ── ODESC DC bus
 ODESC USB ── laptop (commissioning, preflight check; not used at runtime)
```

- Terminate only the two physical ends of the bus with 120 Ω. First check whether the ODESC clone has on-board termination [S1][S2].
- Use twisted pair for CAN and keep it away from the motor phase leads. Join the grounds of the adapter, ODESC and MCUs (an isolated adapter breaks the laptop ground loop).
- AS5047P to ODESC over SPI on GPIO4 (CS). This is already configured; the encoder must be mechanically mounted on the motor before any closed-loop test.

## 2.2 Bench PSU settings (recommendation; PSU model unknown, gate G-10)

| Phase | Voltage | Current limit | Why |
| ---| ---| ---| --- |
| Commissioning, calibration | 24 V | 3 A | The GUI commissioning procedure starts at about 3 A (`odrive/docs/COMMISSIONING.md`) |
| Holding and slow motion tests | 24 V | 6 A | Matches the 6 A bring-up current limit |
| Characterization (later) | 24 V | up to about 10 A | Only after the thermal tests |

- The PSU cannot absorb regenerated energy. The ODESC sends regen into the 2 Ω brake resistor (`dc_max_negative_current = -0.01`, read live), so **measure the resistor with a multimeter** before any motion.
- Set the ODESC over-voltage trip to 28 V for a 24 V bus (§4).

---

# 3. Host preparation (Dell Latitude 5490)

The measured current state is in VAYN-6.2.1 §3.1. Every step below is reversible.

## 3.1 Packages .HOST]

```bash
sudo apt update
sudo apt install -y rt-tests stress-ng can-utils linuxptp ethtool \
  build-essential cmake ninja-build g++ gdb git pkg-config \
  libyaml-cpp-dev libgtest-dev python3-venv
```

`rt-tests` provides `cyclictest` and `hwlatdetect`. `rtla` is already installed.

## 3.2 BIOS (Dell setup, F2 at boot) .HOST]

| Setting | Value | Why |
| ---| ---| --- |
| Performance → Multi Core Support | All | 4 physical cores |
| Performance → Hyper-Threading | Disabled | Sibling threads share a core and add jitter [S3][S4] |
| Performance → C-States Control | Disabled (or keep enabled and use `/dev/cpu_dma_latency`, §3.6) | Deep C-states add wake-up latency |
| Performance → Intel SpeedStep / Turbo | SpeedStep on, Turbo off for repeatable timing | Repeatability; Turbo can be re-enabled after measuring |
| Power Management → Wake-on-LAN, USB wake | Disabled | Fewer firmware events |

Do **not** try to disable all SMIs; vendors warn this can break thermal protection [S5]. Measure them instead (§3.7).

## 3.3 Kernel boot parameters .HOST]

Create `/etc/default/grub.d/90-vayn-rt.cfg`:

```bash
GRUB_CMDLINE_LINUX_DEFAULT="$GRUB_CMDLINE_LINUX_DEFAULT nosmt isolcpus=domain,managed_irq,3 nohz_full=3 rcu_nocbs=3 irqaffinity=0-2 nowatchdog"
```

Then `sudo update-grub`, reboot, and verify:

```bash
cat /proc/cmdline
cat /sys/devices/system/cpu/isolated          # expect: 3
cat /sys/devices/system/cpu/nohz_full         # expect: 3
cat /sys/devices/system/cpu/smt/control       # expect: off or forceoff
```

To undo, delete the file and run `update-grub` again. Parameter meanings: [S3][S4][S6].

## 3.4 Real-time limits for the user .HOST]

Create `/etc/security/limits.d/90-vayn-rt.conf`:

```text
rt    -    rtprio     90
rt    -    memlock    unlimited
```

Log out and back in, then check `ulimit -r` (expect 90) and `ulimit -l` (expect unlimited).

## 3.5 Services and drivers .HOST]

```bash
# dell smm calls can stall a cpu for ~500 ms (kernel docs); do not load the fan driver
echo "blacklist dell_smm_hwmon" | sudo tee /etc/modprobe.d/90-vayn-rt.conf
# performance power profile while testing
powerprofilesctl set performance
# radios off during rt runs
rfkill block wifi bluetooth
```

- Keep `thermald` running. It protects the laptop. If `rtla timerlat` shows it disturbing CPU3, revisit.
- Always run on **AC power with the lid open**.

## 3.6 What the RT core does at start-up (code, not system config)

1. `mlockall(MCL_CURRENT | MCL_FUTURE)` and pre-fault the stack and buffers [S7][S8].
2. Open `/dev/cpu_dma_latency` and write `0`, keeping the file open for the run. This keeps the CPUs out of deep C-states only while the RT core runs, so it is reversible by design [S8].
3. Pin the servo thread to CPU3 and set `SCHED_FIFO` priority 80. Use priority 70 for `motion` and 60 for `comms`, on CPU2.
4. Run the loop with `clock_nanosleep(CLOCK_MONOTONIC, TIMER_ABSTIME, …)`. Never use relative sleeps or `CLOCK_REALTIME` [S7][S9].

## 3.7 Measurement procedure and acceptance (gate G-1)

| Test | Command | Acceptance (target) |
| ---| ---| --- |
| Firmware/SMI latency | `sudo hwlatdetect --duration=3600 --threshold=10` | max < 50 µs |
| Timer latency, isolated core, idle | `sudo cyclictest -m -p 80 -a 3 -t 1 -i 1000 -D 1h -h 400 -q` | max < 60 µs |
| Same, under load | add `stress-ng --cpu 3 --io 2 --vm 1 --vm-bytes 512M --taskset 0-2` | max < 100 µs over 24 h |
| Cause of any outlier | `sudo rtla timerlat top -c 3 -a 80 -d 10m` | stack trace explains every hit |

Record the kernel, BIOS settings and results in `rt_core/measurements/host-<date>.md`. If the targets are not met, the fallback is a 500 Hz servo rate (the budget doubles), then a different RT host.

---

# 4. ODESC configuration for RT use [YOU RUN]

Use the bench GUI (Console, which uses `odrivetool` syntax) or a pinned `odrive==0.5.1.post0` environment. The installed `odrive` 0.6.11 package could _read_ this 0.5.1 board, but the GUI pins 0.5.1.post0 for writes (`odrive/backend/pyproject.toml`).

Prerequisites:
- The motor encoder is mechanically mounted (the magnet holder pinned to the rotor cap, PCB on its bosses).
- The PSU is set to 24 V / 3 A.
- The E-stop is within reach.
- The gearbox output is free, or the arm is on the rig.

```python
# 1. bring-up limits (match the gui profile commissioning step)
odrv0.axis0.motor.config.current_lim = 6
odrv0.axis0.motor.config.calibration_current = 5
odrv0.axis0.controller.config.vel_limit = 2            # motor turn/s during bring-up
odrv0.config.dc_bus_overvoltage_trip_level = 28        # 24 v bus
odrv0.axis0.fet_thermistor.config.temp_limit_lower = 70
odrv0.axis0.fet_thermistor.config.temp_limit_upper = 85

# 2. re-do encoder offset calibration (encoder was re-mounted; old offset -153 is invalid)
odrv0.axis0.requested_state = 7                        # ENCODER_OFFSET_CALIBRATION, motor turns slowly
# check: odrv0.axis0.error == 0 and odrv0.axis0.encoder.is_ready == True
odrv0.axis0.encoder.config.pre_calibrated = True

# 3. can for the rt core
odrv0.can.set_baud_rate(1000000)                       # fw 0.5.1 api (0.5.2+ uses can.config.baud_rate)
odrv0.axis0.config.can_node_id = 0
odrv0.axis0.config.can_heartbeat_rate_ms = 10

# 4. watchdog (the rt core feeds it every cycle)
odrv0.axis0.config.watchdog_timeout = 0.05             # 50 ms
odrv0.axis0.config.enable_watchdog = True

# 5. control mode for level 1 (on-drive impedance)
odrv0.axis0.controller.config.control_mode = 3         # POSITION_CONTROL
odrv0.axis0.controller.config.input_mode = 1           # PASSTHROUGH
odrv0.axis0.controller.config.vel_integrator_gain = 0  # pure spring-damper, no integral windup
odrv0.axis0.controller.config.pos_gain = 5             # bring-up: soft (see section 12)
odrv0.axis0.controller.config.vel_gain = 0.05

odrv0.save_configuration()
odrv0.reboot()
```

Notes:
- After saving with the watchdog enabled, any tool that puts the axis in closed loop must feed it. The bench GUI does this itself (`odrive/docs/SAFETY.md`).
- If the GUI later saves its own watchdog settings, re-run step 4. The RT core preflight (§15) refuses to arm if the watchdog is off.
- Firmware 0.5.1 cannot change these settings over CAN, which is why they are fixed here and checked over USB before each run.

---

# 5. CAN bring-up

```bash
sudo ip link set can0 type can bitrate 1000000 restart-ms 100
sudo ip link set can0 txqueuelen 1000
sudo ip link set can0 up
candump -H -td can0            # hardware timestamps; expect heartbeat id 0x001 (node 0) every 10 ms
```

Checks:
1. A heartbeat from node 0 appears every 10 ms. Its payload is `<IB`: axis error (u32) and axis state (u8), per the 0.5.x codec in `odrive/backend/app/can_bus.py`.
2. An RTR poll `cansend can0 009#R` returns 8 bytes `<ff>`: position in turns and velocity in turns/s.
3. Before trusting the scaling, check the 0.5.1 `Set_Input_Pos` factors (vel_ff × 0.001, torque_ff × 0.001 per the 0.5.x CANSimple table [S10]). With the axis IDLE, send a frame and read back `input_pos`, `input_vel` and `input_torque` over USB.

---

# 6. Repository layout (this workspace, git)

```text
/home/rt/rt/
├── docs/                         existing docs (this file lives here)
└── rt_core/
    ├── CMakeLists.txt            c++20, -O2, -Wall -Wextra -Werror, sanitizer presets for sim builds
    ├── cmake/                    fetchcontent: ruckig (mit), mcap (mit), googletest
    ├── config/
    │   ├── joints/shoulder.yaml  rt-only settings + path and sha256 of the gui actuator profile
    │   └── host/dell5490.yaml    cpu ids, priorities, can interface
    ├── include/vayn/rt/          public headers (types, interfaces)
    ├── src/
    │   ├── core/                 pure step(): gate, arbiter, trajectory, impedance, guard, homing, state machines
    │   ├── io/                   socketcan wrapper, odrive cansimple 0.5.1 codec, sensor mcu codec
    │   ├── rt/                   thread setup, timing, cpu_dma_latency, watchdog of the servo loop
    │   ├── log/                  lock-free rings, mcap writer
    │   ├── config/               yaml loading, profile hashing, limit merge (tighten-only)
    │   └── app/                  vayn_rt_core main, cli
    ├── sim/                      actuator + odesc emulator, fake can bus
    ├── tools/                    python: preflight (usb read-only), can_sniff, log plots
    ├── tests/                    unit, property, replay, fault-injection
    └── measurements/             host and bus measurement reports
```

**Dependencies:**
- Ruckig: trajectory generation [S11][S12].
- MCAP: logging [S13][S14].
- yaml-cpp.
- GoogleTest.
- No ROS 2 in the RT process.
- Python tools use `python-can` and the pinned `odrive==0.5.1.post0`.

---

# 7. Threads and data flow

| Thread | Rate | CPU | Priority | Owns | Never does |
| ---| ---| ---| ---| ---| --- |
| `servo` | 1 kHz (500 Hz fallback) | 3 | FIFO 80 | all CAN TX/RX for actuators, `core::step()` | allocate, lock, file or network I/O, printf |
| `comms` | event | 2 | FIFO 60 | Orin UDP (later), Sensor/Safety MCU decode if on another bus | touch actuator frames |
| `motion` | 100–500 Hz (later) | 2 | FIFO 70 | WBC/MPC | write to CAN |
| `logger` | best effort | 0–1 | OTHER | drain rings to MCAP | anything in the control path |
| `supervisor` | 10 Hz | 0–1 | OTHER | CLI, operator commands, log rotation | block `servo` |

Hand-off between threads: lock-free single-producer/single-consumer rings (servo → logger, comms → servo) and triple buffers (latest reference). The servo thread reads the newest entry and never waits.

---

# 8. Core data types (sketch)

```cpp
// monotonic time in nanoseconds
using TimeNs = std::int64_t;

// one joint's measured state at the joint (si units)
struct JointState {
  double q, qd, tau_est;      // rad, rad/s, n*m
  TimeNs capture_time;        // adapter hardware rx timestamp of the feedback frame
  std::uint32_t drive_error;  // last heartbeat axis error
  std::uint8_t drive_state;   // last heartbeat axis state
  HomingState homing;
  bool valid;
};

// phase-1 reference type of action_v1
struct JointReference {
  std::uint64_t command_id;
  TimeNs timestamp, valid_until;
  double q_ref;               // required
  std::optional<double> qd_ref, tau_ff;
  Limits tighter;             // optional, can only tighten
  Authority source;           // local, ai, fallback
};

// what the servo sends to one drive this cycle (motor side)
struct DriveCommand {
  float pos_turns;            // set_input_pos
  std::int16_t vel_ff_milli;  // turn/s * 1000
  std::int16_t torque_ff_milli; // n*m * 1000
  bool request_idle;
};

// action_ack_v1 (from vayn 6.3)
struct ActionAck {
  std::uint64_t command_id;
  TimeNs received_at, accepted_at, committed_at;
  bool accepted, safety_clipped, residual_applied;
  double committed_q, following_error;
  ControllerMode mode;
  TimeNs valid_until;
};
```

All fields are SI at the joint. Conversion to motor units happens only in the drive codec (§10.3).

---

# 9. The servo cycle

```text
t0  wake (clock_nanosleep abs)          record wake latency
    drain socketcan rx (non-blocking)   heartbeat, encoder estimates (with hw timestamps), vbus, iq
    build Inputs{feedback, latest reference, operator cmds, t0}
    core::step(Inputs, State) -> Outputs   pure: estimate → homing → reference gate → arbiter
                                            → ruckig → impedance reference → output guard → state machines
    encode + send can frames            per joint: set_input_pos, rtr get_encoder_estimates
                                        every 100th cycle: rtr get_vbus_voltage, rtr get_iq
    push log record to ring             fixed-size, no allocation
    check own deadline                  overrun counter; 3 in a row -> controlled stop
    t0 += period
```

- **Pipelining.** Feedback polled in cycle k usually arrives before cycle k+1 and is used there, so the feedback-to-use delay is one period. The data age is computed from the hardware RX timestamp, not assumed.
- **Budget** (targets, VAYN-6.2.1 §7.1):
    - wake-up ≤ 100 µs
    - `step` ≤ 50 µs WCET
    - TX queueing ≤ 20 µs
    - bus 325 µs per joint
- `step` is measured with `CLOCK_MONOTONIC` around the call on every cycle and logged as a histogram.

---

# 10. ODESC CANSimple 0.5.1 driver

## 10.1 Messages used

CAN id = `node_id << 5 | cmd`, standard 11-bit, little-endian [S10] (codec also in `odrive/backend/app/can_bus.py`).

| Cmd | Name | Direction | Payload | Use |
| ---| ---| ---| ---| --- |
| 0x001 | Heartbeat | drive → host, every 10 ms | `<IB` axis_error, axis_state | drive health, state |
| 0x002 | Estop | host → drive | none | software stop: sets ESTOP_REQUESTED, drive disarms |
| 0x007 | Set_Axis_Requested_State | host → drive | `<I` | 1 IDLE, 8 CLOSED_LOOP_CONTROL |
| 0x009 | Get_Encoder_Estimates | RTR → reply | `<ff` pos turns, vel turns/s | feedback every cycle |
| 0x00C | Set_Input_Pos | host → drive | `<fhh` pos turns, vel_ff ×0.001 turn/s, torque_ff ×0.001 N·m | command every cycle |
| 0x014 | Get_Iq | RTR → reply | `<ff` setpoint, measured A | 10 Hz, torque estimate |
| 0x017 | Get_Vbus_Voltage | RTR → reply | `<f` | 10 Hz, power check |
| 0x018 | Clear_Errors | host → drive | none | operator-confirmed reset only |

- On 0.5.1, the "Get" messages are call-and-response with the RTR bit set [S10].
- Accepting DLC = 0 without RTR was only added in 0.5.5 (changelog [S15]).

## 10.2 Watchdog semantics

On firmware 0.5.x most (practically all) CAN messages to an axis feed the watchdog, including polls [S15][S16]. The RT core therefore sends commands and polls from the **same** `servo` thread. If the servo thread or process dies, traffic stops and the drive disarms after `watchdog_timeout` (50 ms). A dedicated test (§17) checks this.

## 10.3 Unit conversion (joint ↔ motor)

```text
p_motor[turn]  = s · q[rad] · N / (2π) + p_offset[turn]       s = joint sign (+1/-1), N = 30
v_motor[turn/s]= s · qd[rad/s] · N / (2π)
τ_motor[N·m]   = s · τ_joint / (N · η_ff)                     η_ff from characterization (default 0.87, unproven)
q[rad]         = s · (p_motor − p_offset) · 2π / N
```

- `p_offset` comes from homing (§11).
- `vel_ff` and `torque_ff` are clamped to the int16 range (±32.767) before scaling. At the output, the torque_ff resolution is 0.001 N·m × 30 × 0.87 ≈ 0.026 N·m.

## 10.4 Bus schedule and load

| Item | Bits (worst case) | Time at 1 Mbit/s |
| ---| ---| --- |
| `Set_Input_Pos` (8 bytes) | 135 | 135 µs |
| RTR request (0 bytes) | 55 | 55 µs |
| `Get_Encoder_Estimates` reply (8 bytes) | 135 | 135 µs |
| Per joint per cycle |  | 325 µs |

```text
load = f_servo · Σ_joints 325 µs  +  heartbeat (100 Hz · ~90 µs)  +  10 Hz polls
```

- 1 joint at 1 kHz is about 33%; 2 joints about 65%. The design ceiling is 70% (VAYN-6.2.1 §12).
- Frame sizes follow the standard CAN length formula [S17][S18].
- The bus-load estimator runs live, from the counted frames, and is logged.

## 10.5 Error handling

- **Drive faults.** A non-zero `axis_error` in the heartbeat sends the RT core to FAULT and logs the decoded flags. The flag names come from `odrive/backend/metadata/odrive-0.5.1.json`.
- **Missed replies.** A missing encoder reply for more than 5 cycles triggers a request for IDLE and FAULT.
- **CAN controller errors.** Error frames, bus-off and the SocketCAN `restart-ms` path are logged. Bus-off triggers FAULT.

---

# 11. Homing

## 11.0 Why this works

The gear train is an exact integer ratio: stage 1 is 1 + 90/18 = 6 and stage 2 is 1 + 72/18 = 5, so N = 30. Each output position therefore always corresponds to the same angle inside the motor turn, repeating every 12° of joint motion. The motor AS5047P is absolute within one turn. So once we know _which_ 12° sector the joint is in, the motor encoder gives the exact joint angle. This holds unless the gearbox is disassembled or skips a tooth.

**One-time calibration** (repeat after any gearbox or encoder re-assembly):
1. Put the joint precisely at the reference pose `q_ref`, measured with an inclinometer or jig.
2. Read the motor angle inside the turn: `φ_ref = frac(pos_estimate)`.
3. Store `φ_ref` in `shoulder.yaml`.

## 11.1 Phase 1A: reference-pose homing (no extra hardware)

1. The joint is UNHOMED and the axis IDLE. The operator moves the arm by hand to the marked reference pose, within ±6° (half a sector) of `q_ref`.
2. The operator runs `homing confirm`. The RT core polls `p = pos_estimate` (motor turns) and snaps it to the nearest motor position whose fraction equals `φ_ref`:

```text
d        = wrap_to_half( frac(p) − φ_ref )      # in [-0.5, 0.5) turn = placement error, at most ±6°
p_ref    = p − d                                # exact motor position of q_ref in this power cycle
p_offset = p_ref − s · q_ref · N / (2π)         # then q = s · (p − p_offset) · 2π / N
```

1. The result is accepted only if |d| < 0.4 turn (±4.8° at the joint), which leaves margin for backlash and placement error. The joint is now HOMED with motor-encoder precision, not operator precision.

## 11.2 Phase 1B: hall homing through a Sensor MCU (target)

The Sensor MCU:
- reads the DRV5033 (open-drain, 10 kΩ pull-up to 3.3 V, per `shoulder-bom.md`)
- timestamps each edge
- sends a CAN frame `{edge_count, level, t_edge_us}`
- samples on the RT core's SYNC frame

The RT core:
1. Arms with a soft impedance and a low current limit.
2. Runs a slow Ruckig sweep (for example 10°/s at the joint) toward the expected hall position.
3. On the edge, takes the motor position at the edge time by interpolating polled positions between cycles. It snaps that position as in 11.1, using `φ_hall` and `q_hall` in place of `φ_ref` and `q_ref`.
4. Stops and holds.

`q_hall` and `φ_hall` are calibrated once against the precise reference pose. The hall edge only needs to be repeatable within ±4.8°; this is tested 20 times (§17).

## 11.3 LOST

The joint goes to LOST if any of these happen:
- the ODESC reboots (the heartbeat stops and then returns, or the state resets)
- the heartbeat shows an encoder error
- feedback is missing beyond the hold time

LOST disables position control; the operator must home again.

---

# 12. Control levels

| Level | Who closes the loop | What the RT core sends | When |
| ---| ---| ---| --- |
| 0 | ODESC, configured by the GUI over USB | nothing | commissioning, characterization |
| 1 | ODESC 8 kHz position and velocity loops = on-drive impedance | `Set_Input_Pos` with v_ff and τ_ff (gravity) at 1 kHz | Phase 1 default (I-8) |
| 2 | RT core impedance, ODESC in torque mode | `Set_Input_Torque` | only after the delay is measured and the passivity check (§12.2) passes |

## 12.1 Level 1 gain mapping

With `vel_integrator_gain = 0`, ODrive's cascade is a spring and damper on the motor side:

```text
τ_motor = vel_gain · (pos_gain · (p_in − p) + v_ff − v) + τ_ff
K_joint ≈ N² · vel_gain · pos_gain / (2π)     [N·m/rad]
D_joint ≈ N² · vel_gain / (2π)                [N·m·s/rad]
```

| Gains | K_joint | D_joint |
| ---| ---| --- |
| pos_gain 20, vel_gain 0.1667 (current live values) | about 477 N·m/rad (8.3 N·m/deg) | about 23.9 N·m·s/rad |
| pos_gain 5, vel_gain 0.05 (bring-up recommendation) | about 35.8 N·m/rad (0.62 N·m/deg) | about 7.2 N·m·s/rad |

- Gearbox losses are ignored here; real stiffness at the joint is lower.
- The torque is still capped by the current limit: at 6 A, about 0.55 N·m at the motor, or about 14 N·m at the joint with η = 0.87.
- Damping ratio ζ = D / (2·√(K·J)). Joint inertia J is not yet known. As an illustration with an _assumed_ J of 0.2 kg·m² (arm about 0.09 kg·m² from the CAD masses, plus an unknown reflected rotor inertia), the bring-up gains give ζ ≈ 1.3 (well damped, natural frequency about 2 Hz). Measure J in the characterization tests and re-tune.
- On firmware 0.5.1, gains cannot be changed over CAN. Set them per session in the GUI and record them in the run log; the preflight reads them.

## 12.2 Level 2 entry check

The sampled-data passivity bound b > K·T/2 + |B| [S19][S20] is used with T = the measured loop period plus delay, b = the measured physical damping, and K, B = the host gains. Level 2 is enabled only if the chosen gains satisfy it with a safety factor of 2.

---

# 13. Trajectory, extrapolation and fallback

- **Ruckig** [S11][S12] runs inside `step()` with limits taken from the profile, tightened by the reference.
    - Phase-1 joint defaults (targets): v_max 60°/s, a_max 200°/s², j_max 2000°/s³. These are well below the profile's 360°/s.
- **Bounded extrapolation.** When `valid_until` passes, the RT core continues along the last target with Ruckig for up to **50 ms** (configurable per skill). After that, authority moves to FALLBACK.
- **Fallback references:**

| Fallback | What it does | Stop category |
| ---| ---| --- |
| HOLD | target = current position, v = 0, gravity τ_ff kept | SS2 |
| SS1 | Ruckig to v = 0 within the deceleration limit, then request IDLE (only on the rig) | Cat 1 |
| RETRACT | Ruckig to a configured safe pose, then HOLD | SS2 |

- **Gravity feed-forward for the v0 arm:** τ_g(q) = m·g·r·sin(q) with m·g·r = 3.26 N·m (arm horizontal, `arm/cad/calc.txt`). The elbow angle is ignored until the elbow is added. It is converted to motor τ_ff through §10.3.

---

# 14. Validation

## 14.1 Reference gate (input)

The gate checks:
- interface version
- required fields present
- frame = joint, units = SI
- `valid_until` > now and < now + 1 s
- `q_ref` inside the soft range
- |Δq_ref| per cycle below the velocity limit × period × 2
- no field that loosens a limit

A rejected reference is logged with a reason code. The previous valid reference keeps running until it expires.

## 14.2 Output guard (last line before CAN)

1. **Braking distance:** `q + qd·|qd| / (2·a_stop)` must lie inside \[q_min + m, q_max − m\]. Otherwise the guard switches to a stop-at-limit trajectory.
2. **Command limits:** |p_cmd − p| (following error), |v_ff| and |τ_ff| within the profile; slew limit on τ_ff.
3. **Thermal derating:** the torque command is scaled by the thermal model (14.3).
4. **Drive state:** frames are sent only if the joint state is ENABLED and homing is HOMED (or LOCAL low-current mode during homing).
5. **Following error:** |q_ref_committed − q| above `e_max` (target 3° in Phase 1) leads to SS1, then FAULT if it persists for 100 ms.

## 14.3 Thermal model (two-node)

```text
C_w · dT_w/dt = I² · R(T_w) − (T_w − T_h) / R_wh
C_h · dT_h/dt = (T_w − T_h) / R_wh − (T_h − T_a) / R_ha
R(T) = R_25 · (1 + 0.0039 · (T − 25))          (copper)
```

- I comes from `Get_Iq` (10 Hz) or from the command when no poll is available. R_25 = 0.0846 Ω (measured phase resistance).
- C_w, C_h, R_wh and R_ha are fitted from the GUI's thermal-hold test (6 / 8 / 12 A, `odrive/docs/COMMISSIONING.md`).
- Derating starts at a winding temperature of 80 °C; the command is cut to zero torque, via SS1, at 100 °C. These are the profile's `motor_warn_c` / `motor_abort_c`.

---

# 15. Configuration and preflight

## 15.1 `config/joints/shoulder.yaml` (RT-only settings)

```yaml
joint_id: shoulder_l
actuator_profile:
  path: ../Prime-TheHumanoid/odrive/backend/profiles/vayn_shoulder.yaml
  sha256: "<filled by tools/pin_profile.py>"
can:
  interface: can0
  node_id: 0
  bitrate: 1000000
servo:
  rate_hz: 1000
  fallback_rate_hz: 500
joint:
  sign: 1
  q_min_deg: -10        # placeholder until rig limits are measured
  q_max_deg: 120
  margin_deg: 3
homing:
  method: reference_pose      # reference_pose | hall
  q_ref_deg: 0
  phi_ref_turn: null          # one-time calibration (section 11.0)
  q_hall_deg: null
  phi_hall_turn: null
limits_tighten:               # may only be lower than the profile
  vel_deg_s: 60
  acc_deg_s2: 200
  jerk_deg_s3: 2000
  following_error_deg: 3
extrapolation_ms: 50
```

## 15.2 Preflight (read-only, over USB, before every run)

`tools/preflight.py` reads the live ODESC configuration and compares it with the profile and this file. The RT core refuses to leave PREFLIGHT unless every check passes:

| Check | Expected |
| ---| --- |
| hw / fw | 3.6-56V / 0.5.1 |
| `can` baud, node id, heartbeat | 1 000 000, 0, 10 ms |
| watchdog | enabled, 0.05 s |
| encoder | mode 257, cpr 16384, CS GPIO4, `pre_calibrated` True |
| motor | pole pairs 20, phase R within ±60% of 0.093 Ω (profile tolerance) |
| limits | `current_lim` ≤ profile, `vel_limit` ≤ profile, over-voltage trip ≤ 28 V |
| control | POSITION, PASSTHROUGH, `vel_integrator_gain` 0 |
| thermistor | FET limits 70 / 85 °C |
| profile hash | matches `shoulder.yaml` |

---

# 16. Logging

| Channel | Rate | Content |
| ---| ---| --- |
| `servo/timing` | 1 kHz | wake latency, step time, overruns |
| `joint/state` | 1 kHz | q, qd, τ_est, capture_time, age |
| `joint/command` | 1 kHz | committed reference, drive command, clip flags |
| `ack` | per reference | `ACTION_ACK_V1` |
| `drive/heartbeat` | 100 Hz | error, state |
| `drive/slow` | 10 Hz | vbus, Iq, thermal estimate |
| `can/bus` | 10 Hz | load %, error counters, round-trip histogram |
| `events` | on change | state transitions, faults, operator commands |
| `meta` | once | git sha, config files, profile sha256, host report |

- Format: MCAP [S13][S14], written by the `logger` thread from lock-free rings, one file per run.
- Retention: keep everything during Phase 1.

---

# 17. Simulation and test plan

## 17.1 Simulator (`sim/`)

The simulator emulates:
- the ODESC: an 8 kHz position/velocity/current cascade with the same gains, current limit, vel_limit, watchdog and heartbeat
- the motor: Kt, R, an L/R electrical lag and a thermal model
- the gearbox: N = 30, backlash 0.1–0.2°, Coulomb plus viscous friction, efficiency
- the arm: inertia and gravity (3.26 N·m)
- CAN timing: frame times, a configurable USB latency distribution and dropped frames

It runs the **same** `core::step()` through a fake SocketCAN, so the simulator and the hardware differ only in the I/O layer (I-18). The GUI's mock board (`odrive/backend/app/transport/mock.py`) is a cross-check reference.

## 17.2 Test list

| Group | Tests |
| ---| --- |
| Unit | codec round-trip, unit conversion, homing math (all sectors), braking-distance guard, tighten-only limit merge, state-machine transitions |
| Property | random references never exceed limits after the guard; no NaN reaches the codec |
| Timing | servo WCET histogram; 24 h host soak; CAN round-trip histogram with hardware timestamps |
| Fault injection (sim, then rig) | stale reference, invalid reference, CAN unplugged, ODESC power cycle, encoder error, RT process kill (watchdog must disarm in ≤ 50 ms + one heartbeat), 3 overruns, following-error trip, over-voltage, E-stop |
| Homing | 1A repeatability ×20; 1B hall repeatability ×20 (must be < ±4.8°) |
| Replay | re-run logged inputs through `step()`; outputs must match bit-for-bit |

---

# 18. Milestones and exit criteria

| ID | Milestone | Exit criteria (targets) |
| ---| ---| --- |
| P1.0 | Repo, build, simulator, `step()` skeleton | unit tests pass; simulated hold and step response look sane |
| P1.1 | Host tuned (§3) | G-1 met (§3.7) or fallback decided |
| P1.2 | ODESC commissioned: encoder mounted, offset re-calibrated, §4 config saved | GUI health check passes; preflight passes |
| P1.3 | CAN bring-up | heartbeat at 10 ms; RTR poll works; scaling verified; round-trip histogram recorded (G-2) |
| P1.4 | RT core drives the IDLE axis read-only over CAN | 1 h at 1 kHz with no missed feedback; bus load matches §10.4 within 10% |
| P1.5 | Level 1 hold, motor only (gearbox free) | holds position; watchdog kill test passes |
| P1.6 | Level 1 on the gearbox, arm on the rig, homing 1A | homing repeatable; hold with gravity feed-forward, following error < 1° |
| P1.7 | Slow motion with Ruckig, soft limits, fallbacks | all fault-injection tests pass on the rig |
| P1.8 | Characterization feeds back into the profile | measured Kt, η, friction, backlash, thermal constants committed (G-3) |
| P1.9 | Hall homing with the Sensor MCU (1B) | repeatability < ±4.8°, 20 runs |
| P1.10 | Phase-1 review | VAYN-6.2.1 gates G-1, G-2, G-3, G-5, G-6, G-10 closed |

---

# 19. Recommended purchases (Phase 1)

You decide what to buy; availability in India must be checked.

| # | Item | Spec to look for | Why |
| ---| ---| ---| --- |
| 1 | USB-CAN adapter (×2: bus + spare/sniffer) | Galvanically isolated; mainline SocketCAN driver (`gs_usb`/candleLight-compatible or PEAK `peak_usb`); hardware RX timestamps; CAN-FD capable for the future | No CAN on the laptop. Hardware timestamps are needed for honest timing [S21][S22] |
| 2 | Latching E-stop (mushroom, twist release, NC contacts) | Rated for the PSU DC output current, or switching a relay that is | Hardware E-stop is mandatory; on-screen buttons are not E-stops (`odrive/docs/SAFETY.md`) |
| 3 | DC fuse and holder | DC-rated, about 15 A for the bench | Wiring protection |
| 4 | Safety MCU board | STM32G4 Nucleo (for example NUCLEO-G474RE: 3× FDCAN, 170 MHz) | Matches earlier VAYN choices; independent watchdog, ADCs, GPIO for contactor/brake |
| 5 | Sensor MCU board | Small STM32G4 with FDCAN (for example NUCLEO-G431KB) | Hall homing (1B), later IMU and output encoders |
| 6 | CAN transceivers (×3) | 3.3 V, for example TJA1051T/3 or TCAN1042 modules | The Nucleo boards have no transceiver |
| 7 | 10 kΩ NTC (already in the BOM) | Glass bead, β about 3435–3950 | Winding temperature for the Safety MCU (gate G-6) |
| 8 | DC contactor or relay plus flyback diode | Coil driven by the Safety MCU through a driver; contacts rated for the bus current | Lets the Safety MCU remove power (Cat 0) |
| 9 | 120 Ω terminators, twisted-pair cable, connectors | — | Clean CAN physical layer |
| 10 | 8-channel USB logic analyzer (optional) | sigrok-compatible | Debugging SPI/CAN timing |

---

# 20. Risks

| Risk | Effect | Mitigation |
| ---| ---| --- |
| Laptop SMIs or USB jitter exceed the budget | 1 kHz not reachable | 500 Hz fallback; measure first (G-1, G-2); dedicated RT host later |
| Clone firmware behaves differently from official 0.5.1 | wrong scaling, watchdog or state behaviour | verify every message on the bench (§5) before closed loop |
| A drive fault drops the arm | damage or injury | guarded, tethered rig only; brake decision G-9 |
| Unmeasured Kt, η, J | poor gravity compensation and tuning | characterization in P1.8 before raising gains |
| Encoder mounting runout above 0.5 mm | noisy commutation | CAD budget 0.22 mm RSS (`shoulder/cad/calc.txt` §9); GUI encoder-noise check (< 3 counts) |

---

# 21. References

- [S1] ODrive docs, "CAN Bus Guide" (twisted pair, 120 Ω termination at both ends). [https://docs.odriverobotics.com/v/0.5.6/can-guide.html](https://docs.odriverobotics.com/v/0.5.6/can-guide.html)
- [S2] ODrive Community, ODESC CAN wiring and termination differences. [https://discourse.odriverobotics.com/t/request-for-review-of-my-can-bus-wiring-diagram/12150](https://discourse.odriverobotics.com/t/request-for-review-of-my-can-bus-wiring-diagram/12150)
- [S3] Intel ECI docs, "Real-Time Scheduling on Linux". [https://eci.intel.com/docs/3.3/development/performance/rt_scheduling.html](https://eci.intel.com/docs/3.3/development/performance/rt_scheduling.html)
- [S4] TechVeda, "SCHED_FIFO and CPU Isolation on Real-Time Linux — Part 3" (isolcpus, nohz_full, irqaffinity, rtla). [https://www.techveda.live/2026/07/05/sched-fifo-cpu-isolation-part-3/](https://www.techveda.live/2026/07/05/sched-fifo-cpu-isolation-part-3/)
- [S5] Red Hat, RHEL for Real Time 8, "Running and interpreting hardware and firmware latency tests" (do not disable SMIs completely).
- [S6] Linux kernel admin guide, kernel parameters (`nosmt`, `isolcpus`, `nohz_full`, `rcu_nocbs`, `irqaffinity`). [https://docs.kernel.org/admin-guide/kernel-parameters.html](https://docs.kernel.org/admin-guide/kernel-parameters.html)
- [S7] Linux kernel docs, "Real-time application monitors". [https://docs.kernel.org/trace/rv/monitor_rtapp.html](https://docs.kernel.org/trace/rv/monitor_rtapp.html)
- [S8] [realtime-linux.org](http://realtime-linux.org), "A Checklist for Real-Time Applications in Linux". [https://realtime-linux.org/a-checklist-for-real-time-applications-in-linux/](https://realtime-linux.org/a-checklist-for-real-time-applications-in-linux/)
- [S9] J. Ogness, ELC-E 2020 real-time checklist. [https://ogness.net/ese2020/ese2020_johnogness_rtchecklist.pdf](https://ogness.net/ese2020/ese2020_johnogness_rtchecklist.pdf)
- [S10] ODrive docs 0.5.4 / 0.5.6, CAN Protocol (message table, factors, RTR). [https://docs.odriverobotics.com/v/0.5.6/can-protocol.html](https://docs.odriverobotics.com/v/0.5.6/can-protocol.html)
- [S11] Berscheid and Kröger, RSS 2021 (Ruckig). [https://www.roboticsproceedings.org/rss17/p015.html](https://www.roboticsproceedings.org/rss17/p015.html)
- [S12] Ruckig repository. [https://github.com/pantor/ruckig](https://github.com/pantor/ruckig)
- [S13] MCAP specification. [https://github.com/foxglove/mcap](https://github.com/foxglove/mcap)
- [S14] ros2/rosbag2 default storage `mcap`. [https://github.com/ros2/rosbag2](https://github.com/ros2/rosbag2)
- [S15] ODrive docs 0.5.6 Changelog (0.5.2 cyclic encoder messages, 0.5.4 gains over CAN, 0.5.5 DLC = 0 polls, 0.5.6 homing fix). [https://docs.odriverobotics.com/v/0.5.6/changelog.html](https://docs.odriverobotics.com/v/0.5.6/changelog.html)
- [S16] ODrive 0.6 Changelog ("previously, all CAN messages fed the watchdog timer unconditionally"). [https://docs.odriverobotics.com/v/latest/changelog.html](https://docs.odriverobotics.com/v/latest/changelog.html)
- [S17] Nolte et al., bit-stuffing in CAN analysis (135 bits for 8 bytes). [http://www.es.mdh.se/pdf_publications/298.pdf](http://www.es.mdh.se/pdf_publications/298.pdf)
- [S18] Vector, CAN bit stuffing. [https://certification.vector.com/mod/page/view.php?id=349](https://certification.vector.com/mod/page/view.php?id=349)
- [S19] Colgate and Schenkel 1997, passivity of sampled-data systems.
- [S20] Colgate and Brown 1994, Z-width. [https://cim.mcgill.ca/~hayward/Teach/papers/Part-II/Colgate-Brown-94.pdf](https://cim.mcgill.ca/~hayward/Teach/papers/Part-II/Colgate-Brown-94.pdf)
- [S21] Linux `gs_usb` driver (hardware timestamp support since 6.1). [https://github.com/torvalds/linux/blob/master/drivers/net/can/usb/gs_usb.c](https://github.com/torvalds/linux/blob/master/drivers/net/can/usb/gs_usb.c)
- [S22] J. Whittington, "Adding gs_usb hardware timestamping" (hardware vs software timestamp jitter). [https://engineer.john-whittington.co.uk/programming/2023/01/07/socketcan-gsusb-timestamping.html](https://engineer.john-whittington.co.uk/programming/2023/01/07/socketcan-gsusb-timestamping.html)

---

# 22. Implementation status (2026-10-27)

**Code** (`rt_core/`, see its README):
- CANSimple 0.5.1 codec, joint/motor units, homing snap, output guard, two-node thermal model, lifecycle state machine
- RT helpers (mlockall, CPU pinning, SCHED_FIFO, `cpu_dma_latency`, absolute-time timer, latency histogram)
- SocketCAN with hardware RX timestamps
- simulated ODESC 0.5.1 + LA8308 + 30:1 + arm
- tools: `vayn_rt_timing_probe`, read-only `vayn_rt_can_probe`, read-only `tools/preflight.py`
- 36 unit and closed-loop simulator tests; all pass, also under address and undefined-behaviour sanitizers

**Simulator results** (same codec, 1 kHz loop):
- holding 45° with gravity feed-forward: error under 0.2°
- without feed-forward: sag equals τ_g / K_joint, as predicted in §12.1
- host stops sending: the watchdog disarms within 50 ms and the arm falls
- RTR polls alone keep a 0.5.x drive armed, confirming §10.2
- reference-pose homing through CAN: recovers the true angle to within 0.01°

**Host scripts** (`rt_core/host/`):
- `setup_host.sh` automates §3.1 and §3.3–3.5, and `revert_host.sh` undoes it.
- **Additions beyond §3:**
    - a `realtime` group with a udev rule, so the RT core can hold `/dev/cpu_dma_latency` without root
    - a boot service that turns turbo off and sets the performance EPP
    - a udev rule that brings any USB-CAN adapter up at 1 Mbit/s
- **BIOS:** §3.2 is replaced by kernel and runtime settings (`nosmt`, `cpu_dma_latency`, turbo off), so no BIOS change is needed.
- **Wi-Fi:** the script does not block Wi-Fi; turn radios off manually for the final measurements.
- `check_host.sh` verifies the result without root, and `measure_host.sh` runs the §3.7 measurements.

**Baseline before host setup:**
- `vayn_rt_timing_probe`, 1 kHz, untuned, no RT priority: maximum wake-up latency 3.4–5.3 ms, 82–89 missed deadlines in 10 s
- target: under 100 µs and 0 missed deadlines; re-measured after setup

**Preflight against the 2026-10-20 ODESC read-out:**
- 17/30 checks pass
- the 13 failures are exactly the §4 settings: CAN baud, heartbeat, watchdog, `pre_calibrated`, current/velocity/over-voltage/FET limits, control mode, gains
