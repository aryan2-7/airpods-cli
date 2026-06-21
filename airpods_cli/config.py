"""Read and write persistent user config at ~/.airpods.json."""

import json
import os
from pathlib import Path

CONFIG_PATH = Path.home() / ".airpods.json"

DEFAULT_CONFIG = {
    "default_device": None,
    "toggle_order": ["anc", "transparency", "adaptive", "off"],
}


def load_config() -> dict:
    """Load config from disk. Returns defaults if file doesn't exist yet."""
    if not CONFIG_PATH.exists():
        return DEFAULT_CONFIG.copy()
    try:
        with open(CONFIG_PATH, "r") as f:
            data = json.load(f)
        return {**DEFAULT_CONFIG, **data}
    except (json.JSONDecodeError, OSError):
        return DEFAULT_CONFIG.copy()


def save_config(config: dict) -> None:
    """Write config dict to disk as JSON."""
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)


def get(key: str):
    """Get a single config value by key."""
    return load_config().get(key)


def set_value(key: str, value) -> None:
    """Set a single config value and save to disk."""
    config = load_config()
    config[key] = value
    save_config(config)


def reset() -> None:
    """Delete the config file and reset to defaults."""
    if CONFIG_PATH.exists():
        CONFIG_PATH.unlink()
