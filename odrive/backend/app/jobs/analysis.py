"""Signal analysis used by the test jobs (step metrics, sine fit, thermal fit, linear fit)."""

from __future__ import annotations

import math

import numpy as np


def step_metrics(t: list[float], y: list[float], y0: float, y1: float) -> dict:
    """Compute rise time, overshoot, settling time and steady-state error of one step.

    Args:
        t: sample times in seconds (starting at the step instant).
        y: measured response.
        y0: value before the step.
        y1: commanded target.
    Returns:
        dict with rise_s (10-90 %), overshoot_pct, settle_s (2 % band), sse, iae.
    """
    ta, ya = np.asarray(t, float), np.asarray(y, float)
    ok = np.isfinite(ya)
    ta, ya = ta[ok], ya[ok]
    amp = y1 - y0
    if len(ta) < 5 or amp == 0:
        return {"rise_s": None, "overshoot_pct": None, "settle_s": None, "sse": None, "iae": None}
    norm = (ya - y0) / amp
    def first(cond):
        idx = np.argmax(cond)
        return float(ta[idx]) if cond.any() else None
    t10, t90 = first(norm >= 0.1), first(norm >= 0.9)
    rise = (t90 - t10) if t10 is not None and t90 is not None else None
    overshoot = max(0.0, float(norm.max() - 1.0) * 100.0)
    outside = np.abs(norm - 1.0) > 0.02
    settle = float(ta[np.where(outside)[0][-1]]) if outside.any() else 0.0
    if outside.any() and np.where(outside)[0][-1] == len(ta) - 1:
        settle = None
    tail = ya[int(len(ya) * 0.8):]
    sse = float(y1 - tail.mean()) if len(tail) else None
    iae = float(np.trapezoid(np.abs(y1 - ya), ta)) if hasattr(np, "trapezoid") else float(np.trapz(np.abs(y1 - ya), ta))
    return {"rise_s": rise, "overshoot_pct": overshoot, "settle_s": settle, "sse": sse, "iae": iae}


def sine_fit(t: list[float], y: list[float], freq: float) -> tuple[float, float, float]:
    """Least-squares fit y = a*sin(wt) + b*cos(wt) + c.

    Returns:
        (amplitude, phase in degrees, offset).
    """
    ta, ya = np.asarray(t, float), np.asarray(y, float)
    w = 2 * math.pi * freq
    A = np.column_stack([np.sin(w * ta), np.cos(w * ta), np.ones_like(ta)])
    (a, b, c), *_ = np.linalg.lstsq(A, ya, rcond=None)
    return float(math.hypot(a, b)), float(math.degrees(math.atan2(b, a))), float(c)


def thermal_fit(t: list[float], temp: list[float]) -> dict:
    """Fit T(t) = T0 + dT * (1 - exp(-t / tau)) by scanning tau.

    Returns:
        dict with t0, dT, tau_s, t_inf (predicted steady state) and rms error;
        tau is None if the data is too short to fit.
    """
    ta, ya = np.asarray(t, float), np.asarray(temp, float)
    if len(ta) < 10 or ta[-1] - ta[0] < 30:
        return {"t0": float(ya[0]) if len(ya) else None, "dT": None, "tau_s": None, "t_inf": None, "rms": None}
    ta = ta - ta[0]
    best = None
    for tau in np.geomspace(10, 20000, 300):
        basis = 1 - np.exp(-ta / tau)
        A = np.column_stack([np.ones_like(ta), basis])
        coef, *_ = np.linalg.lstsq(A, ya, rcond=None)
        rms = float(np.sqrt(np.mean((A @ coef - ya) ** 2)))
        if best is None or rms < best[0]:
            best = (rms, tau, coef)
    rms, tau, (t0, dT) = best
    return {"t0": float(t0), "dT": float(dT), "tau_s": float(tau), "t_inf": float(t0 + dT), "rms": rms}


def linear_fit(x: list[float], y: list[float]) -> dict:
    """Fit y = k*x + b and report r^2."""
    xa, ya = np.asarray(x, float), np.asarray(y, float)
    if len(xa) < 2:
        return {"k": None, "b": None, "r2": None}
    k, b = np.polyfit(xa, ya, 1)
    pred = k * xa + b
    ss = float(((ya - ya.mean()) ** 2).sum())
    r2 = 1 - float(((ya - pred) ** 2).sum()) / ss if ss > 0 else 1.0
    return {"k": float(k), "b": float(b), "r2": r2}


def rel_time(t: list[float], t0: float) -> list[float]:
    """Shift absolute timestamps so the step instant is zero."""
    return [x - t0 for x in t]
