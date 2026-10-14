"""Actuator characterization: friction/breakaway, effective Kt and efficiency, lost motion (backlash)."""

from __future__ import annotations

import statistics

from ..storage import save_report
from .analysis import linear_fit
from .tuning import enter_closed_loop
from . import JobCtx, job


@job("friction", "Friction / breakaway torque", energizes=True)
async def friction(ctx: JobCtx, params: dict) -> dict:
    """Ramp torque in each direction until the shaft starts moving; then measure running friction."""
    pr = ctx.safety.profile
    axis = int(params.get("axis", pr.axis))
    ramp = float(params.get("ramp_nm_s", 0.02))
    move_vel = float(params.get("move_vel", 0.2))
    tmax = float(params.get("max_torque_nm", min(0.5, pr.torque_max_nm)))
    vel_lim_path = ctx.worker.path(f"torque_mode_vel_limit.{axis}")
    if vel_lim_path:
        await ctx.write(vel_lim_path, True)
    await ctx.write(ctx.p(f"vel_limit.{axis}"), 1.0)
    result = {"axis": axis, "breakaway": {}, "running": []}
    torque_path = ctx.p(f"input_torque.{axis}")
    for sign, name in ((1, "positive"), (-1, "negative")):
        await enter_closed_loop(ctx, axis, "torque")
        tq = 0.0
        found = None
        while abs(tq) < tmax:
            tq += sign * ramp * 0.05
            await ctx.write(torque_path, tq)
            await ctx.sleep(0.05)
            vel = (await ctx.get(f"vel.{axis}"))[0]
            if abs(vel) > move_vel:
                found = tq
                break
        await ctx.write(torque_path, 0.0)
        await ctx.idle(axis)
        result["breakaway"][name] = found
        ctx.log(f"breakaway {name}: {found:.4f} Nm" if found is not None else f"breakaway {name}: no motion below {tmax} Nm")
        ctx.progress(0.25 if sign > 0 else 0.5)
        await ctx.sleep(0.5)
    # running friction at constant speed in velocity mode
    for i, v in enumerate(params.get("speeds", [0.5, 1.0, 2.0])):
        v = min(float(v), float(pr.get("limits.vel_max_turns_s")))
        await enter_closed_loop(ctx, axis, "velocity")
        await ctx.write(ctx.p(f"input_vel.{axis}"), v)
        await ctx.sleep(1.5)
        samples = []
        for _ in range(20):
            samples.append((await ctx.get(f"iq.{axis}"))[0])
            await ctx.sleep(0.05)
        await ctx.write(ctx.p(f"input_vel.{axis}"), 0.0)
        await ctx.idle(axis)
        kt = float((await ctx.get(f"kt.{axis}"))[0])
        iq = statistics.fmean(samples)
        result["running"].append({"vel": v, "iq": iq, "torque_nm": iq * kt})
        ctx.log(f"running at {v:g} turn/s: {iq:.3f} A = {iq * kt:.4f} Nm")
        ctx.progress(0.5 + 0.5 * (i + 1) / 3)
        await ctx.sleep(0.5)
    fit = linear_fit([r["vel"] for r in result["running"]], [r["torque_nm"] for r in result["running"]])
    result["viscous_nm_per_turn_s"] = fit["k"]
    result["coulomb_nm"] = fit["b"]
    result["report_id"] = save_report("friction", {"kind": "friction", **result, "verdict": "pass"},
                                      f"# Friction axis{axis}\n\nbreakaway: {result['breakaway']}\n\ncoulomb {fit['b']} Nm, viscous {fit['k']} Nm/(turn/s)\n")["id"]
    return result


@job("kt_efficiency", "Effective Kt and efficiency", energizes=True)
async def kt_efficiency(ctx: JobCtx, params: dict) -> dict:
    """Hold several currents against a torque arm on a scale; the user enters the force readings.

    Params:
        axis, currents (list of A), arm_length_m (distance from joint axis to the scale contact).
    """
    pr = ctx.safety.profile
    axis = int(params.get("axis", pr.axis))
    currents = [float(c) for c in params.get("currents", [1, 2, 3, 4])]
    arm = float(params.get("arm_length_m", 0.2))
    if max(currents) > float(pr.get("motor.current_continuous_a")):
        raise ValueError("test currents must stay below the continuous current")
    await ctx.ask(f"Attach a torque arm of {arm:g} m to the joint output resting on a scale (or load cell). Ready?", ["Ready"])
    kt = float((await ctx.get(f"kt.{axis}"))[0])
    vel_lim_path = ctx.worker.path(f"torque_mode_vel_limit.{axis}")
    if vel_lim_path:
        await ctx.write(vel_lim_path, True)
    await ctx.write(ctx.p(f"vel_limit.{axis}"), 0.5)
    points = []
    for i, cur in enumerate(currents):
        await enter_closed_loop(ctx, axis, "torque")
        await ctx.write(ctx.p(f"input_torque.{axis}"), cur * kt)
        await ctx.sleep(1.0)
        iq = (await ctx.get(f"iq.{axis}"))[0]
        ans = await ctx.ask(f"Holding {cur:g} A (measured {iq:.2f} A). Enter the scale reading.", ["Record"],
                            [{"key": "force_n", "label": "force", "unit": "N (kg x 9.81)"}])
        await ctx.write(ctx.p(f"input_torque.{axis}"), 0.0)
        await ctx.idle(axis)
        force = float((ans.get("values") or {}).get("force_n", 0))
        t_out = force * arm
        points.append({"current_cmd": cur, "iq": iq, "force_n": force, "torque_out_nm": t_out})
        ctx.log(f"{cur:g} A -> {t_out:.2f} Nm at the output")
        ctx.progress((i + 1) / len(currents))
        await ctx.sleep(1.0)
    fit = linear_fit([p["iq"] for p in points], [p["torque_out_nm"] for p in points])
    ideal = kt * pr.gear_ratio
    eff = fit["k"] / ideal if fit["k"] else None
    result = {"axis": axis, "points": points, "kt_out_nm_per_a": fit["k"], "offset_nm": fit["b"], "r2": fit["r2"],
              "kt_ideal_out": ideal, "efficiency": eff}
    ctx.log(f"output Kt {fit['k']:.3f} Nm/A vs ideal {ideal:.3f} -> efficiency {eff * 100:.1f} %" if eff else "fit failed")
    result["report_id"] = save_report("kt_efficiency", {"kind": "kt_efficiency", **result, "verdict": "pass"},
                                      f"# Kt / efficiency axis{axis}\n\nKt_out {fit['k']} Nm/A, ideal {ideal}, efficiency {eff}\n")["id"]
    return result


@job("backlash", "Lost motion (backlash + compliance)", energizes=True)
async def backlash(ctx: JobCtx, params: dict) -> dict:
    """With the joint output locked, alternate +/- torque and measure motor-side motion.

    Without an output encoder this measures backlash plus elastic compliance of the
    gearbox together, expressed at the joint.
    """
    pr = ctx.safety.profile
    axis = int(params.get("axis", pr.axis))
    torque = float(params.get("torque_nm", 0.1))
    cycles = int(params.get("cycles", 3))
    if torque > pr.torque_max_nm * 0.5:
        raise ValueError("torque too high for a lost-motion test")
    await ctx.ask("Lock the joint OUTPUT (not the motor) mechanically. Ready?", ["Output is locked"])
    vel_lim_path = ctx.worker.path(f"torque_mode_vel_limit.{axis}")
    if vel_lim_path:
        await ctx.write(vel_lim_path, True)
    await ctx.write(ctx.p(f"vel_limit.{axis}"), 0.5)
    await enter_closed_loop(ctx, axis, "torque")
    tp = ctx.p(f"input_torque.{axis}")
    spans = []
    for i in range(cycles):
        await ctx.write(tp, torque)
        await ctx.sleep(0.8)
        p_plus = (await ctx.get(f"pos.{axis}"))[0]
        await ctx.write(tp, -torque)
        await ctx.sleep(0.8)
        p_minus = (await ctx.get(f"pos.{axis}"))[0]
        spans.append(p_plus - p_minus)
        ctx.log(f"cycle {i + 1}: {abs(p_plus - p_minus) * 360:.2f} deg at the motor")
        ctx.progress((i + 1) / cycles)
    await ctx.write(tp, 0.0)
    await ctx.idle(axis)
    motor_turns = statistics.fmean(abs(s) for s in spans)
    joint_deg = motor_turns * 360.0 / pr.gear_ratio
    result = {"axis": axis, "torque_nm": torque, "spans_turns": spans, "motor_turns": motor_turns, "joint_deg": joint_deg,
              "joint_arcmin": joint_deg * 60}
    ctx.log(f"lost motion {joint_deg:.3f} deg ({joint_deg * 60:.1f} arcmin) at the joint")
    result["report_id"] = save_report("backlash", {"kind": "backlash", **result, "verdict": "pass"},
                                      f"# Lost motion axis{axis}\n\n{joint_deg:.3f} deg at the joint ({motor_turns:.4f} motor turns) at +-{torque} Nm\n")["id"]
    return result
