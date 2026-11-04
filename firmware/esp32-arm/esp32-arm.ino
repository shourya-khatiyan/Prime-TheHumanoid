#include "config.h"
#include "esc.h"
#include "as5047p.h"
#include "trajectory.h"

// staged bench firmware for the two-joint arm after the odrive died.
// stage 0: read encoders. stage 1: arm escs. stage 2: spin one or both.
// it will not hold a pose. drone escs have no standstill commutation.

enum Stage {
  STAGE_IDLE = 0,
  STAGE_ARMED = 1,
  STAGE_SPIN = 2,
  STAGE_MOVE = 3,
  STAGE_SWEEP = 4,
  STAGE_OPEN = 5,
  STAGE_GOTO = 6,
  STAGE_PATTERN = 7
};

enum SweepPhase {
  SWEEP_DRIVE = 0,
  SWEEP_COAST = 1
};

struct JointEnc {
  int cs;
  float ratio;
  float last_raw_deg;
  float unwrapped_deg;
  float zero_joint_deg;
  bool inited;
};

static Stage g_stage = STAGE_IDLE;
static float g_thr_s = 0.0f;
static float g_thr_e = 0.0f;
static uint32_t g_last_cmd_ms = 0;
static uint32_t g_last_print_ms = 0;
static uint32_t g_move_start_ms = 0;
static float g_move_target_s = 0.0f;
static float g_move_target_e = 0.0f;
static bool g_move_use_s = false;
static bool g_move_use_e = false;
static bool g_enc_ok = false;
static String g_line;
static JointEnc g_sh;
static JointEnc g_el;

static void service_move();
static void print_encoders();
static bool start_move(bool use_s, bool use_e, float tgt_s, float tgt_e);

static void joint_init(JointEnc *j, int cs, float ratio) {
  j->cs = cs;
  j->ratio = ratio;
  j->last_raw_deg = 0.0f;
  j->unwrapped_deg = 0.0f;
  j->zero_joint_deg = 0.0f;
  j->inited = false;
}

static void joint_update(JointEnc *j) {
  EncSample s = enc_read(j->cs);
  if (!s.ok) {
    return;
  }
  if (!j->inited) {
    j->last_raw_deg = s.deg;
    j->unwrapped_deg = s.deg;
    j->inited = true;
    return;
  }
  j->unwrapped_deg += wrap_deg(s.deg - j->last_raw_deg);
  j->last_raw_deg = s.deg;
}

static float joint_deg(const JointEnc *j) {
  return (j->unwrapped_deg / j->ratio) - j->zero_joint_deg;
}

static float g_stop_mark = 0.0f;
static uint32_t g_stop_since = 0;
static bool g_stop_mark_set = false;
static SweepPhase g_sweep_phase = SWEEP_DRIVE;
static uint32_t g_sweep_t0 = 0;
static uint32_t g_coast_t0 = 0;
static float g_coast_from = 0.0f;
static float g_coast_mark = 0.0f;
static uint32_t g_coast_still = 0;
static int g_sweeps = 0;
static int g_loops_left = 1;
static int g_loops_done = 0;
static bool g_end_down = false;
static float g_lift_from = 0.0f;
static float g_slow_from = 0.0f;
static uint32_t g_time_until = 0;
static uint32_t g_pattern_t0 = 0;
static bool g_sh_was_on = false;
static uint32_t g_slow_t0 = 0;
static float g_drive_from = 0.0f;
static float g_drive_peak = 0.0f;
static uint32_t g_peak_since = 0;

static float absf(float v) {
  return v < 0.0f ? -v : v;
}

static bool elbow_stalled() {
  if (!g_el.inited || g_thr_e <= 0.0f) {
    g_stop_mark_set = false;
    return false;
  }
  if (!g_stop_mark_set) {
    g_stop_mark = g_el.unwrapped_deg;
    g_stop_since = millis();
    g_stop_mark_set = true;
    return false;
  }
  if (absf(g_el.unwrapped_deg - g_stop_mark) >= STOP_STALL_DEG) {
    g_stop_mark = g_el.unwrapped_deg;
    g_stop_since = millis();
    return false;
  }
  return (millis() - g_stop_since) > STOP_STALL_MS;
}

static void service_sweep() {
  if (g_stage != STAGE_SWEEP) {
    return;
  }
  if ((millis() - g_sweep_t0) > SWEEP_MAX_MS) {
    g_thr_e = 0.0f;
    g_stage = STAGE_ARMED;
    Serial.println(F("sweep finished."));
    return;
  }
  if (g_sweep_phase == SWEEP_DRIVE) {
    g_thr_e = SWEEP_THROTTLE_PERCENT;
    float risen = g_el.unwrapped_deg - g_drive_from;
    if (g_el.unwrapped_deg > g_drive_peak + 1.0f) {
      g_drive_peak = g_el.unwrapped_deg;
      g_peak_since = millis();
    }
    // ceiling is absolute. peak-stall only counts after the arm has actually moved,
    // so a slow start is not treated as the stop. vibration does not raise the peak.
    bool at_ceiling = g_el.unwrapped_deg >= ELBOW_CEILING_DEG;
    bool at_end = risen > 8.0f && (millis() - g_peak_since) > PEAK_STALL_MS;
    if (risen < SWEEP_LIFT_DEG && !at_end && !at_ceiling) {
      return;
    }
    g_thr_e = 0.0f;
    g_stop_mark_set = false;
    g_sweep_phase = SWEEP_COAST;
    g_coast_t0 = millis();
    g_coast_from = g_el.unwrapped_deg;
    g_coast_mark = g_el.unwrapped_deg;
    g_coast_still = millis();
    Serial.println(F("coast"));
    return;
  }
  float returned = absf(g_el.unwrapped_deg - g_coast_from);
  if (absf(g_el.unwrapped_deg - g_coast_mark) >= STOP_STALL_DEG) {
    g_coast_mark = g_el.unwrapped_deg;
    g_coast_still = millis();
  }
  bool settled = (millis() - g_coast_still) > STOP_STALL_MS;
  if (returned >= SWEEP_MIN_RETURN_DEG && settled) {
    g_sweeps++;
    g_sweep_phase = SWEEP_DRIVE;
    g_drive_from = g_el.unwrapped_deg;
    g_drive_peak = g_drive_from;
    g_peak_since = millis();
    g_stop_mark_set = false;
    g_thr_e = SWEEP_THROTTLE_PERCENT;
    Serial.print(F("lift "));
    Serial.println(g_sweeps);
    return;
  }
  if ((millis() - g_coast_t0) > SWEEP_COAST_MS && returned < SWEEP_MIN_RETURN_DEG) {
    g_thr_e = 0.0f;
    g_stage = STAGE_ARMED;
    Serial.println(F("CUT no-fall. elbow did not come back. x is stop."));
  }
}

static void service_goto() {
  if (g_stage != STAGE_GOTO) {
    return;
  }
  float joint = g_el.unwrapped_deg - g_drive_from;
  if (g_sweep_phase == SWEEP_DRIVE && joint > 120.0f) {
    g_thr_e = 0.0f;
    g_stage = STAGE_ARMED;
    Serial.println(F("CUT past 120"));
    return;
  }
  if (g_sweep_phase == SWEEP_DRIVE) {
    if (g_el.unwrapped_deg > g_drive_peak + 1.0f) {
      g_drive_peak = g_el.unwrapped_deg;
      g_peak_since = millis();
    }
    bool arrived = joint >= ELBOW_CUT_DEG;
    bool stalled = joint > g_lift_from + 5.0f && (millis() - g_peak_since) > PEAK_STALL_MS;
    bool too_long = (millis() - g_sweep_t0) > ELBOW_GOTO_MS;
    if (!arrived && !stalled && !too_long) {
      g_thr_e = ESC_THROTTLE_CAP_PERCENT;
      return;
    }
    g_thr_e = 0.0f;
    if (!arrived) {
      g_stage = STAGE_ARMED;
      Serial.print(F("stopped at "));
      Serial.println(joint, 1);
      return;
    }
    g_loops_done++;
    Serial.print(F("top "));
    Serial.println(g_loops_done);
    g_end_down = g_loops_done >= g_loops_left;
    g_sweep_phase = SWEEP_COAST;
    g_coast_t0 = millis();
    g_coast_mark = joint;
    g_coast_still = millis();
    return;
  }
  if (joint > g_coast_mark) {
    g_coast_mark = joint;
  }
  bool falling = joint < g_coast_mark - 6.0f;
  if (falling && joint > ELBOW_TURN_DEG) {
    float span = ELBOW_BRAKE_START_DEG - ELBOW_TURN_DEG;
    float t = (ELBOW_BRAKE_START_DEG - joint) / span;
    if (t < 0.0f) {
      t = 0.0f;
    }
    if (t > 1.0f) {
      t = 1.0f;
    }
    g_thr_e = 4.0f + 8.0f * t;
    return;
  }
  if (g_end_down && joint <= ELBOW_TURN_DEG) {
    if (absf(joint - g_lift_from) >= 3.0f) {
      g_lift_from = joint;
      g_coast_still = millis();
    }
    if ((millis() - g_coast_still) > 350) {
      g_thr_e = 0.0f;
      g_stage = STAGE_ARMED;
      Serial.print(F("loops done at "));
      Serial.println(joint, 1);
      return;
    }
    g_thr_e = ESC_THROTTLE_CAP_PERCENT;
    return;
  }
  if (joint <= ELBOW_TURN_DEG) {
    g_sweep_phase = SWEEP_DRIVE;
    g_lift_from = joint;
    g_drive_peak = g_el.unwrapped_deg;
    g_peak_since = millis();
    g_sweep_t0 = millis();
    g_thr_e = ESC_THROTTLE_CAP_PERCENT;
    Serial.print(F("low "));
    Serial.println(joint, 1);
    return;
  }
  if ((millis() - g_coast_t0) > ELBOW_FALL_MS && joint > 20.0f) {
    g_thr_e = 0.0f;
    g_stage = STAGE_ARMED;
    Serial.println(F("CUT no-fall"));
  }
}

static void service_pattern() {
  if (g_stage != STAGE_PATTERN) {
    return;
  }
  uint32_t cycle = PATTERN_SHOULDER_ON_MS + PATTERN_SHOULDER_OFF_MS;
  bool on = ((millis() - g_pattern_t0) % cycle) < PATTERN_SHOULDER_ON_MS;
  if (on != g_sh_was_on) {
    g_sh_was_on = on;
    Serial.println(on ? F("shoulder up") : F("shoulder down"));
  }
  g_thr_s = on ? SHOULDER_TIME_THROTTLE : 0.0f;

  float joint = g_el.unwrapped_deg - g_drive_from;
  if (joint > PATTERN_RELEASE_DEG) {
    g_thr_e = 0.0f;
    if (g_sweep_phase == SWEEP_DRIVE) {
      g_loops_done++;
      Serial.print(F("top "));
      Serial.println(g_loops_done);
      g_end_down = g_loops_done >= g_loops_left;
      g_sweep_phase = SWEEP_COAST;
      g_coast_t0 = millis();
      g_coast_mark = joint;
      g_coast_still = millis();
    }
    return;
  }
  if (g_sweep_phase == SWEEP_DRIVE) {
    if (joint < 3.0f && (millis() - g_sweep_t0) > PATTERN_START_MS) {
      g_thr_s = 0.0f;
      g_thr_e = 0.0f;
      g_stage = STAGE_ARMED;
      Serial.println(F("elbow did not start"));
      return;
    }
    if (g_el.unwrapped_deg > g_drive_peak + 1.0f) {
      g_drive_peak = g_el.unwrapped_deg;
      g_peak_since = millis();
    }
    bool arrived = joint >= PATTERN_CUT_DEG;
    bool stalled = joint > g_lift_from + 5.0f && (millis() - g_peak_since) > PATTERN_STALL_MS;
    bool too_long = (millis() - g_sweep_t0) > PATTERN_CLIMB_MS;
    if (!arrived && !stalled && !too_long) {
      g_thr_e = PATTERN_CLIMB_PERCENT;
      return;
    }
    g_thr_e = 0.0f;
    if (!arrived) {
      g_thr_s = 0.0f;
      g_stage = STAGE_ARMED;
      Serial.print(F("stopped at "));
      Serial.println(joint, 1);
      return;
    }
    g_loops_done++;
    Serial.print(F("top "));
    Serial.println(g_loops_done);
    g_end_down = g_loops_done >= g_loops_left;
    g_sweep_phase = SWEEP_COAST;
    g_coast_t0 = millis();
    g_coast_mark = joint;
    g_coast_still = millis();
    return;
  }
  if (joint > g_coast_mark) {
    g_coast_mark = joint;
  }
  bool falling = joint < g_coast_mark - 6.0f;
  if (falling && joint > PATTERN_LOW_DEG) {
    float span = PATTERN_BRAKE_START_DEG - PATTERN_LOW_DEG;
    float t = (PATTERN_BRAKE_START_DEG - joint) / span;
    if (t < 0.0f) {
      t = 0.0f;
    }
    if (t > 1.0f) {
      t = 1.0f;
    }
    g_thr_e = 4.0f + 8.0f * t;
    return;
  }
  if (g_end_down && joint <= PATTERN_LOW_DEG) {
    if (absf(joint - g_lift_from) >= 3.0f) {
      g_lift_from = joint;
      g_coast_still = millis();
    }
    if ((millis() - g_coast_still) > 350) {
      g_thr_e = 0.0f;
      g_thr_s = 0.0f;
      g_stage = STAGE_ARMED;
      Serial.print(F("loops done at "));
      Serial.println(joint, 1);
      return;
    }
    g_thr_e = PATTERN_CLIMB_PERCENT;
    return;
  }
  if (joint <= PATTERN_LOW_DEG) {
    g_sweep_phase = SWEEP_DRIVE;
    g_lift_from = joint;
    g_drive_peak = g_el.unwrapped_deg;
    g_peak_since = millis();
    g_sweep_t0 = millis();
    g_thr_e = PATTERN_CLIMB_PERCENT;
    Serial.print(F("low "));
    Serial.println(joint, 1);
    return;
  }
  if ((millis() - g_coast_t0) > PATTERN_FALL_MS && joint > 20.0f) {
    g_thr_e = 0.0f;
    g_thr_s = 0.0f;
    g_stage = STAGE_ARMED;
    Serial.println(F("CUT no-fall"));
  }
}

static void note_elbow_motion() {
  if (g_stage == STAGE_SWEEP || g_stage == STAGE_GOTO || g_stage == STAGE_PATTERN) {
    return;
  }
  if (!g_el.inited || g_thr_e <= 0.0f) {
    g_stop_mark_set = false;
    return;
  }
  if (!g_stop_mark_set) {
    g_stop_mark = g_el.unwrapped_deg;
    g_stop_since = millis();
    g_stop_mark_set = true;
    return;
  }
  if (g_el.unwrapped_deg > g_stop_mark + 1.0f) {
    g_stop_mark = g_el.unwrapped_deg;
    g_stop_since = millis();
    return;
  }
  if ((millis() - g_stop_since) <= PEAK_STALL_MS) {
    return;
  }
  g_thr_e = 0.0f;
  g_stop_mark_set = false;
  if (g_stage == STAGE_SPIN || g_stage == STAGE_MOVE) {
    g_stage = STAGE_ARMED;
  }
  Serial.println(F("elbow hit a stop. throttle cut."));
}

static void print_help() {
  Serial.println(F("esp32-arm " FW_VERSION));
  Serial.println(F("shoulder gpio 25 by time. elbow gpio 26 by degrees."));
  Serial.println(F("  help              this text"));
  Serial.println(F("  enc               one encoder sample"));
  Serial.println(F("  stream            encoder print every 100 ms"));
  Serial.println(F("  arm               send min throttle, wait for esc tone"));
  Serial.println(F("  loops             20 times, rest 0 to 110"));
  Serial.println(F("  pattern           elbow 40 turns 30-130, shoulder 3s on 3s off"));
  Serial.println(F("  time <sec>        shoulder runs for that many seconds"));
  Serial.println(F("  open              two short pulses, no encoder"));
  Serial.println(F("  sweep             drive to the stop, let it fall, repeat"));
  Serial.println(F("  spin s <pct>      shoulder on gpio 25, 0-12"));
  Serial.println(F("  spin e <pct>      elbow on gpio 26, 0-12"));
  Serial.println(F("  zero              current pose = 0 deg"));
  Serial.println(F("  move s <deg>      shoulder joint deg, then cut"));
  Serial.println(F("  move e <deg>      elbow joint deg, then cut"));
  Serial.println(F("  move both <s> <e> both joints, same clock, then cut"));
  Serial.println(F("  stop              throttle 0, stay armed"));
  Serial.println(F("  disarm            throttle 0, leave armed"));
  Serial.println(F("  x                 emergency stop, same as kill pin"));
}

static void cut_all(const char *why) {
  esc_all_stop();
  g_thr_s = 0.0f;
  g_thr_e = 0.0f;
  g_time_until = 0;
  g_stage = STAGE_IDLE;
  Serial.print(F("CUT "));
  Serial.println(why);
}

static void service_slow() {
#if BOARD_IS_SHOULDER
  if (g_stage != STAGE_SPIN) {
    return;
  }
  float joint = (g_sh.unwrapped_deg - g_slow_from) / SHOULDER_RATIO;
  if (joint < 0.0f) {
    joint = -joint;
  }
  bool too_far = joint >= SLOW_JOINT_DEG;
  bool too_long = (millis() - g_slow_t0) > SLOW_MAX_MS;
  if (too_far || too_long) {
    g_thr_s = 0.0f;
    g_stage = STAGE_ARMED;
    Serial.println(too_far ? F("stop at 4 deg") : F("stop, time"));
    return;
  }
  uint32_t phase = (millis() - g_slow_t0) % (SLOW_ON_MS + SLOW_OFF_MS);
  g_thr_s = phase < SLOW_ON_MS ? SLOW_THROTTLE_PERCENT : 0.0f;
#else
  (void)0;
#endif
}

static void service_time() {
  if (g_time_until == 0) {
    return;
  }
  if ((int32_t)(millis() - g_time_until) < 0) {
    g_thr_s = SHOULDER_TIME_THROTTLE;
    return;
  }
  g_thr_s = 0.0f;
  g_time_until = 0;
  Serial.println(F("time done"));
}

static void service_open() {
  if (g_stage != STAGE_OPEN) {
    return;
  }
  uint32_t elapsed = millis() - g_slow_t0;
  if (elapsed >= OPEN_TOTAL_MS) {
    g_thr_s = 0.0f;
    g_thr_e = 0.0f;
    g_stage = STAGE_ARMED;
    Serial.println(F("open done"));
    return;
  }
  uint32_t phase = elapsed % (OPEN_ON_MS + OPEN_OFF_MS);
  float thr = phase < OPEN_ON_MS ? OPEN_THROTTLE_PERCENT : 0.0f;
  g_thr_s = thr;
}

static void apply_throttles() {
  if (esc_kill_pressed()) {
    cut_all("kill");
    return;
  }
  if (g_stage == STAGE_SPIN && (millis() - g_last_cmd_ms) > ESC_DEADMAN_MS) {
    cut_all("deadman");
    return;
  }
  if (g_stage == STAGE_IDLE) {
    esc_all_stop();
    return;
  }
#if BOARD_IS_SHOULDER
  service_slow();
#else
  service_move();
  service_sweep();
  service_goto();
  service_pattern();
  note_elbow_motion();
#endif
  service_open();
  service_time();
  esc_write_percent(ESC_SHOULDER, g_thr_s);
  esc_write_percent(ESC_ELBOW, g_thr_e);
  if (g_stage != STAGE_IDLE) {
    digitalWrite(PIN_ARMED_LED, HIGH);
  }
}

static void print_encoders() {
  EncSample sh = enc_read(PIN_ENC_CS_SHOULDER);
  EncSample el = enc_read(PIN_ENC_CS_ELBOW);
  Serial.print(F("sh raw "));
  Serial.print(sh.deg, 2);
  Serial.print(sh.ok ? F(" ok") : F(" BAD"));
  Serial.print(F("  j "));
  Serial.print(joint_deg(&g_sh), 2);
  Serial.print(F("  el raw "));
  Serial.print(el.deg, 2);
  Serial.print(el.ok ? F(" ok") : F(" BAD"));
  Serial.print(F("  j "));
  Serial.print(joint_deg(&g_el), 2);
  Serial.print(F("  thr "));
  Serial.print(g_thr_s, 1);
  Serial.print('/');
  Serial.print(g_thr_e, 1);
  Serial.print(F("  stage "));
  Serial.println((int)g_stage);
}

static bool start_move(bool use_s, bool use_e, float tgt_s, float tgt_e) {
  if (g_stage == STAGE_IDLE) {
    Serial.println(F("not armed. send arm first."));
    return false;
  }
  if (use_s && !g_sh.inited) {
    Serial.println(F("shoulder encoder not talking."));
    return false;
  }
  if (use_e && !g_el.inited) {
    Serial.println(F("elbow encoder not talking."));
    return false;
  }
  if (use_s && tgt_s + 0.2f < joint_deg(&g_sh)) {
    Serial.println(F("esc is one-way. target is behind. swap two phase wires or pick a higher angle."));
    return false;
  }
  if (use_e && tgt_e + 0.2f < joint_deg(&g_el)) {
    Serial.println(F("esc is one-way. target is behind. swap two phase wires or pick a higher angle."));
    return false;
  }
  g_move_use_s = use_s;
  g_move_use_e = use_e;
  g_move_target_s = tgt_s;
  g_move_target_e = tgt_e;
  g_thr_s = use_s ? MOVE_THROTTLE_PERCENT : 0.0f;
  g_thr_e = use_e ? MOVE_THROTTLE_PERCENT : 0.0f;
  g_move_start_ms = millis();
  g_stage = STAGE_MOVE;
  Serial.print(F("move to sh="));
  Serial.print(tgt_s, 1);
  Serial.print(F(" el="));
  Serial.println(tgt_e, 1);
  return true;
}

static void service_move() {
  if (g_stage != STAGE_MOVE) {
    return;
  }
  if ((millis() - g_move_start_ms) > MOVE_TIMEOUT_MS) {
    cut_all("move-timeout");
    return;
  }
  bool done_s = !g_move_use_s || (joint_deg(&g_sh) >= g_move_target_s - MOVE_ARRIVE_JOINT_DEG);
  bool done_e = !g_move_use_e || (joint_deg(&g_el) >= g_move_target_e - MOVE_ARRIVE_JOINT_DEG);
  if (done_s) {
    g_thr_s = 0.0f;
  }
  if (done_e) {
    g_thr_e = 0.0f;
  }
  if (done_s && done_e) {
    esc_all_stop();
    g_stage = STAGE_ARMED;
    digitalWrite(PIN_ARMED_LED, HIGH);
    Serial.print(F("arrived sh="));
    Serial.print(joint_deg(&g_sh), 2);
    Serial.print(F(" el="));
    Serial.println(joint_deg(&g_el), 2);
    Serial.println(F("holding by gearbox friction only. spot the arm."));
  }
}

static void handle_line(String line) {
  line.trim();
  line.toLowerCase();
  if (line.length() == 0) {
    return;
  }
  g_last_cmd_ms = millis();

  if (line == "x" || line == "kill") {
    cut_all("serial");
    return;
  }
  if (line == "help" || line == "?") {
    print_help();
    return;
  }
  if (line == "enc") {
    print_encoders();
    return;
  }
  if (line == "stream") {
    Serial.println(F("stream on. send stop or any cmd to keep alive."));
    return;
  }
  if (line == "arm") {
    esc_all_stop();
    g_thr_s = 0.0f;
    g_thr_e = 0.0f;
    Serial.println(F("arming: min throttle. wait for esc beeps."));
    uint32_t t0 = millis();
    while (millis() - t0 < ESC_ARM_MS) {
      if (esc_kill_pressed()) {
        cut_all("kill");
        return;
      }
      esc_write_us(ESC_SHOULDER, ESC_ARM_US);
      esc_write_us(ESC_ELBOW, ESC_ARM_US);
      delay(20);
    }
    g_stage = STAGE_ARMED;
    digitalWrite(PIN_ARMED_LED, HIGH);
    Serial.println(F("armed. now: spin s 6"));
    return;
  }
  if (line == "stop") {
    g_thr_s = 0.0f;
    g_thr_e = 0.0f;
    g_time_until = 0;
    if (g_stage == STAGE_SPIN || g_stage == STAGE_MOVE || g_stage == STAGE_SWEEP || g_stage == STAGE_OPEN || g_stage == STAGE_GOTO || g_stage == STAGE_PATTERN) {
      g_stage = STAGE_ARMED;
    }
    esc_all_stop();
    if (g_stage == STAGE_ARMED) {
      digitalWrite(PIN_ARMED_LED, HIGH);
    }
    Serial.println(F("stop"));
    return;
  }
  if (line == "disarm") {
    cut_all("disarm");
    return;
  }

  if (line.startsWith("spin ")) {
    if (g_stage == STAGE_IDLE) {
      Serial.println(F("not armed. send arm first."));
      return;
    }
    String rest = line.substring(5);
    rest.trim();
    float pct = 0.0f;
    bool use_s = false;
    bool use_e = false;
    if (rest.startsWith("both ")) {
      pct = rest.substring(5).toFloat();
      use_s = true;
      use_e = true;
    } else if (rest.startsWith("s ")) {
      pct = rest.substring(2).toFloat();
      use_s = true;
    } else if (rest.startsWith("e ")) {
      pct = rest.substring(2).toFloat();
      use_e = true;
    } else {
      Serial.println(F("spin s|e|both <pct>"));
      return;
    }
    if (use_s) {
      g_thr_s = pct;
    }
    if (use_e) {
      g_thr_e = pct;
    }
    if (g_thr_s < 0.0f) {
      g_thr_s = 0.0f;
    }
    if (g_thr_e < 0.0f) {
      g_thr_e = 0.0f;
    }
    g_stage = STAGE_SPIN;
    Serial.print(F("spin s="));
    Serial.print(g_thr_s, 1);
    Serial.print(F(" e="));
    Serial.println(g_thr_e, 1);
    return;
  }

  if (line.startsWith("time ")) {
    if (g_stage == STAGE_IDLE) {
      Serial.println(F("not armed. send arm first."));
      return;
    }
    float seconds = line.substring(5).toFloat();
    if (seconds < 0.2f) {
      seconds = 0.2f;
    }
    if (seconds > SHOULDER_TIME_MAX_S) {
      seconds = SHOULDER_TIME_MAX_S;
    }
    g_thr_s = SHOULDER_TIME_THROTTLE;
    g_time_until = millis() + (uint32_t)(seconds * 1000.0f);
    if (g_stage == STAGE_IDLE) {
      g_stage = STAGE_ARMED;
    }
    Serial.print(F("shoulder time "));
    Serial.print(seconds, 1);
    Serial.println(F(" s"));
    return;
  }

  if (line == "open") {
    if (g_stage == STAGE_IDLE) {
      Serial.println(F("not armed. send arm first."));
      return;
    }
    g_slow_t0 = millis();
    g_thr_s = 0.0f;
    g_thr_e = 0.0f;
    g_stage = STAGE_OPEN;
    Serial.println(F("open loop on gpio 25. two pulses. no encoder."));
    return;
  }

  if (line == "slow") {
#if !BOARD_IS_SHOULDER
    Serial.println(F("this board is the elbow."));
    return;
#else
    if (g_stage == STAGE_IDLE) {
      Serial.println(F("not armed. send arm first."));
      return;
    }
    if (!g_sh.inited) {
      Serial.println(F("shoulder encoder not talking."));
      return;
    }
    g_slow_from = g_sh.unwrapped_deg;
    g_slow_t0 = millis();
    g_drive_peak = g_slow_from;
    g_peak_since = millis();
    g_thr_s = SLOW_THROTTLE_PERCENT;
    g_stage = STAGE_SPIN;
    Serial.println(F("shoulder slow. pulsed. stop at 4 deg."));
    return;
#endif
  }

  if (line == "go") {
    if (g_stage == STAGE_IDLE) {
      Serial.println(F("not armed. send arm first."));
      return;
    }
    if (!g_el.inited) {
      Serial.println(F("elbow encoder not talking."));
      return;
    }
    if (g_el.last_raw_deg > 40.0f && g_el.last_raw_deg < 320.0f) {
      Serial.println(F("not at rest. let the forearm down first."));
      return;
    }
    g_drive_from = g_el.unwrapped_deg;
    g_el.zero_joint_deg = g_el.unwrapped_deg / g_el.ratio;
    g_drive_peak = g_drive_from;
    g_peak_since = millis();
    g_sweep_t0 = millis();
    g_sweep_phase = SWEEP_DRIVE;
    g_loops_left = 1;
    g_loops_done = 0;
    g_thr_e = ESC_THROTTLE_CAP_PERCENT;
    g_stage = STAGE_GOTO;
    Serial.println(F("rest is 0. driving to 110."));
    return;
  }

  if (line == "loops") {
    if (g_stage == STAGE_IDLE) {
      Serial.println(F("not armed. send arm first."));
      return;
    }
    if (!g_el.inited) {
      Serial.println(F("elbow encoder not talking."));
      return;
    }
    if (g_el.last_raw_deg > 40.0f && g_el.last_raw_deg < 320.0f) {
      Serial.println(F("not at rest. let the forearm down first."));
      return;
    }
    g_drive_from = g_el.unwrapped_deg;
    g_el.zero_joint_deg = g_el.unwrapped_deg / g_el.ratio;
    g_drive_peak = g_drive_from;
    g_peak_since = millis();
    g_sweep_t0 = millis();
    g_sweep_phase = SWEEP_DRIVE;
    g_loops_left = ELBOW_LOOPS;
    g_loops_done = 0;
    g_end_down = false;
    g_lift_from = 0.0f;
    g_thr_e = ESC_THROTTLE_CAP_PERCENT;
    g_stage = STAGE_GOTO;
    Serial.println(F("20 loops. light brake near 110, full climb from 40."));
    return;
  }

  if (line == "pattern") {
    if (g_stage == STAGE_IDLE) {
      Serial.println(F("not armed. send arm first."));
      return;
    }
    if (!g_el.inited) {
      Serial.println(F("elbow encoder not talking."));
      return;
    }
    if (g_el.last_raw_deg > 40.0f && g_el.last_raw_deg < 320.0f) {
      Serial.println(F("not at rest. let the forearm down first."));
      return;
    }
    g_drive_from = g_el.unwrapped_deg;
    g_el.zero_joint_deg = g_el.unwrapped_deg / g_el.ratio;
    g_drive_peak = g_drive_from;
    g_peak_since = millis();
    g_sweep_t0 = millis();
    g_sweep_phase = SWEEP_DRIVE;
    g_loops_left = PATTERN_LOOPS;
    g_loops_done = 0;
    g_end_down = false;
    g_lift_from = 0.0f;
    g_pattern_t0 = millis();
    g_sh_was_on = false;
    g_thr_e = PATTERN_CLIMB_PERCENT;
    g_thr_s = SHOULDER_TIME_THROTTLE;
    g_stage = STAGE_PATTERN;
    Serial.println(F("pattern. elbow 40 turns, 30 to 130, slow. shoulder 3s up, 3s down."));
    return;
  }

  if (line == "sweep") {
    if (g_stage == STAGE_IDLE) {
      Serial.println(F("not armed. send arm first."));
      return;
    }
    if (!g_el.inited) {
      Serial.println(F("elbow encoder not talking."));
      return;
    }
    if (g_el.unwrapped_deg >= ELBOW_CEILING_DEG - 20.0f) {
      Serial.println(F("too close to the top stop. not starting."));
      return;
    }
    g_stage = STAGE_SWEEP;
    g_sweep_phase = SWEEP_DRIVE;
    g_sweep_t0 = millis();
    g_sweeps = 0;
    g_drive_from = g_el.unwrapped_deg;
    g_drive_peak = g_drive_from;
    g_peak_since = millis();
    g_stop_mark_set = false;
    g_thr_e = SWEEP_THROTTLE_PERCENT;
    Serial.println(F("sweep on. 40 deg lift, hard stop at 95 deg. x stops."));
    return;
  }

  if (line == "zero") {
    if (!g_el.inited) {
      Serial.println(F("elbow encoder not talking. cannot zero."));
      return;
    }
    g_el.zero_joint_deg = g_el.unwrapped_deg / g_el.ratio;
    Serial.println(F("zero set at this pose."));
    return;
  }

  if (line.startsWith("move ")) {
    String rest = line.substring(5);
    rest.trim();
    if (rest.startsWith("s ") || rest.startsWith("both ")) {
      Serial.println(F("this esp is the elbow. use: move e 20"));
      return;
    } else if (rest.startsWith("e ")) {
      start_move(false, true, 0.0f, rest.substring(2).toFloat());
    } else {
      Serial.println(F("move s|e|both ..."));
    }
    return;
  }

  if (line.startsWith("goto ")) {
    Serial.println(F("true goto needs a foc drive. today use: move s 25"));
    return;
  }

  Serial.println(F("unknown. type help"));
}

void setup() {
  Serial.begin(115200);
  delay(200);
  joint_init(&g_sh, PIN_ENC_CS_SHOULDER, SHOULDER_RATIO);
  joint_init(&g_el, PIN_ENC_CS_ELBOW, ELBOW_RATIO);
  esc_begin();
  enc_begin();
  joint_update(&g_sh);
  joint_update(&g_el);
  EncSample sh = enc_read(PIN_ENC_CS_SHOULDER);
  EncSample el = enc_read(PIN_ENC_CS_ELBOW);
  g_enc_ok = el.ok;
  print_help();
#if BOARD_IS_SHOULDER
  Serial.print(F("shoulder encoder "));
  Serial.println(sh.ok ? F("ok") : F("not talking"));
  Serial.println(F("30:1 shoulder. command: arm then slow"));
#else
  Serial.print(F("elbow encoder "));
  Serial.println(el.ok ? F("ok") : F("not talking — check 3v3 gnd spi"));
  Serial.println(F("elbow is direct drive. stops near -5 deg and 140 deg."));
  Serial.println(F("then: enc   then: arm   then: spin e 12"));
#endif
}

void loop() {
  joint_update(&g_sh);
  joint_update(&g_el);

  while (Serial.available()) {
    char c = (char)Serial.read();
    if (c == '\n' || c == '\r') {
      if (g_line.length() > 0) {
        handle_line(g_line);
        g_line = "";
      }
    } else if (g_line.length() < 80) {
      g_line += c;
    }
  }

  apply_throttles();

  if (millis() - g_last_print_ms > 200) {
    g_last_print_ms = millis();
#if BOARD_IS_SHOULDER
    if (g_stage == STAGE_SPIN) {
      float joint = (g_sh.unwrapped_deg - g_slow_from) / SHOULDER_RATIO;
      Serial.print(F("shoulder "));
      Serial.println(joint, 2);
    } else
#endif
    if (g_stage == STAGE_PATTERN) {
      Serial.print(F("joint "));
      Serial.print(g_el.unwrapped_deg - g_drive_from, 1);
      Serial.print(F(" el "));
      Serial.print(g_thr_e, 0);
      Serial.print(F(" sh "));
      Serial.println(g_thr_s, 0);
    } else if (g_stage == STAGE_GOTO) {
      Serial.print(F("joint "));
      Serial.print(g_el.unwrapped_deg - g_drive_from, 1);
      Serial.print(F(" thr "));
      Serial.println(g_thr_e, 0);
    } else if (g_stage == STAGE_SWEEP) {
      Serial.print(F("elbow "));
      Serial.print(g_el.unwrapped_deg, 1);
      Serial.print(g_sweep_phase == SWEEP_DRIVE ? F(" drive ") : F(" coast "));
      Serial.println(g_thr_e, 0);
    } else if (g_stage == STAGE_SPIN || g_stage == STAGE_MOVE) {
      print_encoders();
    }
  }
}
