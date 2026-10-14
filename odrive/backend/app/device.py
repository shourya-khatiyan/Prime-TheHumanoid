"""Device worker: the single thread that owns the ODrive connection.

Every read, write and call runs on this thread, in order. Between operations it
samples telemetry at the requested rate, feeds per-sample hooks (safety
monitor, recorder) and reconnects automatically after a reboot or unplug.
"""

from __future__ import annotations

import collections
import logging
import queue
import threading
import time
from concurrent.futures import Future
from typing import Any, Callable

from . import aliases, meta as meta_mod
from .transport import DeviceInfo, Transport, TransportError

log = logging.getLogger("device")

Op = Callable[[Transport], Any]
SampleHook = Callable[["DeviceWorker", list[str], list[Any]], None]


def _make_transport(kind: str) -> Transport:
    """Create a transport by name ('usb', 'ascii' or 'mock')."""
    if kind == "usb":
        from .transport.fibre_usb import FibreUsbTransport

        return FibreUsbTransport()
    if kind == "ascii":
        from .transport.ascii_serial import AsciiSerialTransport

        return AsciiSerialTransport()
    if kind == "mock":
        from .transport.mock import MockTransport

        return MockTransport()
    raise ValueError(f"unknown transport '{kind}'")


class DeviceWorker(threading.Thread):
    """Owns one ODrive connection; all device access goes through `submit`."""

    def __init__(self, mode: str = "auto", serial: str | None = None, emit: Callable[[dict], None] | None = None):
        super().__init__(name="device-worker", daemon=True)
        self.mode = mode
        self.serial = serial
        self.emit = emit or (lambda ev: None)
        self.ops: queue.Queue[tuple[Op, Future]] = queue.Queue()
        self.stop_evt = threading.Event()
        self.disarm_evt = threading.Event()
        self.disarm_reason = ""
        self.reconnect_evt = threading.Event()

        # connection state (read by the asyncio side, written only here)
        self.transport: Transport | None = None
        self.info: DeviceInfo | None = None
        self.meta: meta_mod.Metadata | None = None
        self.tree: dict[str, dict] = {}
        self.alias: dict[str, str] = {}
        self.connected = False
        self.generation = 0
        self.last_error = ""
        self._mock = None

        # telemetry
        self.primary_axis = 0
        self.base_paths: list[str] = []
        self.subs: dict[str, list[str]] = {}
        self.sub_paths: list[str] = []
        self.cols: list[str] = []
        self.cols_version = 0
        self.rate_hz = 100.0
        self.achieved_hz = 0.0
        self.rows: collections.deque = collections.deque(maxlen=50000)
        self.latest: dict[str, Any] = {}
        self.sample_hooks: list[SampleHook] = []
        self.tick_hooks: list[Callable[["DeviceWorker"], None]] = []
        self._sample_times: collections.deque = collections.deque(maxlen=200)

    # ---------- api used from other threads ----------

    def submit(self, fn: Op) -> Future:
        """Queue a function that receives the live transport; returns a Future with its result."""
        fut: Future = Future()
        self.ops.put((fn, fut))
        return fut

    def request_disarm(self, reason: str) -> None:
        """Ask the worker to put both axes into IDLE before anything else."""
        self.disarm_reason = reason
        self.disarm_evt.set()
        self.ops.put((lambda t: None, Future()))

    def request_reconnect(self, mode: str | None = None, serial: str | None = None) -> None:
        """Drop the current link and connect again (optionally with another transport)."""
        if mode:
            self.mode = mode
        if serial is not None:
            self.serial = serial or None
        self.reconnect_evt.set()
        self.ops.put((lambda t: None, Future()))

    def set_subscription(self, paths: list[str], rate_hz: float | None = None, owner: str = "ui") -> None:
        """Choose extra telemetry paths for one owner (ui, a job, the recorder).

        The safety base set is always sampled; the sampled columns are the union
        of all owners' paths.
        """
        if paths:
            self.subs[owner] = list(dict.fromkeys(paths))
        else:
            self.subs.pop(owner, None)
        if rate_hz:
            self.rate_hz = max(1.0, min(1000.0, float(rate_hz)))
        self.sub_paths = list(dict.fromkeys(p for ps in self.subs.values() for p in ps))
        self._rebuild_cols()

    def path(self, alias: str) -> str | None:
        """Resolve an alias like 'fet_temp.0' to the device path."""
        return self.alias.get(alias)

    # ---------- thread body ----------

    def run(self) -> None:
        """Main loop: connect, then alternate between queued ops and telemetry samples."""
        next_sample = time.monotonic()
        backoff = 0.2
        while not self.stop_evt.is_set():
            if self.reconnect_evt.is_set():
                self.reconnect_evt.clear()
                self._lost("reconnect requested", quiet=True)
            if not self.connected:
                if self._try_connect():
                    backoff = 0.2
                    next_sample = time.monotonic()
                else:
                    self._fail_pending("device not connected")
                    self.stop_evt.wait(backoff)
                    backoff = min(backoff * 1.5, 2.0)
                continue
            try:
                if self.disarm_evt.is_set():
                    self._disarm()
                now = time.monotonic()
                timeout = max(0.0, next_sample - now)
                try:
                    fn, fut = self.ops.get(timeout=timeout)
                    self._run_op(fn, fut)
                    # keep draining ops that are already waiting, but never starve sampling
                    while time.monotonic() < next_sample:
                        fn, fut = self.ops.get_nowait()
                        self._run_op(fn, fut)
                except queue.Empty:
                    pass
                if self.disarm_evt.is_set():
                    self._disarm()
                if time.monotonic() >= next_sample:
                    self._sample()
                    next_sample += 1.0 / self.rate_hz
                    if next_sample < time.monotonic():
                        next_sample = time.monotonic()
                    for hook in self.tick_hooks:
                        hook(self)
            except TransportError as ex:
                self._lost(str(ex))
            except Exception as ex:
                # never let the owner thread die; treat unknown failures as a lost link
                log.exception("device worker error")
                self._lost(f"{type(ex).__name__}: {ex}")

    def _run_op(self, fn: Op, fut: Future) -> None:
        if fut.done():
            return
        try:
            fut.set_result(fn(self.transport))
        except TransportError as ex:
            fut.set_exception(ex)
            raise
        except Exception as ex:
            fut.set_exception(ex)

    def _fail_pending(self, msg: str) -> None:
        while True:
            try:
                _, fut = self.ops.get_nowait()
            except queue.Empty:
                return
            if not fut.done():
                fut.set_exception(TransportError(msg))

    # ---------- connection ----------

    def _candidates(self) -> list[str]:
        if self.mode == "off":
            # paused: another tool (e.g. the firmware flasher) owns the usb device
            return []
        if self.mode == "auto":
            last = self.transport.name if self.transport else None
            order = ["usb", "ascii"]
            return [last] + [k for k in order if k != last] if last in order else order
        return [self.mode]

    def _try_connect(self) -> bool:
        errors = []
        if not self._candidates():
            self.last_error = "paused (device released)"
            return False
        for kind in self._candidates():
            t = self._mock if kind == "mock" and self._mock else _make_transport(kind)
            if kind == "mock":
                self._mock = t
            try:
                info = t.connect(self.serial, timeout=2.0 if kind == "usb" else 1.0)
            except TransportError as ex:
                errors.append(f"{kind}: {ex}")
                t.close()
                continue
            self.transport = t
            self.info = info
            self.serial = self.serial or info.serial
            self.meta = meta_mod.load(meta_mod.pick_version(*info.fw))
            self.tree = t.tree()
            self.alias = aliases.resolve_all(self.tree)
            self._build_base_paths()
            self.connected = True
            self.generation += 1
            self.last_error = ""
            log.info("connected via %s: %s", kind, info.to_json())
            self.emit({"t": "event", "level": "info", "src": "device", "msg": f"connected via {kind}: fw {'.'.join(map(str, info.fw))}, serial {info.serial}"})
            return True
        msg = "; ".join(errors)
        if msg != self.last_error:
            self.last_error = msg
            self.emit({"t": "event", "level": "warn", "src": "device", "msg": f"connect failed ({msg})"})
        return False

    def _lost(self, reason: str, quiet: bool = False) -> None:
        if self.transport is not None:
            try:
                self.transport.close()
            except Exception:
                pass
        was = self.connected
        self.connected = False
        self.achieved_hz = 0.0
        self._fail_pending(f"link lost: {reason}")
        if was and not quiet:
            self.emit({"t": "event", "level": "warn", "src": "device", "msg": f"link lost: {reason}; reconnecting"})

    # ---------- telemetry ----------

    def _build_base_paths(self) -> None:
        """Always-sampled paths that the safety monitor and status bar rely on."""
        keys = ["clock", "vbus", "ibus", "sys_error", "brake_armed"]
        full = ["state", "error", "motor_error", "enc_error", "ctrl_error", "fet_temp", "iq", "iq_set", "pos", "vel", "spi_err", "motor_temp"]
        # the unused axis only needs what the safety monitor and status bar show
        light = ["state", "error", "motor_error", "enc_error", "ctrl_error", "fet_temp", "iq"]
        base = [self.alias[k] for k in keys if k in self.alias]
        for ax in (0, 1):
            per_axis = full if ax == self.primary_axis else light
            base += [self.alias[f"{k}.{ax}"] for k in per_axis if f"{k}.{ax}" in self.alias]
        self.base_paths = base
        self._rebuild_cols()

    def _rebuild_cols(self) -> None:
        valid = [p for p in self.sub_paths if self.tree.get(p, {}).get("kind") == "prop" and p not in self.base_paths]
        cols = self.base_paths + valid
        if cols != self.cols:
            self.cols = cols
            self.cols_version += 1

    def _sample(self) -> None:
        cols = self.cols
        if not cols or self.transport is None:
            return
        t_host = time.time()
        values = self.transport.read_many(cols)
        self.latest.update(zip(cols, values))
        self.rows.append((self.cols_version, t_host, values))
        now = time.monotonic()
        self._sample_times.append(now)
        if len(self._sample_times) > 1:
            span = self._sample_times[-1] - self._sample_times[0]
            self.achieved_hz = (len(self._sample_times) - 1) / span if span > 0 else 0.0
        for hook in self.sample_hooks:
            try:
                hook(self, cols, values)
            except TransportError:
                raise
            except Exception:
                log.exception("sample hook failed")

    # ---------- disarm ----------

    def _disarm(self) -> None:
        """Write IDLE to both axes; called on the worker thread with highest priority."""
        self.disarm_evt.clear()
        t = self.transport
        for ax in (0, 1):
            p = self.alias.get(f"req_state.{ax}")
            if p and t is not None:
                try:
                    t.write(p, 1)
                except TransportError:
                    raise
                except Exception as ex:
                    log.warning("disarm axis%d failed: %s", ax, ex)
        self.emit({"t": "event", "level": "alarm", "src": "safety", "msg": f"DISARM: {self.disarm_reason or 'requested'}"})

    def status(self) -> dict:
        """Snapshot of the connection for the status bar."""
        return {
            "connected": self.connected,
            "transport": self.transport.name if self.transport and self.connected else None,
            "mode": self.mode,
            "info": self.info.to_json() if self.info and self.connected else None,
            "meta_fw": self.meta.fw if self.meta else None,
            "rate_target": self.rate_hz,
            "rate_achieved": round(self.achieved_hz, 1),
            "cols": len(self.cols),
            "generation": self.generation,
            "last_error": self.last_error,
        }
