"""Tests for config read/write logic."""

from unittest.mock import patch

from airpods_cli.config import DEFAULT_CONFIG, load_config, save_config, set_value


def test_load_config_returns_defaults_when_no_file(tmp_path):
    """If ~/.airpods.json doesn't exist, we get default values back."""
    fake_config_path = tmp_path / ".airpods.json"
    with patch("airpods_cli.config.CONFIG_PATH", fake_config_path):
        config = load_config()
    assert config == DEFAULT_CONFIG


def test_save_and_load_roundtrip(tmp_path):
    """Values saved to disk come back correctly when loaded."""
    fake_config_path = tmp_path / ".airpods.json"
    with patch("airpods_cli.config.CONFIG_PATH", fake_config_path):
        save_config({"default_device": "Aryan's AirPods Pro", "toggle_order": ["anc", "off"]})
        config = load_config()
    assert config["default_device"] == "Aryan's AirPods Pro"


def test_set_value_updates_single_key(tmp_path):
    """set_value() only changes the key it's given."""
    fake_config_path = tmp_path / ".airpods.json"
    with patch("airpods_cli.config.CONFIG_PATH", fake_config_path):
        set_value("default_device", "My AirPods")
        config = load_config()
    assert config["default_device"] == "My AirPods"
    assert config["toggle_order"] == DEFAULT_CONFIG["toggle_order"]
