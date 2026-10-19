"""Safety layer: every write and call from the GUI passes through here.

Responsibilities:
- clamp setpoints and reject limit values beyond the actuator profile
- require a short-lived confirmation token for dangerous actions
- enable and feed the ODrive watchdog while the GUI has an axis active
- disarm on GUI heartbeat loss, bus voltage, temperature, current, speed or position faults
- raise alarms (with first-out tracking) when error registers change
- write every action to the audit log
"""

from __future__ import annotations

import math
import secrets
import threading
import time
from typing import Any

from .device import DeviceWorker
from .profile import Profile, save_profile
from .storage import AuditLog
from .transport import Transport, TransportError

IDLE = 1
STATE_NAMES = {0: "UNDEFINED", 1: "IDLE", 2: "STARTUP_SEQUENCE", 3: "FULL_CALIBRATION_SEQUENCE", 4: "MOTOR_CALIBRATION",
               5: "SENSORLESS_CONTROL", 6: "ENCODER_INDEX_SEARCH", 7: "ENCODER_OFFSET_CALIBRATION", 8: "CLOSED_LOOP_CONTROL",
               9: "LOCKIN_SPIN", 10: "ENCODER_DIR_FIND", 11: "HOMING", 12: "ENCODER_HALL_POLARITY_CALIBRATION",
               13: "ENCODER_HALL_PHASE_CALIBRATION"}
DANGEROUS_CALLS = {"save_configuration", "erase_configuration", "reboot", "enter_dfu_mode",
                   "controller.start_anticogging_calibration", "can.set_baud_rate"}
ERROR_ALIASES = ["error", "motor_error", "enc_error", "ctrl_error"]


class ConfirmRequired(Exception):
    """Raised when an action needs an explicit confirmation token from the user."""

    def __init__(self, action: str, message: str):
        super().__init__(message)
        self.action = action
        self.message = message


class Safety:
    """Guards device access and monitors telemetry for unsafe conditions."""

    def __init__(self, worker: DeviceWorker, profile: Profile, audit: AuditLog):
        self.worker = worker
        self.profile = profile
        self.audit = audit
        self.tokens: dict[str, tuple[str, float]] = {}
        self.active_axes: set[int] = set()
        self._activated: dict[int, float] = {}
        self._wd_enabled: set[int] = set()
        self.client_seen = time.monotonic()
        self.client_count = 0
        self.alarms: dict[str, dict] = {}
        self.first_out: str | None = None
        self._prev_err: dict[str, int] = {}
        # per-axis zero (motor turns) that the position window and joint angles are measured from
        self.origin: dict[int, float] = {0: 0.0, 1: 0.0}
        self._origin_gen = worker.generation
        self._last_feed = 0.0
        self._lock = threading.Lock()
        worker.sample_hooks.append(self.on_sample)
        worker.tick_hooks.append(self.on_tick)

    # ---------- confirmation tokens ----------

    def arm(self, action: str, ttl: float = 20.0) -> dict:
        """Issue a one-shot token that authorizes exactly `action` for `ttl` seconds."""
        tok = secrets.token_hex(8)
        with self._lock:
            now = time.monotonic()
            self.tokens = {k: v for k, v in self.tokens.items() if v[1] > now}
            self.tokens[tok] = (action, now + ttl)
        return {"token": tok, "action": action, "ttl": ttl}

    def consume(self, action: str, token: str | None) -> bool:
        if not token:
            return False
        with self._lock:
            entry = self.tokens.pop(token, None)
        return bool(entry and entry[0] == action and entry[1] > time.monotonic())

    def _require(self, action: str, token: str | None, message: str) -> None:
        if not self.consume(action, token):
            raise ConfirmRequired(action, message)

    # ---------- limits ----------

    def _limit_for(self, path: str) -> tuple[float | None, str, float | None]:
        """Return (profile max, profile key, hardware max) for a limit-type path."""
        p = self.profile
        tail = path.split(".", 1)[1] if path.startswith("axis") else path
        table = {
            "motor.config.current_lim": (p.get("motor.current_peak_a"), "motor.current_peak_a", 60.0),
            "motor.config.calibration_current": (p.get("motor.current_continuous_a"), "motor.current_continuous_a", 25.0),
            "motor.config.torque_lim": (p.torque_max_nm, "derived torque_max_nm", 20.0),
            "motor.config.requested_current_range": (60.0, "hardware range 60 A", 60.0),
            "controller.config.vel_limit": (p.get("limits.vel_max_turns_s"), "limits.vel_max_turns_s", 100.0),
            "trap_traj.config.vel_limit": (p.get("limits.vel_max_turns_s"), "limits.vel_max_turns_s", 100.0),
            "config.dc_bus_overvoltage_trip_level": (p.get("power.overvoltage_trip_v"), "power.overvoltage_trip_v", 58.0),
            "config.dc_max_positive_current": (p.get("motor.current_peak_a"), "motor.current_peak_a", 60.0),
            "motor.config.resistance_calib_max_voltage": (16.0, "max calibration voltage 16 V", 18.0),
        }
        lim, label, hw_max = table.get(tail, (None, "", None))
        return ((float(lim) if lim is not None else None), label, hw_max)

    def _expand_profile_limit(self, label: str, value: float) -> None:
        """Raise the matching profile limit when the operator sets a higher value within hardware bounds."""
        if "." not in label or label.startswith("derived"):
            return
        sec, key = label.split(".", 1)
        if isinstance(self.profile.data.get(sec), dict) and key in self.profile.data[sec]:
            self.profile.data[sec][key] = float(value)
            if sec == "power" and key == "overvoltage_trip_v":
                self.profile.data["power"]["bus_max_v"] = max(float(self.profile.get("power.bus_max_v", 26.5)), float(value) - 1.5)
            save_profile(self.profile.data)

    def clamp_setpoint(self, path: str, value: float) -> tuple[float, str | None]:
        """Clamp input_pos / input_vel / input_torque to the profile envelope.

        Returns:
            (clamped value, warning text or None).
        """
        p = self.profile
        if path.endswith("controller.input_torque"):
            lo, hi = -p.torque_max_nm, p.torque_max_nm
        elif path.endswith("controller.input_vel"):
            v = float(p.get("limits.vel_max_turns_s", 1))
            lo, hi = -v, v
        elif path.endswith("controller.input_pos"):
            ax = int(path[4])
            org = self.origin.get(ax, 0.0)
            lo, hi = org + float(p.get("limits.pos_min_turns", -1)), org + float(p.get("limits.pos_max_turns", 1))
            # clamping would drag an axis that is already outside the window across the whole range
            pos = self.worker.latest.get(self.worker.path(f"pos.{ax}") or "")
            margin = 0.05 * (hi - lo)
            if isinstance(pos, float) and not (lo - margin <= pos <= hi + margin):
                raise ValueError(f"axis{ax} is at {pos:.2f} motor turns, outside the position window {lo:.1f}..{hi:.1f} "
                                 f"(zero {org:.2f} {p.get('limits.pos_min_turns')}..{p.get('limits.pos_max_turns')} turns). "
                                 "Click 'set zero here' in Control, then retry.")
        else:
            return value, None
        if not math.isfinite(value):
            raise ValueError(f"{path}: non-finite setpoint rejected")
        c = min(hi, max(lo, value))
        return c, (f"clamped {value:g} -> {c:g} (profile limit)" if c != value else None)

    # ---------- guarded operations (run on the worker thread) ----------

    def write(self, path: str, value: Any, token: str | None = None, source: str = "gui") -> dict:
        """Validate and perform one property write. Returns {'value', 'old', 'warning'}.

        Raises:
            ConfirmRequired: the action needs user confirmation (retry with a token).
            ValueError: the value violates the profile.
        """
        meta = self.worker.meta
        value = meta.parse_value(path, value) if meta else value
        warning = None
        if path.endswith(".requested_state"):
            return self._request_state(path, int(value), token, source)
        if path.endswith((".input_torque", ".input_vel", ".input_pos")):
            value, warning = self.clamp_setpoint(path, float(value))
        lim, label, hw_max = self._limit_for(path)

        def op(t: Transport) -> dict:
            nonlocal warning
            old = t.read(path)
            if path.endswith("controller.config.control_mode") and int(path[4]) in self.active_axes and value != old:
                # bumpless switch: the new loop would otherwise chase a stale input_pos / input_vel / input_torque
                self._reset_setpoints(t, int(path[4]))
            if lim is not None and isinstance(value, (int, float)) and value > lim:
                if hw_max is None or value > hw_max:
                    raise ValueError(f"{path} = {value:g} exceeds profile limit {lim:g} (hardware max {hw_max or lim:g})")
                self._require(f"write:{path}", token, f"Raise {path} from {old:g} to {value:g} (and update profile {label})?")
                self._expand_profile_limit(label, float(value))
                warning = f"updated profile {label} -> {value:g}"
            elif lim is not None and isinstance(old, (int, float)) and value > old:
                self._require(f"write:{path}", token, f"Raise {path} from {old:g} to {value:g}?")
            t.write(path, value)
            return {"value": value, "old": old, "warning": warning}

        return self._audited("write", source, path, value, op)

    def _request_state(self, path: str, state: int, token: str | None, source: str) -> dict:
        ax = int(path[4])
        name = STATE_NAMES.get(state, str(state))

        def op(t: Transport) -> dict:
            old = t.read(self.worker.path(f"state.{ax}") or path)
            if state in (0, IDLE):
                t.write(path, IDLE)
                self.active_axes.discard(ax)
                return {"value": IDLE, "old": old, "warning": None}
            self._preflight(t, ax, state)
            self._require(f"state:{ax}:{state}", token, f"Put axis{ax} into {name}? The motor will be energized.")
            if state == 8:
                self._reset_setpoints(t, ax)
            self._enable_watchdog(t, ax)
            self.active_axes.add(ax)
            self._activated[ax] = self.client_seen = time.monotonic()
            t.write(path, state)
            return {"value": state, "old": old, "warning": None}

        return self._audited("write", source, path, state, op)

    def _preflight(self, t: Transport, ax: int, state: int) -> None:
        """Refuse to energize the motor when the device config is outside the profile."""
        w, p = self.worker, self.profile
        vbus = t.read(w.path("vbus"))
        if not (p.get("power.bus_min_v") <= vbus <= p.get("power.bus_max_v")):
            raise ValueError(f"bus voltage {vbus:.2f} V outside profile window {p.get('power.bus_min_v')}-{p.get('power.bus_max_v')} V")
        checks = [("current_lim", p.get("motor.current_peak_a")), ("vel_limit", p.get("limits.vel_max_turns_s"))]
        for alias, lim in checks:
            path = w.path(f"{alias}.{ax}")
            if path:
                val = t.read(path)
                if isinstance(val, (int, float)) and val > float(lim) * 1.0001:
                    raise ValueError(f"{path} = {val:g} is above the profile limit {lim}; apply profile limits first")
        trip = self._safe_read(t, "config.dc_bus_overvoltage_trip_level")
        if isinstance(trip, float) and trip > float(p.get("power.overvoltage_trip_v")) + 0.01:
            raise ValueError(f"over-voltage trip {trip:.1f} V is above profile {p.get('power.overvoltage_trip_v')} V; apply profile power settings first")
        if state == 8:
            for alias in ("iq", "pos"):
                if not w.path(f"{alias}.{ax}"):
                    raise ValueError(f"axis{ax} has no {alias} telemetry")

    def set_origin(self, ax: int, value: float | None = None, source: str = "gui") -> float:
        """Set the axis zero (motor turns) used by the position window and joint angles.

        Inputs: axis index, and a position in motor turns (None = where the rotor is now).
        Output: the new zero. It resets to 0 whenever the board reconnects, because
        the encoder count restarts at boot.
        """
        if value is None:
            value = self.worker.latest.get(self.worker.path(f"pos.{ax}") or "")
            if not isinstance(value, float):
                raise ValueError(f"axis{ax} has no position reading yet")
        old = self.origin.get(ax, 0.0)
        self.origin[ax] = float(value)
        self.audit.add("config", source, f"axis{ax}.origin", old, float(value), detail="zero set")
        return float(value)

    def _reset_setpoints(self, t: Transport, ax: int) -> None:
        """Start closed loop at rest: hold the current position, zero velocity, torque and the integrator.

        The odrive keeps the last setpoints after a fault, so without this a setpoint that tripped
        the axis is applied again the moment closed loop is re-entered.
        """
        w = self.worker
        hold = t.read(w.path(f"pos.{ax}"))
        for alias, value in (("input_pos", hold), ("input_vel", 0.0), ("input_torque", 0.0), ("vel_integ", 0.0)):
            path = w.path(f"{alias}.{ax}")
            if path:
                t.write(path, value)

    @staticmethod
    def _safe_read(t: Transport, path: str) -> Any:
        try:
            return t.read(path)
        except TransportError:
            raise
        except Exception:
            return None

    def call(self, path: str, args: list[Any], token: str | None = None, source: str = "gui") -> Any:
        """Validate and perform a device function call."""
        tail = path.split(".", 1)[1] if path.startswith("axis") else path
        if tail in DANGEROUS_CALLS:
            if path in ("save_configuration", "erase_configuration", "reboot", "enter_dfu_mode"):
                # saving/rebooting while energized would drop the motor
                if self.active_axes:
                    raise ValueError("disarm all axes before saving, erasing or rebooting")
            self._require(f"call:{path}", token, {
                "save_configuration": "Save configuration to flash? The board may reboot.",
                "erase_configuration": "Erase ALL configuration and reboot to factory defaults?",
                "reboot": "Reboot the ODrive?",
                "enter_dfu_mode": "Enter DFU (firmware update) mode? The board stops responding until flashed or power-cycled.",
            }.get(path, f"Run {path}?"))

        def op(t: Transport) -> Any:
            try:
                return t.call(path, list(args))
            except TransportError:
                if path in ("save_configuration", "reboot", "erase_configuration", "enter_dfu_mode"):
                    return None  # the board dropped the link because it rebooted
                raise

        return self._audited("call", source, path, list(args), op)

    def _audited(self, kind: str, source: str, path: str, value: Any, op) -> Any:
        fut = self.worker.submit(op)
        try:
            res = fut.result(timeout=10)
        except ConfirmRequired:
            raise
        except Exception as ex:
            self.audit.add(kind, source, path, None, value, ok=False, detail=str(ex))
            raise
        old = res.get("old") if isinstance(res, dict) else None
        self.audit.add(kind, source, path, old, value, ok=True, detail=(res.get("warning") or "") if isinstance(res, dict) else "")
        return res

    # ---------- watchdog ----------

    def _enable_watchdog(self, t: Transport, ax: int) -> None:
        w = self.worker
        en, to, feed = w.path(f"wd_enable.{ax}"), w.path(f"wd_timeout.{ax}"), w.path(f"watchdog_feed.{ax}")
        if not (en and to and feed):
            return
        t.write(to, float(self.profile.get("watchdog.timeout_s", 0.5)))
        t.call(feed, [])
        t.write(en, True)
        self._wd_enabled.add(ax)

    def on_tick(self, w: DeviceWorker) -> None:
        """Feed the watchdog for active axes, and drop to idle if the GUI went away."""
        now = time.monotonic()
        if self.active_axes and now - self.client_seen > 1.5:
            self.active_axes.clear()
            self.audit.add("safety", "monitor", detail="gui heartbeat lost -> disarm")
            w.request_disarm("gui heartbeat lost")
            return
        t = w.transport
        if t is None:
            return
        if self.active_axes and now - self._last_feed > 0.05:
            self._last_feed = now
            for ax in list(self.active_axes):
                feed = w.path(f"watchdog_feed.{ax}")
                if feed:
                    t.call(feed, [])
        # turn the watchdog off again once an axis is back in idle
        for ax in list(self._wd_enabled - self.active_axes):
            st = w.latest.get(w.path(f"state.{ax}") or "")
            if st == IDLE:
                en = w.path(f"wd_enable.{ax}")
                if en:
                    t.write(en, False)
                self._wd_enabled.discard(ax)

    def heartbeat(self) -> None:
        """Called whenever any GUI client is alive."""
        self.client_seen = time.monotonic()

    def disarm_all(self, reason: str, source: str = "gui") -> None:
        """Highest-priority stop: both axes to IDLE."""
        self.active_axes.clear()
        self.audit.add("safety", source, detail=f"disarm all: {reason}")
        self.worker.request_disarm(reason)

    # ---------- monitor (runs on the worker thread after each sample) ----------

    def on_sample(self, w: DeviceWorker, cols: list[str], values: list[Any]) -> None:
        """Check limits on fresh telemetry and turn error-register changes into alarms."""
        v = dict(zip(cols, values))
        p = self.profile
        get = lambda alias: v.get(w.path(alias) or "")
        if w.generation != self._origin_gen:
            self._origin_gen = w.generation
            self.origin = {0: 0.0, 1: 0.0}
        vbus = get("vbus")
        for ax in (0, 1):
            state = get(f"state.{ax}")
            if state not in (None, 0, IDLE):
                reason = self._violation(ax, state, vbus, get)
                if reason:
                    self.active_axes.discard(ax)
                    self._alarm(f"limit.{ax}", "alarm", f"axis{ax}: {reason}", [])
                    self.audit.add("safety", "monitor", detail=f"axis{ax} disarm: {reason}")
                    w.request_disarm(f"axis{ax}: {reason}")
            elif ax in self.active_axes and state == IDLE and time.monotonic() - self._activated.get(ax, 0) > 0.5:
                # calibration finished or the axis faulted back to idle
                self.active_axes.discard(ax)
            temp = get(f"fet_temp.{ax}")
            if isinstance(temp, float) and temp > float(p.get("thermal.fet_warn_c", 70)):
                self._alarm(f"fet_temp.{ax}", "warn", f"axis{ax} FET {temp:.1f} C above warn level", [])
        self._check_errors(w, get)

    def _violation(self, ax: int, state: int, vbus: Any, get) -> str | None:
        p = self.profile
        if isinstance(vbus, float) and not (p.get("power.bus_min_v") <= vbus <= p.get("power.bus_max_v")):
            return f"bus voltage {vbus:.2f} V outside window"
        temp = get(f"fet_temp.{ax}")
        if isinstance(temp, float) and temp > float(p.get("thermal.fet_abort_c", 85)):
            return f"FET temperature {temp:.1f} C above abort level"
        mtemp = get(f"motor_temp.{ax}")
        if isinstance(mtemp, float) and get(f"motor_temp_enabled.{ax}") and mtemp > float(p.get("thermal.motor_abort_c", 100)):
            return f"motor temperature {mtemp:.1f} C above abort level"
        iq = get(f"iq.{ax}")
        if isinstance(iq, float) and abs(iq) > float(p.get("motor.current_peak_a")) * 1.15:
            return f"phase current {iq:.1f} A above peak limit"
        if state == 8:
            vel = get(f"vel.{ax}")
            if isinstance(vel, float) and abs(vel) > float(p.get("limits.vel_max_turns_s")) * 1.5:
                return f"velocity {vel:.2f} turn/s above limit"
            if p.get("limits.enforce_pos_limits", False):
                pos = get(f"pos.{ax}")
                lo = self.origin.get(ax, 0.0) + float(p.get("limits.pos_min_turns"))
                hi = self.origin.get(ax, 0.0) + float(p.get("limits.pos_max_turns"))
                margin = 0.05 * (hi - lo)
                if isinstance(pos, float) and not (lo - margin <= pos <= hi + margin):
                    return f"position {pos:.2f} turns outside limits"
        return None

    def _check_errors(self, w: DeviceWorker, get) -> None:
        meta = w.meta
        keys = ["sys_error"] + [f"{a}.{ax}" for ax in (0, 1) for a in ERROR_ALIASES]
        for key in keys:
            path = w.path(key)
            val = get(key)
            if path is None or not isinstance(val, int):
                continue
            prev = self._prev_err.get(path, 0)
            if val == prev:
                continue
            self._prev_err[path] = val
            if val == 0:
                self.alarms.pop(path, None)
                if self.first_out == path:
                    self.first_out = None
                continue
            flags = meta.decode_flags(path, val) if meta else []
            self._alarm(path, "alarm", f"{path} = 0x{val:X}: {', '.join(flags)}", flags)

    def _alarm(self, key: str, level: str, msg: str, flags: list[str]) -> None:
        existing = self.alarms.get(key)
        if existing and existing["msg"] == msg:
            return
        if self.first_out is None and level == "alarm":
            self.first_out = key
        self.alarms[key] = {"key": key, "level": level, "msg": msg, "flags": flags, "ts": time.time(),
                            "acked": False, "shelved_until": 0}
        self.worker.emit({"t": "event", "level": level, "src": "alarm", "msg": msg, "key": key})

    def ack(self, key: str | None = None) -> None:
        """Acknowledge one alarm (or all) so it stops flashing."""
        for k, a in self.alarms.items():
            if key is None or k == key:
                a["acked"] = True

    def shelve(self, key: str, seconds: float) -> None:
        """Hide an alarm for a limited time (logged)."""
        if key in self.alarms:
            self.alarms[key]["shelved_until"] = time.time() + max(10.0, min(3600.0, seconds))
            self.audit.add("safety", "gui", key, detail=f"shelved {seconds:.0f}s")

    def clear_stale_alarms(self) -> None:
        """Drop non-register alarms (limits, temperature warnings) after the user clears errors."""
        for k in [k for k in self.alarms if k.startswith(("limit.", "fet_temp."))]:
            self.alarms.pop(k, None)
        if self.first_out and self.first_out not in self.alarms:
            self.first_out = None

    def status(self) -> dict:
        """Safety summary for the status bar."""
        now = time.time()
        return {
            "active_axes": sorted(self.active_axes),
            "watchdog_axes": sorted(self._wd_enabled),
            "alarms": [a for a in self.alarms.values() if a["shelved_until"] < now],
            "shelved": [a for a in self.alarms.values() if a["shelved_until"] >= now],
            "first_out": self.first_out,
            "origin": self.origin,
        }
