"""CAN bus monitor and send console (python-can), with ODrive CANSimple decoding.

Needs a USB-CAN adapter. Motion-related frames require a confirmation token,
because CAN commands bypass the USB-side safety layer.
"""

from __future__ import annotations

import collections
import struct
import threading
import time
from typing import Any

import can

# ODrive 0.5.x CANSimple command ids (arbitration id = node_id << 5 | cmd)
CMDS = {
    0x001: ("heartbeat", "<IB"), 0x002: ("estop", ""), 0x003: ("get_motor_error", "<Q"), 0x004: ("get_encoder_error", "<I"),
    0x005: ("get_sensorless_error", "<I"), 0x006: ("set_node_id", "<I"), 0x007: ("set_requested_state", "<I"),
    0x008: ("set_startup_config", ""), 0x009: ("get_encoder_estimates", "<ff"), 0x00A: ("get_encoder_count", "<ii"),
    0x00B: ("set_controller_mode", "<ii"), 0x00C: ("set_input_pos", "<fhh"), 0x00D: ("set_input_vel", "<ff"),
    0x00E: ("set_input_torque", "<f"), 0x00F: ("set_limits", "<ff"), 0x010: ("start_anticogging", ""),
    0x011: ("set_traj_vel_limit", "<f"), 0x012: ("set_traj_accel_limits", "<ff"), 0x013: ("set_traj_inertia", "<f"),
    0x014: ("get_iq", "<ff"), 0x015: ("get_sensorless_estimates", "<ff"), 0x016: ("reboot", ""), 0x017: ("get_vbus_voltage", "<f"),
    0x018: ("clear_errors", ""), 0x019: ("set_linear_count", "<i"), 0x01A: ("set_pos_gain", "<f"), 0x01B: ("set_vel_gains", "<ff"),
}
MOTION_CMDS = {0x006, 0x008, 0x00B, 0x00C, 0x00D, 0x00E, 0x00F, 0x010, 0x011, 0x012, 0x013, 0x016, 0x019, 0x01A, 0x01B}

INTERFACES = ["slcan", "gs_usb", "pcan", "kvaser", "socketcan", "vector", "ixxat", "canalystii", "serial", "virtual"]


def decode(arb_id: int, data: bytes, is_remote: bool) -> dict:
    """Decode a standard-id frame as ODrive CANSimple.

    Returns:
        {node, cmd, name, fields} (fields is None for remote/unknown frames).
    """
    node, cmd = arb_id >> 5, arb_id & 0x1F
    name, fmt = CMDS.get(cmd, (f"cmd_0x{cmd:02X}", ""))
    fields = None
    if fmt and not is_remote and len(data) >= struct.calcsize(fmt):
        fields = list(struct.unpack_from(fmt, data))
    return {"node": node, "cmd": cmd, "name": name, "fields": fields}


def encode(cmd: int, values: list[Any]) -> bytes:
    """Pack field values for a CANSimple command (padded to 8 bytes when non-empty)."""
    fmt = CMDS.get(cmd, ("", ""))[1]
    if not fmt:
        return b""
    raw = struct.pack(fmt, *values)
    return raw + bytes(8 - len(raw)) if len(raw) < 8 else raw


def requires_confirm(arb_id: int, data: bytes) -> bool:
    """True if a frame could move the motor or change its configuration."""
    cmd = arb_id & 0x1F
    if cmd == 0x007 and len(data) >= 4:
        return struct.unpack_from("<I", data)[0] not in (0, 1)
    return cmd in MOTION_CMDS


class CanMonitor:
    """Owns an optional python-can bus and a receive thread."""

    def __init__(self):
        self.bus: can.BusABC | None = None
        self.cfg: dict = {}
        self.frames: collections.deque = collections.deque(maxlen=5000)
        self.pending: collections.deque = collections.deque(maxlen=2000)
        self.stats = {"rx": 0, "tx": 0, "errors": 0}
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self.last_error = ""

    @staticmethod
    def detect() -> list[dict]:
        """Ask python-can which adapters are present (may take a few seconds)."""
        out = []
        for cfg in can.detect_available_configs(interfaces=[i for i in INTERFACES if i != "virtual"]):
            out.append({k: str(v) for k, v in cfg.items()})
        return out

    def open(self, interface: str, channel: str, bitrate: int) -> dict:
        """Open the bus and start receiving."""
        self.close()
        try:
            self.bus = can.Bus(interface=interface, channel=channel, bitrate=bitrate)
        except Exception as ex:
            self.last_error = str(ex)
            raise ValueError(f"cannot open {interface}:{channel}: {ex}") from ex
        self.cfg = {"interface": interface, "channel": channel, "bitrate": bitrate}
        self.stats = {"rx": 0, "tx": 0, "errors": 0}
        self._stop.clear()
        self._thread = threading.Thread(target=self._rx, name="can-rx", daemon=True)
        self._thread.start()
        return self.status()

    def close(self) -> None:
        """Stop the receive thread and release the adapter."""
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=1)
        if self.bus is not None:
            try:
                self.bus.shutdown()
            except Exception:
                pass
        self.bus = None
        self.cfg = {}

    def _rx(self) -> None:
        while not self._stop.is_set() and self.bus is not None:
            try:
                msg = self.bus.recv(timeout=0.2)
            except Exception as ex:
                self.stats["errors"] += 1
                self.last_error = str(ex)
                time.sleep(0.2)
                continue
            if msg is None:
                continue
            self._record(msg, "rx")

    def _record(self, msg: can.Message, direction: str) -> None:
        frame = {"ts": msg.timestamp or time.time(), "dir": direction, "id": msg.arbitration_id, "ext": msg.is_extended_id,
                 "rtr": msg.is_remote_frame, "err": msg.is_error_frame, "data": bytes(msg.data).hex()}
        if not msg.is_extended_id:
            frame.update(decode(msg.arbitration_id, bytes(msg.data), msg.is_remote_frame))
        self.stats[direction] += 1
        self.frames.append(frame)
        self.pending.append(frame)

    def send(self, arb_id: int, data: bytes, is_remote: bool = False, extended: bool = False) -> None:
        """Transmit one frame (caller has already handled confirmation)."""
        if self.bus is None:
            raise ValueError("CAN bus not open")
        msg = can.Message(arbitration_id=arb_id, data=data, is_remote_frame=is_remote, is_extended_id=extended,
                          dlc=8 if is_remote else len(data))
        self.bus.send(msg, timeout=0.2)
        self._record(msg, "tx")

    def drain(self, limit: int = 400) -> list[dict]:
        """Take newly received/sent frames for broadcasting."""
        out = []
        while self.pending and len(out) < limit:
            out.append(self.pending.popleft())
        return out

    def status(self) -> dict:
        """Bus state summary."""
        return {"open": self.bus is not None, **self.cfg, **self.stats, "last_error": self.last_error}
