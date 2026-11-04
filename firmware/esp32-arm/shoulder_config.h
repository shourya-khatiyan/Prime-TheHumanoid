#pragma once

// Shoulder actuator only. 30:1 gearbox.
// Change this file for shoulder work. Do not edit elbow_config.h.
// The elbow profile is included so the shared sketch still builds. Its numbers stay there.

#define SLOW_THROTTLE_PERCENT 12
#define SLOW_ON_MS 200
#define SLOW_OFF_MS 400
#define SLOW_JOINT_DEG 4.0f
#define SLOW_MAX_MS 12000
#define SHOULDER_TIME_THROTTLE 12
#define SHOULDER_TIME_MAX_S 30

// Combined pattern. Does not change the saved elbow profile.
// 8% is 1080 us and did not start this ESC. 12% is 1120 us and did.
// Shoulder can only drive one way.
#define PATTERN_LOOPS 40
#define PATTERN_LOW_DEG 30.0f
#define PATTERN_CUT_DEG 105.0f
#define PATTERN_BRAKE_START_DEG 130.0f
#define PATTERN_ABORT_DEG 134.0f
#define PATTERN_CLIMB_PERCENT 12.0f
#define PATTERN_STALL_MS 700
#define PATTERN_START_MS 4000
#define PATTERN_CLIMB_MS 20000
#define PATTERN_FALL_MS 12000
#define PATTERN_SHOULDER_ON_MS 3000
#define PATTERN_SHOULDER_OFF_MS 3000
