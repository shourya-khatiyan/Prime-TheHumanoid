"""Wire encoding helpers.

WebSocket traffic uses msgpack, which carries NaN/Infinity floats and 64-bit
integers natively. JSON (REST and files) cannot, so `jsonable` maps them to
strings that the frontend understands.
"""

from __future__ import annotations

import math
from typing import Any

import msgpack

JS_SAFE_INT = 2**53 - 1


def _default(obj: Any) -> Any:
    """Fallback for msgpack: turn sets/tuples/paths into plain lists or strings."""
    if isinstance(obj, (set, tuple)):
        return list(obj)
    return str(obj)


def pack(obj: Any) -> bytes:
    """Serialize a python object into a msgpack frame.

    Args:
        obj: any json-like structure (dicts, lists, numbers, strings, bytes).
    Returns:
        the encoded bytes.
    """
    return msgpack.packb(obj, default=_default, use_bin_type=True)


def unpack(data: bytes) -> Any:
    """Decode a msgpack frame sent by the browser."""
    return msgpack.unpackb(data, raw=False, strict_map_key=False)


def jsonable(obj: Any) -> Any:
    """Make a structure safe for json: NaN/Inf and huge ints become strings.

    Args:
        obj: nested dict/list/scalar structure.
    Returns:
        a copy where non-finite floats are 'NaN'/'Infinity'/'-Infinity' and ints
        above 2^53 are decimal strings.
    """
    if isinstance(obj, float):
        if math.isnan(obj):
            return "NaN"
        if math.isinf(obj):
            return "Infinity" if obj > 0 else "-Infinity"
        return obj
    if isinstance(obj, bool) or obj is None or isinstance(obj, str):
        return obj
    if isinstance(obj, int):
        return str(obj) if abs(obj) > JS_SAFE_INT else obj
    if isinstance(obj, dict):
        return {str(k): jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple, set)):
        return [jsonable(v) for v in obj]
    return str(obj)


def from_jsonable(value: Any) -> Any:
    """Reverse of `jsonable` for scalar values loaded from json files."""
    if value == "NaN":
        return math.nan
    if value == "Infinity":
        return math.inf
    if value == "-Infinity":
        return -math.inf
    if isinstance(value, str) and value.lstrip("-").isdigit():
        return int(value)
    return value
