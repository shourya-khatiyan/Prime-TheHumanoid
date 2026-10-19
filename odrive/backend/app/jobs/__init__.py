"""Long-running test jobs (calibration, health check, tuning, thermal, characterization, firmware).

Jobs run as asyncio tasks on the server, so they keep going if the browser
reloads, and any failure or abort always ends with the axis disarmed.
"""

from __future__ import annotations

import asyncio
import itertools
import logging
import time
import traceback
from typing import Any, Awaitable, Callable

from ..device import DeviceWorker
from ..safety import ConfirmRequired, Safety
from ..storage import AuditLog

log = logging.getLogger("jobs")

JobFn = Callable[["JobCtx", dict], Awaitable[dict]]
REGISTRY: dict[str, dict] = {}


def job(kind: str, title: str, energizes: bool, confirm: bool | None = None):
    """Register a job function.

    Args:
        kind: id used by the frontend ('health', 'calibrate', ...).
        title: human readable name.
        energizes: True if the job can move or heat the motor (axes are idled when it ends).
        confirm: require a confirmation token to start (defaults to `energizes`).
    """
    def deco(fn: JobFn) -> JobFn:
        REGISTRY[kind] = {"fn": fn, "title": title, "energizes": energizes,
                          "confirm": energizes if confirm is None else confirm}
        return fn
    return deco


class JobAborted(Exception):
    """Raised inside a job when the user aborts it."""


class JobCtx:
    """Helpers a job uses to talk to the device safely."""

    def __init__(self, mgr: "JobManager", jid: str, kind: str):
        self.mgr = mgr
        self.id = jid
        self.kind = kind
        self.worker: DeviceWorker = mgr.worker
        self.safety: Safety = mgr.safety
        self.aborted = asyncio.Event()
        self.logs: list[dict] = []
        self.progress_val = 0.0
        self.prompt: dict | None = None
        self._answer: asyncio.Future | None = None
        self._capture: dict | None = None
        self._hook = None
        self.source = f"job:{jid}"

    # ---------- reporting ----------

    def log(self, msg: str, level: str = "info") -> None:
        """Append a log line visible in the job panel."""
        self.logs.append({"ts": time.time(), "level": level, "msg": msg})
        self.mgr.publish(self)

    def progress(self, frac: float) -> None:
        """Report completion between 0 and 1."""
        self.progress_val = max(0.0, min(1.0, frac))
        self.mgr.publish(self)

    def check(self) -> None:
        """Raise JobAborted if the user pressed abort."""
        if self.aborted.is_set():
            raise JobAborted()

    async def sleep(self, seconds: float) -> None:
        """Sleep but wake up immediately on abort."""
        try:
            await asyncio.wait_for(self.aborted.wait(), timeout=seconds)
        except asyncio.TimeoutError:
            return
        raise JobAborted()

    async def ask(self, text: str, options: list[str], inputs: list[dict] | None = None) -> dict:
        """Show a prompt in the GUI and wait for the user's answer.

        Args:
            text: instruction for the user.
            options: button labels; the chosen one is returned as 'choice'.
            inputs: optional numeric fields [{key, label, unit}] returned as 'values'.
        """
        loop = asyncio.get_running_loop()
        self._answer = loop.create_future()
        self.prompt = {"text": text, "options": options, "inputs": inputs or []}
        self.mgr.publish(self)
        abort_wait = asyncio.ensure_future(self.aborted.wait())
        done, _ = await asyncio.wait({self._answer, abort_wait}, return_when=asyncio.FIRST_COMPLETED)
        abort_wait.cancel()
        self.prompt = None
        self.mgr.publish(self)
        if self._answer not in done:
            raise JobAborted()
        return self._answer.result()

    def answer(self, data: dict) -> None:
        """Deliver the user's answer to a pending prompt."""
        if self._answer and not self._answer.done():
            self._answer.set_result(data)

    # ---------- device access ----------

    def p(self, alias: str) -> str:
        """Resolve an alias to a device path (raises if the firmware lacks it)."""
        path = self.worker.path(alias)
        if not path:
            raise ValueError(f"this firmware has no '{alias}'")
        return path

    async def read(self, *paths: str) -> list[Any]:
        """Read raw paths in one worker op."""
        self.check()
        fut = self.worker.submit(lambda t: t.read_many(list(paths)))
        return await asyncio.wrap_future(fut)

    async def read1(self, path: str) -> Any:
        """Read one raw path."""
        return (await self.read(path))[0]

    async def get(self, *aliases: str) -> list[Any]:
        """Read values by alias."""
        return await self.read(*[self.p(a) for a in aliases])

    def _confirmed(self, fn: Callable[[str | None], Any]) -> Any:
        """Run a safety op; the user confirmed the job itself, so inner confirmations are auto-issued."""
        try:
            return fn(None)
        except ConfirmRequired as ex:
            return fn(self.safety.arm(ex.action)["token"])

    async def write(self, path: str, value: Any) -> Any:
        """Write through the safety layer (limits and clamps still apply)."""
        self.check()
        return await asyncio.to_thread(self._confirmed, lambda tok: self.safety.write(path, value, tok, self.source))

    async def call(self, path: str, *args: Any) -> Any:
        """Call a device function through the safety layer."""
        self.check()
        return await asyncio.to_thread(self._confirmed, lambda tok: self.safety.call(path, list(args), tok, self.source))

    async def set_state(self, ax: int, state: int) -> None:
        """Request an axis state."""
        await self.write(self.p(f"req_state.{ax}"), state)

    async def idle(self, ax: int) -> None:
        """Put an axis into IDLE; never raises."""
        try:
            await asyncio.to_thread(self.safety.write, self.p(f"req_state.{ax}"), 1, None, self.source)
        except Exception as ex:
            log.warning("idle failed: %s", ex)

    async def restore(self, path: str, value: Any) -> None:
        """Write a saved setting back, even after an abort; never raises."""
        try:
            await asyncio.to_thread(self._confirmed, lambda tok: self.safety.write(path, value, tok, self.source))
        except Exception as ex:
            log.warning("restore %s failed: %s", path, ex)

    async def wait_state(self, ax: int, leave: int | None = None, reach: int | None = 1, timeout: float = 60.0) -> int:
        """Wait until the axis leaves `leave` (if given) and then reaches `reach`.

        Returns:
            the final state.
        Raises:
            TimeoutError if the state is not reached in time.
        """
        t0 = time.monotonic()
        st = None
        left = leave is None
        while time.monotonic() - t0 < timeout:
            st, err = await self.get(f"state.{ax}", f"error.{ax}")
            if not left and st != leave:
                left = True
            if left and (reach is None or st == reach):
                return st
            # if the axis already faulted and returned to IDLE before we polled, stop waiting
            if not left and st == 1 and (err or time.monotonic() - t0 > 2.5):
                return st
            await self.sleep(0.1)
        raise TimeoutError(f"axis{ax} stayed in state {st} for {timeout:.0f}s")

    async def errors(self, ax: int) -> dict[str, list[str]]:
        """Read and decode all error registers of an axis; empty dict means no errors."""
        out = {}
        meta = self.worker.meta
        for alias in ("error", "motor_error", "enc_error", "ctrl_error"):
            path = self.worker.path(f"{alias}.{ax}")
            if not path:
                continue
            val = await self.read1(path)
            if val:
                out[path] = meta.decode_flags(path, int(val)) if meta else [hex(val)]
        return out

    # ---------- capture ----------

    def capture_start(self, paths: list[str], rate_hz: float | None = None) -> None:
        """Start collecting samples for `paths`; `rate_hz` raises the sample rate until capture_stop."""
        self._prev_rate = self.worker.rate_hz
        self.worker.set_subscription(paths, rate_hz, owner=self.source)
        self._capture = {"paths": paths, "t": [], "v": {p: [] for p in paths}}

        def hook(w, cols, values):
            cap = self._capture
            if cap is None:
                return
            idx = {c: i for i, c in enumerate(cols)}
            if not all(p in idx for p in cap["paths"]):
                return
            cap["t"].append(time.time())
            for p in cap["paths"]:
                cap["v"][p].append(values[idx[p]])

        self._hook = hook
        self.worker.sample_hooks.append(hook)

    def capture_stop(self) -> dict:
        """Stop collecting and return {'t': [...], 'v': {path: [...]}}."""
        cap, self._capture = self._capture, None
        if self._hook in self.worker.sample_hooks:
            self.worker.sample_hooks.remove(self._hook)
        self.worker.set_subscription([], getattr(self, "_prev_rate", None), owner=self.source)
        return cap or {"t": [], "v": {}}

    def to_json(self) -> dict:
        """Public state for the frontend."""
        return {"id": self.id, "kind": self.kind, "progress": self.progress_val, "logs": self.logs[-200:], "prompt": self.prompt}


class JobManager:
    """Starts, tracks and aborts jobs; publishes their state to the hub."""

    def __init__(self, worker: DeviceWorker, safety: Safety, audit: AuditLog, publish: Callable[[dict], None]):
        self.worker = worker
        self.safety = safety
        self.audit = audit
        self._publish = publish
        self.jobs: dict[str, dict] = {}
        self._ids = itertools.count(1)
        self._ctx: dict[str, JobCtx] = {}

    def publish(self, ctx: JobCtx) -> None:
        """Push job state to all clients."""
        rec = self.jobs.get(ctx.id)
        if rec:
            self._publish({"t": "job", **rec, **ctx.to_json()})

    def running(self) -> list[str]:
        """Ids of jobs that are still running."""
        return [j for j, r in self.jobs.items() if r["state"] == "running"]

    def start(self, kind: str, params: dict, token: str | None) -> dict:
        """Start a job; energizing jobs need a confirmation token for 'job:<kind>'."""
        spec = REGISTRY.get(kind)
        if spec is None:
            raise ValueError(f"unknown job '{kind}'")
        if self.running():
            raise ValueError("another job is already running")
        if spec["confirm"] and not self.safety.consume(f"job:{kind}", token):
            what = "It will energize the motor." if spec["energizes"] else "It changes the device configuration."
            raise ConfirmRequired(f"job:{kind}", f"Start '{spec['title']}'? {what}")
        jid = f"{kind}-{next(self._ids)}"
        ctx = JobCtx(self, jid, kind)
        self._ctx[jid] = ctx
        self.jobs[jid] = {"id": jid, "kind": kind, "title": spec["title"], "state": "running", "params": params,
                          "started": time.time(), "result": None, "error": None}
        self.audit.add("job", "gui", kind, None, params, detail=f"start {jid}")
        asyncio.get_running_loop().create_task(self._run(ctx, spec["fn"], params))
        self.publish(ctx)
        return self.jobs[jid]

    async def _run(self, ctx: JobCtx, fn: JobFn, params: dict) -> None:
        rec = self.jobs[ctx.id]
        try:
            rec["result"] = await fn(ctx, params)
            rec["state"] = "done"
            ctx.progress_val = 1.0
        except JobAborted:
            rec["state"] = "aborted"
            ctx.logs.append({"ts": time.time(), "level": "warn", "msg": "aborted by user"})
        except Exception as ex:
            rec["state"] = "failed"
            rec["error"] = str(ex)
            ctx.logs.append({"ts": time.time(), "level": "alarm", "msg": f"failed: {ex}"})
            log.debug(traceback.format_exc())
        finally:
            if ctx._capture is not None:
                ctx.capture_stop()
            if REGISTRY[ctx.kind]["energizes"]:
                for ax in (0, 1):
                    await ctx.idle(ax)
            rec["ended"] = time.time()
            self.audit.add("job", ctx.source, ctx.kind, None, rec["state"], ok=rec["state"] == "done", detail=rec.get("error") or "")
            self.publish(ctx)

    def abort(self, jid: str | None = None) -> None:
        """Abort one job (or every running job)."""
        for j in [jid] if jid else self.running():
            ctx = self._ctx.get(j)
            if ctx:
                ctx.aborted.set()

    def answer(self, jid: str, data: dict) -> None:
        """Forward a prompt answer to a job."""
        ctx = self._ctx.get(jid)
        if ctx:
            ctx.answer(data)

    def list(self) -> list[dict]:
        """All jobs with their logs, newest first."""
        out = []
        for jid in reversed(list(self.jobs)):
            ctx = self._ctx.get(jid)
            out.append({**self.jobs[jid], **(ctx.to_json() if ctx else {})})
        return out
