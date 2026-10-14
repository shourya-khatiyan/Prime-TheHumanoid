"""Persistent storage: audit log (sqlite), telemetry recordings (parquet + csv), config backups, reports."""

from __future__ import annotations

import json
import re
import sqlite3
import threading
import time
from pathlib import Path
from typing import Any

import pyarrow as pa
import pyarrow.csv as pacsv
import pyarrow.parquet as pq

from .codec import jsonable
from .paths import AUDIT_DB, BACKUPS_DIR, RECORDINGS_DIR, REPORTS_DIR


def safe_name(name: str) -> str:
    """Make a user-supplied name safe for use as a file name."""
    return re.sub(r"[^A-Za-z0-9_.-]+", "_", name).strip("_")[:80] or "untitled"


class AuditLog:
    """Append-only log of every write, call and safety event."""

    def __init__(self, path: Path = AUDIT_DB):
        path.parent.mkdir(parents=True, exist_ok=True)
        self._db = sqlite3.connect(str(path), check_same_thread=False)
        self._lock = threading.Lock()
        with self._lock:
            self._db.execute(
                "create table if not exists audit (id integer primary key, ts real, kind text, source text,"
                " path text, old text, new text, ok integer, detail text)"
            )
            self._db.commit()

    def add(self, kind: str, source: str, path: str = "", old: Any = None, new: Any = None, ok: bool = True, detail: str = "") -> None:
        """Record one entry.

        Args:
            kind: 'write', 'call', 'safety', 'job' or 'config'.
            source: who caused it ('gui', 'console', 'job:<id>', 'monitor').
            path: device path, if any.
            old, new: values before and after (stored as json).
            ok: whether the action succeeded.
            detail: free text (error message, reason).
        """
        row = (time.time(), kind, source, path, json.dumps(jsonable(old)), json.dumps(jsonable(new)), int(ok), detail)
        with self._lock:
            self._db.execute("insert into audit (ts, kind, source, path, old, new, ok, detail) values (?,?,?,?,?,?,?,?)", row)
            self._db.commit()

    def list(self, limit: int = 500, kind: str | None = None) -> list[dict]:
        """Return the newest entries first."""
        q = "select id, ts, kind, source, path, old, new, ok, detail from audit"
        args: tuple = ()
        if kind:
            q += " where kind = ?"
            args = (kind,)
        q += " order by id desc limit ?"
        with self._lock:
            rows = self._db.execute(q, args + (limit,)).fetchall()
        keys = ["id", "ts", "kind", "source", "path", "old", "new", "ok", "detail"]
        out = []
        for r in rows:
            d = dict(zip(keys, r))
            d["old"], d["new"], d["ok"] = json.loads(d["old"]), json.loads(d["new"]), bool(d["ok"])
            out.append(d)
        return out


class Recorder:
    """Collects telemetry rows in memory while a recording is active and writes them on stop."""

    def __init__(self):
        self.active: dict | None = None
        self._lock = threading.Lock()

    def start(self, name: str, cols: list[str], meta: dict) -> dict:
        """Begin recording; rows are appended by `on_sample`."""
        with self._lock:
            self.active = {"name": safe_name(name), "cols": list(cols), "t": [], "v": [], "started": time.time(), "meta": meta}
            return {"name": self.active["name"], "started": self.active["started"]}

    def on_sample(self, cols: list[str], t_host: float, values: list[Any]) -> None:
        """Append one sample (called from the device worker thread)."""
        rec = self.active
        if rec is None:
            return
        with self._lock:
            if cols != rec["cols"]:
                # column set changed mid-recording: map by name, missing -> None
                idx = {c: i for i, c in enumerate(cols)}
                values = [values[idx[c]] if c in idx else None for c in rec["cols"]]
            rec["t"].append(t_host)
            rec["v"].append(values)

    def stop(self) -> dict | None:
        """Finish the recording and write parquet + csv + a small json header."""
        with self._lock:
            rec, self.active = self.active, None
        if rec is None:
            return None
        stamp = time.strftime("%Y%m%d-%H%M%S", time.localtime(rec["started"]))
        rid = f"{stamp}_{rec['name']}"
        folder = RECORDINGS_DIR / rid
        folder.mkdir(parents=True, exist_ok=True)
        table = self._table(rec)
        pq.write_table(table, folder / "data.parquet")
        pacsv.write_csv(table, folder / "data.csv")
        header = {"id": rid, "name": rec["name"], "started": rec["started"], "samples": len(rec["t"]), "cols": rec["cols"], **rec["meta"]}
        (folder / "meta.json").write_text(json.dumps(jsonable(header), indent=1), encoding="utf-8")
        return header

    @staticmethod
    def _table(rec: dict) -> pa.Table:
        cols = {"t": pa.array(rec["t"], pa.float64())}
        for i, c in enumerate(rec["cols"]):
            raw = [row[i] for row in rec["v"]]
            if all(isinstance(x, bool) or x is None for x in raw):
                cols[c] = pa.array(raw, pa.bool_())
            elif all(isinstance(x, int) and not isinstance(x, bool) or x is None for x in raw) and any(isinstance(x, int) for x in raw):
                big = any(x is not None and x > 2**63 - 1 for x in raw)
                cols[c] = pa.array(raw, pa.uint64() if big else pa.int64())
            else:
                cols[c] = pa.array([float(x) if x is not None else None for x in raw], pa.float64())
        return pa.table(cols)

    @staticmethod
    def list() -> list[dict]:
        """List saved recordings, newest first."""
        out = []
        for meta in sorted(RECORDINGS_DIR.glob("*/meta.json"), reverse=True):
            try:
                out.append(json.loads(meta.read_text(encoding="utf-8")))
            except Exception:
                continue
        return out

    @staticmethod
    def load(rid: str, max_points: int = 200000) -> dict:
        """Load a recording as columns for replay (downsampled by stride if huge)."""
        folder = RECORDINGS_DIR / safe_name(rid)
        table = pq.read_table(folder / "data.parquet")
        stride = max(1, table.num_rows // max_points)
        data = {name: table.column(name).to_pylist()[::stride] for name in table.column_names}
        meta = json.loads((folder / "meta.json").read_text(encoding="utf-8"))
        return {"meta": meta, "cols": data}

    @staticmethod
    def file(rid: str, fmt: str) -> Path:
        """Path of the stored csv or parquet file for download."""
        return RECORDINGS_DIR / safe_name(rid) / ("data.csv" if fmt == "csv" else "data.parquet")


def save_backup(name: str, info: dict, values: dict[str, Any]) -> dict:
    """Write a config backup (all writable config values) to a json file."""
    stamp = time.strftime("%Y%m%d-%H%M%S")
    bid = f"{stamp}_{safe_name(name)}"
    doc = {"format": "vayn-odrive-config", "version": 1, "id": bid, "name": name, "created": time.time(), "device": info, "values": jsonable(values)}
    (BACKUPS_DIR / f"{bid}.json").write_text(json.dumps(doc, indent=1, sort_keys=True), encoding="utf-8")
    return {k: doc[k] for k in ("id", "name", "created", "device")} | {"count": len(values)}


def list_backups() -> list[dict]:
    """List config backups, newest first."""
    out = []
    for f in sorted(BACKUPS_DIR.glob("*.json"), reverse=True):
        try:
            doc = json.loads(f.read_text(encoding="utf-8"))
            out.append({k: doc.get(k) for k in ("id", "name", "created", "device")} | {"count": len(doc.get("values", {}))})
        except Exception:
            continue
    return out


def load_backup(bid: str) -> dict:
    """Load one backup document."""
    return json.loads((BACKUPS_DIR / f"{safe_name(bid)}.json").read_text(encoding="utf-8"))


def save_report(kind: str, report: dict, markdown: str) -> dict:
    """Store a test report as json + markdown and return its id."""
    stamp = time.strftime("%Y%m%d-%H%M%S")
    rid = f"{stamp}_{safe_name(kind)}"
    (REPORTS_DIR / f"{rid}.json").write_text(json.dumps(jsonable(report), indent=1), encoding="utf-8")
    (REPORTS_DIR / f"{rid}.md").write_text(markdown, encoding="utf-8")
    return {"id": rid, "kind": kind}


def list_reports() -> list[dict]:
    """List saved reports, newest first."""
    out = []
    for f in sorted(REPORTS_DIR.glob("*.json"), reverse=True):
        try:
            doc = json.loads(f.read_text(encoding="utf-8"))
            out.append({"id": f.stem, "kind": doc.get("kind"), "verdict": doc.get("verdict"), "created": doc.get("created")})
        except Exception:
            continue
    return out


def load_report(rid: str) -> dict:
    """Load one report json."""
    return json.loads((REPORTS_DIR / f"{safe_name(rid)}.json").read_text(encoding="utf-8"))
