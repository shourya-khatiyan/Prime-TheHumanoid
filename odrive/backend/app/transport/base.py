"""Common transport interface so the device worker does not care how it talks to the ODrive."""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any


class TransportError(Exception):
    """Raised when the link to the device is lost or a request fails at the protocol level."""


@dataclass
class DeviceInfo:
    """Identity of the connected board."""

    serial: str
    fw: tuple[int, int, int]
    hw: tuple[int, int, int]
    unreleased: int = 0
    extra: dict = field(default_factory=dict)

    def to_json(self) -> dict:
        """Return a plain dict for the frontend."""
        return {
            "serial": self.serial,
            "fw": ".".join(map(str, self.fw)),
            "hw": f"{self.hw[0]}.{self.hw[1]}-{self.hw[2]}V",
            "fw_unreleased": self.unreleased,
            **self.extra,
        }


class Transport(ABC):
    """One way of talking to the device (native usb, ascii serial, or a mock).

    All methods are blocking and must only be called from the device worker thread.
    """

    name = "base"

    @abstractmethod
    def connect(self, serial: str | None, timeout: float) -> DeviceInfo:
        """Open the link and return the board identity. Raises TransportError on failure."""

    @abstractmethod
    def close(self) -> None:
        """Release the link."""

    @abstractmethod
    def tree(self) -> dict[str, dict]:
        """Return {path: {kind: 'prop'|'func', type, writable}} for everything the device exposes."""

    @abstractmethod
    def read(self, path: str) -> Any:
        """Read one property."""

    def read_many(self, paths: list[str]) -> list[Any]:
        """Read several properties; transports may pipeline this. Failed reads return None."""
        out = []
        for p in paths:
            try:
                out.append(self.read(p))
            except TransportError:
                raise
            except Exception:
                out.append(None)
        return out

    @abstractmethod
    def write(self, path: str, value: Any) -> None:
        """Write one property."""

    @abstractmethod
    def call(self, path: str, args: list[Any]) -> Any:
        """Invoke a device function."""
