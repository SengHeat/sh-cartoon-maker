MOVEMENT_DEFAULTS: dict[str, tuple[float, float, float]] = {
    "static": (0.0, 0.0, 0.0),
    "slow_push": (0.0, 0.0, 0.10),
    "slow_pull": (0.0, 0.0, -0.08),
    "pan_left": (-0.10, 0.0, 0.0),
    "pan_right": (0.10, 0.0, 0.0),
    "pan_up": (0.0, -0.10, 0.0),
    "pan_down": (0.0, 0.10, 0.0),
    "drift_left": (-0.04, 0.0, 0.0),
    "drift_right": (0.04, 0.0, 0.0),
    "handheld_subtle": (0.0, 0.0, 0.0),
}

