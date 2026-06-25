"""Tests for CLI commands using Click's test runner."""

from unittest.mock import patch

from click.testing import CliRunner

from airpods_cli.bluetooth import AirPodsDevice
from airpods_cli.cli import cli

FAKE_DEVICE = AirPodsDevice(
    name="Test AirPods Pro",
    model="AirPods Pro (2nd generation)",
    current_mode="anc",
    battery={"left": 80, "right": 75, "case": 100},
)


def runner():
    return CliRunner()


def test_mode_anc_success():
    with patch("airpods_cli.bluetooth.get_default_device", return_value=FAKE_DEVICE), \
         patch("airpods_cli.bluetooth.set_mode", return_value=True):
        result = CliRunner().invoke(cli, ["mode", "anc"])
    assert result.exit_code == 0
    assert "Noise Cancellation" in result.output


def test_mode_numeric_alias():
    with patch("airpods_cli.bluetooth.get_default_device", return_value=FAKE_DEVICE), \
         patch("airpods_cli.bluetooth.set_mode", return_value=True):
        result = CliRunner().invoke(cli, ["mode", "2"])
    assert result.exit_code == 0
    assert "Transparency" in result.output


def test_mode_invalid_input():
    with patch("airpods_cli.bluetooth.get_default_device", return_value=FAKE_DEVICE):
        result = CliRunner().invoke(cli, ["mode", "superanc"])
    assert result.exit_code != 0


def test_mode_quiet_flag_suppresses_output():
    with patch("airpods_cli.bluetooth.get_default_device", return_value=FAKE_DEVICE), \
         patch("airpods_cli.bluetooth.set_mode", return_value=True):
        result = CliRunner().invoke(cli, ["mode", "anc", "--quiet"])
    assert result.exit_code == 0
    assert result.output.strip() == ""


def test_mode_no_device_connected():
    with patch("airpods_cli.bluetooth.get_default_device", return_value=None):
        result = CliRunner().invoke(cli, ["mode", "anc"])
    assert result.exit_code != 0


def test_mode_toggle_cycles():
    device = AirPodsDevice("Test", "AirPods Pro", current_mode="anc")
    with patch("airpods_cli.bluetooth.get_default_device", return_value=device), \
         patch("airpods_cli.bluetooth.get_current_mode", return_value="anc"), \
         patch("airpods_cli.bluetooth.set_mode", return_value=True):
        result = CliRunner().invoke(cli, ["mode", "toggle"])
    assert result.exit_code == 0
    assert "Transparency" in result.output


def test_status_shows_device_info():
    with patch("airpods_cli.bluetooth.get_default_device", return_value=FAKE_DEVICE), \
         patch("airpods_cli.bluetooth.get_current_mode", return_value="anc"):
        result = CliRunner().invoke(cli, ["status"])
    assert result.exit_code == 0
    assert "Test AirPods Pro" in result.output
    assert "Noise Cancellation" in result.output
    assert "80%" in result.output


def test_status_no_device():
    with patch("airpods_cli.bluetooth.get_default_device", return_value=None):
        result = CliRunner().invoke(cli, ["status"])
    assert result.exit_code != 0


def test_devices_lists_connected():
    with patch("airpods_cli.bluetooth.get_connected_airpods", return_value=[FAKE_DEVICE]), \
         patch("airpods_cli.bluetooth.get_current_mode", return_value="anc"):
        result = CliRunner().invoke(cli, ["devices"])
    assert result.exit_code == 0
    assert "Test AirPods Pro" in result.output
    assert "Found 1 device" in result.output


def test_devices_none_connected():
    with patch("airpods_cli.bluetooth.get_connected_airpods", return_value=[]):
        result = CliRunner().invoke(cli, ["devices"])
    assert result.exit_code == 0
    assert "No AirPods" in result.output


def test_config_show(tmp_path):
    with patch("airpods_cli.config.CONFIG_PATH", tmp_path / ".airpods.json"):
        result = CliRunner().invoke(cli, ["config", "--show"])
    assert result.exit_code == 0
    assert "Toggle order" in result.output


def test_config_reset(tmp_path):
    with patch("airpods_cli.config.CONFIG_PATH", tmp_path / ".airpods.json"):
        result = CliRunner().invoke(cli, ["config", "--reset"])
    assert result.exit_code == 0
    assert "reset" in result.output.lower()
