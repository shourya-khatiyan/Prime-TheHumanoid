#include "esc.h"
#include "soc/soc.h"
#include "soc/rtc_cntl_reg.h"

extern "C" void initVariant(void) {
  WRITE_PERI_REG(RTC_CNTL_BROWN_OUT_REG, 0);
}

static const int kPins[ESC_COUNT] = {PIN_ESC_SHOULDER, PIN_ESC_ELBOW};
static const int kChannels[ESC_COUNT] = {0, 1};

// map pulse width onto the 16-bit ledc duty for a 20 ms period.
static uint32_t pulse_to_duty(uint16_t pulse_us) {
  const uint32_t max_duty = (1UL << ESC_PWM_RES_BITS) - 1UL;
  uint32_t duty = (uint32_t)pulse_us * max_duty / ESC_PERIOD_US;
  if (duty > max_duty) {
    duty = max_duty;
  }
  return duty;
}

static void attach_channel(EscId id) {
#if ESP_ARDUINO_VERSION_MAJOR >= 3
  ledcAttach(kPins[id], ESC_PWM_FREQ_HZ, ESC_PWM_RES_BITS);
#else
  ledcSetup(kChannels[id], ESC_PWM_FREQ_HZ, ESC_PWM_RES_BITS);
  ledcAttachPin(kPins[id], kChannels[id]);
#endif
}

static void write_duty(EscId id, uint32_t duty) {
#if ESP_ARDUINO_VERSION_MAJOR >= 3
  ledcWrite(kPins[id], duty);
#else
  ledcWrite(kChannels[id], duty);
#endif
}

void esc_begin() {
  pinMode(PIN_KILL, INPUT_PULLUP);
  pinMode(PIN_ARMED_LED, OUTPUT);
  digitalWrite(PIN_ARMED_LED, LOW);
  for (int i = 0; i < ESC_COUNT; i++) {
    attach_channel((EscId)i);
    write_duty((EscId)i, pulse_to_duty(ESC_ARM_US));
  }
}

uint16_t esc_percent_to_us(float percent) {
  if (percent < 0.0f) {
    percent = 0.0f;
  }
  if (percent > ESC_THROTTLE_CAP_PERCENT) {
    percent = ESC_THROTTLE_CAP_PERCENT;
  }
  const float span = (float)(ESC_MAX_US - ESC_MIN_US);
  return (uint16_t)(ESC_MIN_US + span * (percent / 100.0f));
}

void esc_write_us(EscId id, uint16_t pulse_us) {
  if (id < 0 || id >= ESC_COUNT) {
    return;
  }
  if (pulse_us < ESC_MIN_US) {
    pulse_us = ESC_MIN_US;
  }
  if (pulse_us > ESC_MAX_US) {
    pulse_us = ESC_MAX_US;
  }
  write_duty(id, pulse_to_duty(pulse_us));
}

void esc_write_percent(EscId id, float percent) {
  esc_write_us(id, esc_percent_to_us(percent));
}

void esc_all_stop() {
  for (int i = 0; i < ESC_COUNT; i++) {
    esc_write_us((EscId)i, ESC_ARM_US);
  }
  digitalWrite(PIN_ARMED_LED, LOW);
}

bool esc_kill_pressed() {
  return digitalRead(PIN_KILL) == LOW;
}
