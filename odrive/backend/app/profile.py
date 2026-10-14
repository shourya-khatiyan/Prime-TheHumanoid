"""Actuator profile: the physical limits and parameters of the connected actuator."""

from __future__ import annotations

import copy
from typing import Any

import yaml

from .paths import PROFILES_DIR, USER_PROFILE

DEFAULT_PROFILE = PROFILES_DIR / "vayn_shoulder.yaml"


class Profile:
    """Wraps the profile yaml and exposes derived values (Kt, torque limit, unit conversion)."""

    def __init__(self, data: dict):
        self.data = data

    def get(self, dotted: str, default: Any = None) -> Any:
        """Read a nested value such as 'motor.kv'."""
        cur: Any = self.data
        for part in dotted.split("."):
            if not isinstance(cur, dict) or part not in cur:
                return default
            cur = cur[part]
        return cur

    @property
    def axis(self) -> int:
        """Axis index the actuator is wired to."""
        return int(self.get("axis", 0))

    @property
    def kt(self) -> float:
        """Motor torque constant in Nm/A, from Kt = 8.27 / KV."""
        return 8.27 / float(self.get("motor.kv", 90))

    @property
    def gear_ratio(self) -> float:
        """Total reduction from motor to joint output."""
        return float(self.get("gear.ratio", 1))

    @property
    def torque_max_nm(self) -> float:
        """Motor-side torque limit derived from the peak current."""
        return self.kt * float(self.get("motor.current_peak_a", 10))

    def to_json(self) -> dict:
        """Return the profile plus derived values for the frontend."""
        out = copy.deepcopy(self.data)
        out["derived"] = {
            "kt_nm_per_a": self.kt,
            "torque_max_nm": self.torque_max_nm,
            "joint_torque_peak_nm": self.torque_max_nm * self.gear_ratio * float(self.get("gear.efficiency", 1)),
            "joint_vel_max_deg_s": float(self.get("limits.vel_max_turns_s", 0)) * 360.0 / self.gear_ratio,
        }
        return out


def load_profile() -> Profile:
    """Load the user profile if saved, otherwise the bundled default."""
    path = USER_PROFILE if USER_PROFILE.exists() else DEFAULT_PROFILE
    return Profile(yaml.safe_load(path.read_text(encoding="utf-8")))


def save_profile(data: dict) -> Profile:
    """Persist an edited profile to the user data folder.

    Args:
        data: full profile dict (the 'derived' block is ignored).
    Returns:
        the new Profile.
    """
    clean = {k: v for k, v in data.items() if k != "derived"}
    USER_PROFILE.parent.mkdir(parents=True, exist_ok=True)
    USER_PROFILE.write_text(yaml.safe_dump(clean, sort_keys=False), encoding="utf-8")
    return Profile(clean)
