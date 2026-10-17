"""ASCII protocol transport over the ODrive's usb serial port (CDC, e.g. COM7).

This works without any usb driver changes and is used as a fallback when the
native usb interface cannot be opened. Function calls are limited to what the
ascii protocol supports (save, erase, reboot, watchdog feed, clear errors).
"""

from __future__ import annotations

import math
import threading
from typing import Any

import serial
import serial.tools.list_ports

from .. import meta as meta_mod
from .base import DeviceInfo, Transport, TransportError

VID, PID = 0x1209, 0x0D32
ERROR_REPLIES = ("invalid property", "invalid command format", "not implemented", "invalid value", "unknown command")


def find_ports() -> list[dict]:
    """List serial ports that belong to an ODrive (by usb vid/pid)."""
    out = []
    for p in serial.tools.list_ports.comports():
        if p.vid == VID and p.pid == PID:
            out.append({"port": p.device, "serial": (p.serial_number or "").upper()})
    return out


def parse_reply(text: str, typ: str) -> Any:
    """Convert one ascii reply line into a python value.

    Args:
        text: the reply line (fw 0.5.1 appends 'd' to some integers, e.g. '256d').
        typ: property type from metadata ('float32', 'uint64', 'bool', ...).
    Returns:
        float, int or bool.
    Raises:
        KeyError: when the device says the property is invalid.
    """
    t = text.strip()
    if t in ERROR_REPLIES:
        raise KeyError(t)
    if typ == "float32":
        try:
            return float(t)
        except ValueError:
            return math.nan
    if t.endswith("d") and t[:-1].lstrip("-").isdigit():
        t = t[:-1]
    if typ == "bool":
        return t not in ("0", "false", "False")
    try:
        return int(t)
    except ValueError:
        return float(t)


class AsciiSerialTransport(Transport):
    """Line-based ascii protocol: 'r path', 'w path value', 'ss', 'se', 'sr', 'u axis'."""

    name = "ascii"

    def __init__(self, port: str | None = None):
        self.port = port
        self.ser: serial.Serial | None = None
        self.meta: meta_mod.Metadata | None = None
        self._lock = threading.Lock()

    def connect(self, serial_no: str | None, timeout: float) -> DeviceInfo:
        """Open the serial port of the (first or matching) ODrive and identify it."""
        port, usb_serial = self.port, ""
        if port is None:
            ports = [p for p in find_ports() if not serial_no or p["serial"] == serial_no.upper()]
            if not ports:
                raise TransportError("no odrive serial port found")
            port, usb_serial = ports[0]["port"], ports[0]["serial"]
        try:
            self.ser = serial.Serial(port, 115200, timeout=0.3, write_timeout=0.5)
            self.ser.reset_input_buffer()
        except serial.SerialException as ex:
            raise TransportError(f"cannot open {port}: {ex}") from ex
        try:
            fw = tuple(int(parse_reply(self._raw(f"r fw_version_{k}"), "uint8")) for k in ("major", "minor", "revision"))
            hw = tuple(int(parse_reply(self._raw(f"r hw_version_{k}"), "uint8")) for k in ("major", "minor", "variant"))
            self.meta = meta_mod.load(meta_mod.pick_version(*fw))
            unreleased = int(parse_reply(self._raw("r fw_version_unreleased"), "uint8"))
        except (KeyError, ValueError) as ex:
            self.close()
            raise TransportError(f"serial handshake failed on {port}: {ex}") from ex
        return DeviceInfo(serial=usb_serial or "unknown", fw=fw, hw=hw, unreleased=unreleased, extra={"port": port})

    def close(self) -> None:
        """Close the serial port."""
        if self.ser is not None:
            try:
                self.ser.close()
            finally:
                self.ser = None

    def _send(self, text: str) -> None:
        if self.ser is None:
            raise TransportError("serial port not open")
        try:
            self.ser.write(text.encode("ascii"))
        except serial.SerialException as ex:
            raise TransportError(f"serial write failed: {ex}") from ex

    def _line(self) -> str:
        if self.ser is None:
            raise TransportError("serial port not open")
        try:
            raw = self.ser.readline()
        except serial.SerialException as ex:
            raise TransportError(f"serial read failed: {ex}") from ex
        if not raw.endswith(b"\n"):
            raise TransportError("ascii reply timeout")
        return raw.decode("ascii", errors="replace").strip()

    def _raw(self, cmd: str) -> str:
        with self._lock:
            self._send(cmd + "\n")
            return self._line()

    def _type(self, path: str) -> str:
        return (self.meta.prop(path).get("type") if self.meta else None) or "float32"

    def tree(self) -> dict[str, dict]:
        """Ascii cannot list properties, so the tree comes from firmware metadata."""
        out: dict[str, dict] = {}
        for path, m in (self.meta.props if self.meta else {}).items():
            if m.get("type") == "endpoint_ref":
                continue
            out[path] = {"kind": "prop", "type": m.get("type"), "writable": m.get("access") == "rw"}
        for path in self.ASCII_CALLS:
            out[path] = {"kind": "func", "args": []}
        for ax in (0, 1):
            for fn in ("clear_errors", "watchdog_feed"):
                out[f"axis{ax}.{fn}"] = {"kind": "func", "args": []}
        return out

    def read(self, path: str) -> Any:
        """Read one property with 'r path'."""
        return parse_reply(self._raw(f"r {path}"), self._type(path))

    def read_many(self, paths: list[str]) -> list[Any]:
        """Pipeline all reads in one write, then collect one reply line per path."""
        if not paths:
            return []
        with self._lock:
            self._send("".join(f"r {p}\n" for p in paths))
            lines = [self._line() for _ in paths]
        out = []
        for p, line in zip(paths, lines):
            try:
                out.append(parse_reply(line, self._type(p)))
            except KeyError:
                out.append(None)
        return out

    def write(self, path: str, value: Any) -> None:
        """Write with 'w path value', then read back so errors are detected."""
        if isinstance(value, bool):
            text = "1" if value else "0"
        elif isinstance(value, float):
            text = "inf" if value == math.inf else "-inf" if value == -math.inf else repr(value)
        else:
            text = str(int(value))
        with self._lock:
            self._send(f"w {path} {text}\nr {path}\n")
            first = self._line()
            if first in ERROR_REPLIES:
                self._line()
                raise ValueError(f"write {path} rejected: {first}")

    ASCII_CALLS = {"save_configuration": "ss", "erase_configuration": "se", "reboot": "sr"}

    def call(self, path: str, args: list[Any]) -> Any:
        """Map supported device functions onto ascii system commands."""
        if path in self.ASCII_CALLS:
            self._send(self.ASCII_CALLS[path] + "\n")
            return None
        head, _, fn = path.partition(".")
        if head.startswith("axis") and fn == "watchdog_feed":
            self._send(f"u {head[4:]}\n")
            return None
        if head.startswith("axis") and fn == "clear_errors":
            # fw 0.5.1 has no 'sc' command; error registers are writable, so zero them
            for sub in ("", "motor.", "encoder.", "controller.", "sensorless_estimator.", "fet_thermistor.", "motor_thermistor."):
                p = f"{head}.{sub}error"
                if not self.meta or p in self.meta.props:
                    try:
                        self.write(p, 0)
                    except ValueError:
                        pass
            return None
        raise NotImplementedError(f"'{path}' is not available over the ascii protocol")
