# Commissioning the shoulder actuator

Follow the **Commissioning** screen top to bottom. Gearbox disconnected, bench PSU with a current
limit (start ~3 A), hardware e-stop in reach.

## Board facts (read from this unit)

- ODESC 3.6 56V, hw 3.6-56V, firmware 0.5.1 (Flipsky build; 0.5.6 is the last official v3.6 release)
- USB: CDC COM port + native interface (WinUSB). Run `tools/fix_winusb_guid.ps1` once per PC,
  otherwise libusb cannot open the native interface (the firmware omits the interface GUID)
- Found misconfigured: encoder CS on GPIO1 (UART pin), cpr 8192, over-voltage trip 59.9 V,
  calibration current 12 A, CAN 250 kbit

## Encoder: absolute vs incremental

The AS5047P has two independent outputs:

| | absolute (SPI) | incremental (ABI) |
|---|---|---|
| wires to ODrive | 3V3, GND, SCK, MISO, MOSI (or tie to 3V3), CSn -> GPIO | 3V3, GND, A, B, I (Z) on the encoder connector |
| ODrive mode | `ENCODER_MODE_SPI_ABS_AMS` (257) | `ENCODER_MODE_INCREMENTAL` (0) |
| cpr | 16384 (14 bit) | 4000 (1000 pulses x 4, chip default) |
| at power-up | knows the rotor angle immediately | knows nothing until the index pulse (`use_index`) |
| per-boot motion | none once `pre_calibrated` | index search turns the motor |

**This actuator uses SPI absolute mode** (wired on MISO/MOSI/SCK + CS on GPIO4); the profile
default `encoder.mode: SPI_ABS_AMS` matches. Absolute here means absolute within one motor
revolution: with the 30:1 two-stage planetary gearbox (6:1 stage 1 × 5:1 stage 2) the joint angle is still ambiguous across the 12 deg sectors, so
the output-side absolute encoder (Phase 1, P1.6) remains required before arm motion.

Reading the encoder card:
- `spi error rate` ~0 and `pos_abs` changing when you turn the shaft: good
- `pos_abs` stuck at 16383: MISO floating or CS on the wrong pin
- `pos_abs` stuck at 0 with a low error rate: frames are all zeros (passes parity), so MISO is
  held low or the encoder is unpowered, or the new mode/CS pin has not been activated yet:
  on fw 0.5.1 encoder mode and CS changes need **save configuration + reboot**

## Steps

1. **Identify**: transport, serial, fw, hw.
2. **Encoder wiring**: table + live encoder card + hand-turn test (one slow turn by hand, expect
   ~16384 counts, no jumps, no SPI errors). Run it after steps 3-4.
3. **Apply profile**: diff of device vs profile, then apply (confirm). Sets bring-up limits:
   6 A current limit, 5 A calibration current, 4 V R-cal voltage, 2 turn/s, 28 V over-voltage
   trip, encoder mode/cpr/CS, brake resistance, unused axis encoder off. Live, not saved.
4. **Save + reboot**: the GUI reconnects by itself.
5. **Health check**: passive, see [HEALTH_CHECKS.md](HEALTH_CHECKS.md). Fix every FAIL first.
6. **Motor calibration**: measures R and L (expect ~0.093 ohm phase-to-neutral if the 0.186 ohm
   datasheet value is line-to-line; L 2-4000 uH).
7. **Encoder offset calibration**: rotor turns slowly; sets `pre_calibrated`; save again.
   `CPR_POLEPAIRS_MISMATCH` means wrong pole pairs (20), wrong cpr, or a slipping magnet.
8. **First spin**: velocity step to 0.5 turn/s for 2 s; peak Iq should stay well below 6 A.

Then: Tests > tuning (step / sweep / sine), thermal holds at 6/8/12 A with a motor NTC fitted,
characterization with the gearbox (friction, Kt/efficiency with a torque arm, lost motion).

## Firmware 0.5.6

Firmware screen: backup config, ST-Link dump of flash + OTP, WinUSB for `STM32 BOOTLOADER`,
then the guarded flash job (official `ODriveFirmware_v3.6-56V.elf` converted to hex, `odrivetool
dfu`, reconnect, multimeter check of vbus scaling). Flipsky boards may differ from the reference
hardware; the backup is the way back.
