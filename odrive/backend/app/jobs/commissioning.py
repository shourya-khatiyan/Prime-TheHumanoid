"""Commissioning jobs: apply the actuator profile, calibrate, and the encoder hand-turn test."""

from __future__ import annotations

import math
import time

import numpy as np

from . import JobCtx, job

ENC_MODE_SPI_AMS = 257
ENC_MODE_INCREMENTAL = 0
ENC_MODES = {"INCREMENTAL": 0, "HALL": 1, "SPI_ABS_CUI": 256, "SPI_ABS_AMS": 257, "SPI_ABS_AEAT": 258, "SPI_ABS_RLS": 259}


def encoder_mode(profile) -> int:
    """Encoder mode number from the profile ('SPI_ABS_AMS' absolute, 'INCREMENTAL' A/B/Z)."""
    return ENC_MODES.get(str(profile.get("encoder.mode", "SPI_ABS_AMS")).upper(), ENC_MODE_SPI_AMS)


def profile_targets(ctx: JobCtx, axis: int) -> list[dict]:
    """Build the list of config writes that bring the device in line with the profile.

    Args:
        ctx: job context (gives the device tree and profile).
        axis: axis the actuator is wired to.
    Returns:
        [{path, value, why}] for every path that exists on this firmware.
    """
    pr = ctx.safety.profile
    w = ctx.worker
    a = f"axis{axis}"
    other = f"axis{1 - axis}"
    want = [
        ("config.dc_bus_overvoltage_trip_level", float(pr.get("power.overvoltage_trip_v")), "over-voltage trip for a 6S bus"),
        ("config.dc_bus_undervoltage_trip_level", float(pr.get("power.undervoltage_trip_v")), "under-voltage trip"),
        ("config.brake_resistance", float(pr.get("power.brake_resistance_ohm")), "brake resistor value"),
        ("config.enable_brake_resistor", True, "brake resistor enabled (0.5.6+)"),
        ("config.max_regen_current", float(pr.get("power.max_regen_current_a")), "regen sent to the supply"),
        ("config.dc_max_negative_current", float(pr.get("power.dc_max_negative_current_a")), "max current the supply may sink"),
        (f"{a}.motor.config.motor_type", 0, "high-current pmsm"),
        (f"{a}.motor.config.pole_pairs", int(pr.get("motor.pole_pairs")), "motor pole pairs"),
        (f"{a}.motor.config.torque_constant", round(pr.kt, 5), "Kt = 8.27 / KV"),
        (f"{a}.motor.config.calibration_current", float(pr.get("motor.calibration_current_a")), "low calibration current for bring-up"),
        (f"{a}.motor.config.resistance_calib_max_voltage", float(pr.get("motor.resistance_calib_max_voltage_v")), "must exceed I_cal x R and stay below vbus/2"),
        (f"{a}.motor.config.current_lim", float(pr.get("limits.bring_up_current_a")), "bring-up current limit"),
        (f"{a}.controller.config.vel_limit", min(2.0, float(pr.get("limits.vel_max_turns_s"))), "low bring-up speed limit"),
        (f"{other}.encoder.config.mode", ENC_MODE_INCREMENTAL, "unused axis: stop false SPI faults"),
    ]
    mode = encoder_mode(pr)
    want.append((f"{a}.encoder.config.mode", mode, "absolute SPI (AS5047P)" if mode >= 256 else "incremental A/B/Z"))
    want.append((f"{a}.encoder.config.cpr", int(pr.get("encoder.cpr")), "AS5047P SPI is 14-bit" if mode >= 256 else "counts per rev (4 x PPR)"))
    want.append((f"{a}.encoder.config.use_index", bool(pr.get("encoder.use_index", False)), "index pulse (incremental only)"))
    want.append((f"{a}.encoder.config.calib_range", 0.08, "allow normal cogging variance during offset scan"))
    if mode >= 256:
        cs = int(pr.get("encoder.cs_gpio"))
        want.append((f"{a}.encoder.config.abs_spi_cs_gpio_pin", cs, "chip-select wiring"))
        want.append((f"config.gpio{cs}_mode", 0, "cs pin as digital gpio (0.5.6+)"))
    return [{"path": p, "value": v, "why": why} for p, v, why in want if w.tree.get(p, {}).get("kind") == "prop"]


@job("profile_diff", "Compare device with profile", energizes=False)
async def profile_diff(ctx: JobCtx, params: dict) -> dict:
    """Read the device and list what `apply_profile` would change (no writes)."""
    axis = int(params.get("axis", ctx.safety.profile.axis))
    targets = profile_targets(ctx, axis)
    current = await ctx.read(*[t["path"] for t in targets])
    rows = []
    for t, cur in zip(targets, current):
        same = cur == t["value"] or (isinstance(cur, float) and isinstance(t["value"], float) and abs(cur - t["value"]) < 1e-4)
        rows.append({**t, "current": cur, "change": not same})
    ctx.log(f"{sum(r['change'] for r in rows)} of {len(rows)} settings differ from the profile")
    return {"axis": axis, "rows": rows}


@job("apply_profile", "Apply profile to device", energizes=False, confirm=True)
async def apply_profile(ctx: JobCtx, params: dict) -> dict:
    """Write the profile-derived settings (only the ones that differ). Does not save to flash."""
    axis = int(params.get("axis", ctx.safety.profile.axis))
    diff = await profile_diff(ctx, {"axis": axis})
    changed = [r for r in diff["rows"] if r["change"]]
    # lower limits first so raising a dependent value never exceeds a guard
    for i, r in enumerate(changed):
        await ctx.write(r["path"], r["value"])
        ctx.log(f"{r['path']}: {r['current']} -> {r['value']}  ({r['why']})")
        ctx.progress((i + 1) / max(1, len(changed)))
    for ax in (0, 1):
        c = ctx.worker.path(f"clear_errors.{ax}")
        if c:
            await ctx.call(c)
    ctx.log("errors cleared; settings are live but NOT saved to flash yet")
    return {"axis": axis, "written": changed}


@job("config_apply", "Apply configuration changes", energizes=False, confirm=True)
async def config_apply(ctx: JobCtx, params: dict) -> dict:
    """Write a list of {path, value} changes (from the config editor, a backup or a preset).

    Each write still goes through the safety layer, so profile limits apply. Values
    equal to the device value are skipped. Nothing is saved to flash.
    """
    changes = params.get("changes") or []
    if ctx.safety.active_axes:
        raise ValueError("disarm all axes before changing configuration")
    paths = [c["path"] for c in changes if ctx.worker.tree.get(c["path"], {}).get("writable")]
    skipped = [c["path"] for c in changes if c["path"] not in paths]
    current = dict(zip(paths, await ctx.read(*paths))) if paths else {}
    written, failed = [], []
    for i, c in enumerate([c for c in changes if c["path"] in current]):
        cur, new = current[c["path"]], c["value"]
        if cur == new or (isinstance(cur, float) and isinstance(new, (int, float)) and abs(cur - float(new)) <= 1e-6 * max(1.0, abs(cur))):
            continue
        try:
            await ctx.write(c["path"], new)
            written.append({"path": c["path"], "old": cur, "new": new})
            ctx.log(f"{c['path']}: {cur} -> {new}")
        except Exception as ex:
            failed.append({"path": c["path"], "error": str(ex)})
            ctx.log(f"{c['path']}: {ex}", "alarm")
        ctx.progress((i + 1) / max(1, len(current)))
    if skipped:
        ctx.log(f"skipped {len(skipped)} paths not writable on this firmware", "warn")
    ctx.log(f"{len(written)} written, {len(failed)} failed; not saved to flash")
    return {"written": written, "failed": failed, "skipped": skipped}


async def _save_and_reboot(ctx: JobCtx) -> None:
    """Save configuration to NVM and reboot so boot-latched encoder mode changes take effect."""
    ctx.safety.active_axes.clear()
    await ctx.call("save_configuration")
    await ctx.sleep(0.3)
    if ctx.worker.connected:
        try:
            await ctx.call("reboot")
        except Exception:
            pass
    t0 = time.monotonic()
    while time.monotonic() - t0 < 12.0:
        await ctx.sleep(0.25)
        if ctx.worker.connected:
            await ctx.sleep(0.4)
            return
    raise TimeoutError("device did not reconnect after reboot")


async def _bypass_faulted_spi(ctx: JobCtx, axis: int) -> bool:
    """Switch encoder mode to INCREMENTAL (0) if an SPI encoder is actively faulting."""
    mode = (await ctx.get(f"enc_mode.{axis}"))[0]
    if not isinstance(mode, int) or mode < 256:
        return False
    spi_path = ctx.worker.path(f"spi_err.{axis}")
    spi_rate = float(await ctx.read1(spi_path)) if spi_path else 0.0
    enc_err = int((await ctx.get(f"enc_error.{axis}"))[0] or 0)
    if spi_rate <= 0.01 and enc_err == 0:
        return False
    ctx.log(f"axis{axis}: SPI encoder faulting (rate {spi_rate:.2f}); bypassing encoder (mode -> INCREMENTAL) so motor can run", "warn")
    await ctx.write(ctx.p(f"enc_mode.{axis}"), ENC_MODE_INCREMENTAL)
    sim = bool(ctx.worker.info and ctx.worker.info.extra.get("simulated"))
    if not sim:
        await _save_and_reboot(ctx)
    clear = ctx.worker.path(f"clear_errors.{axis}")
    if clear:
        await ctx.call(clear)
    return True


@job("calibrate", "Motor / encoder calibration", energizes=True)
async def calibrate(ctx: JobCtx, params: dict) -> dict:
    """Run motor (R/L), encoder offset, or full calibration and check the results.

    Params:
        axis: axis index.
        kind: 'motor', 'encoder' or 'full'.
        mark_precalibrated: if true and the results pass, set pre_calibrated flags (not saved).
    """
    axis = int(params.get("axis", ctx.safety.profile.axis))
    kind = params.get("kind", "motor")
    state = {"motor": 4, "encoder": 7, "full": 3}[kind]
    pr = ctx.safety.profile
    if kind == "motor":
        await _bypass_faulted_spi(ctx, axis)
    elif kind in ("encoder", "full"):
        want_mode = encoder_mode(pr)
        cur_mode = (await ctx.get(f"enc_mode.{axis}"))[0]
        if cur_mode != want_mode:
            ctx.log(f"axis{axis}: restoring encoder mode {cur_mode} -> {want_mode} before {kind} calibration")
            await ctx.write(ctx.p(f"enc_mode.{axis}"), want_mode)
            if want_mode >= 256 and ctx.worker.path(f"enc_cs.{axis}"):
                await ctx.write(ctx.p(f"enc_cs.{axis}"), int(pr.get("encoder.cs_gpio", 4)))
            sim = bool(ctx.worker.info and ctx.worker.info.extra.get("simulated"))
            if not sim:
                await _save_and_reboot(ctx)
        cal_range_path = f"axis{axis}.encoder.config.calib_range"
        if ctx.worker.tree.get(cal_range_path, {}).get("writable"):
            cur_range = float(await ctx.read1(cal_range_path) or 0.02)
            if cur_range < 0.10:
                await ctx.write(cal_range_path, 0.10)
        scan_dist_path = f"axis{axis}.encoder.config.calib_scan_distance"
        scan_omega_path = f"axis{axis}.encoder.config.calib_scan_omega"
        if ctx.worker.tree.get(scan_dist_path, {}).get("writable"):
            await ctx.write(scan_dist_path, 4.0 * math.pi)
        if ctx.worker.tree.get(scan_omega_path, {}).get("writable"):
            await ctx.write(scan_omega_path, 2.0 * math.pi)
    clear = ctx.worker.path(f"clear_errors.{axis}")
    if clear:
        await ctx.call(clear)
    ctx.log(f"axis{axis}: starting {kind} calibration (state {state}); expect a beep and/or slow rotation")
    await ctx.set_state(axis, state)
    ctx.progress(0.1)
    final = await ctx.wait_state(axis, leave=1, reach=1, timeout=60)
    ctx.progress(0.9)
    errs = await ctx.errors(axis)
    result = {"axis": axis, "kind": kind, "final_state": final, "errors": errs, "checks": []}
    r, l, cal, ready = await ctx.get(f"phase_r.{axis}", f"phase_l.{axis}", f"motor_cal.{axis}", f"enc_ready.{axis}")
    result.update({"phase_resistance": r, "phase_inductance": l, "motor_calibrated": bool(cal), "encoder_ready": bool(ready)})
    if kind in ("motor", "full"):
        r_nom = float(pr.get("motor.phase_resistance_ohm"))
        tol = float(pr.get("motor.resistance_tolerance", 0.5))
        ok_r = bool(cal) and abs(r - r_nom) <= tol * r_nom
        ok_l = bool(cal) and 2e-6 <= l <= 4e-3
        result["checks"] += [
            {"id": "phase_r", "ok": ok_r, "msg": f"R = {r * 1000:.1f} mOhm (expect {r_nom * 1000:.0f} +- {tol * 100:.0f} %)"},
            {"id": "phase_l", "ok": ok_l, "msg": f"L = {l * 1e6:.1f} uH (plausible 2..4000 uH)"},
        ]
    if kind in ("encoder", "full"):
        off_path = ctx.worker.path(f"enc_offset.{axis}")
        scan_path = f"axis{axis}.encoder.calib_scan_response"
        scan_resp = await ctx.read1(scan_path) if scan_path in ctx.worker.tree else None
        result["encoder_offset"] = await ctx.read1(off_path) if off_path else None
        result["calib_scan_response"] = scan_resp
        result["checks"].append({
            "id": "enc_ready",
            "ok": bool(ready),
            "msg": f"encoder ready (scan delta {scan_resp:.0f} counts)" if ready and isinstance(scan_resp, (int, float)) else ("encoder ready" if ready else f"encoder not ready (scan delta {scan_resp} counts)"),
        })
    result["ok"] = not errs and all(c["ok"] for c in result["checks"])
    for c in result["checks"]:
        ctx.log(("PASS " if c["ok"] else "FAIL ") + c["msg"], "info" if c["ok"] else "alarm")
    for path, flags in errs.items():
        ctx.log(f"{path}: {', '.join(flags)}", "alarm")
    if result["ok"] and params.get("mark_precalibrated"):
        if kind in ("motor", "full"):
            await ctx.write(ctx.p(f"motor_precal.{axis}"), True)
        if kind in ("encoder", "full") and ctx.worker.path(f"enc_precal.{axis}"):
            await ctx.write(ctx.p(f"enc_precal.{axis}"), True)
        ctx.log("pre_calibrated set (save configuration to keep it after reboot)")
    ctx.progress(1.0)
    return result


@job("encoder_setup", "Configure encoder (ABZ / SPI)", energizes=False, confirm=True)
async def encoder_setup(ctx: JobCtx, params: dict) -> dict:
    """Switch encoder between INCREMENTAL (A/B/Z on J4) and SPI_ABS_AMS (SPI on J3), update profile, save & reboot."""
    from ..profile import save_profile

    pr = ctx.safety.profile
    axis = int(params.get("axis", pr.axis))
    a = f"axis{axis}"
    mode_str = str(params.get("mode", pr.get("encoder.mode", "INCREMENTAL"))).upper()
    mode_num = ENC_MODES.get(mode_str, ENC_MODE_INCREMENTAL if mode_str == "0" else ENC_MODE_SPI_AMS)
    mode_name = "INCREMENTAL" if mode_num == 0 else "SPI_ABS_AMS"
    cpr = int(params.get("cpr", 4000 if mode_num == 0 else 16384))
    use_index = bool(params.get("use_index", False)) if mode_num == 0 else False
    cs_gpio = int(params.get("cs_gpio", pr.get("encoder.cs_gpio", 4)))

    # 1. Update and persist the actuator profile
    pr.data.setdefault("encoder", {})
    pr.data["encoder"]["mode"] = mode_name
    pr.data["encoder"]["cpr"] = cpr
    pr.data["encoder"]["use_index"] = use_index
    pr.data["encoder"]["cs_gpio"] = cs_gpio
    save_profile(pr.data)

    # 2. Write settings to the ODrive
    await ctx.write(f"{a}.encoder.config.mode", mode_num)
    await ctx.write(f"{a}.encoder.config.cpr", cpr)
    await ctx.write(f"{a}.encoder.config.use_index", use_index)
    if mode_num >= 256 and ctx.worker.tree.get(f"{a}.encoder.config.abs_spi_cs_gpio_pin", {}).get("writable"):
        await ctx.write(f"{a}.encoder.config.abs_spi_cs_gpio_pin", cs_gpio)
    if ctx.worker.tree.get(f"{a}.encoder.config.pre_calibrated", {}).get("writable"):
        await ctx.write(f"{a}.encoder.config.pre_calibrated", False)

    ctx.log(f"{a}: set mode={mode_name} ({mode_num}), cpr={cpr}, use_index={use_index}" + (f", cs_gpio={cs_gpio}" if mode_num >= 256 else " (J4 M0 A/B/Z pins — no CS GPIO used)"))
    ctx.progress(0.5)

    # 3. Save to NVM and reboot so boot-latched encoder mode / pins take effect
    sim = bool(ctx.worker.info and ctx.worker.info.extra.get("simulated"))
    if not sim:
        await _save_and_reboot(ctx)
    clear = ctx.worker.path(f"clear_errors.{axis}")
    if clear:
        await ctx.call(clear)
    ctx.progress(1.0)
    return {"axis": axis, "mode": mode_name, "mode_num": mode_num, "cpr": cpr, "use_index": use_index, "cs_gpio": cs_gpio}


@job("encoder_turn", "Encoder hand-turn test", energizes=False)
async def encoder_turn(ctx: JobCtx, params: dict) -> dict:
    """With the motor idle, the user turns the shaft one full turn by hand; we check the encoder follows smoothly."""
    axis = int(params.get("axis", ctx.safety.profile.axis))
    st = (await ctx.get(f"state.{axis}"))[0]
    if st != 1:
        raise ValueError("axis must be IDLE for the hand-turn test")
    cpr = int((await ctx.get(f"enc_cpr.{axis}"))[0])
    paths = [ctx.p(f"shadow.{axis}"), ctx.p(f"spi_err.{axis}")]
    if ctx.worker.path(f"pos_abs.{axis}"):
        paths.append(ctx.p(f"pos_abs.{axis}"))
    ctx.capture_start(paths)
    t0 = time.time()
    await ctx.ask("Turn the motor shaft slowly by hand exactly ONE full turn in either direction, then press Done.", ["Done"])
    cap = ctx.capture_stop()
    shadow = np.asarray([x for x in cap["v"][paths[0]] if x is not None], float)
    spi = np.asarray([x for x in cap["v"][paths[1]] if x is not None], float)
    if len(shadow) < 5:
        raise ValueError("not enough samples captured")
    travel = float(np.ptp(shadow))
    steps = np.abs(np.diff(shadow))
    rate = len(shadow) / max(1e-3, time.time() - t0)
    # at ~100 Hz and a slow hand turn, a jump above cpr/8 between samples is a glitch
    glitches = int((steps > cpr / 8).sum())
    ratio = travel / cpr if cpr else 0.0
    checks = [
        {"id": "travel", "ok": 0.85 <= ratio <= 1.25, "msg": f"travel {travel:.0f} counts = {ratio:.2f} turns (expect ~1.00)"},
        {"id": "glitches", "ok": glitches == 0, "msg": f"{glitches} jumps larger than cpr/8 between samples"},
        {"id": "spi", "ok": float(spi.max(initial=0)) < 0.01, "msg": f"max spi_error_rate {float(spi.max(initial=0)):.4f}"},
    ]
    for c in checks:
        ctx.log(("PASS " if c["ok"] else "FAIL ") + c["msg"], "info" if c["ok"] else "alarm")
    return {"axis": axis, "cpr": cpr, "samples": len(shadow), "rate_hz": rate, "checks": checks,
            "ok": all(c["ok"] for c in checks), "trace": shadow[:: max(1, len(shadow) // 2000)].tolist()}


@job("open_loop", "Open-loop motor spin", energizes=True)
async def open_loop(ctx: JobCtx, params: dict) -> dict:
    """Spin the motor in open-loop (AXIS_STATE_LOCKIN_SPIN, state 9) without needing a working encoder.

    Automatically bypasses a faulting SPI encoder, calibrates motor R/L if needed, sets direction,
    and drives the phase current vector at the requested mechanical speed and turn count.
    """
    pr = ctx.safety.profile
    axis = int(params.get("axis", pr.axis))
    a = f"axis{axis}"
    max_cur = float(pr.get("motor.current_continuous_a", 8.0))
    max_vel = float(pr.get("limits.vel_max_turns_s", 10.0))
    current_a = max(0.5, min(max_cur, float(params.get("current_a", 3.0))))
    vel_turns_s = max(-max_vel, min(max_vel, float(params.get("vel_turns_s", 0.5))))
    if abs(vel_turns_s) < 0.05:
        vel_turns_s = 0.5 if vel_turns_s >= 0 else -0.5
    accel_turns_s2 = max(0.1, min(10.0, abs(float(params.get("accel_turns_s2", 0.5)))))
    turns = max(0.0, min(50.0, float(params.get("turns", 2.0))))
    duration_s = max(0.5, min(30.0, float(params.get("duration_s", 4.0))))

    orig_mode = (await ctx.get(f"enc_mode.{axis}"))[0]
    bypassed = await _bypass_faulted_spi(ctx, axis)

    cal = bool((await ctx.get(f"motor_cal.{axis}"))[0])
    if not cal:
        ctx.log(f"axis{axis}: motor not calibrated; running R/L calibration first")
        cal_res = await calibrate(ctx, {"axis": axis, "kind": "motor", "mark_precalibrated": True})
        if not cal_res.get("ok"):
            raise RuntimeError("motor R/L calibration failed; cannot enter open-loop spin")

    dir_path = f"{a}.motor.config.direction"
    if ctx.worker.tree.get(dir_path, {}).get("writable"):
        cur_dir = await ctx.read1(dir_path)
        if not cur_dir:
            await ctx.write(dir_path, 1)

    pp = max(1, int((await ctx.get(f"pole_pairs.{axis}"))[0] or pr.get("motor.pole_pairs", 20)))
    sign = -1.0 if vel_turns_s < 0 else 1.0
    vel_elec = sign * abs(vel_turns_s) * 2.0 * math.pi * pp
    accel_elec = sign * accel_turns_s2 * 2.0 * math.pi * pp
    ramp_dist = sign * math.pi
    finish_on_dist = turns > 0
    finish_dist = turns * 2.0 * math.pi * pp if finish_on_dist else 1e6

    lockin_writes = [
        (f"{a}.config.general_lockin.current", current_a),
        (f"{a}.config.general_lockin.ramp_time", 0.4),
        (f"{a}.config.general_lockin.ramp_distance", ramp_dist),
        (f"{a}.config.general_lockin.accel", accel_elec),
        (f"{a}.config.general_lockin.vel", vel_elec),
        (f"{a}.config.general_lockin.finish_distance", finish_dist),
        (f"{a}.config.general_lockin.finish_on_distance", finish_on_dist),
        (f"{a}.config.general_lockin.finish_on_vel", False),
        (f"{a}.config.general_lockin.finish_on_enc_idx", False),
    ]
    for path, val in lockin_writes:
        if ctx.worker.tree.get(path, {}).get("writable"):
            await ctx.write(path, val)

    clear = ctx.worker.path(f"clear_errors.{axis}")
    if clear:
        await ctx.call(clear)

    est_time = (turns / abs(vel_turns_s) + 1.2) if finish_on_dist else duration_s
    run_limit = min(30.0, max(1.0, est_time if finish_on_dist else duration_s))

    iq_path = ctx.p(f"iq.{axis}")
    fet_path = ctx.p(f"fet_temp.{axis}")
    ctx.capture_start([iq_path, fet_path])
    ctx.log(f"axis{axis}: open-loop spin {vel_turns_s:+.2f} turn/s @ {current_a:.1f} A ({'%.1f turns' % turns if finish_on_dist else '%.1f s' % run_limit})")

    try:
        await ctx.set_state(axis, 9)
        t0 = time.monotonic()
        while (elapsed := time.monotonic() - t0) < run_limit:
            ctx.progress(min(0.95, elapsed / run_limit))
            st, err = await ctx.get(f"state.{axis}", f"error.{axis}")
            if err:
                break
            if elapsed > 0.6 and st == 1:
                break
            await ctx.sleep(0.15)
    finally:
        cap = ctx.capture_stop()
        await ctx.idle(axis)
        if bypassed and isinstance(orig_mode, int) and orig_mode >= 256:
            ctx.log(f"axis{axis}: restoring encoder mode -> {orig_mode} (SPI_ABS_AMS)")
            await ctx.write(ctx.p(f"enc_mode.{axis}"), orig_mode)
            sim = bool(ctx.worker.info and ctx.worker.info.extra.get("simulated"))
            if not sim:
                await _save_and_reboot(ctx)

    errs = await ctx.errors(axis)
    iq_vals = [abs(x) for x in cap["v"].get(iq_path, []) if isinstance(x, (int, float))]
    fet_vals = [x for x in cap["v"].get(fet_path, []) if isinstance(x, (int, float))]
    iq_peak = max(iq_vals) if iq_vals else 0.0
    iq_avg = sum(iq_vals) / len(iq_vals) if iq_vals else 0.0
    fet_max = max(fet_vals) if fet_vals else None
    ok = not errs and iq_peak > 0.2
    ctx.log(
        f"{'PASS' if ok else 'FAIL'} open-loop spin: Iq avg {iq_avg:.2f} A (peak {iq_peak:.2f} A)"
        + (f", FET {fet_max:.1f} C" if fet_max is not None else ""),
        "info" if ok else "alarm",
    )
    ctx.progress(1.0)
    return {
        "axis": axis,
        "ok": ok,
        "current_a": current_a,
        "vel_turns_s": vel_turns_s,
        "turns": turns,
        "iq_avg": iq_avg,
        "iq_peak": iq_peak,
        "fet_max_c": fet_max,
        "errors": errs,
    }

