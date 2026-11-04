#pragma once

#include <Arduino.h>
#include "config.h"

// one hobby-esc channel. writes a 1000-2000 us pulse. does not commutate the motor.

enum EscId {
  ESC_SHOULDER = 0,
  ESC_ELBOW = 1,
  ESC_COUNT = 2
};

void esc_begin();
void esc_write_us(EscId id, uint16_t pulse_us);
void esc_write_percent(EscId id, float percent);
void esc_all_stop();
bool esc_kill_pressed();
uint16_t esc_percent_to_us(float percent);
