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
#define PATTERN_CUT_DEG 94.0f
// While the shoulder is driving, release the elbow sooner. The two crests
// in that window were 116 then 131. This is a first correction, not a model.
#define PATTERN_COUPLE_DEG 16.0f
#define PATTERN_HANDOFF_MS 1500
#define PATTERN_BRAKE_START_DEG 130.0f
#define PATTERN_RELEASE_DEG 132.0f
#define PATTERN_CLIMB_PERCENT 12.0f
#define PATTERN_STALL_MS 700
#define PATTERN_STALL_ARM_MS 2500
#define PATTERN_START_MS 4000
#define PATTERN_CLIMB_MS 20000
#define PATTERN_FALL_MS 12000
#define PATTERN_SHOULDER_ON_MS 3000
#define PATTERN_SHOULDER_OFF_MS 3000

// Smooth run. Elbow numbers stay in elbow_config.h.
// Shoulder holds at least 3 s, then releases only near the elbow's low turn.
#define SMOOTH_SHOULDER_MIN_MS 3000
#define SMOOTH_SHOULDER_MAX_MS 8000

// Shoulder only. 3 s drive, 3 s released, for one minute. Elbow stays at 0.
#define SHOULDER_LOOP_ON_MS 3000
#define SHOULDER_LOOP_OFF_MS 3000
#define SHOULDER_LOOP_TOTAL_MS 60000

// Run both. Elbow stays in a short band so it does not rest on the upper arm.
#define BOTH_HOLD_DEG 30.0f
#define BOTH_HOLD_LIFT_DEG 2.0f
#define BOTH_AIM_DEG 78.0f
#define BOTH_CAP_DEG 92.0f
#define BOTH_GAP_MS 2000
#define BOTH_SLOW_ON_MS 220
#define BOTH_SLOW_OFF_MS 700
#define BOTH_MOVE_MAX_MS 8000
#define BOTH_TOTAL_MS 60000
