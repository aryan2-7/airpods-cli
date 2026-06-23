"""
Bluetooth / osascript bridge — Phase 4: real implementation.

All device detection and mode switching goes through osascript / AppleScript.
Works on macOS 13 (Ventura) and later with AirPods Pro or AirPods Max.
"""

from __future__ import annotations

import re

from airpods_cli import config
from airpods_cli.utils import run_osascript

_MODE_TO_INT: dict[str, int] = {
    "off":          1,
    "anc":          2,
    "transparency": 3,
    "adaptive":     4,
}
_INT_TO_MODE: dict[int, str] = {v: k for k, v in _MODE_TO_INT.items()}

_SUPPORTED_MODELS = (
    "airpods pro",
    "airpods max",
    "airpods (3rd generation)",
)


class AirPodsDevice:
    """Represents a connected AirPods device."""

    def __init__(
        self,
        name: str,
        model: str,
        current_mode: str,
        battery: dict | None = None,
    ):
        self.name = name
        self.model = model
        self.current_mode = current_mode
        self.battery = battery or {}

    def supports_modes(self) -> bool:
        return any(m in self.model.lower() for m in _SUPPORTED_MODELS)

    def __repr__(self) -> str:
        return f"AirPodsDevice(name={self.name!r}, mode={self.current_mode!r})"


def _get_bluetooth_device_names() -> list[str]:
    script = """
        set deviceNames to {}
        tell application "System Preferences"
        end tell
        do shell script "system_profiler SPBluetoothDataType 2>/dev/null | grep -A2 'Connected: Yes' | grep -v 'Connected' | grep -v '--' | awk -F: '{print $1}' | sed 's/^[ \\t]*//'"
    """
    output, code = run_osascript(script)
    if code != 0 or not output:
        return []
    return [line.strip() for line in output.splitlines() if line.strip()]


def _get_device_model(device_name: str) -> str:
    script = f"""
        do shell script "system_profiler SPBluetoothDataType 2>/dev/null | grep -A10 '{device_name}' | grep 'Minor Type' | head -1 | awk -F: '{{print $2}}' | sed 's/^[ \\t]*//'"
    """
    output, code = run_osascript(script)
    if code == 0 and output:
        return output.strip()

    name_lower = device_name.lower()
    if "pro" in name_lower:
        return "AirPods Pro"
    if "max" in name_lower:
        return "AirPods Max"
    if "airpods" in name_lower:
        return "AirPods"
    return device_name


def _get_noise_control_mode(device_name: str) -> str:
    script = f"""
        do shell script "defaults read com.apple.airpods 2>/dev/null | grep -A5 '{device_name}' | grep NoiseControlMode | head -1 | awk '{{print $3}}' | tr -d ';'"
    """
    output, code = run_osascript(script)

    if code == 0 and output.strip().isdigit():
        mode_int = int(output.strip())
        return _INT_TO_MODE.get(mode_int, "off")

    script2 = f"""
        do shell script "plutil -p ~/Library/Preferences/com.apple.airpods.plist 2>/dev/null | grep -A3 '{device_name}' | grep NoiseControlMode | awk '{{print $3}}'"
    """
    output2, code2 = run_osascript(script2)
    if code2 == 0 and output2.strip().isdigit():
        mode_int = int(output2.strip())
        return _INT_TO_MODE.get(mode_int, "off")

    return "off"


def _get_battery(device_name: str) -> dict:
    script = f"""
        do shell script "system_profiler SPBluetoothDataType 2>/dev/null | grep -A20 '{device_name}'"
    """
    output, code = run_osascript(script)
    if code != 0 or not output:
        return {}

    battery: dict[str, int] = {}

    left_match  = re.search(r"Left:\s*(\d+)%",  output, re.IGNORECASE)
    right_match = re.search(r"Right:\s*(\d+)%", output, re.IGNORECASE)
    case_match  = re.search(r"Case:\s*(\d+)%",  output, re.IGNORECASE)

    if left_match:
        battery["left"]  = int(left_match.group(1))
    if right_match:
        battery["right"] = int(right_match.group(1))
    if case_match:
        battery["case"]  = int(case_match.group(1))

    return battery


def _set_noise_control_mode(device_name: str, mode_key: str) -> bool:
    mode_int = _MODE_TO_INT.get(mode_key)
    if mode_int is None:
        return False

    write_script = f"""
        do shell script "defaults write com.apple.airpods \\\"{device_name}\\\" -dict-add NoiseControlMode -int {mode_int} && killall -HUP cfprefsd"
    """
    _, code = run_osascript(write_script)
    if code == 0:
        return True

    return False


def get_connected_airpods() -> list[AirPodsDevice]:
    script = """
        do shell script "system_profiler SPBluetoothDataType 2>/dev/null"
    """
    output, code = run_osascript(script)
    if code != 0 or not output:
        return []

    devices: list[AirPodsDevice] = []
    current_name: str | None = None
    connected = False

    for line in output.splitlines():
        stripped = line.strip()

        if re.match(r"^\s{6,10}\S.*:$", line) and not stripped.startswith("Address") \
                and not stripped.startswith("Battery") and not stripped.startswith("Minor"):
            if current_name and connected and "airpods" in current_name.lower():
                model   = _get_device_model(current_name)
                mode    = _get_noise_control_mode(current_name)
                battery = _get_battery(current_name)
                devices.append(AirPodsDevice(
                    name=current_name,
                    model=model,
                    current_mode=mode,
                    battery=battery,
                ))

            current_name = stripped.rstrip(":")
            connected = False

        elif stripped == "Connected: Yes":
            connected = True
        elif stripped == "Connected: No":
            connected = False

    if current_name and connected and "airpods" in current_name.lower():
        model   = _get_device_model(current_name)
        mode    = _get_noise_control_mode(current_name)
        battery = _get_battery(current_name)
        devices.append(AirPodsDevice(
            name=current_name,
            model=model,
            current_mode=mode,
            battery=battery,
        ))

    return devices


def get_current_mode(device: AirPodsDevice) -> str:
    return _get_noise_control_mode(device.name)


def set_mode(device: AirPodsDevice, mode_key: str) -> bool:
    ok = _set_noise_control_mode(device.name, mode_key)
    if ok:
        device.current_mode = mode_key
    return ok


def get_default_device() -> AirPodsDevice | None:
    devices = get_connected_airpods()
    if not devices:
        return None

    default_name = config.get("default_device")
    if default_name:
        match = next(
            (d for d in devices if d.name.lower() == default_name.lower()),
            None,
        )
        if match:
            return match

    return devices[0]
