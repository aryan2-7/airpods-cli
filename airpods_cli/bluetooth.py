"""
Bluetooth / osascript bridge — Phase 4: real implementation.

Parses system_profiler SPBluetoothDataType output to find connected AirPods,
reads noise control mode from com.apple.airpods plist, and writes mode changes
back via defaults write + cfprefsd flush.
"""

from __future__ import annotations

import re

from airpods_cli import config
from airpods_cli.utils import run_osascript

# ── Mode maps ──────────────────────────────────────────────────────────────────
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


# ── Data shape ─────────────────────────────────────────────────────────────────

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


# ── system_profiler parser ─────────────────────────────────────────────────────

def _parse_profiler_output(output: str) -> list[dict]:
    """
    Parse system_profiler SPBluetoothDataType text output into a list of
    device dicts with keys: name, connected, services, battery, model.

    Handles the real macOS format where:
    - Devices are grouped under 'Connected:' / 'Not Connected:' section headers
    - Device names are indented with variable leading spaces and end with ':'
    - A device may appear twice (BLE-only case entry + full audio entry)
      We keep the entry with the most data (Left/Right battery, Services with HFP)
    """
    devices: dict[str, dict] = {}  # name → best entry so far

    in_connected_section = False
    current_name: str | None = None
    current_block: dict = {}

    # Determine indent level of section headers like "Connected:" and "Not Connected:"
    # Device names are indented one level deeper than those headers.
    # We use a flexible indent matcher instead of hard-coding spaces.

    for line in output.splitlines():
        stripped = line.strip()
        if not stripped:
            continue

        leading = len(line) - len(line.lstrip())

        # ── Section headers ──────────────────────────────────────────────────
        if stripped in ("Connected:", "Not Connected:"):
            # Save previous device block before switching section
            if current_name and current_block:
                _merge_device(devices, current_name, current_block, in_connected_section)
            current_name = None
            current_block = {}
            in_connected_section = (stripped == "Connected:")
            continue

        # ── Device name lines ────────────────────────────────────────────────
        # A device name line ends with ':' and is NOT a known key:value pair.
        # Known keys contain ':' mid-line (e.g. "Address: XX:XX") — device
        # names either have no ':' before the trailing one, or the name itself
        # contains an apostrophe but not a key pattern.
        if stripped.endswith(":") and ":" not in stripped[:-1].replace("'", ""):
            # Flush previous device
            if current_name and current_block:
                _merge_device(devices, current_name, current_block, in_connected_section)
            current_name = stripped[:-1]  # strip trailing ':'
            current_block = {"leading": leading}
            continue

        # ── Key: value lines inside a device block ───────────────────────────
        if current_name and ":" in stripped:
            key, _, val = stripped.partition(":")
            key = key.strip()
            val = val.strip()
            current_block[key] = val

    # Flush last block
    if current_name and current_block:
        _merge_device(devices, current_name, current_block, in_connected_section)

    # Return only connected devices
    return [d for d in devices.values() if d.get("connected")]


def _merge_device(store: dict, name: str, block: dict, connected: bool) -> None:
    """
    Merge a device block into the store, preferring the richer entry.
    AirPods appear twice (BLE case + full audio). We keep the one
    with Left Battery Level data and HFP in services.
    """
    entry = {
        "name":      name,
        "connected": connected,
        "services":  block.get("Services", ""),
        "minor":     block.get("Minor Type", ""),
        "left":      _parse_pct(block.get("Left Battery Level", "")),
        "right":     _parse_pct(block.get("Right Battery Level", "")),
        "case":      _parse_pct(block.get("Case Battery Level", "")),
    }

    if name not in store:
        store[name] = entry
        return

    # Prefer entry with Left/Right battery data (i.e. the full audio entry)
    existing = store[name]
    if entry["left"] is not None and existing["left"] is None:
        store[name] = entry
    # Also prefer entry with HFP services (more capable entry)
    elif "HFP" in entry["services"] and "HFP" not in existing["services"]:
        store[name] = entry


def _parse_pct(val: str) -> int | None:
    """Parse '100%' → 100, return None if not a percentage string."""
    m = re.match(r"(\d+)%", val.strip())
    return int(m.group(1)) if m else None


# ── Mode read/write ────────────────────────────────────────────────────────────

def _get_noise_control_mode(device_name: str) -> str:
    """
    Read current noise control mode from com.apple.airpods plist.
    Tries defaults read first, then plutil as fallback.
    Returns an internal key ("anc", "transparency", "adaptive", "off").
    """
    # Attempt 1: defaults read
    script = (
        f'do shell script "defaults read com.apple.airpods 2>/dev/null'
        f' | grep -A5 \\"{device_name}\\"'
        f' | grep NoiseControlMode | head -1'
        f' | awk \'{{print $3}}\' | tr -d \';\'"'
    )
    output, code = run_osascript(script)
    if code == 0 and output.strip().isdigit():
        return _INT_TO_MODE.get(int(output.strip()), "off")

    # Attempt 2: plutil
    script2 = (
        f'do shell script "plutil -p ~/Library/Preferences/com.apple.airpods.plist 2>/dev/null'
        f' | grep -A3 \\"{device_name}\\"'
        f' | grep NoiseControlMode | awk \'{{print $3}}\'"'
    )
    output2, code2 = run_osascript(script2)
    if code2 == 0 and output2.strip().isdigit():
        return _INT_TO_MODE.get(int(output2.strip()), "off")

    return "off"


def _set_noise_control_mode(device_name: str, mode_key: str) -> bool:
    """
    Write the noise control mode to com.apple.airpods plist via defaults write,
    then flush cfprefsd so the AirPods pick up the change.
    Returns True on success.
    """
    mode_int = _MODE_TO_INT.get(mode_key)
    if mode_int is None:
        return False

    # Escape the device name for the shell (handles apostrophes like "meow's")
    escaped = device_name.replace("'", "'\\''")

    script = (
        f"do shell script \"defaults write com.apple.airpods '{escaped}'"
        f" -dict-add NoiseControlMode -int {mode_int}"
        f" && killall -HUP cfprefsd\""
    )
    _, code = run_osascript(script)
    return code == 0


# ── Public API ─────────────────────────────────────────────────────────────────

def get_connected_airpods() -> list[AirPodsDevice]:
    """
    Return all connected AirPods devices found via system_profiler.
    Filters to devices whose name contains 'airpods' (case-insensitive).
    """
    script = 'do shell script "system_profiler SPBluetoothDataType 2>/dev/null"'
    output, code = run_osascript(script)
    if code != 0 or not output:
        return []

    parsed = _parse_profiler_output(output)
    result = []

    for entry in parsed:
        name = entry["name"]
        if "airpods" not in name.lower():
            continue

        # Build model string from Minor Type, or fall back to name heuristic
        minor = entry.get("minor", "")
        if minor and minor.lower() not in ("headphones", "headset"):
            model = minor
        else:
            name_lower = name.lower()
            if "pro" in name_lower:
                model = "AirPods Pro"
            elif "max" in name_lower:
                model = "AirPods Max"
            else:
                model = "AirPods"

        battery = {}
        if entry["left"]  is not None: battery["left"]  = entry["left"]
        if entry["right"] is not None: battery["right"] = entry["right"]
        if entry["case"]  is not None: battery["case"]  = entry["case"]

        mode = _get_noise_control_mode(name)
        result.append(AirPodsDevice(name=name, model=model, current_mode=mode, battery=battery))

    return result


def get_current_mode(device: AirPodsDevice) -> str:
    """Return the live current mode by querying the plist directly."""
    return _get_noise_control_mode(device.name)


def set_mode(device: AirPodsDevice, mode_key: str) -> bool:
    """Switch the device to mode_key. Returns True on success."""
    ok = _set_noise_control_mode(device.name, mode_key)
    if ok:
        device.current_mode = mode_key
    return ok


def get_default_device() -> AirPodsDevice | None:
    """
    Return the configured default device, or the first connected AirPods.
    """
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