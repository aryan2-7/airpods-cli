"""
Tests for bluetooth.py — real system_profiler output format.
All osascript calls are mocked so tests run without a Mac / AirPods.
"""

from unittest.mock import patch

import pytest

from airpods_cli.bluetooth import (
    AirPodsDevice,
    _INT_TO_MODE,
    _MODE_TO_INT,
    _get_noise_control_mode,
    _merge_device,
    _parse_pct,
    _parse_profiler_output,
    _set_noise_control_mode,
    get_connected_airpods,
    get_current_mode,
    get_default_device,
    set_mode,
)

# ── Real system_profiler output (matches meow's machine exactly) ───────────────
REAL_PROFILER = """
Bluetooth:

    Bluetooth Controller:
          Address: AC:07:75:0D:42:AC
          State: On

      Connected:

          meow's AirPods Pro:
              Address: E5:D4:4A:4D:2D:CA
              Case Battery Level: 42%
              Firmware Version: 0.11.81
              RSSI: -37
              Services: 0x400000 < BLE >

          meow's AirPods Pro:
              Address: 50:F3:51:C8:23:7E
              Vendor ID: 0x004C
              Product ID: 0x2024
              Case Battery Level: 42%
              Left Battery Level: 100%
              Right Battery Level: 100%
              Minor Type: Headphones
              RSSI: -64
              Services: 0x980019 < HFP AVRCP A2DP AACP GATT ACL >

      Not Connected:

          meow:
              Address: 64:48:42:3A:DA:A8
              RSSI: -65

          Monkey:
              Address: 41:42:D6:17:AB:A2
              Minor Type: Headset
"""


# ── _parse_pct ─────────────────────────────────────────────────────────────────

def test_parse_pct_valid():
    assert _parse_pct("42%") == 42
    assert _parse_pct("100%") == 100
    assert _parse_pct("0%") == 0

def test_parse_pct_with_whitespace():
    assert _parse_pct("  82%  ") == 82

def test_parse_pct_empty_returns_none():
    assert _parse_pct("") is None

def test_parse_pct_non_pct_returns_none():
    assert _parse_pct("Connected") is None


# ── _parse_profiler_output ─────────────────────────────────────────────────────

def test_parse_profiler_finds_connected_airpods():
    entries = _parse_profiler_output(REAL_PROFILER)
    names = [e["name"] for e in entries]
    assert "meow's AirPods Pro" in names

def test_parse_profiler_only_connected():
    entries = _parse_profiler_output(REAL_PROFILER)
    for e in entries:
        assert e["connected"] is True

def test_parse_profiler_excludes_non_airpods():
    entries = _parse_profiler_output(REAL_PROFILER)
    names = [e["name"] for e in entries]
    assert "meow" not in names
    assert "Monkey" not in names

def test_parse_profiler_deduplicates_to_richer_entry():
    """The BLE-only entry and the full audio entry should merge to one,
    keeping the entry with Left/Right battery data."""
    entries = _parse_profiler_output(REAL_PROFILER)
    airpods_entries = [e for e in entries if "AirPods Pro" in e["name"]]
    assert len(airpods_entries) == 1
    entry = airpods_entries[0]
    assert entry["left"] == 100
    assert entry["right"] == 100

def test_parse_profiler_reads_battery():
    entries = _parse_profiler_output(REAL_PROFILER)
    entry = next(e for e in entries if "AirPods" in e["name"])
    assert entry["case"] == 42

def test_parse_profiler_empty_string():
    assert _parse_profiler_output("") == []


# ── _merge_device ──────────────────────────────────────────────────────────────

def test_merge_device_first_entry_stored():
    store = {}
    _merge_device(store, "Test", {"left": None, "right": None, "case": 42, "services": "", "minor": ""}, True)
    assert "Test" in store

def test_merge_device_prefers_entry_with_left_battery():
    store = {}
    ble_block  = {"Services": "0x400000 < BLE >"}
    full_block = {"Left Battery Level": "100%", "Right Battery Level": "95%",
                  "Case Battery Level": "42%", "Services": "0x980019 < HFP AVRCP >",
                  "Minor Type": "Headphones"}
    _merge_device(store, "Test", ble_block,  True)
    _merge_device(store, "Test", full_block, True)
    assert store["Test"]["left"] == 100

def test_merge_device_prefers_hfp_services():
    store = {}
    _merge_device(store, "Test", {"Services": "0x400000 < BLE >"}, True)
    _merge_device(store, "Test", {"Services": "0x980019 < HFP AVRCP >"}, True)
    assert "HFP" in store["Test"]["services"]


# ── _get_noise_control_mode ────────────────────────────────────────────────────

def test_get_noise_control_mode_anc():
    with patch("airpods_cli.bluetooth.run_osascript", return_value=("2", 0)):
        assert _get_noise_control_mode("Test") == "anc"

def test_get_noise_control_mode_transparency():
    with patch("airpods_cli.bluetooth.run_osascript", return_value=("3", 0)):
        assert _get_noise_control_mode("Test") == "transparency"

def test_get_noise_control_mode_adaptive():
    with patch("airpods_cli.bluetooth.run_osascript", return_value=("4", 0)):
        assert _get_noise_control_mode("Test") == "adaptive"

def test_get_noise_control_mode_off():
    with patch("airpods_cli.bluetooth.run_osascript", return_value=("1", 0)):
        assert _get_noise_control_mode("Test") == "off"

def test_get_noise_control_mode_fallback_on_failure():
    with patch("airpods_cli.bluetooth.run_osascript", return_value=("", 1)):
        assert _get_noise_control_mode("Test") == "off"

def test_get_noise_control_mode_unknown_int():
    with patch("airpods_cli.bluetooth.run_osascript", return_value=("99", 0)):
        assert _get_noise_control_mode("Test") == "off"


# ── _set_noise_control_mode ────────────────────────────────────────────────────

def test_set_noise_control_mode_success():
    with patch("airpods_cli.bluetooth.run_osascript", return_value=("", 0)):
        assert _set_noise_control_mode("Test", "anc") is True

def test_set_noise_control_mode_failure():
    with patch("airpods_cli.bluetooth.run_osascript", return_value=("", 1)):
        assert _set_noise_control_mode("Test", "anc") is False

def test_set_noise_control_mode_invalid_key():
    assert _set_noise_control_mode("Test", "superanc") is False

def test_set_noise_control_mode_apostrophe_in_name():
    """Device names with apostrophes (meow's AirPods) must not break the shell command."""
    with patch("airpods_cli.bluetooth.run_osascript", return_value=("", 0)) as mock:
        _set_noise_control_mode("meow's AirPods Pro", "anc")
    # Should have been called — no exception from apostrophe escaping
    mock.assert_called_once()


# ── set_mode / get_current_mode (public) ───────────────────────────────────────

def test_set_mode_updates_device_on_success():
    device = AirPodsDevice("Test", "AirPods Pro", "off")
    with patch("airpods_cli.bluetooth._set_noise_control_mode", return_value=True):
        assert set_mode(device, "anc") is True
    assert device.current_mode == "anc"

def test_set_mode_does_not_update_on_failure():
    device = AirPodsDevice("Test", "AirPods Pro", "off")
    with patch("airpods_cli.bluetooth._set_noise_control_mode", return_value=False):
        assert set_mode(device, "anc") is False
    assert device.current_mode == "off"

def test_get_current_mode_queries_live():
    device = AirPodsDevice("Test", "AirPods Pro", "off")
    with patch("airpods_cli.bluetooth._get_noise_control_mode", return_value="transparency"):
        assert get_current_mode(device) == "transparency"


# ── get_connected_airpods ──────────────────────────────────────────────────────

def test_get_connected_airpods_finds_meow_airpods():
    with patch("airpods_cli.bluetooth.run_osascript") as mock:
        mock.side_effect = [
            (REAL_PROFILER, 0),   # get_connected_airpods scan
            ("2", 0),              # _get_noise_control_mode
        ]
        devices = get_connected_airpods()
    assert len(devices) == 1
    assert "AirPods Pro" in devices[0].name

def test_get_connected_airpods_battery_populated():
    with patch("airpods_cli.bluetooth.run_osascript") as mock:
        mock.side_effect = [
            (REAL_PROFILER, 0),
            ("2", 0),
        ]
        devices = get_connected_airpods()
    assert devices[0].battery.get("left") == 100
    assert devices[0].battery.get("right") == 100
    assert devices[0].battery.get("case") == 42

def test_get_connected_airpods_empty_on_failure():
    with patch("airpods_cli.bluetooth.run_osascript", return_value=("", 1)):
        assert get_connected_airpods() == []


# ── get_default_device ─────────────────────────────────────────────────────────

def test_get_default_device_none_when_empty():
    with patch("airpods_cli.bluetooth.get_connected_airpods", return_value=[]):
        assert get_default_device() is None

def test_get_default_device_returns_first_without_config():
    d = AirPodsDevice("Test", "AirPods Pro", "anc")
    with patch("airpods_cli.bluetooth.get_connected_airpods", return_value=[d]), \
         patch("airpods_cli.config.get", return_value=None):
        assert get_default_device() is d

def test_get_default_device_matches_config():
    d1 = AirPodsDevice("Work AirPods", "AirPods Pro", "anc")
    d2 = AirPodsDevice("meow's AirPods Pro", "AirPods Pro", "off")
    with patch("airpods_cli.bluetooth.get_connected_airpods", return_value=[d1, d2]), \
         patch("airpods_cli.config.get", return_value="meow's AirPods Pro"):
        assert get_default_device() is d2

def test_get_default_device_falls_back_when_config_missing():
    d = AirPodsDevice("Work AirPods", "AirPods Pro", "anc")
    with patch("airpods_cli.bluetooth.get_connected_airpods", return_value=[d]), \
         patch("airpods_cli.config.get", return_value="Not Connected AirPods"):
        assert get_default_device() is d


# ── Mode map integrity ─────────────────────────────────────────────────────────

def test_mode_to_int_values():
    assert _MODE_TO_INT == {"off": 1, "anc": 2, "transparency": 3, "adaptive": 4}

def test_int_to_mode_roundtrip():
    for key, val in _MODE_TO_INT.items():
        assert _INT_TO_MODE[val] == key


# ── AirPodsDevice ──────────────────────────────────────────────────────────────

def test_supports_modes_pro():
    assert AirPodsDevice("T", "AirPods Pro (2nd generation)", "anc").supports_modes()

def test_supports_modes_max():
    assert AirPodsDevice("T", "AirPods Max", "anc").supports_modes()

def test_supports_modes_gen2_false():
    assert not AirPodsDevice("T", "AirPods (2nd generation)", "off").supports_modes()