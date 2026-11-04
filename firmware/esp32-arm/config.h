#pragma once

// one sentence: this board talks to two drone escs and two as5047p chips.
// it can spin a motor. it cannot hold a joint. see README.md.

#define FW_VERSION "0.2.4"

#ifndef BOARD_IS_SHOULDER
#define BOARD_IS_SHOULDER 0
#endif

// Shared wiring. Elbow motion numbers are in elbow_config.h.
// Shoulder motion numbers are in shoulder_config.h.

// --- board pins (esp32 devkitc). change these to match your wiring. ---
#define PIN_ESC_SHOULDER 25
#define PIN_ESC_ELBOW 26
#define PIN_ENC_SCK 18
#define PIN_ENC_MISO 19
#define PIN_ENC_MOSI 23
#define PIN_ENC_CS_SHOULDER 4
#define PIN_ENC_CS_ELBOW 5
#define PIN_KILL 27          // button to gnd. held low = cut throttle
#define PIN_ARMED_LED 2

// --- esc pwm ---
// standard hobby throttle: 1000 us stop, 2000 us full, 50 hz.
#define ESC_PERIOD_US 20000
#define ESC_MIN_US 1000
#define ESC_MAX_US 2000
#define ESC_ARM_US 1000
#define ESC_ARM_MS 2500
#define ESC_PWM_RES_BITS 16
#define ESC_PWM_FREQ_HZ 50

// 12 v bench. 12% is the elbow cap. Do not change it here.
#define ESC_THROTTLE_CAP_PERCENT 12
#define OPEN_THROTTLE_PERCENT 12
#define OPEN_ON_MS 200
#define OPEN_OFF_MS 500
#define OPEN_TOTAL_MS 1400

// spin stops if the serial line stays quiet this long. type stop or x sooner.
#define ESC_DEADMAN_MS 20000

// --- encoder ---
#define ENC_SPI_HZ 1000000
#define ENC_COUNTS 16384
#define SHOULDER_RATIO 30.0f
#define ELBOW_RATIO 1.0f

#include "elbow_config.h"
#include "shoulder_config.h"

// 0 = spin and encoder only. 1 = experimental outer pid on esc (will not hold).
#define UNSAFE_ESC_POSITION 0
