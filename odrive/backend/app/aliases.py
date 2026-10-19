"""Stable logical names for properties whose paths differ between firmware 0.5.1 and 0.5.6.

The backend and frontend refer to e.g. 'fet_temp' instead of a raw path; the
alias resolves to whichever candidate path exists on the connected device.
"""

from __future__ import annotations

GLOBAL = {
    "vbus": ["vbus_voltage"],
    "ibus": ["ibus"],
    "clock": ["n_evt_control_loop", "axis0.loop_counter"],
    "sys_error": ["error"],
    "brake_armed": ["brake_resistor_armed"],
    "brake_saturated": ["brake_resistor_saturated"],
    "can_baud": ["can.config.baud_rate"],
    "uptime": ["system_stats.uptime"],
}

AXIS = {
    "state": ["current_state"],
    "req_state": ["requested_state"],
    "error": ["error"],
    "motor_error": ["motor.error"],
    "enc_error": ["encoder.error"],
    "ctrl_error": ["controller.error"],
    "sens_error": ["sensorless_estimator.error"],
    "fet_error": ["motor.fet_thermistor.error", "fet_thermistor.error"],
    "drv_fault": ["last_drv_fault", "motor.gate_driver.drv_fault"],
    "iq": ["motor.current_control.Iq_measured"],
    "iq_set": ["motor.current_control.Iq_setpoint"],
    "id": ["motor.current_control.Id_measured"],
    "ph_b": ["motor.current_meas_phB"],
    "ph_c": ["motor.current_meas_phC"],
    "pos": ["encoder.pos_estimate"],
    "vel": ["encoder.vel_estimate"],
    "pos_abs": ["encoder.pos_abs"],
    "shadow": ["encoder.shadow_count"],
    "count_in_cpr": ["encoder.count_in_cpr"],
    "spi_err": ["encoder.spi_error_rate"],
    "enc_ready": ["encoder.is_ready"],
    "enc_offset": ["encoder.config.phase_offset", "encoder.config.offset"],
    "enc_mode": ["encoder.config.mode"],
    "enc_cpr": ["encoder.config.cpr"],
    "enc_cs": ["encoder.config.abs_spi_cs_gpio_pin"],
    "enc_use_index": ["encoder.config.use_index"],
    "enc_index": ["encoder.index_found"],
    "hall_state": ["encoder.hall_state"],
    "enc_precal": ["encoder.config.pre_calibrated"],
    "fet_temp": ["motor.fet_thermistor.temperature", "fet_thermistor.temperature"],
    "motor_temp": ["motor.motor_thermistor.temperature", "motor_thermistor.temperature"],
    "motor_temp_enabled": ["motor.motor_thermistor.config.enabled", "motor_thermistor.config.enabled"],
    "motor_cal": ["motor.is_calibrated"],
    "armed": ["motor.is_armed", "motor.armed_state"],
    "phase_r": ["motor.config.phase_resistance"],
    "phase_l": ["motor.config.phase_inductance"],
    "pole_pairs": ["motor.config.pole_pairs"],
    "kt": ["motor.config.torque_constant"],
    "current_lim": ["motor.config.current_lim"],
    "cal_current": ["motor.config.calibration_current"],
    "r_cal_vmax": ["motor.config.resistance_calib_max_voltage"],
    "motor_precal": ["motor.config.pre_calibrated"],
    "effective_current_lim": ["motor.effective_current_lim"],
    "ctrl_mode": ["controller.config.control_mode"],
    "input_mode": ["controller.config.input_mode"],
    "input_pos": ["controller.input_pos"],
    "input_vel": ["controller.input_vel"],
    "input_torque": ["controller.input_torque"],
    "pos_set": ["controller.pos_setpoint"],
    "vel_set": ["controller.vel_setpoint"],
    "torque_set": ["controller.torque_setpoint"],
    "vel_integ": ["controller.vel_integrator_torque"],
    "pos_gain": ["controller.config.pos_gain"],
    "vel_gain": ["controller.config.vel_gain"],
    "vel_int_gain": ["controller.config.vel_integrator_gain"],
    "vel_limit": ["controller.config.vel_limit"],
    "torque_mode_vel_limit": ["controller.config.enable_torque_mode_vel_limit", "controller.config.enable_current_mode_vel_limit"],
    "wd_enable": ["config.enable_watchdog"],
    "wd_timeout": ["config.watchdog_timeout"],
    "can_node": ["config.can.node_id", "config.can_node_id"],
    "clear_errors": ["clear_errors"],
    "watchdog_feed": ["watchdog_feed"],
}


def resolve_all(tree: dict[str, dict]) -> dict[str, str]:
    """Build the alias table for one device tree.

    Args:
        tree: {path: {kind, ...}} from the transport.
    Returns:
        {alias: path} where per-axis aliases look like 'fet_temp.0'. Aliases with
        no matching path are left out. 'clear_errors.N' falls back to the
        device-level clear_errors on 0.5.6.
    """
    out: dict[str, str] = {}
    for key, cands in GLOBAL.items():
        for c in cands:
            if c in tree:
                out[key] = c
                break
    for ax in (0, 1):
        for key, cands in AXIS.items():
            for c in cands:
                p = f"axis{ax}.{c}"
                if p in tree:
                    out[f"{key}.{ax}"] = p
                    break
        if f"clear_errors.{ax}" not in out and "clear_errors" in tree:
            out[f"clear_errors.{ax}"] = "clear_errors"
    return out
