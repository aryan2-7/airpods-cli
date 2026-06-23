"""Tests for bluetooth.py — Phase 4.

All osascript calls are mocked so tests run without a Mac / AirPods.
"""

from unittest.mock import patch

from airpods_cli.bluetooth import (
    _INT_TO_MODE,
    _MODE_TO_INT,
    AirPodsDevice,
    _get_battery,
    _get_noise_control_mode,
    _set_noise_control_mode,
    get_connected_airpods,
    get_current_mode,
    get_default_device,
    set_mode,
)


def test_device_supports_modes_pro():
    d = AirPodsDevice("Test", "AirPods Pro (2nd generation)", "anc")
    assert d.supports_modes() is True


def test_device_supports_modes_max():
    d = AirPodsDevice("Test", "AirPods Max", "anc")
    assert d.supports_modes() is True


def test_device_does_not_support_modes_gen2():
    d = AirPodsDevice("Test", "AirPods (2nd generation)", "off")
    assert d.supports_modes() is False


def test_mode_to_int_complete():
    assert _MODE_TO_INT["anc"]          == 2
    assert _MODE_TO_INT["transparency"] == 3
    assert _MODE_TO_INT["adaptive"]     == 4
    assert _MODE_TO_INT["off"]          == 1


def test_int_to_mode_roundtrip():
    for key, val in _MODE_TO_INT.items():
        assert _INT_TO_MODE[val] == key


def test_get_noise_control_mode_anc():
    with patch("airpods_cli.bluetooth.run_osascript", return_value=("2", 0)):
        result = _get_noise_control_mode("Test AirPods Pro")
    assert result == "anc"


def test_get_noise_control_mode_transparency():
    with patch("airpods_cli.bluetooth.run_osascript", return_value=("3", 0)):
        result = _get_noise_control_mode("Test AirPods Pro")
    assert result == "transparency"


def test_get_noise_control_mode_off():
    with patch("airpods_cli.bluetooth.run_osascript", return_value=("1", 0)):
        result = _get_noise_control_mode("Test AirPods Pro")
    assert result == "off"


def test_get_noise_control_mode_fallback_on_failure():
    with patch("airpods_cli.bluetooth.run_osascript", return_value=("", 1)):
        result = _get_noise_control_mode("Test AirPods Pro")
    assert result == "off"


def test_get_noise_control_mode_unknown_int():
    with patch("airpods_cli.bluetooth.run_osascript", return_value=("99", 0)):
        result = _get_noise_control_mode("Test AirPods Pro")
    assert result == "off"


SAMPLE_PROFILER_OUTPUT = """
    Aryan's AirPods Pro:
      Address: AA:BB:CC:DD:EE:FF
      Battery Level:
        Left: 82%
        Right: 79%
        Case: 100%
      Connected: Yes
"""


def test_get_battery_parses_all_three():
    with patch("airpods_cli.bluetooth.run_osascript", return_value=(SAMPLE_PROFILER_OUTPUT, 0)):
        result = _get_battery("Aryan's AirPods Pro")
    assert result == {"left": 82, "right": 79, "case": 100}


def test_get_battery_partial_output():
    partial = "Left: 50%\nRight: 60%"
    with patch("airpods_cli.bluetooth.run_osascript", return_value=(partial, 0)):
        result = _get_battery("Test")
    assert result["left"] == 50
    assert result["right"] == 60
    assert "case" not in result


def test_get_battery_returns_empty_on_failure():
    with patch("airpods_cli.bluetooth.run_osascript", return_value=("", 1)):
        result = _get_battery("Test")
    assert result == {}


def test_set_noise_control_mode_success():
    with patch("airpods_cli.bluetooth.run_osascript", return_value=("", 0)):
        ok = _set_noise_control_mode("Test AirPods Pro", "anc")
    assert ok is True


def test_set_noise_control_mode_failure_falls_back():
    with patch("airpods_cli.bluetooth.run_osascript", return_value=("", 1)):
        ok = _set_noise_control_mode("Test AirPods Pro", "anc")
    assert ok is False


def test_set_noise_control_mode_invalid_key():
    ok = _set_noise_control_mode("Test", "superanc")
    assert ok is False


def test_set_mode_updates_device_object_on_success():
    device = AirPodsDevice("Test", "AirPods Pro", "off")
    with patch("airpods_cli.bluetooth._set_noise_control_mode", return_value=True):
        result = set_mode(device, "anc")
    assert result is True
    assert device.current_mode == "anc"


def test_set_mode_does_not_update_object_on_failure():
    device = AirPodsDevice("Test", "AirPods Pro", "off")
    with patch("airpods_cli.bluetooth._set_noise_control_mode", return_value=False):
        result = set_mode(device, "anc")
    assert result is False
    assert device.current_mode == "off"


def test_get_current_mode_live_query():
    device = AirPodsDevice("Test AirPods", "AirPods Pro", "off")
    with patch("airpods_cli.bluetooth._get_noise_control_mode", return_value="transparency"):
        result = get_current_mode(device)
    assert result == "transparency"


FULL_PROFILER_OUTPUT = """
Bluetooth:

    Connected:

        Aryan's AirPods Pro:
          Address: AA:BB:CC:DD:EE:FF
          Major Type: Audio/Video
          Minor Type: Headphones
          Connected: Yes
          Paired: Yes
          Handsfree Profile (HFP): Supported
"""


def test_get_connected_airpods_returns_list():
    with patch("airpods_cli.bluetooth.run_osascript") as mock_osa:
        mock_osa.side_effect = [
            (FULL_PROFILER_OUTPUT, 0),
            ("Headphones", 0),
            ("2", 0),
            (SAMPLE_PROFILER_OUTPUT, 0),
        ]
        devices = get_connected_airpods()

    assert isinstance(devices, list)


def test_get_connected_airpods_empty_on_no_output():
    with patch("airpods_cli.bluetooth.run_osascript", return_value=("", 1)):
        devices = get_connected_airpods()
    assert devices == []


def test_get_default_device_returns_none_when_nothing_connected():
    with patch("airpods_cli.bluetooth.get_connected_airpods", return_value=[]):
        result = get_default_device()
    assert result is None


def test_get_default_device_returns_first_when_no_config():
    fake = AirPodsDevice("My AirPods", "AirPods Pro", "anc")
    with patch("airpods_cli.bluetooth.get_connected_airpods", return_value=[fake]), \
         patch("airpods_cli.config.get", return_value=None):
        result = get_default_device()
    assert result is fake


def test_get_default_device_matches_config_name():
    d1 = AirPodsDevice("Work AirPods", "AirPods Pro", "anc")
    d2 = AirPodsDevice("Home AirPods Max", "AirPods Max", "off")
    with patch("airpods_cli.bluetooth.get_connected_airpods", return_value=[d1, d2]), \
         patch("airpods_cli.config.get", return_value="Home AirPods Max"):
        result = get_default_device()
    assert result is d2


def test_get_default_device_falls_back_to_first_if_config_not_connected():
    d1 = AirPodsDevice("Work AirPods", "AirPods Pro", "anc")
    with patch("airpods_cli.bluetooth.get_connected_airpods", return_value=[d1]), \
         patch("airpods_cli.config.get", return_value="Home AirPods Max"):
        result = get_default_device()
    assert result is d1
