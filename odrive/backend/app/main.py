"""FastAPI server: websocket hub (msgpack rpc + telemetry), file downloads and the built frontend."""

from __future__ import annotations

import asyncio
import logging
import os
import secrets
import time
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from . import codec, meta as meta_mod
from .can_bus import CanMonitor, encode, requires_confirm
from .device import DeviceWorker
from .jobs import REGISTRY, JobManager
from .jobs import characterize, commissioning, firmware, health, thermal, tuning  # noqa: F401  (registers jobs)
from .paths import FRONTEND_DIST, REPORTS_DIR, TOKEN_FILE, ensure_dirs
from .profile import load_profile, save_profile
from .safety import ConfirmRequired, Safety
from .storage import AuditLog, Recorder, list_backups, list_reports, load_backup, load_report, save_backup
from .transport.ascii_serial import find_ports

log = logging.getLogger("server")

PORT = int(os.environ.get("ODRV_PORT", "8765"))
MODE = os.environ.get("ODRV_MODE", "auto")
ensure_dirs()
TOKEN = TOKEN_FILE.read_text(encoding="utf-8").strip() if TOKEN_FILE.exists() and TOKEN_FILE.read_text(encoding="utf-8").strip() else secrets.token_urlsafe(24)
ALLOWED_ORIGINS = {f"http://{h}:{p}" for h in ("127.0.0.1", "localhost") for p in (PORT, 5173)}
SKIP_CONFIG = (".requested_state", ".input_pos", ".input_vel", ".input_torque", "test_property", ".error")


class Hub:
    """Tracks websocket clients and fans out messages to them."""

    def __init__(self):
        self.clients: set[asyncio.Queue] = set()
        self.loop: asyncio.AbstractEventLoop | None = None

    def broadcast(self, msg: dict) -> None:
        """Send a message to every client (drops frames for clients that fall behind)."""
        data = codec.pack(msg)
        for q in list(self.clients):
            if q.qsize() < 400:
                q.put_nowait(data)

    def emit_threadsafe(self, msg: dict) -> None:
        """Broadcast from any thread."""
        if self.loop is not None:
            self.loop.call_soon_threadsafe(self.broadcast, msg)


hub = Hub()
ensure_dirs()
audit = AuditLog()
profile = load_profile()
worker = DeviceWorker(mode=MODE, emit=hub.emit_threadsafe)
worker.primary_axis = profile.axis
safety = Safety(worker, profile, audit)
recorder = Recorder()
canmon = CanMonitor()
jobs = JobManager(worker, safety, audit, hub.broadcast)
worker.sample_hooks.append(lambda w, cols, values: recorder.on_sample(cols, time.time(), values))


async def telemetry_pump() -> None:
    """Every 40 ms, ship new telemetry rows and CAN frames to all clients."""
    while True:
        await asyncio.sleep(0.04)
        rows = []
        while worker.rows:
            rows.append(worker.rows.popleft())
        if rows and hub.clients:
            # keep only rows of the newest column layout; older ones are from before a resubscribe
            ver = rows[-1][0]
            rows = [r for r in rows if r[0] == ver]
            hub.broadcast({"t": "tel", "ver": ver, "cols": worker.cols, "ts": [r[1] for r in rows], "rows": [r[2] for r in rows]})
        frames = canmon.drain()
        if frames and hub.clients:
            hub.broadcast({"t": "can", "frames": frames})


async def status_pump() -> None:
    """Four times a second, publish connection, safety and job status."""
    while True:
        await asyncio.sleep(0.25)
        if hub.clients:
            hub.broadcast({"t": "status", **status_payload()})


def status_payload() -> dict:
    """Everything the status bar needs."""
    return {
        "device": worker.status(),
        "safety": safety.status(),
        "jobs": jobs.running(),
        "recording": bool(recorder.active),
        "can": canmon.status(),
        "profile": profile.get("name"),
        "clients": len(hub.clients),
        "server_time": time.time(),
    }


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Start the device worker and background pumps; write the session token file."""
    hub.loop = asyncio.get_running_loop()
    TOKEN_FILE.write_text(TOKEN, encoding="utf-8")
    if not worker.is_alive():
        worker.start()
    tasks = [asyncio.create_task(telemetry_pump()), asyncio.create_task(status_pump())]
    yield
    for t in tasks:
        t.cancel()
    # the worker is a daemon thread and ends with the process; just make the motor safe
    safety.disarm_all("server shutdown", "server")
    await asyncio.sleep(0.2)
    canmon.close()


app = FastAPI(title="VAYN ODrive terminal", lifespan=lifespan)


def _check_token(token: str | None) -> None:
    if not token or not secrets.compare_digest(token, TOKEN):
        raise HTTPException(status_code=403, detail="bad session token")


# ---------- rpc ops ----------

def _config_paths() -> list[str]:
    """Writable configuration properties (excludes setpoints, state requests and error registers)."""
    return [p for p, n in worker.tree.items()
            if n.get("kind") == "prop" and n.get("writable") and n.get("type") != "endpoint_ref" and not p.endswith(SKIP_CONFIG)]


async def _read_paths(paths: list[str]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for i in range(0, len(paths), 120):
        chunk = paths[i:i + 120]
        vals = await asyncio.wrap_future(worker.submit(lambda t, c=chunk: t.read_many(c)))
        out.update(zip(chunk, vals))
    return out


async def op_hello(a: dict) -> dict:
    return {"status": status_payload(), "profile": profile.to_json(), "alias": worker.alias, "tree": worker.tree,
            "jobs": {k: {"title": v["title"], "energizes": v["energizes"], "confirm": v["confirm"]} for k, v in REGISTRY.items()},
            "meta_fw": worker.meta.fw if worker.meta else None}


async def op_meta(a: dict) -> dict:
    ver = a.get("fw") or (worker.meta.fw if worker.meta else "0.5.1")
    return meta_mod.load(ver).to_json()


async def op_read(a: dict) -> dict:
    return await _read_paths(list(a["paths"]))


async def op_write(a: dict) -> dict:
    return await asyncio.to_thread(safety.write, a["path"], a["value"], a.get("token"), a.get("source", "gui"))


async def op_call(a: dict) -> Any:
    return await asyncio.to_thread(safety.call, a["path"], list(a.get("args") or []), a.get("token"), a.get("source", "gui"))


async def op_setpoint(a: dict) -> dict:
    ax, kind = int(a["axis"]), a["kind"]
    path = worker.path(f"input_{kind}.{ax}")
    if not path:
        raise ValueError(f"no input_{kind} on this firmware")
    if ax not in safety.active_axes:
        raise ValueError(f"axis{ax} is not active; enter closed loop from this GUI first")
    return await asyncio.to_thread(safety.write, path, float(a["value"]), None, "gui")


async def op_subscribe(a: dict) -> dict:
    worker.set_subscription(list(a.get("paths") or []), a.get("rate"), owner="ui")
    return {"cols": worker.cols, "rate": worker.rate_hz}


async def op_arm(a: dict) -> dict:
    return safety.arm(a["action"])


async def op_disarm(a: dict) -> dict:
    jobs.abort()
    safety.disarm_all(a.get("reason", "operator"))
    return {"ok": True}


async def op_clear_errors(a: dict) -> dict:
    for ax in [int(a["axis"])] if "axis" in a else [0, 1]:
        path = worker.path(f"clear_errors.{ax}")
        if path:
            await asyncio.to_thread(safety.call, path, [], None, "gui")
    safety.clear_stale_alarms()
    return {"ok": True}


async def op_ack(a: dict) -> dict:
    safety.ack(a.get("key"))
    return {"ok": True}


async def op_shelve(a: dict) -> dict:
    safety.shelve(a["key"], float(a.get("seconds", 300)))
    return {"ok": True}


async def op_profile_get(a: dict) -> dict:
    return profile.to_json()


async def op_profile_set(a: dict) -> dict:
    global profile
    if safety.active_axes:
        raise ValueError("disarm all axes before editing the profile")
    profile = save_profile(a["data"])
    safety.profile = profile
    if worker.connected:
        ax = profile.axis
        mode_num = commissioning.encoder_mode(profile)
        cpr = int(profile.get("encoder.cpr", 4000 if mode_num == 0 else 16384))
        use_idx = bool(profile.get("encoder.use_index", False)) if mode_num == 0 else False
        cs_pin = int(profile.get("encoder.cs_gpio", 4))
        for p, v in [
            (f"axis{ax}.encoder.config.mode", mode_num),
            (f"axis{ax}.encoder.config.cpr", cpr),
            (f"axis{ax}.encoder.config.use_index", use_idx),
            (f"axis{ax}.encoder.config.abs_spi_cs_gpio_pin", cs_pin),
        ]:
            if worker.tree.get(p, {}).get("writable"):
                try:
                    await asyncio.to_thread(safety.write, p, v, None, "profile")
                except Exception:
                    pass
    audit.add("config", "gui", "profile", None, a["data"], detail="profile saved")
    return profile.to_json()


async def op_connect(a: dict) -> dict:
    worker.request_reconnect(a.get("mode"), a.get("serial"))
    return {"ok": True}


async def op_ports(a: dict) -> dict:
    return {"serial": find_ports()}


async def op_job_start(a: dict) -> dict:
    return jobs.start(a["kind"], dict(a.get("params") or {}), a.get("token"))


async def op_job_abort(a: dict) -> dict:
    jobs.abort(a.get("id"))
    return {"ok": True}


async def op_job_answer(a: dict) -> dict:
    jobs.answer(a["id"], dict(a.get("data") or {}))
    return {"ok": True}


async def op_jobs(a: dict) -> list:
    return jobs.list()


async def op_config_snapshot(a: dict) -> dict:
    return await _read_paths(_config_paths())


async def op_backup_save(a: dict) -> dict:
    values = await _read_paths(_config_paths())
    info = worker.info.to_json() if worker.info else {}
    res = save_backup(a.get("name") or "backup", info, values)
    audit.add("config", "gui", "backup", None, res["id"], detail=f"{len(values)} values")
    return res


async def op_backup_list(a: dict) -> list:
    return list_backups()


async def op_backup_load(a: dict) -> dict:
    doc = load_backup(a["id"])
    doc["values"] = {k: codec.from_jsonable(v) for k, v in doc["values"].items()}
    return doc


async def op_audit(a: dict) -> list:
    return audit.list(int(a.get("limit", 300)), a.get("kind"))


async def op_rec_start(a: dict) -> dict:
    paths = list(a.get("paths") or [])
    worker.set_subscription(paths, None, owner="recorder")
    info = worker.info.to_json() if worker.info else {}
    return recorder.start(a.get("name") or "recording", worker.cols, {"device": info, "rate_hz": worker.rate_hz})


async def op_rec_stop(a: dict) -> dict | None:
    res = await asyncio.to_thread(recorder.stop)
    worker.set_subscription([], None, owner="recorder")
    return res


async def op_rec_list(a: dict) -> list:
    return Recorder.list()


async def op_rec_load(a: dict) -> dict:
    return await asyncio.to_thread(Recorder.load, a["id"])


async def op_reports(a: dict) -> list:
    return list_reports()


async def op_report_load(a: dict) -> dict:
    return load_report(a["id"])


async def op_can_detect(a: dict) -> list:
    return await asyncio.to_thread(CanMonitor.detect)


async def op_can_open(a: dict) -> dict:
    return await asyncio.to_thread(canmon.open, a["interface"], a.get("channel", ""), int(a.get("bitrate", 1000000)))


async def op_can_close(a: dict) -> dict:
    await asyncio.to_thread(canmon.close)
    return canmon.status()


async def op_can_send(a: dict) -> dict:
    if "cmd" in a:
        arb = (int(a["node"]) << 5) | int(a["cmd"])
        data = encode(int(a["cmd"]), list(a.get("values") or [])) if not a.get("rtr") else b""
    else:
        arb = int(str(a["id"]), 0)
        data = bytes.fromhex(str(a.get("data", "")).replace(" ", ""))
    if requires_confirm(arb, data) and not safety.consume(f"can:{arb:x}", a.get("token")):
        raise ConfirmRequired(f"can:{arb:x}", f"Send CAN frame 0x{arb:03X}? It can move the motor and bypasses USB safety checks.")
    await asyncio.to_thread(canmon.send, arb, data, bool(a.get("rtr")), bool(a.get("ext")))
    audit.add("call", "gui", f"can:0x{arb:03X}", None, data.hex())
    return {"ok": True}


OPS = {name[3:]: fn for name, fn in globals().items() if name.startswith("op_")}


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket, token: str = Query("")):
    """Main channel: msgpack rpc requests in, responses + telemetry + status + events out."""
    origin = ws.headers.get("origin", "")
    if not secrets.compare_digest(token, TOKEN) or (origin and origin not in ALLOWED_ORIGINS):
        await ws.close(code=4403)
        return
    await ws.accept()
    q: asyncio.Queue = asyncio.Queue()
    hub.clients.add(q)
    safety.client_count = len(hub.clients)

    async def sender():
        while True:
            await ws.send_bytes(await q.get())

    send_task = asyncio.create_task(sender())
    try:
        while True:
            raw = await ws.receive_bytes()
            safety.heartbeat()
            try:
                msg = codec.unpack(raw)
            except Exception:
                continue
            asyncio.create_task(_handle(q, msg))
    except (WebSocketDisconnect, RuntimeError):
        pass
    finally:
        send_task.cancel()
        hub.clients.discard(q)
        safety.client_count = len(hub.clients)


async def _handle(q: asyncio.Queue, msg: dict) -> None:
    rid, op = msg.get("id"), msg.get("op")
    if op == "ping":
        q.put_nowait(codec.pack({"t": "res", "id": rid, "ok": True, "data": time.time()}))
        return
    fn = OPS.get(op or "")
    try:
        if fn is None:
            raise ValueError(f"unknown op '{op}'")
        data = await fn(msg.get("args") or {})
        out = {"t": "res", "id": rid, "ok": True, "data": data}
    except ConfirmRequired as ex:
        out = {"t": "res", "id": rid, "ok": False, "code": "confirm", "action": ex.action, "error": ex.message}
    except Exception as ex:
        out = {"t": "res", "id": rid, "ok": False, "code": type(ex).__name__, "error": str(ex)}
    q.put_nowait(codec.pack(out))


# ---------- rest: downloads and the spa ----------

@app.get("/api/health")
def api_health() -> dict:
    """Liveness probe (no token needed, reveals nothing sensitive)."""
    return {"ok": True, "connected": worker.connected}


@app.get("/api/recording/{rid}.{fmt}")
def api_recording(rid: str, fmt: str, token: str = Query("")):
    """Download a recording as csv or parquet."""
    _check_token(token)
    path = Recorder.file(rid, fmt)
    if fmt not in ("csv", "parquet") or not path.exists():
        raise HTTPException(404)
    return FileResponse(path, filename=f"{rid}.{fmt}")


@app.get("/api/report/{rid}.{fmt}")
def api_report(rid: str, fmt: str, token: str = Query("")):
    """Download a report as markdown or json."""
    _check_token(token)
    path = REPORTS_DIR / f"{rid}.{'md' if fmt == 'md' else 'json'}"
    if not path.exists() or path.parent != REPORTS_DIR:
        raise HTTPException(404)
    return FileResponse(path, filename=path.name)


@app.get("/api/backup/{bid}.json")
def api_backup(bid: str, token: str = Query("")):
    """Download a config backup."""
    _check_token(token)
    return JSONResponse(load_backup(bid))


def _index() -> HTMLResponse:
    html = (FRONTEND_DIST / "index.html").read_text(encoding="utf-8")
    return HTMLResponse(html.replace("<!--odrv-session-->", f'<meta name="odrv-token" content="{TOKEN}">'))


if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/")
    def index():
        """Serve the built frontend with the session token injected."""
        return _index()
else:
    @app.get("/")
    def index_missing():
        """Explain how to run the frontend when it is not built."""
        return HTMLResponse("<pre>frontend not built: run `npm run build` in odrive/frontend, or `npm run dev` and open http://localhost:5173</pre>")
