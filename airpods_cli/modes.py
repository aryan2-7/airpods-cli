"""Mode constants, display names, numeric aliases, and toggle logic."""

from airpods_cli import config

MODES = {
    "anc":          "Noise Cancellation",
    "transparency": "Transparency",
    "adaptive":     "Adaptive Audio",
    "off":          "Off",
}

NUMERIC_ALIASES = {
    "0": "off",
    "1": "anc",
    "2": "transparency",
    "3": "adaptive",
}

ALL_VALID_INPUTS = set(MODES.keys()) | set(NUMERIC_ALIASES.keys()) | {"toggle"}


def resolve_mode(raw: str) -> str:
    lowered = raw.lower().strip()
    if lowered in MODES:
        return lowered
    if lowered in NUMERIC_ALIASES:
        return NUMERIC_ALIASES[lowered]
    valid = ", ".join(sorted(MODES.keys()) + sorted(NUMERIC_ALIASES.keys()))
    raise ValueError(f"Unknown mode '{raw}'. Valid options: {valid}")


def display_name(mode_key: str) -> str:
    return MODES.get(mode_key, mode_key)


def next_mode(current_key: str) -> str:
    order = config.get("toggle_order")
    if current_key not in order:
        return order[0]
    idx = order.index(current_key)
    return order[(idx + 1) % len(order)]
