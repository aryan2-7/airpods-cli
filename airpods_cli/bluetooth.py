"""
Bluetooth / osascript bridge.

Phase 3: stub implementations that return fake data.
Phase 4: replace stub bodies with real osascript calls.
"""

from __future__ import annotations


class AirPodsDevice:
    """Represents a connected AirPods device."""

    def __init__(self, name: str, model: str, current_mode: str, battery: dict | None = None):
        self.name = name
        self.model = model
        self.current_mode = current_mode
        self.battery = battery or {}

    def __repr__(self):
        return f"AirPodsDevice(name={self.name!r}, mode={self.current_mode!r})"


def get_connected_airpods() -> list[AirPodsDevice]:
    return [
        AirPodsDevice(
            name="Aryan's AirPods Pro",
            model="AirPods Pro (2nd generation)",
            current_mode="anc",
            battery={"left": 82, "right": 79, "case": 100},
        )
    ]


def get_current_mode(device: AirPodsDevice) -> str:
    return device.current_mode


def set_mode(device: AirPodsDevice, mode_key: str) -> bool:
    device.current_mode = mode_key
    return True


def get_default_device() -> AirPodsDevice | None:
    devices = get_connected_airpods()
    return devices[0] if devices else None
