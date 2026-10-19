/** firmware metadata helpers: units, docs, enum names, 64-bit error flag decoding, and actionable resolution guides */

export type PropMeta = { type: string; access: 'r' | 'rw'; unit?: string; brief?: string; doc?: string; enum?: string }
export type EnumDef =
  | { kind: 'enum'; values: Record<string, number>; docs: Record<string, string> }
  | { kind: 'flags'; nullflag: string; bits: Record<string, string>; docs: Record<string, string> }
export type Metadata = {
  fw: string
  props: Record<string, PropMeta>
  funcs: Record<string, { in: { name: string; type: string }[]; out: { name: string; type: string }[]; doc: string }>
  enums: Record<string, EnumDef>
}

export type ErrorGuide = {
  summary: string
  why: string
  fix: string
  fixes?: { label: string; kind: 'write' | 'job' | 'clear'; path?: string; value?: unknown; job?: string; params?: Record<string, unknown> }[]
}

const GUIDES: Record<string, ErrorGuide> = {
  INVALID_STATE: {
    summary: 'Axis refused the requested state because a prerequisite calibration flag is false.',
    why: 'Closed-Loop Control (state 8) requires both motor.is_calibrated = true AND encoder.is_ready = true.',
    fix: 'Keep the encoder mounted over the rotor magnet, run Encoder Offset Calibration (or Full Calibration), then enter Closed Loop.',
    fixes: [{ label: 'run encoder offset cal', kind: 'job', job: 'calibrate', params: { kind: 'encoder', mark_precalibrated: true } }],
  },
  MOTOR_FAILED: {
    summary: 'The motor subsystem tripped a fault and disarmed the PWM stage.',
    why: 'Triggered whenever axis.motor.error is non-zero (see the MOTOR error row for the exact cause).',
    fix: 'Resolve the underlying motor.error flag below, then click Clear Errors.',
  },
  ENCODER_FAILED: {
    summary: 'The encoder subsystem tripped a fault and invalidated position/velocity feedback.',
    why: 'Triggered whenever axis.encoder.error is non-zero (see the ENCODER error row for the exact cause).',
    fix: 'Resolve the underlying encoder.error flag below, then click Clear Errors.',
  },
  CONTROLLER_FAILED: {
    summary: 'The motion controller tripped a safety check (such as OVERSPEED or SPINOUT) and disarmed the motor.',
    why: 'Triggered whenever axis.controller.error is non-zero (see the CONTROLLER error row below).',
    fix: 'Raise vel_limit if the speed trip was too low, or lower gains if the motor oscillated.',
  },
  WATCHDOG_TIMER_EXPIRED: {
    summary: 'The safety watchdog timer expired without receiving a heartbeat from the host.',
    why: 'The USB/serial link paused or a blocking operation starved the watchdog feed.',
    fix: 'Click Clear Errors to reset.',
  },
  DC_BUS_OVER_VOLTAGE: {
    summary: 'DC bus voltage rose above config.dc_bus_overvoltage_trip_level.',
    why: 'Regenerative braking pumped energy into the bus or the overvoltage trip level is set lower than your supply.',
    fix: 'Verify the 2.0 Ohm brake resistor is wired to AUX, or raise dc_bus_overvoltage_trip_level (54 V for 12S).',
    fixes: [{ label: 'set ov_trip = 54V', kind: 'write', path: 'config.dc_bus_overvoltage_trip_level', value: 54 }],
  },
  DC_BUS_UNDER_VOLTAGE: {
    summary: 'DC bus voltage dropped below config.dc_bus_undervoltage_trip_level.',
    why: 'The power supply current-limited/sagged under load or main DC power was turned off.',
    fix: 'Increase bench PSU current limit or check DC bus wiring.',
  },
  OVERSPEED: {
    summary: 'Motor speed exceeded controller.config.vel_limit × vel_limit_tolerance.',
    why: 'In Position mode, pushing the shaft away by hand or commanding a large step makes the controller snap back at high speed (or hand movement alone exceeds vel_limit).',
    fix: 'Raise vel_limit (e.g. 20–30 turn/s), increase vel_limit_tolerance (e.g. 1.5), or disable enable_overspeed_error while back-driving by hand.',
    fixes: [
      { label: 'set vel_limit = 20 t/s', kind: 'write', path: 'axis0.controller.config.vel_limit', value: 20 },
      { label: 'set vel_limit = 30 t/s', kind: 'write', path: 'axis0.controller.config.vel_limit', value: 30 },
      { label: 'disable overspeed trip', kind: 'write', path: 'axis0.controller.config.enable_overspeed_error', value: false },
    ],
  },
  CONTROL_DEADLINE_MISSED: {
    summary: 'The 8 kHz PWM interrupt fired before the control loop finished computing the next PWM timings.',
    why: 'Secondary symptom that occurs on the exact cycle the controller aborts from OVERSPEED or another fault and stops enqueuing PWM timings.',
    fix: 'Fix the primary fault (such as OVERSPEED) and click Clear Errors.',
  },
  CURRENT_LIMIT_VIOLATION: {
    summary: 'Measured phase current exceeded motor.config.current_lim + current_lim_margin.',
    why: 'Most often a wrong encoder cpr (e.g. 4096 set for the AS5047P A/B/Z output, which is 4000): commutation drifts as the rotor turns until torque reverses and current runs away. Also aggressive gains, a mechanical impact, or encoder noise.',
    fix: 'First run an open-loop spin of 2+ turns and check counts/turn equals cpr. Only if cpr is right: increase current_lim_margin (e.g. 12 A), lower current_control_bandwidth (250–500), or raise current_lim.',
    fixes: [
      { label: 'set current_lim_margin = 12 A', kind: 'write', path: 'axis0.motor.config.current_lim_margin', value: 12 },
      { label: 'set current_lim = 15 A', kind: 'write', path: 'axis0.motor.config.current_lim', value: 15 },
    ],
  },
  PHASE_RESISTANCE_OUT_OF_RANGE: {
    summary: 'Measured motor phase resistance is outside plausible bounds or needed more voltage than resistance_calib_max_voltage.',
    why: 'Motor phase wires (A/B/C) are loose, or calibration_current × R exceeded resistance_calib_max_voltage.',
    fix: 'Check the 3 motor phase screw terminals and set resistance_calib_max_voltage = 4.0 V.',
    fixes: [{ label: 'set r_cal_vmax = 4 V', kind: 'write', path: 'axis0.motor.config.resistance_calib_max_voltage', value: 4 }],
  },
  CPR_POLEPAIRS_MISMATCH: {
    summary: 'During encoder offset calibration, the measured encoder count change did not match (scan_distance / (2π × pole_pairs)) × cpr.',
    why: '1) cpr does not match the encoder (AS5047P: 4000 on A/B/Z, 16384 on SPI) or pole_pairs is wrong; 2) the encoder PCB/magnet moved, tilted, or was not rigidly fixed over the shaft center during the scan; or 3) calib_range (default 2%) is too tight for motor cogging.',
    fix: 'Check counts/turn with an open-loop spin first; widening calib_range hides a wrong cpr. Then mount the AS5047P centered 1–2 mm above the magnet, widen calib_range to 0.15 and re-run Encoder Offset Calibration.',
    fixes: [
      { label: 'relax calib_range (0.15) & re-calibrate', kind: 'job', job: 'calibrate', params: { kind: 'encoder', mark_precalibrated: true } },
      { label: 'set calib_range = 0.15', kind: 'write', path: 'axis0.encoder.config.calib_range', value: 0.15 },
    ],
  },
  NO_RESPONSE: {
    summary: 'The motor rotated during calibration, but encoder shadow_count changed by less than 8 counts.',
    why: '1) The encoder PCB is not over the rotating motor magnet; 2) encoder.config.mode does not match the wiring (INCREMENTAL (0) for A/B/Z on J4, SPI_ABS_AMS (257) for SPI); or 3) the A/B wires are loose.',
    fix: 'Position the AS5047P chip directly over the motor shaft magnet (1–2 mm gap) and run Encoder Offset Calibration.',
    fixes: [{ label: 'run encoder offset cal', kind: 'job', job: 'calibrate', params: { kind: 'encoder', mark_precalibrated: true } }],
  },
  BRAKE_RESISTOR_DISARMED: {
    summary: 'The brake resistor was disarmed by an earlier fault, so the axis refuses to arm the motor.',
    why: 'A system fault (often regen current the bench PSU cannot sink, after a hard stop from high speed or torque) disarms the brake resistor. fw 0.5.1 re-arms it only at boot; 0.5.2+ also on clear_errors.',
    fix: 'Click Clear Errors and confirm the reboot, then run Encoder Offset again before closed loop. Avoid commanding speeds above what the bus voltage allows (~25 turn/s at 20 V).',
    fixes: [{ label: 'clear errors (reboots on fw 0.5.1)', kind: 'clear' }],
  },
  INDEX_NOT_FOUND_YET: {
    summary: 'use_index is on, but the encoder index (Z) pulse has not been seen since boot.',
    why: 'With use_index = true the firmware refuses encoder offset calibration and closed loop until an index search (state 6) has crossed the Z pulse. index_found resets at every reboot.',
    fix: 'Run Index Search (Encoder Offset also searches first). If the search itself fails, check the encoder I/PWM -> J4 Z wire.',
    fixes: [{ label: 'index search + offset cal', kind: 'job', job: 'calibrate', params: { kind: 'encoder', mark_precalibrated: true } }],
  },
  ABS_SPI_COM_FAIL: {
    summary: 'More than 0.5% of 16-bit SPI packets from the AS5047P failed parity or had the Error Flag (EF) bit set.',
    why: 'Loose SCK/MISO/MOSI/CSn jumper pins, missing 3.3V/GND, EMI from motor phase wires, or AS5047P latch-up after a power glitch.',
    fix: 'Check J3/J4 SPI jumper pins, separate encoder wires from motor phase leads, and power-cycle the 5V/3.3V encoder supply if latched.',
  },
}

/** return detailed plain-English explanation and one-click fixes for an ODrive error flag */
export function explainFlag(meta: Metadata | null, path: string, flag: string): ErrorGuide {
  const g = GUIDES[flag]
  if (g) return g
  const raw = flagDoc(meta, path, flag)
  return {
    // firmware docs wrap mid-sentence, so take the first sentence rather than the first line
    summary: raw ? raw.replace(/\s+/g, ' ').split(/(?<=\.) /)[0] : `Hardware fault flag ${flag} on ${path}.`,
    why: raw || 'See ODrive error register documentation.',
    fix: 'Fix the underlying condition and click Clear Errors.',
  }
}

export type TermGuide = { title: string; desc: string; range?: string }

const GLOSSARY: Record<string, TermGuide> = {
  vbus: { title: 'VBUS (DC Bus Voltage)', desc: 'Main DC supply voltage measured across the ODrive bus capacitors.', range: '18.0–52.0 V (6S–12S LiPo)' },
  ibus: { title: 'IBUS (DC Bus Current)', desc: 'Total DC current drawn from (positive) or returned to (negative) the power supply.', range: '0–12 A continuous' },
  power: { title: 'Electrical Bus Power', desc: 'Instantaneous DC electrical power (Vbus × Ibus) drawn from the supply.', range: 'W (Watts)' },
  pos: { title: 'Motor Shaft Position', desc: 'Multi-turn rotor position measured by the encoder in motor shaft revolutions.', range: 'turns (1 turn = 360° motor = 12° joint at 30:1)' },
  pos_set: { title: 'Position Setpoint', desc: 'Target rotor position the closed-loop controller is actively tracking.', range: 'turns' },
  vel: { title: 'Motor Shaft Velocity', desc: 'Rotor angular speed estimated by the encoder PLL in motor revolutions per second.', range: 'turn/s (1 turn/s = 60 RPM = 12°/s joint)' },
  iq: { title: 'Iq (Quadrature Torque Current)', desc: 'Measured torque-producing phase current in the rotor d-q frame. Proportional to motor torque (τ = Iq × Kt).', range: '±12 A continuous / ±30 A peak' },
  iq_set: { title: 'Iq Setpoint', desc: 'Commanded torque-producing phase current from the velocity/torque controller.', range: 'Amps (A)' },
  id: { title: 'Id (Direct Field Current)', desc: 'Non-torque field-weakening current along the rotor magnet axis (kept at 0 A for normal PMSM operation).', range: '0 A nominal' },
  fet: { title: 'MOSFET Inverter Temperature', desc: 'On-board NTC thermistor reading of the DRV8301 power MOSFET bridge.', range: 'Warn > 70 °C, Abort > 85 °C' },
  'fet 0/1': { title: 'Axis 0 / Axis 1 MOSFET Temps', desc: 'Temperature of the power MOSFET bridges on M0 and M1.', range: '< 70 °C normal' },
  thermal: { title: 'Inverter Thermal Margin', desc: 'MOSFET bridge temperature relative to the 85 °C safety shutoff limit.', range: '25–85 °C' },
  load: { title: 'Phase Current Load', desc: 'Present motor phase current (Iq) as a fraction of the peak current envelope.', range: '0–30 A' },
  angle: { title: 'Output Joint Angle', desc: 'Actuator output angle after the 30:1 two-stage planetary reduction (6:1 × 5:1; motor_turns × 360° / 30).', range: 'degrees (°)' },
  torque: { title: 'Estimated Output Joint Torque', desc: 'Output torque at the 30:1 planetary joint (Iq × Kt × 30 × efficiency).', range: 'Nm (30 Nm cont / 50 Nm proof)' },
  envelope: { title: 'Joint Torque Envelope', desc: 'Present joint output torque relative to the 50 Nm proof actuator capability.', range: '0–50 Nm' },
  ratio: { title: 'Gearbox Reduction Ratio', desc: 'Two-stage planetary reduction (Stage 1 = 6:1, Stage 2 = 5:1 -> 30:1 overall) from the 90KV LA8308 motor to the shoulder output.', range: '30:1 (6:1 × 5:1, 87% efficiency)' },
  shaft: { title: 'Mechanical Shaft Angle', desc: 'Single-turn absolute rotor angle from the 14-bit AS5047P magnetic sensor (pos_abs / 16384 × 360°).', range: '0.0–360.0°' },
  abs: { title: 'pos_abs (Raw 14-Bit SPI Angle)', desc: 'Raw 14-bit absolute angle word read over SPI from the AS5047P sensor within one revolution.', range: '0–16383 counts' },
  cnt: { title: 'count_in_cpr', desc: 'Encoder count wrapped modulo CPR (16384 counts per revolution).', range: '0–16383 counts' },
  spi: { title: 'SPI Packet Health', desc: 'Percentage of 16-bit SPI angle frames passing even-parity and command-error checks (100% − spi_error_rate).', range: '99–100% healthy' },
  brake: { title: 'AUX Brake Resistor Chopper', desc: '2.0 Ω power resistor across AUX that dissipates regenerative braking energy so DC bus voltage does not spike.', range: 'ARMED (2.0 Ω)' },
  rate: { title: 'Telemetry Sample Rate', desc: 'Live streaming frequency of batched property reads over USB/Serial.', range: '50–100 Hz over USB' },
  alarms: { title: 'Active Hardware & Safety Alarms', desc: 'Count of unacknowledged axis, motor, encoder, controller, or safety-monitor faults.', range: '0 = nominal' },
  link: { title: 'Controller Transport Link', desc: 'Active physical communication channel to the ODESC 3.6 (USB native Fibre, ASCII serial, or SIM).', range: 'USB preferred' },
  idle: { title: 'AXIS_STATE_IDLE (State 1)', desc: 'De-energizes all 6 MOSFETs so the motor phases float freely with zero torque.', range: 'Safe resting state' },
  open: { title: 'Open-Loop Spin (State 9)', desc: 'Rotates a fixed-current magnetic field vector without using encoder feedback.', range: '0.5–12 A' },
  loop: { title: 'AXIS_STATE_CLOSED_LOOP_CONTROL (State 8)', desc: 'Energizes the motor with full FOC feedback from the AS5047P encoder.', range: 'Requires motor cal + encoder ready' },
  'closed loop': { title: 'Closed-Loop FOC Control (State 8)', desc: 'Actively regulates torque, velocity, or position using live AS5047P encoder feedback.', range: 'Requires motor_cal & enc_ready' },
  'motor r/l': { title: 'Motor Phase R / L Calibration (State 4)', desc: 'Injects a test current to measure stator phase resistance (R ≈ 84 mΩ) and inductance (L ≈ 37 µH), then tunes current PI gains.', range: '~3 seconds (motor beeps)' },
  'encoder offset': { title: 'Encoder Offset Calibration (State 7)', desc: 'Slowly sweeps the rotor forward and backward to align the encoder zero angle with the motor magnetic poles.', range: '~5 seconds (sets is_ready = true)' },
  'index search': { title: 'Encoder Index Search (State 6)', desc: 'Turns the motor slowly until the encoder Z (index) pulse is seen. Needed after every reboot when use_index is on, before closed loop.', range: 'up to 5 motor turns (~16 s)' },
  full: { title: 'Full Calibration Sequence (State 3)', desc: 'Runs Motor R/L Calibration (State 4), an Index Search (State 6) when use_index is on, then Encoder Offset Calibration (State 7).', range: '~8 seconds total (+ index search)' },
  pos_gain: { title: 'pos_gain (Position P Gain)', desc: 'Outer position loop proportional gain: converts position error (turns) into a velocity command (turn/s). Higher = stiffer position hold.', range: 'Typical: 10–30 [(turn/s) / turn]' },
  vel_gain: { title: 'vel_gain (Velocity P Gain)', desc: 'Velocity loop proportional gain: converts speed error (turn/s) into motor torque (Nm). Too high causes buzzing/vibration.', range: 'Typical: 0.08–0.30 [Nm / (turn/s)]' },
  vel_integrator_gain: { title: 'vel_integrator_gain (Velocity I Gain)', desc: 'Velocity loop integral gain: eliminates steady-state speed or position droop under constant load.', range: 'Typical: 0.15–0.60 [Nm / (turn/s · s)]' },
  input_filter_bandwidth: { title: 'input_filter_bandwidth', desc: '2nd-order low-pass filter cutoff frequency applied to step position commands when input_mode = POS_FILTER.', range: '1–50 Hz (default 2 Hz)' },
  vel_ramp_rate: { title: 'vel_ramp_rate', desc: 'Maximum acceleration rate when input_mode = VEL_RAMP.', range: 'turn/s² (default 1.0)' },
  torque_ramp_rate: { title: 'torque_ramp_rate', desc: 'Maximum torque slew rate when input_mode = TORQUE_RAMP.', range: 'Nm/s (default 0.01)' },
  'vel_limit (max speed)': { title: 'vel_limit (Maximum Speed Limit)', desc: 'Caps closed-loop velocity commands and sets the base threshold for OVERSPEED trips (vel_limit × vel_limit_tolerance).', range: '2–30 turn/s (120–1800 RPM)' },
  vel_limit: { title: 'vel_limit (Maximum Speed Limit)', desc: 'Caps closed-loop velocity commands and sets the base threshold for OVERSPEED trips.', range: '2–30 turn/s' },
  vel_limit_tolerance: { title: 'vel_limit_tolerance (Overspeed Multiplier)', desc: 'Multiplier above vel_limit that triggers an OVERSPEED fault (e.g. 1.5 = trip at 150% of vel_limit). Set 0 to disable.', range: '1.2–2.0 (default 1.2)' },
  enable_overspeed_error: { title: 'enable_overspeed_error', desc: 'When enabled, disarms the axis with OVERSPEED if shaft speed exceeds vel_limit × vel_limit_tolerance. Uncheck when back-driving by hand.', range: 'true / false' },
  'current_lim (max current)': { title: 'current_lim (Maximum Phase Current)', desc: 'Maximum FOC torque-producing phase current (Iq) the controller will command.', range: '12 A continuous / 30 A peak' },
  current_lim: { title: 'current_lim (Maximum Phase Current)', desc: 'Maximum FOC phase current (Iq) allowed in closed-loop operation.', range: '12–30 A' },
  current_lim_margin: { title: 'current_lim_margin (Overcurrent Headroom)', desc: 'Extra transient headroom above current_lim before CURRENT_LIMIT_VIOLATION trips and disarms the inverter.', range: '8–15 A (default 8 A)' },
  'torque-mode vel limit': { title: 'enable_current_mode_vel_limit', desc: 'When enabled in Torque/Current mode, automatically reduces torque as speed approaches vel_limit to prevent unloaded runaway.', range: 'true recommended' },
  'encoder calib_range': { title: 'encoder.config.calib_range', desc: 'Allowed fractional tolerance between measured encoder counts and pole_pairs during offset calibration.', range: '0.02–0.15 (0.15 tolerates cogging)' },
  'trap vel_limit': { title: 'trap_traj.config.vel_limit', desc: 'Cruise speed of the trapezoidal trajectory planner (input_mode = TRAP_TRAJ).', range: 'turn/s' },
  'trap accel_limit': { title: 'trap_traj.config.accel_limit', desc: 'Acceleration rate of the trapezoidal trajectory planner.', range: 'turn/s²' },
  'trap decel_limit': { title: 'trap_traj.config.decel_limit', desc: 'Deceleration rate of the trapezoidal trajectory planner.', range: 'turn/s²' },
  'control mode': { title: 'controller.config.control_mode', desc: 'Selects the active closed-loop feedback law: CURRENT / TORQUE (direct Iq/τ), VELOCITY (speed PI loop), or POSITION (cascaded position + speed loop).', range: 'TORQUE (1), VELOCITY (2), POSITION (3)' },
  'input mode': { title: 'controller.config.input_mode', desc: 'Selects how setpoint changes are shaped before reaching the controller: PASSTHROUGH (instant), VEL_RAMP, TORQUE_RAMP, POS_FILTER, or TRAP_TRAJ.', range: 'PASSTHROUGH (1) default' },
  'desired current (iq)': { title: 'Desired Phase Current (Iq)', desc: 'Directly commands motor q-axis current in Amps. Motor torque is Iq × Kt (0.0919 Nm/A); joint torque is 30× higher (6:1 × 5:1 planetary).', range: '-12.0 to +12.0 A' },
  'desired motor torque (iq × kt)': { title: 'Desired Motor Shaft Torque', desc: 'Directly commands electromagnetic torque at the motor rotor before the 30:1 two-stage planetary gearbox.', range: 'Nm (1.10 Nm @ 12 A)' },
  'speed (+fwd / -rev)': { title: 'Open-Loop Mechanical Speed', desc: 'Target rotational speed of the open-loop current vector (+ forward, − reverse).', range: 'turn/s' },
  'phase current': { title: 'Open-Loop Phase Current Magnitude', desc: 'Current magnitude (Amps) injected into the stator windings to drag the rotor in open-loop mode.', range: '2–12 A' },
  'target distance (0 = timed)': { title: 'Open-Loop Target Turns', desc: 'Number of mechanical motor turns to spin before stopping automatically (set 0 for timed run).', range: '0–50 turns' },
}

/** look up a plain-English hover guide for any UI label, keyword, or device property path */
export function explainTerm(meta: Metadata | null, rawKey: string, path?: string): TermGuide | null {
  const k = rawKey.trim().toLowerCase().replace(/\s+/g, ' ')
  if (GLOSSARY[k]) return GLOSSARY[k]
  const clean = k.replace(/^[\d]+\s+/, '').replace(/\s*\(.*\)$/, '')
  if (GLOSSARY[clean]) return GLOSSARY[clean]
  if (path && meta?.props[path]) {
    const p = meta.props[path]
    return {
      title: path,
      desc: [p.brief, p.doc].filter(Boolean).join(' — ') || `ODrive ${p.access === 'rw' ? 'writable' : 'read-only'} ${p.type} property.`,
      range: p.unit ? `Unit: ${p.unit} (${p.type})` : p.type,
    }
  }
  return null
}

export function toBig(v: unknown): bigint {
  if (typeof v === 'bigint') return v
  if (typeof v === 'number' && Number.isFinite(v)) return BigInt(Math.trunc(v))
  if (typeof v === 'string' && /^-?\d+$/.test(v)) return BigInt(v)
  return 0n
}

/** split an error bitfield into flag names; works above bit 31 (BigInt) */
export function decodeFlags(meta: Metadata | null, path: string, value: unknown): string[] {
  const v = toBig(value)
  if (v === 0n) return []
  const e = meta && meta.props[path]?.enum ? meta.enums[meta.props[path].enum!] : undefined
  const out: string[] = []
  let known = 0n
  if (e && e.kind === 'flags') {
    for (const [name, bit] of Object.entries(e.bits)) {
      const b = BigInt(bit)
      known |= b
      if (v & b) out.push(name)
    }
  }
  let rest = v & ~known
  let i = 0
  while (rest > 0n) {
    if (rest & 1n) out.push(`BIT_${i}`)
    rest >>= 1n
    i++
  }
  return out
}

/** doc string for one error flag */
export function flagDoc(meta: Metadata | null, path: string, flag: string): string {
  const e = meta && meta.props[path]?.enum ? meta.enums[meta.props[path].enum!] : undefined
  return e?.docs?.[flag] ?? ''
}

export function enumDef(meta: Metadata | null, path: string): EnumDef | undefined {
  const name = meta?.props[path]?.enum
  return name ? meta!.enums[name] : undefined
}

/** enum value -> name ('8' -> 'CLOSED_LOOP_CONTROL') */
export function enumName(meta: Metadata | null, path: string, value: unknown): string {
  const e = enumDef(meta, path)
  if (!e || e.kind !== 'enum') return undefined as unknown as string
  const n = Number(value)
  return Object.entries(e.values).find(([, v]) => v === n)?.[0] as string
}

export function unitOf(meta: Metadata | null, path: string): string {
  return meta?.props[path]?.unit ?? ''
}

export const AXIS_STATES: Record<number, string> = {
  0: 'UNDEFINED',
  1: 'IDLE',
  2: 'STARTUP',
  3: 'FULL_CALIBRATION',
  4: 'MOTOR_CALIBRATION',
  5: 'SENSORLESS',
  6: 'INDEX_SEARCH',
  7: 'ENCODER_OFFSET_CAL',
  8: 'CLOSED_LOOP',
  9: 'LOCKIN_SPIN',
  10: 'ENCODER_DIR_FIND',
  11: 'HOMING',
  12: 'HALL_POLARITY_CAL',
  13: 'HALL_PHASE_CAL',
}
