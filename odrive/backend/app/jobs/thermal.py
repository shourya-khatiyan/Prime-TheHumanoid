"""Thermal test: hold a constant current on a mechanically locked rotor and log temperatures."""

from __future__ import annotations

import time

from ..storage import save_report
from .analysis import thermal_fit
from .tuning import enter_closed_loop
from . import JobCtx, job


@job("thermal", "Thermal hold test", energizes=True)
async def thermal(ctx: JobCtx, params: dict) -> dict:
    """Hold `current_a` for `duration_min` with the rotor locked; abort on movement or over-temperature.

    Params:
        axis, current_a (A), duration_min, max_motion_turns (abort if the rotor moves more than this).
    """
    pr = ctx.safety.profile
    axis = int(params.get("axis", pr.axis))
    current = float(params.get("current_a", 6))
    minutes = float(params.get("duration_min", 30))
    max_motion = float(params.get("max_motion_turns", 0.25))
    if current > float(pr.get("motor.current_peak_a")):
        raise ValueError("test current above profile peak current")
    if not 0.5 <= minutes <= 120:
        raise ValueError("duration must be 0.5-120 min")
    await ctx.ask(
        f"Lock the rotor (or joint output) mechanically. The test will apply {current:g} A for {minutes:g} min. "
        "It aborts if the rotor moves more than "
        f"{max_motion:g} turn or a temperature limit is reached. Is the rotor locked?",
        ["Rotor is locked, start"],
    )
    kt = float((await ctx.get(f"kt.{axis}"))[0])
    # torque mode with velocity limiting so an unlocked rotor cannot run away
    vel_lim_path = ctx.worker.path(f"torque_mode_vel_limit.{axis}")
    if vel_lim_path:
        await ctx.write(vel_lim_path, True)
    await ctx.write(ctx.p(f"vel_limit.{axis}"), 0.5)
    await ctx.write(ctx.p(f"current_lim.{axis}"), min(float(pr.get("motor.current_peak_a")), current * 1.25))
    start_pos = await enter_closed_loop(ctx, axis, "torque")
    await ctx.write(ctx.p(f"input_torque.{axis}"), current * kt)
    ctx.log(f"holding {current:g} A ({current * kt:.3f} Nm motor torque)")
    rows = []
    t0 = time.time()
    end = t0 + minutes * 60
    fet_abort, motor_abort = float(pr.get("thermal.fet_abort_c")), float(pr.get("thermal.motor_abort_c"))
    reason = "completed"
    while time.time() < end:
        st, pos, iq, fet, mot, vbus, ibus = await ctx.get(f"state.{axis}", f"pos.{axis}", f"iq.{axis}", f"fet_temp.{axis}",
                                                        f"motor_temp.{axis}", "vbus", "ibus")
        rows.append({"t": time.time() - t0, "iq": iq, "fet_c": fet, "motor_c": mot, "vbus": vbus, "ibus": ibus})
        if st != 8:
            reason = f"axis left closed loop: {await ctx.errors(axis)}"
            break
        if abs(pos - start_pos) > max_motion:
            reason = f"rotor moved {pos - start_pos:+.3f} turn: not locked"
            break
        if fet > fet_abort - 2:
            reason = f"FET {fet:.1f} C reached abort level"
            break
        if isinstance(mot, float) and mot > motor_abort - 2 and mot > 0:
            reason = f"motor {mot:.1f} C reached abort level"
            break
        if len(rows) % 10 == 0:
            ctx.log(f"t={rows[-1]['t']:.0f}s  Iq={iq:.2f} A  FET={fet:.1f} C  motor={mot:.1f} C")
        ctx.progress((time.time() - t0) / (end - t0))
        await ctx.sleep(1.0)
    await ctx.write(ctx.p(f"input_torque.{axis}"), 0.0)
    await ctx.idle(axis)
    ctx.log(f"stopped: {reason}", "info" if reason == "completed" else "warn")
    t = [r["t"] for r in rows]
    fits = {"fet": thermal_fit(t, [r["fet_c"] for r in rows])}
    if any(isinstance(r["motor_c"], float) and r["motor_c"] > 0 for r in rows):
        fits["motor"] = thermal_fit(t, [r["motor_c"] for r in rows])
    report = {"kind": "thermal", "axis": axis, "created": time.time(), "current_a": current, "duration_s": t[-1] if t else 0,
              "stop_reason": reason, "fits": fits, "rows": rows, "verdict": "pass" if reason == "completed" else "warn"}
    md = [f"# Thermal hold {current:g} A axis{axis}", "", f"stop: {reason}", "", "| sensor | T0 | dT | tau s | T inf |", "|---|---|---|---|---|"]
    for k, f in fits.items():
        md.append(f"| {k} | {f['t0']} | {f['dT']} | {f['tau_s']} | {f['t_inf']} |")
    report["report_id"] = save_report(f"thermal_{current:g}A", report, "\n".join(md) + "\n")["id"]
    return report
