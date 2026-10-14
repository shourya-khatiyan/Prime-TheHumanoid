"""Tuning assistant: step response, gain sweep and sine (frequency) response."""

from __future__ import annotations

import asyncio
import math
import time

from .analysis import rel_time, sine_fit, step_metrics
from . import JobCtx, job

CONTROL = {"torque": 1, "velocity": 2, "position": 3}
PASSTHROUGH = 1


async def enter_closed_loop(ctx: JobCtx, axis: int, mode: str) -> float:
    """Configure control mode, hold the current position and enter CLOSED_LOOP_CONTROL.

    Returns:
        the position (turns) the axis is holding.
    """
    clear = ctx.worker.path(f"clear_errors.{axis}")
    if clear:
        await ctx.call(clear)
    await ctx.write(ctx.p(f"ctrl_mode.{axis}"), CONTROL[mode])
    await ctx.write(ctx.p(f"input_mode.{axis}"), PASSTHROUGH)
    pos = float((await ctx.get(f"pos.{axis}"))[0])
    await ctx.write(ctx.p(f"input_vel.{axis}"), 0.0)
    await ctx.write(ctx.p(f"input_torque.{axis}"), 0.0)
    if mode == "position":
        await ctx.write(ctx.p(f"input_pos.{axis}"), pos)
    await ctx.set_state(axis, 8)
    await ctx.wait_state(axis, reach=8, timeout=3)
    await ctx.sleep(0.3)
    errs = await ctx.errors(axis)
    if errs:
        raise RuntimeError(f"axis faulted entering closed loop: {errs}")
    return pos


async def one_step(ctx: JobCtx, axis: int, mode: str, base: float, amp: float, hold: float) -> dict:
    """Apply one step of `amp` around `base`, capture the response, step back."""
    meas = ctx.p(f"pos.{axis}") if mode == "position" else ctx.p(f"vel.{axis}")
    target_path = ctx.p(f"input_pos.{axis}") if mode == "position" else ctx.p(f"input_vel.{axis}")
    paths = [meas, ctx.p(f"iq.{axis}"), ctx.p(f"iq_set.{axis}")]
    ctx.capture_start(paths, rate_hz=1000)
    await ctx.sleep(0.2)
    t_step = time.time()
    await ctx.write(target_path, base + amp)
    await ctx.sleep(hold)
    await ctx.write(target_path, base)
    await ctx.sleep(hold * 0.6)
    cap = ctx.capture_stop()
    t = rel_time(cap["t"], t_step)
    seg = [(ti, yi) for ti, yi in zip(t, cap["v"][meas]) if 0 <= ti <= hold and isinstance(yi, (int, float))]
    pre = [yi for ti, yi in zip(t, cap["v"][meas]) if ti < 0 and isinstance(yi, (int, float))]
    y0 = sum(pre) / len(pre) if pre else base
    m = step_metrics([s[0] for s in seg], [s[1] for s in seg], y0, base + amp)
    iq = [abs(x) for x in cap["v"][paths[1]] if isinstance(x, (int, float))]
    m["iq_peak"] = max(iq) if iq else None
    stride = max(1, len(t) // 1500)
    trace = {"t": t[::stride], "y": cap["v"][meas][::stride], "iq": cap["v"][paths[1]][::stride], "target": [base + amp if 0 <= ti <= hold else base for ti in t[::stride]]}
    return {"metrics": m, "trace": trace, "samples": len(t)}


def _check_amp(ctx: JobCtx, mode: str, amp: float) -> None:
    pr = ctx.safety.profile
    if mode == "position" and abs(amp) > 0.5:
        raise ValueError("position step above 0.5 turn is not allowed in the tuning assistant")
    if mode == "velocity" and abs(amp) > float(pr.get("limits.vel_max_turns_s")):
        raise ValueError("velocity step exceeds the profile velocity limit")


@job("step_response", "Step response", energizes=True)
async def step_response(ctx: JobCtx, params: dict) -> dict:
    """Closed-loop step test in position or velocity mode with metrics."""
    axis = int(params.get("axis", ctx.safety.profile.axis))
    mode = params.get("mode", "position")
    amp = float(params.get("amplitude", 0.1))
    hold = float(params.get("hold_s", 1.0))
    _check_amp(ctx, mode, amp)
    base = await enter_closed_loop(ctx, axis, mode)
    if mode == "velocity":
        base = 0.0
    ctx.log(f"step {amp:+g} {'turn' if mode == 'position' else 'turn/s'} for {hold:g} s")
    res = await one_step(ctx, axis, mode, base, amp, hold)
    gains = await ctx.get(f"pos_gain.{axis}", f"vel_gain.{axis}", f"vel_int_gain.{axis}")
    res["gains"] = dict(zip(("pos_gain", "vel_gain", "vel_integrator_gain"), gains))
    await ctx.idle(axis)
    m = res["metrics"]
    ctx.log(f"rise {m['rise_s']}, overshoot {m['overshoot_pct']}, settle {m['settle_s']}, sse {m['sse']}")
    return {"axis": axis, "mode": mode, "amplitude": amp, **res}


@job("gain_sweep", "Gain sweep", energizes=True)
async def gain_sweep(ctx: JobCtx, params: dict) -> dict:
    """Repeat the step test for a list of gain values and rank them (gain is restored after)."""
    axis = int(params.get("axis", ctx.safety.profile.axis))
    mode = params.get("mode", "position")
    gain = params.get("gain", "vel_gain")
    values = [float(v) for v in params.get("values", [])]
    amp = float(params.get("amplitude", 0.1))
    hold = float(params.get("hold_s", 0.8))
    if not values or len(values) > 12:
        raise ValueError("give 1-12 gain values")
    _check_amp(ctx, mode, amp)
    alias = {"pos_gain": "pos_gain", "vel_gain": "vel_gain", "vel_integrator_gain": "vel_int_gain"}[gain]
    gpath = ctx.p(f"{alias}.{axis}")
    original = await ctx.read1(gpath)
    rows = []
    try:
        base = await enter_closed_loop(ctx, axis, mode)
        if mode == "velocity":
            base = 0.0
        for i, val in enumerate(values):
            await ctx.write(gpath, val)
            await ctx.sleep(0.3)
            if (await ctx.get(f"state.{axis}"))[0] != 8:
                ctx.log(f"{gain}={val:g}: axis dropped out of closed loop", "alarm")
                rows.append({"value": val, "metrics": None, "fault": await ctx.errors(axis)})
                break
            res = await one_step(ctx, axis, mode, base, amp, hold)
            m = res["metrics"]
            score = (m["iae"] or 1e9) * (1 + (m["overshoot_pct"] or 0) / 20)
            rows.append({"value": val, "metrics": m, "score": score, "trace": res["trace"]})
            ctx.log(f"{gain}={val:g}: overshoot {m['overshoot_pct']:.1f} %, settle {m['settle_s']}, iae {m['iae']:.4f}" if m["iae"] is not None else f"{gain}={val:g}: no data")
            ctx.progress((i + 1) / len(values))
    finally:
        await ctx.idle(axis)
        await ctx.write(gpath, original)
    ranked = sorted([r for r in rows if r.get("score") is not None], key=lambda r: r["score"])
    best = ranked[0]["value"] if ranked else None
    ctx.log(f"best {gain} = {best} (restored {original})")
    return {"axis": axis, "mode": mode, "gain": gain, "original": original, "rows": rows, "best": best}


@job("sine_response", "Sine (frequency) response", energizes=True)
async def sine_response(ctx: JobCtx, params: dict) -> dict:
    """Stream a position sine at several frequencies and fit gain/phase of the response.

    The setpoint is written from the host at ~100 Hz, so results above ~10 Hz are
    dominated by host latency; use it to compare tunings, not as a precise bode plot.
    """
    axis = int(params.get("axis", ctx.safety.profile.axis))
    amp = float(params.get("amplitude", 0.05))
    freqs = [float(f) for f in params.get("freqs", [0.5, 1, 2, 4, 8])]
    if amp > 0.25:
        raise ValueError("sine amplitude above 0.25 turn is not allowed")
    base = await enter_closed_loop(ctx, axis, "position")
    target = ctx.p(f"input_pos.{axis}")
    meas = ctx.p(f"pos.{axis}")
    rows = []
    for i, f in enumerate(freqs):
        cycles = max(3, min(10, int(f * 4)))
        dur = cycles / f
        ctx.capture_start([meas], rate_hz=1000)
        t0 = time.time()
        cmd_t, cmd_y = [], []
        while (now := time.time()) - t0 < dur:
            y = base + amp * math.sin(2 * math.pi * f * (now - t0))
            await ctx.write(target, y)
            cmd_t.append(now - t0)
            cmd_y.append(y)
            await asyncio.sleep(0.008)
            ctx.check()
        cap = ctx.capture_stop()
        await ctx.write(target, base)
        t = [x - t0 for x in cap["t"]]
        ys = [y for y in cap["v"][meas]]
        good = [(a, b) for a, b in zip(t, ys) if isinstance(b, (int, float)) and a > 1.0 / f]
        a_out, ph_out, _ = sine_fit([g[0] for g in good], [g[1] for g in good], f)
        a_in, ph_in, _ = sine_fit(cmd_t, cmd_y, f)
        gain_db = 20 * math.log10(a_out / a_in) if a_out > 0 and a_in > 0 else None
        phase = ((ph_out - ph_in + 180) % 360) - 180
        rows.append({"freq": f, "gain_db": gain_db, "phase_deg": phase, "cmd_rate_hz": len(cmd_t) / dur})
        ctx.log(f"{f:g} Hz: {gain_db:.2f} dB, {phase:.1f} deg (setpoint rate {len(cmd_t) / dur:.0f} Hz)" if gain_db is not None else f"{f:g} Hz: no fit")
        ctx.progress((i + 1) / len(freqs))
        await ctx.sleep(0.3)
    await ctx.idle(axis)
    return {"axis": axis, "amplitude": amp, "rows": rows}
