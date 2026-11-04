#pragma once

#include <Arduino.h>
#include <SPI.h>
#include "config.h"

// as5047p over spi. 14-bit angle, even parity. one chip-select per joint.

struct EncSample {
  uint16_t raw;
  float deg;
  bool ok;
  bool mag_err;
  bool parity_ok;
};

void enc_begin();
EncSample enc_read(int cs_pin);
float wrap_deg(float deg);
