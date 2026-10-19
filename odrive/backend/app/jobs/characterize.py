"""Actuator characterization: friction/breakaway, effective Kt and efficiency, lost motion (backlash)."""

from __future__ import annotations

import statistics
import time

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


TORQUE_RAMP, TRAP_TRAJ = 6, 5


async def _wait_contact(ctx: JobCtx, axis: int, start: float, sign: int, vel_motor: float, ratio: float,
                        max_travel_deg: float, min_s: float, timeout_s: float) -> float:
    """Wait until the joint stalls against the load (push-mode contact detection).

    Returns the joint travel in degrees at contact. Raises if the joint travels past
    `max_travel_deg` (no load in the way) or nothing settles within `timeout_s`.
    """
    t0 = time.monotonic()
    still_since = None
    while (elapsed := time.monotonic() - t0) < timeout_s:
        pos, vel, state = await ctx.get(f"pos.{axis}", f"vel.{axis}", f"state.{axis}")
        if state != 8:
            raise RuntimeError(f"axis left closed loop during the push: {await ctx.errors(axis)}")
        travel = sign * (pos - start) * 360.0 / ratio
        if travel > max_travel_deg:
            raise RuntimeError(f"no contact within {max_travel_deg:g} deg of joint travel; move the load closer or raise max travel")
        # contact = stalled (speed below 15 % of the approach speed) for 0.3 s after the force ramp is done
        if elapsed > min_s and abs(vel) < 0.15 * vel_motor:
            still_since = still_since or time.monotonic()
            if time.monotonic() - still_since > 0.3:
                return travel
        else:
            still_since = None
        await ctx.sleep(0.05)
    raise RuntimeError("the joint did not settle against the load in time")


@job("push_test", "Push against a load (torque test)", energizes=True)
async def push_test(ctx: JobCtx, params: dict) -> dict:
    """Push mode: approach a load slowly, push with each current in turn, record the scale reading.

    Works like the push mode of industrial servo actuators: the motor runs in torque control
    with a speed cap, so it travels at the approach speed until it meets the load, then the
    full torque presses on it.

    Params:
        axis; direction (+1 / -1); approach_deg_s (joint speed before contact);
        currents (A, pushed one after the other); ramp_s (time to build up each push);
        max_travel_deg (joint travel allowed before contact, otherwise abort);
        arm_length_m (joint axis to the scale contact, 0 = only report torque);
        settle_s (wait after contact before measuring); return_to_start (bool).
    Returns:
        points with commanded/measured current, estimated and scale-measured joint torque,
        plus a fit of output torque vs current (Kt at the output, gearbox efficiency).
    """
    pr = ctx.safety.profile
    axis = int(params.get("axis", pr.axis))
    sign = 1 if float(params.get("direction", 1)) >= 0 else -1
    ratio = float(pr.gear_ratio)
    eff = float(pr.get("gear.efficiency", 0.87))
    approach = max(0.5, min(60.0, float(params.get("approach_deg_s", 10.0))))
    vel_motor = approach * ratio / 360.0
    currents = [float(c) for c in params.get("currents", [2.0])]
    max_cur = float(pr.get("motor.current_continuous_a"))
    if not currents or len(currents) > 12 or any(c <= 0 or c > max_cur for c in currents):
        raise ValueError(f"give 1-12 push currents between 0 and {max_cur:g} A (continuous limit)")
    ramp = max(0.1, min(10.0, float(params.get("ramp_s", 1.0))))
    max_travel = max(1.0, min(360.0, float(params.get("max_travel_deg", 30.0))))
    arm = max(0.0, float(params.get("arm_length_m", 0.0)))
    settle = max(0.2, min(10.0, float(params.get("settle_s", 1.0))))
    ret = bool(params.get("return_to_start", True))

    kt = float((await ctx.get(f"kt.{axis}"))[0])
    tq_path, mode_path = ctx.p(f"input_torque.{axis}"), ctx.p(f"input_mode.{axis}")
    ramp_path = f"axis{axis}.controller.config.torque_ramp_rate"
    traj = {k: f"axis{axis}.trap_traj.config.{k}" for k in ("vel_limit", "accel_limit", "decel_limit")}
    vel_lim_path = ctx.worker.path(f"torque_mode_vel_limit.{axis}")
    saved = dict(zip([ctx.p(f"vel_limit.{axis}"), ramp_path, *traj.values()],
                     await ctx.read(ctx.p(f"vel_limit.{axis}"), ramp_path, *traj.values())))
    if ret:
        # the return move is a position command, so refuse early if the axis is outside its window
        ctx.safety.clamp_setpoint(ctx.p(f"input_pos.{axis}"), float((await ctx.get(f"pos.{axis}"))[0]))
    if vel_lim_path:
        await ctx.write(vel_lim_path, True)
    await ctx.write(ctx.p(f"vel_limit.{axis}"), vel_motor)
    start = await enter_closed_loop(ctx, axis, "torque")
    ctx.log(f"approach {'+' if sign > 0 else '-'} at {approach:g} deg/s (joint), max travel {max_travel:g} deg")
    points = []
    try:
        await ctx.write(mode_path, TORQUE_RAMP)
        for i, cur in enumerate(currents):
            await ctx.write(ramp_path, cur * kt / ramp)
            await ctx.write(tq_path, sign * cur * kt)
            travel = await _wait_contact(ctx, axis, start, sign, vel_motor, ratio, max_travel, ramp + 0.2,
                                         ramp + max_travel / approach + 5.0)
            await ctx.sleep(settle)
            iq = statistics.fmean([abs((await ctx.get(f"iq.{axis}"))[0]) for _ in range(10)])
            joint_est = iq * kt * ratio * eff
            expect_kg = joint_est / (arm * 9.81) if arm > 0 else None
            ctx.log(f"contact after {travel:.1f} deg; pushing {cur:g} A (measured {iq:.2f} A) = {joint_est:.2f} Nm at the joint (est.)")
            ans = await ctx.ask(
                f"Pushing with {cur:g} A (measured {iq:.2f} A), about {joint_est:.2f} Nm at the joint"
                + (f", the scale should read about {expect_kg:.2f} kg" if expect_kg is not None else "")
                + ". Enter the scale reading (0 to skip).",
                ["Record"], [{"key": "kg", "label": "scale", "unit": "kg"}])
            kg = float((ans.get("values") or {}).get("kg", 0) or 0)
            measured = kg * 9.81 * arm if kg > 0 and arm > 0 else None
            points.append({"current_cmd": cur, "iq": iq, "travel_deg": travel, "joint_torque_est_nm": joint_est,
                           "expected_kg": expect_kg, "scale_kg": kg or None, "joint_torque_meas_nm": measured,
                           "efficiency": measured / (iq * kt * ratio) if measured else None})
            ctx.log(f"{cur:g} A: scale {kg:g} kg -> {measured:.2f} Nm measured" if measured else f"{cur:g} A: no scale reading")
            ctx.progress((i + 1) / len(currents))
    finally:
        try:
            # release the load, then optionally drive back to the start angle along a gentle trajectory
            await ctx.write(mode_path, 1)
            await ctx.write(tq_path, 0.0)
            if ret and (await ctx.get(f"state.{axis}"))[0] == 8:
                for k in ("vel_limit", "accel_limit", "decel_limit"):
                    await ctx.write(traj[k], vel_motor if k == "vel_limit" else 2 * vel_motor)
                await ctx.write(ctx.p(f"ctrl_mode.{axis}"), 3)
                await ctx.write(mode_path, TRAP_TRAJ)
                await ctx.write(ctx.p(f"input_pos.{axis}"), start)
                t0 = time.monotonic()
                while time.monotonic() - t0 < max_travel / approach + 5.0:
                    if abs((await ctx.get(f"pos.{axis}"))[0] - start) < 0.01:
                        break
                    await ctx.sleep(0.1)
        finally:
            # runs after an abort too, so the approach speed cap never stays behind
            await ctx.idle(axis)
            await ctx.restore(mode_path, 1)
            for path, val in saved.items():
                await ctx.restore(path, val)
    done = [p for p in points if p["joint_torque_meas_nm"]]
    fit = linear_fit([p["iq"] for p in done], [p["joint_torque_meas_nm"] for p in done]) if len(done) >= 2 else {"k": None, "b": None, "r2": None}
    result = {"axis": axis, "direction": sign, "approach_deg_s": approach, "arm_length_m": arm, "points": points,
              "kt_out_nm_per_a": fit["k"], "offset_nm": fit["b"], "r2": fit["r2"], "kt_ideal_out": kt * ratio,
              "efficiency": fit["k"] / (kt * ratio) if fit["k"] else None}
    rows = "\n".join(f"| {p['current_cmd']:g} | {p['iq']:.2f} | {p['joint_torque_est_nm']:.2f} | {p['scale_kg'] or '-'} | "
                     f"{p['joint_torque_meas_nm'] and round(p['joint_torque_meas_nm'], 2) or '-'} |" for p in points)
    result["report_id"] = save_report("push_test", {"kind": "push_test", **result, "verdict": "pass"},
                                      f"# Push test axis{axis}\n\narm {arm} m, approach {approach} deg/s\n\n"
                                      f"| cmd A | Iq A | joint est Nm | scale kg | joint meas Nm |\n|---|---|---|---|---|\n{rows}\n")["id"]
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
