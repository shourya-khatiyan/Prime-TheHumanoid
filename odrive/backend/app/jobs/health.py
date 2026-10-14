"""Passive hardware health check: never energizes the motor.

Checks the link, power, control loop, gate driver, current sensors, thermals,
encoder wiring and noise, calibration results and safety configuration, then
writes a pass/warn/fail report (json + markdown).
"""

from __future__ import annotations

import statistics
import time

from ..storage import save_report
from . import JobCtx, job
from .commissioning import encoder_mode

PASS, WARN, FAIL, SKIP = "pass", "warn", "fail", "skip"


class Checks:
    """Collects check results in order."""

    def __init__(self):
        self.items: list[dict] = []

    def add(self, cid: str, title: str, status: str, value: str = "", expect: str = "", hint: str = "") -> None:
        """Record one check result."""
        self.items.append({"id": cid, "title": title, "status": status, "value": value, "expect": expect, "hint": hint})

    def verdict(self) -> str:
        """Overall result: fail beats warn beats pass."""
        sts = {c["status"] for c in self.items}
        return FAIL if FAIL in sts else WARN if WARN in sts else PASS


def _num(x) -> float | None:
    return float(x) if isinstance(x, (int, float)) and not isinstance(x, bool) else None


@job("health", "Hardware health check", energizes=False)
async def health(ctx: JobCtx, params: dict) -> dict:
    """Run every passive check for one axis and save a report."""
    w, pr = ctx.worker, ctx.safety.profile
    axis = int(params.get("axis", pr.axis))
    c = Checks()
    meta = w.meta
    info = w.info.to_json() if w.info else {}

    # link and identity
    c.add("link", "Device link", PASS, f"{w.transport.name if w.transport else '?'} @ {w.achieved_hz:.0f} Hz", "connected")
    hw_ok = info.get("hw", "").endswith("-56V")
    c.add("hw", "Hardware variant", PASS if hw_ok else WARN, info.get("hw", "?"), "3.6-56V", "firmware build does not match a 56V board" if not hw_ok else "")
    fw = info.get("fw", "?")
    c.add("fw", "Firmware", PASS if fw == "0.5.6" else WARN, fw, "0.5.6 (latest for v3.6)",
          "0.5.1 works, but 0.5.6 fixes CAN baud and adds cyclic CAN messages" if fw != "0.5.6" else "")
    ctx.progress(0.05)

    # sample a 2 s window at standstill
    keys = ["vbus", f"spi_err.{axis}", f"ph_b.{axis}", f"ph_c.{axis}", f"fet_temp.{axis}", "clock"]
    enc_paths = [w.path(k) for k in (f"pos_abs.{axis}", f"count_in_cpr.{axis}") if w.path(k)]
    paths = [w.path(k) for k in keys if w.path(k)] + enc_paths
    ctx.capture_start(paths)
    ctx.log("sampling 2 s at standstill")
    t0 = time.time()
    await ctx.sleep(2.0)
    cap = ctx.capture_stop()
    dt = time.time() - t0
    series = lambda alias: [x for x in cap["v"].get(w.path(alias) or "", []) if isinstance(x, (int, float))]
    ctx.progress(0.35)

    # power
    vb = series("vbus")
    if vb:
        mean, sd = statistics.fmean(vb), statistics.pstdev(vb)
        lo, hi = float(pr.get("power.bus_min_v")), float(pr.get("power.bus_max_v"))
        c.add("vbus", "Bus voltage", PASS if lo <= mean <= hi else FAIL, f"{mean:.2f} V", f"{lo}-{hi} V",
              "compare with a multimeter; a big mismatch means a wrong 24V/56V firmware build")
        c.add("vbus_noise", "Bus voltage noise", PASS if sd < 0.15 else WARN, f"{sd * 1000:.0f} mV rms", "< 150 mV")

    # control loop rate from the device clock
    clk = series("clock")
    if len(clk) > 2 and dt > 0:
        span_t = cap["t"][-1] - cap["t"][0]
        rate = ((clk[-1] - clk[0]) % 2**32) / span_t if span_t > 0 else 0
        c.add("loop", "Control loop rate", PASS if 7600 <= rate <= 8400 else WARN, f"{rate:.0f} Hz", "~8000 Hz")

    # errors
    errs = await ctx.errors(axis)
    sys_path = w.path("sys_error")
    if sys_path:
        sv = await ctx.read1(sys_path)
        if sv:
            errs[sys_path] = meta.decode_flags(sys_path, int(sv))
    c.add("errors", "Error registers", PASS if not errs else FAIL,
          "; ".join(f"{p.split('.')[-2] if '.' in p else p}: {', '.join(f)}" for p, f in errs.items()) or "none", "none",
          "clear errors, fix the cause, run again" if errs else "")

    # gate driver
    drv = w.path(f"drv_fault.{axis}")
    if drv:
        dv = await ctx.read1(drv)
        flags = meta.decode_flags(drv, int(dv)) if dv else []
        c.add("drv", "Gate driver (DRV8301)", FAIL if flags else PASS, ", ".join(flags) or "no fault", "no fault")
    ctx.progress(0.5)

    # current sensors at idle
    st = (await ctx.get(f"state.{axis}"))[0]
    phb, phc = series(f"ph_b.{axis}"), series(f"ph_c.{axis}")
    if st == 1 and phb and phc:
        off = max(abs(statistics.fmean(phb)), abs(statistics.fmean(phc)))
        c.add("isense", "Current sensor offset (idle)", PASS if off < 0.3 else WARN if off < 1.0 else FAIL, f"{off:.3f} A", "< 0.3 A")
    else:
        c.add("isense", "Current sensor offset (idle)", SKIP, "", "", "axis must be idle")

    # thermals
    ft = series(f"fet_temp.{axis}")
    if ft:
        tmean = statistics.fmean(ft)
        c.add("fet_temp", "FET thermistor", PASS if 5 <= tmean <= 60 else WARN if tmean < float(pr.get("thermal.fet_warn_c")) else FAIL,
              f"{tmean:.1f} C", "5-60 C at idle")
    mt_en = w.path(f"motor_temp_enabled.{axis}")
    mt_on = bool(await ctx.read1(mt_en)) if mt_en else False
    c.add("motor_temp", "Motor thermistor", PASS if mt_on else WARN, "enabled" if mt_on else "not configured", "enabled",
          "fit an NTC on the winding before thermal tests" if not mt_on else "")

    # encoder
    mode, cpr, cs = await ctx.get(f"enc_mode.{axis}", f"enc_cpr.{axis}", f"enc_cs.{axis}")
    want_mode, want_cpr = encoder_mode(pr), int(pr.get("encoder.cpr"))
    absolute = want_mode >= 256
    want_cs = int(pr.get("encoder.cs_gpio")) if absolute else cs
    mode_name = meta.enum_name(w.path(f"enc_mode.{axis}"), mode) if meta else str(mode)
    ok_cfg = mode == want_mode and cpr == want_cpr and cs == want_cs
    c.add("enc_cfg", "Encoder config", PASS if ok_cfg else FAIL,
          f"mode {mode_name}, cpr {cpr}" + (f", cs gpio{cs}" if absolute else ""),
          f"{pr.get('encoder.mode')}, cpr {want_cpr}" + (f", cs gpio{want_cs}" if absolute else ""),
          "" if ok_cfg else "apply the profile in the commissioning wizard, then save + reboot")
    spi = series(f"spi_err.{axis}") if absolute else []
    if spi:
        rate = max(spi)
        c.add("enc_spi", "Encoder SPI link", PASS if rate < 0.01 else WARN if rate < 0.05 else FAIL, f"error rate {rate:.4f}", "< 0.01",
              "check CS pin, 3.3 V supply, MISO/SCK wiring and the magnet" if rate >= 0.01 else "")
    raw = [x for x in cap["v"].get(enc_paths[0], []) if isinstance(x, (int, float))] if enc_paths else []
    if raw and not absolute:
        # incremental encoders have no absolute word; jitter of count_in_cpr is the useful check
        raw = [x for x in cap["v"].get(enc_paths[-1], []) if isinstance(x, (int, float))]
        jit = statistics.pstdev(raw) if len(set(raw)) > 1 else 0.0
        c.add("enc_jitter", "Encoder noise at standstill", PASS if jit < 3 else WARN if jit < 10 else FAIL, f"{jit:.2f} counts rms", "< 3 counts")
    elif raw:
        if all(x == 16383 for x in raw):
            c.add("enc_stuck", "Encoder data line", FAIL, "stuck at 16383 (all ones)", "changing values", "MISO floating or CS wrong")
        elif all(x == 0 for x in raw):
            c.add("enc_stuck", "Encoder data line", FAIL, "stuck at 0", "changing values", "MISO shorted to GND or encoder unpowered")
        else:
            jit = statistics.pstdev(raw) if len(set(raw)) > 1 else 0.0
            if max(raw) - min(raw) > 8000:
                jit = float("nan")
            c.add("enc_jitter", "Encoder noise at standstill", PASS if jit < 3 else WARN if jit < 10 else FAIL,
                  f"{jit:.2f} counts rms", "< 3 counts", "check magnet gap/centering and cable routing" if not jit < 3 else "")
    ctx.progress(0.75)

    # motor calibration results
    pp, r, l, cal = await ctx.get(f"pole_pairs.{axis}", f"phase_r.{axis}", f"phase_l.{axis}", f"motor_cal.{axis}")
    c.add("pole_pairs", "Pole pairs", PASS if pp == int(pr.get("motor.pole_pairs")) else FAIL, str(pp), str(pr.get("motor.pole_pairs")))
    if cal and _num(r):
        r_nom, tol = float(pr.get("motor.phase_resistance_ohm")), float(pr.get("motor.resistance_tolerance"))
        c.add("phase_r", "Phase resistance", PASS if abs(r - r_nom) <= tol * r_nom else WARN, f"{r * 1000:.1f} mOhm", f"{r_nom * 1000:.0f} mOhm +- {tol * 100:.0f} %")
        c.add("phase_l", "Phase inductance", PASS if 2e-6 <= l <= 4e-3 else WARN, f"{l * 1e6:.1f} uH", "2-4000 uH")
    else:
        c.add("phase_r", "Phase resistance", SKIP, "not calibrated", "", "run motor calibration")

    # safety configuration
    ov = await ctx.read1("config.dc_bus_overvoltage_trip_level") if "config.dc_bus_overvoltage_trip_level" in w.tree else None
    if _num(ov):
        lim = float(pr.get("power.overvoltage_trip_v"))
        c.add("ov_trip", "Over-voltage trip", PASS if ov <= lim + 0.01 else FAIL, f"{ov:.1f} V", f"<= {lim} V", "apply profile power settings" if ov > lim else "")
    cl, vl = await ctx.get(f"current_lim.{axis}", f"vel_limit.{axis}")
    c.add("current_lim", "Current limit", PASS if cl <= float(pr.get("motor.current_peak_a")) else FAIL, f"{cl:.1f} A", f"<= {pr.get('motor.current_peak_a')} A")
    c.add("vel_limit", "Velocity limit", PASS if vl <= float(pr.get("limits.vel_max_turns_s")) else FAIL, f"{vl:.2f} turn/s", f"<= {pr.get('limits.vel_max_turns_s')} turn/s")
    br = await ctx.read1("config.brake_resistance") if "config.brake_resistance" in w.tree else None
    armed = await ctx.read1(w.path("brake_armed")) if w.path("brake_armed") else None
    c.add("brake", "Brake resistor", PASS if armed and _num(br) and abs(br - float(pr.get("power.brake_resistance_ohm"))) < 0.05 else WARN,
          f"{br} Ohm configured, {'armed' if armed else 'not armed'}", f"{pr.get('power.brake_resistance_ohm')} Ohm, armed",
          "the board cannot measure the resistor: verify its value with a multimeter")
    baud = await ctx.read1(w.path("can_baud")) if w.path("can_baud") else None
    if baud is not None:
        c.add("can_baud", "CAN baud rate", PASS if baud == 1000000 else WARN, f"{baud}", "1000000 (planned RT core bus)")
    ctx.progress(0.95)

    report = {"kind": "health", "axis": axis, "created": time.time(), "device": info, "verdict": c.verdict(), "checks": c.items}
    md = [f"# Health check axis{axis} - {c.verdict().upper()}", "", f"device: {info}", "",
          "| check | status | value | expected | hint |", "|---|---|---|---|---|"]
    md += [f"| {i['title']} | {i['status'].upper()} | {i['value']} | {i['expect']} | {i['hint']} |" for i in c.items]
    saved = save_report(f"health_axis{axis}", report, "\n".join(md) + "\n")
    report["report_id"] = saved["id"]
    for i in c.items:
        ctx.log(f"{i['status'].upper():4} {i['title']}: {i['value']}", "alarm" if i["status"] == FAIL else "warn" if i["status"] == WARN else "info")
    ctx.progress(1.0)
    return report
