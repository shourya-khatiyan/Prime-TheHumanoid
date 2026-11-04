#pragma once

// time-synced two-joint interpolator.
// one clock, two setpoints. this is the sync brain.
// it does not drive phases. a foc board must track these angles.

struct TrajPoint {
  float shoulder_deg;
  float elbow_deg;
};

inline TrajPoint traj_lerp(TrajPoint a, TrajPoint b, float t) {
  if (t < 0.0f) {
    t = 0.0f;
  }
  if (t > 1.0f) {
    t = 1.0f;
  }
  // smoothstep so start and stop are not a step.
  float s = t * t * (3.0f - 2.0f * t);
  TrajPoint p;
  p.shoulder_deg = a.shoulder_deg + (b.shoulder_deg - a.shoulder_deg) * s;
  p.elbow_deg = a.elbow_deg + (b.elbow_deg - a.elbow_deg) * s;
  return p;
}
