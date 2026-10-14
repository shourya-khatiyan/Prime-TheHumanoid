"""Native usb transport using the official odrive python package (fibre protocol)."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from .base import DeviceInfo, Transport, TransportError

_lib = None


def _odrive_lib():
    """Import odrive/fibre lazily after putting the bundled libusb dll on PATH."""
    global _lib
    if _lib is None:
        try:
            import libusb_package

            dll_dir = Path(libusb_package.get_library_path()).parent
            os.environ["PATH"] = str(dll_dir) + os.pathsep + os.environ.get("PATH", "")
        except Exception:
            pass
        import fibre
        import fibre.protocol
        import fibre.remote_object
        import fibre.utils

        _lib = fibre
    return _lib


def _type_name(prop) -> str:
    """Return the wire type of a fibre RemoteProperty (e.g. 'uint64', 'float32')."""
    codec = getattr(prop, "_codec", None)
    fmt = getattr(codec, "_struct_format", "")
    return {
        "<b": "int8", "<B": "uint8", "<h": "int16", "<H": "uint16", "<i": "int32",
        "<I": "uint32", "<q": "int64", "<Q": "uint64", "<?": "bool", "<f": "float32",
    }.get(fmt, "endpoint_ref")


class FibreUsbTransport(Transport):
    """Talks to the ODrive's native usb interface (interface 2, WinUSB on windows)."""

    name = "usb"

    def __init__(self):
        self.root = None
        self._term = None
        self._handles: dict[str, Any] = {}

    def connect(self, serial: str | None, timeout: float) -> DeviceInfo:
        """Find the board over usb (optionally a specific serial) and build the handle cache."""
        fibre = _odrive_lib()
        self._term = fibre.utils.Event()
        try:
            dev = fibre.find_any(path="usb", serial_number=serial, timeout=timeout, channel_termination_token=self._term)
        except Exception as ex:
            raise TransportError(f"usb discovery failed: {ex}") from ex
        if dev is None:
            raise TransportError("no odrive found on native usb")
        self.root = dev
        self._handles = {}
        self._walk(dev, "")
        try:
            return DeviceInfo(
                serial=f"{dev.serial_number:012X}",
                fw=(dev.fw_version_major, dev.fw_version_minor, dev.fw_version_revision),
                hw=(dev.hw_version_major, dev.hw_version_minor, dev.hw_version_variant),
                unreleased=dev.fw_version_unreleased,
            )
        except Exception as ex:
            raise TransportError(f"identify failed: {ex}") from ex

    def _walk(self, obj, prefix: str) -> None:
        """Cache a direct handle for every property and function so reads skip attribute lookups."""
        fibre = _lib
        attrs = object.__getattribute__(obj, "_remote_attributes")
        for name, attr in attrs.items():
            path = f"{prefix}{name}"
            if isinstance(attr, fibre.remote_object.RemoteObject):
                self._walk(attr, path + ".")
            else:
                self._handles[path] = attr

    def close(self) -> None:
        """Terminate the fibre channel threads."""
        if self._term is not None:
            self._term.set()
        self.root = None
        self._handles = {}

    def tree(self) -> dict[str, dict]:
        """Describe every cached handle."""
        fibre = _lib
        out = {}
        for path, h in self._handles.items():
            if isinstance(h, fibre.remote_object.RemoteFunction):
                out[path] = {"kind": "func", "args": [a._name for a in h._inputs]}
            else:
                out[path] = {"kind": "prop", "type": _type_name(h), "writable": bool(h._can_write)}
        return out

    def _handle(self, path: str):
        h = self._handles.get(path)
        if h is None:
            raise KeyError(f"unknown path '{path}'")
        return h

    def _guard(self, fn):
        """Run a fibre op and convert channel failures into TransportError."""
        fibre = _lib
        try:
            return fn()
        except (fibre.protocol.ChannelBrokenException, fibre.protocol.ChannelDamagedException, TimeoutError) as ex:
            raise TransportError(f"usb link lost: {type(ex).__name__}") from ex

    def read(self, path: str) -> Any:
        """Read one property via its cached handle."""
        h = self._handle(path)
        return self._guard(h.get_value)

    def write(self, path: str, value: Any) -> None:
        """Write one property via its cached handle."""
        h = self._handle(path)
        if not h._can_write:
            raise PermissionError(f"'{path}' is read-only")
        self._guard(lambda: h.set_value(value))

    def call(self, path: str, args: list[Any]) -> Any:
        """Call a device function; reboot-style calls may legitimately drop the link."""
        h = self._handle(path)
        return self._guard(lambda: h(*args))
