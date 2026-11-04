#include "as5047p.h"

// as5047p spi is mode 1, 16-bit frames, even parity on bit 15.
// read ANGLECOM (0x3fff). next frame returns the angle. see infineon datasheet.

static const uint16_t kCmdAngle = 0xFFFF;

static bool even_parity_ok(uint16_t frame) {
  uint16_t x = frame;
  x ^= x >> 8;
  x ^= x >> 4;
  x ^= x >> 2;
  x ^= x >> 1;
  return (x & 1) == 0;
}

static uint16_t xfer16(int cs_pin, uint16_t cmd) {
  digitalWrite(cs_pin, LOW);
  delayMicroseconds(1);
  uint16_t value = SPI.transfer16(cmd);
  digitalWrite(cs_pin, HIGH);
  delayMicroseconds(1);
  return value;
}

void enc_begin() {
  pinMode(PIN_ENC_CS_SHOULDER, OUTPUT);
  pinMode(PIN_ENC_CS_ELBOW, OUTPUT);
  digitalWrite(PIN_ENC_CS_SHOULDER, HIGH);
  digitalWrite(PIN_ENC_CS_ELBOW, HIGH);
  SPI.begin(PIN_ENC_SCK, PIN_ENC_MISO, PIN_ENC_MOSI, -1);
  SPI.beginTransaction(SPISettings(ENC_SPI_HZ, MSBFIRST, SPI_MODE1));
  // dummy read so the next call returns a real angle.
  xfer16(PIN_ENC_CS_SHOULDER, kCmdAngle);
  xfer16(PIN_ENC_CS_ELBOW, kCmdAngle);
}

EncSample enc_read(int cs_pin) {
  EncSample s;
  s.raw = 0;
  s.deg = 0.0f;
  s.ok = false;
  s.mag_err = false;

  uint16_t frame = xfer16(cs_pin, kCmdAngle);
  s.raw = frame & 0x3FFF;
  s.deg = (360.0f * (float)s.raw) / (float)ENC_COUNTS;
  s.mag_err = (frame & 0x4000) != 0;
  s.parity_ok = even_parity_ok(frame);
  // bit 14 is a warning on this board. 0 and 16383 are a floating miso line.
  s.ok = s.raw != 0 && s.raw != 0x3FFF;
  return s;
}

float wrap_deg(float deg) {
  while (deg > 180.0f) {
    deg -= 360.0f;
  }
  while (deg < -180.0f) {
    deg += 360.0f;
  }
  return deg;
}
