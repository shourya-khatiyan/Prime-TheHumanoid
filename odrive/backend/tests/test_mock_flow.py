"""End-to-end backend test against the simulated device, over the real websocket protocol."""

from __future__ import annotations

import os
import time

os.environ["ODRV_MODE"] = "mock"

import pytest
from fastapi.testclient import TestClient

from app import codec
from app.main import TOKEN, app


class Client:
    """Tiny synchronous rpc client over the test websocket."""

    def __init__(self, ws):
        self.ws = ws
        self.n = 0
        self.events: list[dict] = []
        self.tel: list[dict] = []

    def rpc(self, op: str, timeout: float = 15, **args):
        """Send one request and wait for its response (other messages are collected)."""
        self.n += 1
        rid = self.n
        self.ws.send_bytes(codec.pack({"id": rid, "op": op, "args": args}))
        t0 = time.time()
        while time.time() - t0 < timeout:
            msg = codec.unpack(self.ws.receive_bytes())
            if msg.get("t") == "res" and msg.get("id") == rid:
                return msg
            self._keep(msg)
        raise TimeoutError(op)

    def _keep(self, msg: dict) -> None:
        if msg.get("t") == "tel":
            self.tel.append(msg)
        elif msg.get("t") in ("event", "job"):
            self.events.append(msg)

    def ok(self, op: str, **args):
        """rpc that must succeed."""
        res = self.rpc(op, **args)
        assert res["ok"], res
        return res["data"]

    def confirmed(self, op: str, **args):
        """rpc that may need a confirmation token: arm and retry like the GUI does."""
        res = self.rpc(op, **args)
        if not res["ok"] and res.get("code") == "confirm":
            tok = self.ok("arm", action=res["action"])["token"]
            res = self.rpc(op, token=tok, **args)
        assert res["ok"], res
        return res["data"]

    def wait_job(self, jid: str, timeout: float = 60) -> dict:
        """Poll the job list until the job ends."""
        t0 = time.time()
        while time.time() - t0 < timeout:
            for j in self.ok("jobs"):
                if j["id"] == jid and j["state"] != "running":
                    return j
            time.sleep(0.3)
        raise TimeoutError(jid)


@pytest.fixture(scope="module")
def cli():
    with TestClient(app) as tc:
        with tc.websocket_connect(f"/ws?token={TOKEN}", headers={"origin": "http://localhost:5173"}) as ws:
            c = Client(ws)
            t0 = time.time()
            while time.time() - t0 < 10:
                if c.ok("hello")["status"]["device"]["connected"]:
                    break
                time.sleep(0.2)
            yield c


def test_rejects_bad_token():
    with TestClient(app) as tc:
        with pytest.raises(Exception):
            with tc.websocket_connect("/ws?token=nope") as ws:
                ws.receive_bytes()


def test_hello_and_telemetry(cli):
    hello = cli.ok("hello")
    assert hello["alias"]["fet_temp.0"] == "axis0.fet_thermistor.temperature"
    assert hello["status"]["device"]["info"]["fw"] == "0.5.1"
    cli.ok("subscribe", paths=["axis0.encoder.shadow_count"], rate=100)
    time.sleep(0.5)
    cli.ok("ping")
    assert any("axis0.encoder.shadow_count" in (f.get("cols") or []) for f in cli.tel)


def test_encoder_fault_matches_real_board(cli):
    vals = cli.ok("read", paths=["axis0.encoder.error", "axis0.encoder.spi_error_rate"])
    assert vals["axis0.encoder.error"] & 0x80
    assert vals["axis0.encoder.spi_error_rate"] > 0.9


def test_state_requires_confirmation_and_preflight(cli):
    res = cli.rpc("write", path="axis0.requested_state", value=8)
    # preflight refuses before confirmation: the board still has the unsafe 59.9 V trip / 12 A limit
    assert not res["ok"]


def test_limits_rejected(cli):
    res = cli.rpc("write", path="axis0.motor.config.current_lim", value=80.0)
    assert not res["ok"] and "profile limit" in res["error"]


def test_apply_profile_calibrate_and_closed_loop(cli):
    p = cli.ok("profile_get")
    p["encoder"] = {"mode": "SPI_ABS_AMS", "cpr": 16384, "cs_gpio": 4, "use_index": False}
    cli.ok("profile_set", data=p)
    diff = cli.wait_job(cli.confirmed("job_start", kind="profile_diff", params={"axis": 0})["id"])
    assert any(r["change"] for r in diff["result"]["rows"])
    job = cli.wait_job(cli.confirmed("job_start", kind="apply_profile", params={"axis": 0})["id"])
    assert job["state"] == "done", job
    vals = cli.ok("read", paths=["axis0.encoder.config.abs_spi_cs_gpio_pin", "axis0.encoder.config.cpr", "config.dc_bus_overvoltage_trip_level"])
    assert vals["axis0.encoder.config.abs_spi_cs_gpio_pin"] == 4 and vals["axis0.encoder.config.cpr"] == 16384
    time.sleep(0.3)
    health = cli.wait_job(cli.ok("job_start", kind="health", params={"axis": 0})["id"])
    assert health["state"] == "done", health
    statuses = {c["id"]: c["status"] for c in health["result"]["checks"]}
    assert statuses["enc_spi"] == "pass" and statuses["errors"] == "pass", statuses
    cal = cli.wait_job(cli.confirmed("job_start", kind="calibrate", params={"axis": 0, "kind": "full"})["id"])
    assert cal["state"] == "done" and cal["result"]["ok"], cal
    # closed loop, move, then disarm
    cli.ok("write", path="axis0.controller.config.control_mode", value=3)
    cli.confirmed("write", path="axis0.requested_state", value=8)
    time.sleep(0.3)
    sp = cli.ok("setpoint", axis=0, kind="pos", value=500.0)
    assert sp["warning"] and sp["value"] > 0  # clamped to profile
    cli.ok("setpoint", axis=0, kind="pos", value=0.2)
    time.sleep(1.0)
    pos = cli.ok("read", paths=["axis0.encoder.pos_estimate"])["axis0.encoder.pos_estimate"]
    assert abs(pos - 0.2) < 0.1, pos
    cli.ok("disarm", reason="test")
    time.sleep(0.3)
    assert cli.ok("read", paths=["axis0.current_state"])["axis0.current_state"] == 1


def test_closed_loop_entry_drops_stale_setpoints(cli):
    cli.ok("write", path="axis0.controller.input_vel", value=1.5)
    cli.ok("write", path="axis0.controller.input_torque", value=0.3)
    cli.confirmed("write", path="axis0.requested_state", value=8)
    vals = cli.ok("read", paths=["axis0.controller.input_vel", "axis0.controller.input_torque", "axis0.controller.vel_integrator_torque"])
    assert all(v == 0.0 for v in vals.values()), vals
    cli.ok("disarm", reason="test")
    time.sleep(0.3)


def test_abz_index_search_then_offset_and_cpr_check(cli):
    p = cli.ok("profile_get")
    p["encoder"] = {"mode": "INCREMENTAL", "cpr": 4000, "cs_gpio": 4, "use_index": True}
    cli.ok("profile_set", data=p)
    cli.ok("clear_errors", axis=0)
    cal = cli.wait_job(cli.confirmed("job_start", kind="calibrate", params={"axis": 0, "kind": "encoder"})["id"])
    assert cal["state"] == "done" and cal["result"]["ok"], cal
    assert any(c["id"] == "index" and c["ok"] for c in cal["result"]["checks"])
    assert any("index search (state 6)" in log["msg"] for log in cal["logs"])
    spin = cli.wait_job(cli.confirmed("job_start", kind="open_loop", params={"axis": 0, "current_a": 3.0, "vel_turns_s": 0.5, "turns": 1.0})["id"])
    assert spin["state"] == "done", spin
    assert abs(spin["result"]["counts_per_turn"] - 4000) < 200, spin["result"]


def test_position_window_follows_zero_and_mode_switch_is_bumpless(cli):
    cli.ok("clear_errors", axis=0)
    cli.ok("write", path="axis0.controller.config.control_mode", value=1)
    cli.confirmed("write", path="axis0.requested_state", value=8)
    time.sleep(0.3)
    # an axis far outside its window must be refused, not dragged back across the range
    cli.ok("set_origin", axis=0, value=1000.0)
    res = cli.rpc("setpoint", axis=0, kind="pos", value=1000.0)
    assert not res["ok"] and "outside the position window" in res["error"], res
    cli.ok("set_origin", axis=0)
    cli.ok("write", path="axis0.controller.config.control_mode", value=3)
    vals = cli.ok("read", paths=["axis0.controller.input_pos", "axis0.encoder.pos_estimate"])
    assert abs(vals["axis0.controller.input_pos"] - vals["axis0.encoder.pos_estimate"]) < 0.05, vals
    cli.ok("setpoint", axis=0, kind="pos", value=vals["axis0.encoder.pos_estimate"] + 0.1)
    cli.ok("disarm", reason="test")
    time.sleep(0.3)


def test_push_test_aborts_without_contact(cli):
    j = cli.wait_job(cli.confirmed("job_start", kind="push_test", params={
        "axis": 0, "currents": [1.0], "approach_deg_s": 30, "max_travel_deg": 5, "ramp_s": 0.2})["id"])
    assert j["state"] == "failed" and "no contact" in j["error"], j
    assert cli.ok("read", paths=["axis0.current_state"])["axis0.current_state"] == 1


def test_step_response_job(cli):
    j = cli.wait_job(cli.confirmed("job_start", kind="step_response", params={"axis": 0, "mode": "position", "amplitude": 0.1, "hold_s": 0.8})["id"])
    assert j["state"] == "done", j
    m = j["result"]["metrics"]
    assert m["rise_s"] is not None and j["result"]["samples"] > 50


def test_open_loop_job(cli):
    j = cli.wait_job(cli.confirmed("job_start", kind="open_loop", params={"axis": 0, "current_a": 3.0, "vel_turns_s": 0.5, "turns": 0.5})["id"])
    assert j["state"] == "done" and j["result"]["ok"], j
    assert j["result"]["iq_peak"] > 1.0


def test_save_requires_confirm_and_reconnects(cli):
    res = cli.rpc("call", path="save_configuration", args=[])
    assert not res["ok"] and res["code"] == "confirm"
    cli.confirmed("call", path="save_configuration", args=[])
    t0 = time.time()
    seen_down = False
    while time.time() - t0 < 10:
        st = cli.ok("hello")["status"]["device"]
        seen_down |= not st["connected"]
        if seen_down and st["connected"]:
            break
        time.sleep(0.2)
    assert seen_down and st["connected"]


def test_backup_and_recording(cli):
    b = cli.ok("backup_save", name="pytest")
    assert b["count"] > 50
    cli.ok("rec_start", name="pytest", paths=["axis0.encoder.shadow_count"])
    time.sleep(0.6)
    rec = cli.ok("rec_stop")
    assert rec["samples"] > 10
    data = cli.ok("rec_load", id=rec["id"])
    assert "axis0.encoder.shadow_count" in data["cols"]


def test_audit_has_writes(cli):
    rows = cli.ok("audit", limit=50)
    assert any(r["kind"] == "write" for r in rows)
