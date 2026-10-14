"""Firmware metadata: units, docs, enum names and error-flag decoding."""

from __future__ import annotations

import json
from functools import lru_cache
from typing import Any

from .paths import METADATA_DIR

KNOWN = ["0.5.1", "0.5.6"]


def pick_version(major: int, minor: int, revision: int) -> str:
    """Choose the closest metadata file for a firmware version.

    Args:
        major, minor, revision: firmware version reported by the device.
    Returns:
        '0.5.1' for 0.5.1 and older, otherwise '0.5.6'.
    """
    return "0.5.1" if (major, minor, revision) <= (0, 5, 1) else "0.5.6"


class Metadata:
    """Lookup helper over one generated metadata file."""

    def __init__(self, data: dict):
        self.fw: str = data["fw"]
        self.props: dict[str, dict] = data["props"]
        self.funcs: dict[str, dict] = data["funcs"]
        self.enums: dict[str, dict] = data["enums"]

    def prop(self, path: str) -> dict:
        """Return the metadata entry for a property path (empty dict if unknown)."""
        return self.props.get(path, {})

    def enum_of(self, path: str) -> dict | None:
        """Return the enum/bitfield definition attached to a property, if any."""
        name = self.prop(path).get("enum")
        return self.enums.get(name) if name else None

    def decode_flags(self, path: str, value: int) -> list[str]:
        """Split a bitfield value into flag names (works for 64-bit fields).

        Args:
            path: property path such as 'axis0.motor.error'.
            value: raw integer read from the device.
        Returns:
            list of set flag names; unknown bits are reported as 'BIT_n'.
        """
        enum = self.enum_of(path)
        if not value:
            return []
        names, known = [], 0
        for name, bit in (enum or {}).get("bits", {}).items():
            b = int(bit)
            known |= b
            if value & b:
                names.append(name)
        rest = int(value) & ~known
        i = 0
        while rest:
            if rest & 1:
                names.append(f"BIT_{i}")
            rest >>= 1
            i += 1
        return names

    def enum_name(self, path: str, value: int) -> str | None:
        """Map an enum value to its name (e.g. 8 -> 'CLOSED_LOOP_CONTROL')."""
        enum = self.enum_of(path)
        if not enum or enum.get("kind") != "enum":
            return None
        for name, v in enum["values"].items():
            if v == value:
                return name
        return None

    def parse_value(self, path: str, value: Any) -> Any:
        """Convert user input (enum names, 'true', numbers as strings) to the device type.

        Args:
            path: target property path.
            value: raw user value.
        Returns:
            a bool, int or float suitable for writing.
        Raises:
            ValueError: if an enum name is unknown or the text is not a number.
        """
        meta = self.prop(path)
        typ = meta.get("type", "float32")
        if isinstance(value, str):
            text = value.strip()
            enum = self.enum_of(path)
            if enum and enum.get("kind") == "enum":
                key = text.upper().split(".")[-1]
                for name, v in enum["values"].items():
                    if key == name or key.endswith("_" + name):
                        return v
            low = text.lower()
            if low in ("true", "false"):
                value = low == "true"
            elif low in ("inf", "+inf", "infinity"):
                value = float("inf")
            elif low in ("-inf", "-infinity"):
                value = float("-inf")
            elif low == "nan":
                value = float("nan")
            else:
                value = float(text) if any(c in text for c in ".eE") else int(text, 0)
        if typ == "bool":
            return bool(value)
        if typ.startswith(("int", "uint")) or meta.get("enum"):
            if isinstance(value, float) and not value.is_integer():
                raise ValueError(f"{path} expects an integer")
            return int(value)
        return float(value)

    def to_json(self) -> dict:
        """Return the raw metadata for the frontend."""
        return {"fw": self.fw, "props": self.props, "funcs": self.funcs, "enums": self.enums}


@lru_cache(maxsize=4)
def load(version: str) -> Metadata:
    """Load and cache metadata for a version string ('0.5.1' or '0.5.6')."""
    path = METADATA_DIR / f"odrive-{version}.json"
    return Metadata(json.loads(path.read_text(encoding="utf-8")))
