"""Simulated ODrive (fw 0.5.1 property tree) for developing the GUI without hardware.

It reproduces the real bench board's starting state (wrong encoder cs pin, so
the encoder reports ABS_SPI_COM_FAIL) and simulates calibration, closed-loop
control, heating, the watchdog and the reboot after save_configuration.
"""

from __future__ import annotations

import math
import random
import time
from typing import Any

from .. import meta as meta_mod
from .base import DeviceInfo, Transport, TransportError

AXIS_ERR = {"INVALID_STATE": 1, "MOTOR_FAILED": 64, "ENCODER_FAILED": 256, "WATCHDOG": 2048}
ENC_SPI_FAIL = 128
MOTOR_R_RANGE = 1


class MockTransport(Transport):
    """In-memory device with simple single-inertia motor physics on axis0."""

    name = "mock"

    def __init__(self):
        self.meta = meta_mod.load("0.5.1")
        self.v: dict[str, Any] = {}
        self._t = time.monotonic()
        self._down_until = 0.0
        self._timers: dict[int, tuple[int, float]] = {}
        self._fed: dict[int, float] = {0: 0.0, 1: 0.0}
        self._integ = [0.0, 0.0]
        self._state = [[0.0, 0.0], [0.0, 0.0]]
        self._reset()

    def _reset(self) -> None:
        """Seed every property with a zero and then the real board's observed values."""
        for path, m in self.meta.props.items():
            self.v[path] = False if m.get("type") == "bool" else 0.0 if m.get("type") == "float32" else 0
        self.v.update({
            "vbus_voltage": 20.2, "serial_number": 0x378635693034, "fw_version_minor": 5, "fw_version_revision": 1,
            "hw_version_major": 3, "hw_version_minor": 6, "hw_version_variant": 56,
            "config.brake_resistance": 2.0, "config.dc_bus_overvoltage_trip_level": 59.92,
            "config.dc_bus_undervoltage_trip_level": 8.0, "config.dc_max_negative_current": -1e-6,
            "config.dc_max_positive_current": math.inf, "can.config.baud_rate": 250000, "brake_resistor_armed": True,
        })
        for ax in (0, 1):
            a = f"axis{ax}"
            self.v.update({
                f"{a}.current_state": 1, f"{a}.encoder.config.mode": 257, f"{a}.encoder.config.cpr": 8192,
                f"{a}.encoder.config.abs_spi_cs_gpio_pin": 1, f"{a}.encoder.config.bandwidth": 1000.0,
                f"{a}.encoder.config.calib_range": 0.02, f"{a}.motor.config.pole_pairs": 20 if ax == 0 else 7,
                f"{a}.motor.config.calibration_current": 12.0, f"{a}.motor.config.current_lim": 12.0,
                f"{a}.motor.config.current_lim_margin": 8.0, f"{a}.motor.config.torque_lim": 20.0,
                f"{a}.motor.config.resistance_calib_max_voltage": 2.0, f"{a}.motor.config.requested_current_range": 60.0,
                f"{a}.motor.config.torque_constant": 0.04, f"{a}.motor.config.current_control_bandwidth": 1000.0,
                f"{a}.controller.config.control_mode": 3, f"{a}.controller.config.input_mode": 1,
                f"{a}.controller.config.pos_gain": 20.0, f"{a}.controller.config.vel_gain": 0.16,
                f"{a}.controller.config.vel_integrator_gain": 0.32, f"{a}.controller.config.vel_limit": 2.0,
                f"{a}.controller.config.vel_limit_tolerance": 1.2, f"{a}.controller.config.enable_vel_limit": True,
                f"{a}.trap_traj.config.vel_limit": 2.0, f"{a}.trap_traj.config.accel_limit": 0.5,
                f"{a}.trap_traj.config.decel_limit": 0.5, f"{a}.fet_thermistor.temperature": 32.0,
                f"{a}.fet_thermistor.config.temp_limit_lower": 100.0, f"{a}.fet_thermistor.config.temp_limit_upper": 120.0,
                f"{a}.fet_thermistor.config.enabled": True,
            })

    # ---------- transport api ----------

    def connect(self, serial: str | None, timeout: float) -> DeviceInfo:
        """Pretend to connect; fails while a simulated reboot is in progress."""
        if time.monotonic() < self._down_until:
            time.sleep(min(timeout, 0.2))
            raise TransportError("mock device rebooting")
        return DeviceInfo(serial="378635693034", fw=(0, 5, 1), hw=(3, 6, 56), extra={"simulated": True})

    def close(self) -> None:
        """Nothing to release."""

    def tree(self) -> dict[str, dict]:
        """Use the 0.5.1 metadata as the property tree."""
        out = {p: {"kind": "prop", "type": m.get("type"), "writable": m.get("access") == "rw"} for p, m in self.meta.props.items()}
        out.update({p: {"kind": "func", "args": [a["name"] for a in f["in"]]} for p, f in self.meta.funcs.items()})
        return out

    def _alive(self) -> None:
        if time.monotonic() < self._down_until:
            raise TransportError("mock device rebooting")

    def read(self, path: str) -> Any:
        """Advance the simulation and return the current value."""
        self._alive()
        self._step()
        if path not in self.v:
            raise KeyError(path)
        return self.v[path]

    def write(self, path: str, value: Any) -> None:
        """Store a value; requested_state starts the simulated state machine."""
        self._alive()
        self._step()
        if path not in self.v:
            raise KeyError(path)
        if self.meta.prop(path).get("access") == "r":
            raise PermissionError(f"'{path}' is read-only")
        self.v[path] = value
        if path.endswith(".requested_state"):
            self._request(int(path[4]), int(value))

    def call(self, path: str, args: list[Any]) -> Any:
        """Simulate device functions."""
        self._alive()
        if path in ("save_configuration", "reboot"):
            self._down_until = time.monotonic() + 1.5
            for ax in (0, 1):
                self.v[f"axis{ax}.current_state"] = 1
            return None
        if path == "erase_configuration":
            self._reset()
            self._down_until = time.monotonic() + 1.5
            return None
        if path.endswith(".clear_errors"):
            a = path.split(".")[0]
            for sub in ("", "motor.", "encoder.", "controller.", "sensorless_estimator."):
                self.v[f"{a}.{sub}error"] = 0
            return None
        if path.endswith(".watchdog_feed"):
            self._fed[int(path[4])] = time.monotonic()
            return None
        if path == "can.set_baud_rate":
            self.v["can.config.baud_rate"] = int(args[0])
            return None
        if path == "get_adc_voltage":
            return 1.65 + random.gauss(0, 0.002)
        return None

    # ---------- simulation ----------

    def _encoder_ok(self, ax: int) -> bool:
        a = f"axis{ax}.encoder.config"
        return ax == 0 and self.v[f"{a}.mode"] == 257 and self.v[f"{a}.abs_spi_cs_gpio_pin"] == 4

    def _request(self, ax: int, state: int) -> None:
        a = f"axis{ax}"
        self.v[f"{a}.requested_state"] = 0
        if state == 1:
            self.v[f"{a}.current_state"] = 1
            self._timers.pop(ax, None)
            return
        motor_ok = self.v[f"{a}.motor.is_calibrated"]
        enc_ready = self.v[f"{a}.encoder.is_ready"]
        if (state in (7, 8) and not motor_ok) or (state == 8 and not enc_ready):
            self.v[f"{a}.error"] |= AXIS_ERR["INVALID_STATE"]
            return
        if state in (3, 4, 7, 8):
            if self.v[f"{a}.error"]:
                return
            self.v[f"{a}.current_state"] = 4 if state == 3 else state
            self._timers[ax] = (state, time.monotonic())
            if state == 8:
                self.v[f"{a}.controller.input_pos"] = self._state[ax][0]
                self._integ[ax] = 0.0
                self._fed[ax] = time.monotonic()

    def _step(self) -> None:
        now = time.monotonic()
        dt = min(now - self._t, 0.05)
        self._t = now
        if dt <= 0:
            return
        self.v["axis0.loop_counter"] = (self.v["axis0.loop_counter"] + int(8000 * dt)) & 0xFFFFFFFF
        self.v["axis1.loop_counter"] = self.v["axis0.loop_counter"]
        ibus = 0.0
        for ax in (0, 1):
            ibus += self._step_axis(ax, now, dt)
        self.v["ibus"] = ibus
        self.v["vbus_voltage"] = 20.2 - 0.05 * ibus + random.gauss(0, 0.01)

    def _step_axis(self, ax: int, now: float, dt: float) -> float:
        a = f"axis{ax}"
        v = self.v
        # encoder health mirrors the real board: wrong cs pin -> spi failure
        if v[f"{a}.encoder.config.mode"] >= 256:
            if self._encoder_ok(ax):
                v[f"{a}.encoder.spi_error_rate"] = 0.0
            else:
                v[f"{a}.encoder.spi_error_rate"] = 0.9998
                v[f"{a}.encoder.error"] |= ENC_SPI_FAIL
                v[f"{a}.error"] |= AXIS_ERR["ENCODER_FAILED"]
                v[f"{a}.encoder.pos_abs"] = 16383
        state = v[f"{a}.current_state"]
        timer = self._timers.get(ax)
        if timer:
            target, t0 = timer
            if state == 4 and now - t0 > 2.5:
                r = 0.094 * (1 + random.gauss(0, 0.02))
                if v[f"{a}.motor.config.calibration_current"] * r > v[f"{a}.motor.config.resistance_calib_max_voltage"] or ax == 1:
                    v[f"{a}.motor.error"] |= MOTOR_R_RANGE
                    v[f"{a}.error"] |= AXIS_ERR["MOTOR_FAILED"]
                    v[f"{a}.current_state"] = 1
                    self._timers.pop(ax, None)
                else:
                    v[f"{a}.motor.config.phase_resistance"] = r
                    v[f"{a}.motor.config.phase_inductance"] = 4.2e-5 * (1 + random.gauss(0, 0.03))
                    v[f"{a}.motor.is_calibrated"] = True
                    if target == 3:
                        v[f"{a}.current_state"] = 7
                        self._timers[ax] = (7, now)
                    else:
                        v[f"{a}.current_state"] = 1
                        self._timers.pop(ax, None)
            elif state == 7:
                if not self._encoder_ok(ax):
                    v[f"{a}.error"] |= AXIS_ERR["ENCODER_FAILED"]
                    v[f"{a}.current_state"] = 1
                    self._timers.pop(ax, None)
                elif now - t0 > 4.0:
                    v[f"{a}.encoder.is_ready"] = True
                    v[f"{a}.encoder.config.offset"] = 1234
                    v[f"{a}.current_state"] = 1
                    self._timers.pop(ax, None)
        # watchdog
        if v[f"{a}.config.enable_watchdog"] and v[f"{a}.config.watchdog_timeout"] > 0:
            if now - self._fed[ax] > v[f"{a}.config.watchdog_timeout"]:
                v[f"{a}.error"] |= AXIS_ERR["WATCHDOG"]
        if v[f"{a}.error"] and state == 8:
            v[f"{a}.current_state"] = state = 1
        return self._physics(ax, state, dt)

    def _physics(self, ax: int, state: int, dt: float) -> float:
        a = f"axis{ax}"
        v = self.v
        c = f"{a}.controller"
        kt = v[f"{a}.motor.config.torque_constant"] or 0.04
        # true state lives apart from the published (noisy) estimates
        pos, vel = self._state[ax]
        torque = 0.0
        if state == 8:
            mode = v[f"{c}.config.control_mode"]
            vel_lim = v[f"{c}.config.vel_limit"]
            if mode == 1:
                torque = v[f"{c}.input_torque"]
                vel_cmd = vel
            else:
                vel_cmd = v[f"{c}.input_vel"]
                if mode == 3:
                    vel_cmd += v[f"{c}.config.pos_gain"] * (v[f"{c}.input_pos"] - pos)
                vel_cmd = max(-vel_lim, min(vel_lim, vel_cmd))
                err = vel_cmd - vel
                self._integ[ax] += v[f"{c}.config.vel_integrator_gain"] * err * dt
                torque = v[f"{c}.config.vel_gain"] * err + self._integ[ax] + v[f"{c}.input_torque"]
            tmax = kt * v[f"{a}.motor.config.current_lim"]
            torque = max(-tmax, min(tmax, torque))
            v[f"{c}.pos_setpoint"] = v[f"{c}.input_pos"]
            v[f"{c}.vel_setpoint"] = vel_cmd
            v[f"{c}.torque_setpoint"] = torque
        # single inertia with coulomb + viscous friction, in turns
        inertia, coulomb, visc = 4e-4, 0.015, 0.002
        fric = coulomb * math.copysign(1, vel) if abs(vel) > 1e-3 else max(-coulomb, min(coulomb, torque))
        acc = (torque - fric - visc * vel) / inertia / (2 * math.pi)
        vel += acc * dt
        if state != 8 and abs(vel) < 0.05:
            vel = 0.0
        pos += vel * dt
        self._state[ax] = [pos, vel]
        iq = torque / kt
        v[f"{a}.encoder.pos_estimate"] = pos + random.gauss(0, 2e-5)
        v[f"{a}.encoder.vel_estimate"] = vel + random.gauss(0, 2e-3)
        cpr = v[f"{a}.encoder.config.cpr"] or 16384
        v[f"{a}.encoder.shadow_count"] = int(pos * cpr)
        v[f"{a}.encoder.count_in_cpr"] = int(pos * cpr) % cpr
        if self._encoder_ok(ax):
            # a real AS5047P flickers by about one count at standstill
            v[f"{a}.encoder.pos_abs"] = int(pos * 16384 + 8000 + random.gauss(0, 0.8)) % 16384
        v[f"{a}.motor.current_control.Iq_setpoint"] = iq
        v[f"{a}.motor.current_control.Iq_measured"] = iq + random.gauss(0, 0.03)
        v[f"{a}.motor.current_meas_phB"] = random.gauss(0, 0.02)
        v[f"{a}.motor.current_meas_phC"] = random.gauss(0, 0.02)
        temp = v[f"{a}.fet_thermistor.temperature"]
        v[f"{a}.fet_thermistor.temperature"] = temp + (iq * iq * 0.004 - (temp - 30.0) * 0.01) * dt
        v[f"{a}.motor.armed_state"] = 3 if state in (4, 7, 8) else 0
        return abs(iq) * 0.05 + (0.04 if state == 8 else 0.0)
