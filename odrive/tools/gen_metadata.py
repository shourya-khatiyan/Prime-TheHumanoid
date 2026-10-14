"""Generate ODrive property metadata JSON from the official odrive-interface.yaml.

The device itself tells us which properties exist, but not their units, docs,
enum names or error-flag names. This script reads the firmware's interface
definition for a given release tag and writes a flat JSON file the backend and
frontend use for labels, units, enum decoding and 64-bit error decoding.

Usage:
    python tools/gen_metadata.py 0.5.1 0.5.6
Output:
    backend/metadata/odrive-<version>.json
"""

from __future__ import annotations

import json
import re
import sys
import urllib.request
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent
CACHE = ROOT / "cache"
OUT = ROOT.parent / "backend" / "metadata"
URL = "https://raw.githubusercontent.com/odriverobotics/ODrive/fw-v{v}/Firmware/odrive-interface.yaml"

SCALARS = {"bool", "float32", "int8", "uint8", "int16", "uint16", "int32", "uint32", "int64", "uint64", "endpoint_ref"}


def upper_snake(name: str) -> str:
    """Convert CamelCase yaml names (e.g. 'DcBusOverVoltage') to UPPER_SNAKE.

    Args:
        name: flag or enum value name as written in the yaml.
    Returns:
        the UPPER_SNAKE form; names that are already upper case are returned as-is.
    """
    if name.upper() == name:
        return name
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", name)
    s = re.sub(r"([A-Z])([A-Z][a-z])", r"\1_\2", s)
    return s.upper()


def camel(name: str) -> str:
    """Turn an attribute name like 'lockin_state' into 'LockinState'."""
    return "".join(p[:1].upper() + p[1:] for p in name.split("_"))


def load_yaml(version: str) -> dict:
    """Load the interface yaml for a firmware tag, downloading it into the cache once.

    Args:
        version: firmware version such as '0.5.1'.
    Returns:
        the parsed yaml document.
    """
    CACHE.mkdir(parents=True, exist_ok=True)
    path = CACHE / f"odrive-interface-{version}.yaml"
    if not path.exists():
        with urllib.request.urlopen(URL.format(v=version), timeout=30) as r:
            path.write_bytes(r.read())
    return yaml.safe_load(path.read_text(encoding="utf-8"))


class Generator:
    """Walks the interface tree from the root object and collects flat metadata."""

    def __init__(self, doc: dict):
        self.interfaces: dict = doc.get("interfaces") or {}
        self.valuetypes: dict = dict(doc.get("valuetypes") or {})
        self.props: dict = {}
        self.funcs: dict = {}
        self.enums: dict = {}

    def resolve(self, name: str, scope: str) -> str | None:
        """Find the full type name for `name` as seen from interface `scope`.

        ODrive yaml uses relative names ('Motor', 'AxisState', 'Error'), so we try
        the innermost scope first and walk outward.
        """
        parts = scope.split(".")
        for i in range(len(parts), -1, -1):
            cand = ".".join(parts[:i] + [name]) if i else name
            if cand in self.interfaces or cand in self.valuetypes:
                return cand
        return None

    def register_valuetype(self, full: str, spec: dict) -> None:
        """Convert one enum or bitfield yaml spec into the json enum format."""
        if full in self.enums:
            return
        if "flags" in spec:
            bits, docs, nxt = {}, {}, 0
            for fname, fspec in (spec.get("flags") or {}).items():
                fspec = fspec or {}
                bit = fspec.get("bit", nxt)
                nxt = bit + 1
                key = upper_snake(fname)
                # 64-bit flags are kept as strings so json consumers never lose precision
                bits[key] = str(1 << bit)
                docs[key] = (fspec.get("brief") or fspec.get("doc") or "").strip()
            self.enums[full] = {"kind": "flags", "nullflag": upper_snake(str(spec.get("nullflag", "NONE"))), "bits": bits, "docs": docs}
        elif "values" in spec:
            values, docs, nxt = {}, {}, 0
            for vname, vspec in (spec.get("values") or {}).items():
                vspec = vspec or {}
                val = vspec.get("value", nxt)
                nxt = val + 1
                key = upper_snake(vname)
                values[key] = val
                docs[key] = (vspec.get("brief") or vspec.get("doc") or "").strip()
            self.enums[full] = {"kind": "enum", "values": values, "docs": docs}

    def members(self, iface: str) -> tuple[dict, dict]:
        """Return (attributes, functions) of an interface, merging any `implements` base."""
        spec = self.interfaces.get(iface) or {}
        attrs, funcs = {}, {}
        base = spec.get("implements")
        if base:
            full = self.resolve(base, iface) or base
            attrs, funcs = self.members(full)
            attrs, funcs = dict(attrs), dict(funcs)
        attrs.update(spec.get("attributes") or {})
        funcs.update(spec.get("functions") or {})
        return attrs, funcs

    def walk_object(self, path: str, attrs: dict, funcs: dict, scope: str, depth: int = 0) -> None:
        """Record every property and function under one object node."""
        if depth > 12:
            return
        for name, spec in attrs.items():
            self.walk_attr(f"{path}.{name}" if path else name, name, spec, scope, depth)
        for fname, fspec in (funcs or {}).items():
            fspec = fspec or {}
            fpath = f"{path}.{fname}" if path else fname
            self.funcs[fpath] = {
                "in": [self.arg(a, s) for a, s in (fspec.get("in") or {}).items()],
                "out": [self.arg(a, s) for a, s in (fspec.get("out") or {}).items()],
                "doc": (fspec.get("doc") or fspec.get("brief") or "").strip(),
            }

    def arg(self, name: str, spec) -> dict:
        """Describe a single function argument."""
        if isinstance(spec, dict):
            return {"name": name, "type": str(spec.get("type")), "doc": (spec.get("doc") or "").strip()}
        return {"name": name, "type": str(spec), "doc": ""}

    def walk_attr(self, path: str, name: str, spec, scope: str, depth: int) -> None:
        """Classify one attribute as scalar, enum, bitfield, struct or sub-object."""
        info = spec if isinstance(spec, dict) else {"type": spec}

        # inline struct (e.g. config: {attributes: ...})
        if "attributes" in info or "functions" in info:
            attrs = dict(info.get("attributes") or {})
            funcs = dict(info.get("functions") or {})
            base = info.get("implements")
            if base:
                full = self.resolve(base, scope) or base
                battrs, bfuncs = self.members(full)
                attrs = {**battrs, **attrs}
                funcs = {**bfuncs, **funcs}
            self.walk_object(path, attrs, funcs, scope, depth + 1)
            return

        # inline enum or bitfield (e.g. error: {flags: ...})
        if "flags" in info or "values" in info:
            full = f"{scope}.Error" if name == "error" else f"{scope}.{camel(name)}"
            self.register_valuetype(full, info)
            mode = (info.get("typeargs") or {}).get("fibre.Property.mode")
            self.add_prop(path, "uint64" if "flags" in info else "uint32", mode == "readonly", info, enum=full)
            return

        type_str = str(info.get("type", "")).strip()
        readonly = type_str.startswith("readonly ")
        if readonly:
            type_str = type_str[len("readonly "):].strip()
        readonly = readonly or (info.get("typeargs") or {}).get("fibre.Property.mode") == "readonly"

        if type_str in SCALARS:
            self.add_prop(path, type_str, readonly, info)
            return

        full = self.resolve(type_str, scope)
        if full is None:
            self.add_prop(path, type_str or "unknown", readonly, info)
            return
        if full in self.valuetypes:
            self.register_valuetype(full, self.valuetypes[full])
            kind = "uint64" if "flags" in self.valuetypes[full] else "uint32"
            self.add_prop(path, kind, readonly, info, enum=full)
            return
        # sub-object: recurse into the referenced interface
        attrs, funcs = self.members(full)
        self.walk_object(path, attrs, funcs, full, depth + 1)

    def add_prop(self, path: str, type_str: str, readonly: bool, info: dict, enum: str | None = None) -> None:
        """Store one flat property entry."""
        doc = info.get("doc")
        entry = {
            "type": type_str,
            "access": "r" if readonly else "rw",
            "unit": info.get("unit"),
            "brief": (info.get("brief") or "").strip(),
            "doc": doc.strip() if isinstance(doc, str) else "",
            "enum": enum,
        }
        self.props[path] = {k: v for k, v in entry.items() if v not in (None, "")}

    def run(self) -> dict:
        """Generate metadata starting from the top-level device interface."""
        root = "ODrive3" if "ODrive3" in self.interfaces else "ODrive"
        attrs, funcs = self.members(root)
        self.walk_object("", attrs, funcs, "ODrive")
        # register every remaining valuetype so enums not reached by a property still decode
        for full, spec in self.valuetypes.items():
            self.register_valuetype(full, spec)
        return {"props": self.props, "funcs": self.funcs, "enums": self.enums}


def main(versions: list[str]) -> None:
    """Generate one metadata file per requested firmware version."""
    OUT.mkdir(parents=True, exist_ok=True)
    for v in versions:
        data = {"fw": v, **Generator(load_yaml(v)).run()}
        path = OUT / f"odrive-{v}.json"
        path.write_text(json.dumps(data, indent=1, sort_keys=True), encoding="utf-8")
        print(f"{v}: {len(data['props'])} props, {len(data['funcs'])} funcs, {len(data['enums'])} enums -> {path}")


if __name__ == "__main__":
    main(sys.argv[1:] or ["0.5.1", "0.5.6"])
