# Devlopment halted for now

# airpods-cli

Switch your AirPods listening mode from the terminal.

```bash
airpods mode anc          # Noise Cancellation
airpods mode transparency # Transparency
airpods mode adaptive     # Adaptive Audio
airpods mode off          # Off
airpods mode toggle       # Cycle through modes
airpods status            # Show current mode + device
```

## Requirements

- macOS 13 (Ventura) or later
- AirPods Pro (1st or 2nd gen), AirPods Max, or AirPods (3rd gen)
- Python 3.10+

> Regular AirPods (1st/2nd gen) and EarPods do not support listening modes.

## Install

```bash
pipx install airpods-cli
```

Or with pip:

```bash
pip install airpods-cli
```

## Usage

```
Usage: airpods [OPTIONS] COMMAND [ARGS]...

  Switch AirPods listening modes from your terminal.

Options:
  --version  Show the version and exit.
  --help     Show this message and exit.

Commands:
  config   Set default device and toggle order.
  devices  List connected AirPods devices.
  mode     Switch or toggle listening mode.
  status   Show current mode and device info.
```

## Commands

### `airpods mode <mode>`

Switch to a specific mode. Available modes: `anc`, `transparency`, `adaptive`, `off`.

```bash
airpods mode anc
airpods mode transparency
airpods mode off
```

Use `--quiet` to suppress output (useful in scripts or Raycast):

```bash
airpods mode anc --quiet
```

Use numeric aliases for even shorter commands:

```bash
airpods mode 1   # anc
airpods mode 2   # transparency
airpods mode 3   # adaptive
airpods mode 0   # off
```

### `airpods mode toggle`

Cycle through modes in order. Default order: anc → transparency → adaptive → off.

```bash
airpods mode toggle
```

Customise the order:

```bash
airpods config --toggle-order anc,transparency,off
```

### `airpods status`

Show the current mode and device name.

```bash
airpods status
```

```
Device:  Aryan's AirPods Pro
Mode:    Noise Cancellation (ANC)
Battery: L 82%  R 79%  Case 100%
```

### `airpods devices`

List all paired AirPods devices.

```bash
airpods devices
```

### `airpods config`

Set a default device or customise the toggle order.

```bash
airpods config --device "Aryan's AirPods Pro"
airpods config --toggle-order anc,transparency,off
airpods config --reset
```

## Permissions

On first run, macOS may ask for Accessibility or Bluetooth permissions. Grant them in **System Settings → Privacy & Security**.

## Known limitations

- macOS only — this uses AppleScript to talk to Bluetooth preferences
- Does not work over SSH (requires a GUI session)
- AirPods must be connected to the Mac running the command
- Litreally doesnt even work rn

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md).

## License

MIT — see [LICENSE](LICENSE).
