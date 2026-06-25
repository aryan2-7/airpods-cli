"""CLI entry point — all commands are registered here."""

import click

from airpods_cli import bluetooth, config, modes, utils


@click.group()
@click.version_option(package_name="airpods-cli")
def cli():
    """Switch AirPods listening modes from your terminal."""
    pass


@cli.command("mode")
@click.argument("mode_input", metavar="MODE")
@click.option("--quiet", "-q", is_flag=True, help="Suppress all output (exit code only).")
@click.option("--device", "-d", default=None, help="Target a specific device by name.")
def mode_cmd(mode_input: str, quiet: bool, device: str | None):
    """Switch or toggle listening mode.

    \b
    MODE can be:
      anc           Noise Cancellation
      transparency  Transparency
      adaptive      Adaptive Audio
      off           Off
      toggle        Cycle to the next mode in order
      0 / 1 / 2 / 3  Numeric aliases for the above
    """
    if device:
        all_devices = bluetooth.get_connected_airpods()
        target = next((d for d in all_devices if d.name.lower() == device.lower()), None)
        if not target:
            utils.error(f"Device '{device}' not found or not connected.")
    else:
        target = bluetooth.get_default_device()
        if not target:
            utils.error("No AirPods connected. Connect your AirPods and try again.")

    if mode_input.lower() == "toggle":
        current = bluetooth.get_current_mode(target)
        mode_key = modes.next_mode(current)
        if not quiet:
            utils.info(f"Toggling from {modes.display_name(current)} \u2192 {modes.display_name(mode_key)}")
    else:
        try:
            mode_key = modes.resolve_mode(mode_input)
        except ValueError as e:
            utils.error(str(e))
            return

    ok = bluetooth.set_mode(target, mode_key)

    if not quiet:
        if ok:
            utils.success(f"Mode set to {modes.display_name(mode_key)} on {target.name}")
        else:
            utils.error(f"Failed to set mode on {target.name}")


@cli.command("status")
@click.option("--device", "-d", default=None, help="Target a specific device by name.")
def status_cmd(device: str | None):
    """Show current mode and device info."""
    if device:
        all_devices = bluetooth.get_connected_airpods()
        target = next((d for d in all_devices if d.name.lower() == device.lower()), None)
        if not target:
            utils.error(f"Device '{device}' not found or not connected.")
    else:
        target = bluetooth.get_default_device()
        if not target:
            utils.error("No AirPods connected. Connect your AirPods and try again.")

    current_mode = bluetooth.get_current_mode(target)

    click.echo(f"  Device:  {click.style(target.name, bold=True)}")
    click.echo(f"  Model:   {target.model}")
    click.echo(f"  Mode:    {click.style(modes.display_name(current_mode), fg='cyan', bold=True)}")

    if target.battery:
        b = target.battery
        left  = f"L {b.get('left',  '?')}%"
        right = f"R {b.get('right', '?')}%"
        case  = f"Case {b.get('case', '?')}%"
        click.echo(f"  Battery: {left}  {right}  {case}")


@cli.command("devices")
def devices_cmd():
    """List all connected AirPods devices."""
    all_devices = bluetooth.get_connected_airpods()

    if not all_devices:
        utils.warn("No AirPods devices connected.")
        return

    default_name = config.get("default_device")

    click.echo(f"  Found {len(all_devices)} device(s):\n")
    for i, d in enumerate(all_devices, start=1):
        marker = click.style(" \u2605 default", fg="yellow") if d.name == default_name else ""
        current = bluetooth.get_current_mode(d)
        click.echo(f"  {i}. {click.style(d.name, bold=True)}{marker}")
        click.echo(f"     {d.model} \u2014 {modes.display_name(current)}")
        if d.battery:
            b = d.battery
            click.echo(f"     Battery: L {b.get('left','?')}%  R {b.get('right','?')}%  Case {b.get('case','?')}%")
        click.echo()


@cli.command("config")
@click.option("--device",       "-d", default=None, help="Set the default device by name.")
@click.option("--toggle-order", "-t", default=None, help="Comma-separated mode order for toggle, e.g. anc,transparency,off")
@click.option("--reset",        "-r", is_flag=True, help="Reset all config to defaults.")
@click.option("--show",         "-s", is_flag=True, help="Print current config and exit.")
def config_cmd(device: str | None, toggle_order: str | None, reset: bool, show: bool):
    """View or update persistent settings."""

    if show:
        cfg = config.load_config()
        click.echo("  Config file:   ~/.airpods.json")
        click.echo(f"  Default device: {cfg.get('default_device') or click.style('not set', fg='bright_black')}")
        click.echo(f"  Toggle order:   {' \u2192 '.join(cfg.get('toggle_order', []))}")
        return

    if reset:
        config.reset()
        utils.success("Config reset to defaults.")
        return

    if device:
        all_devices = bluetooth.get_connected_airpods()
        names = [d.name for d in all_devices]
        if device not in names:
            utils.warn(f"'{device}' isn't currently connected \u2014 saving anyway.")
        config.set_value("default_device", device)
        utils.success(f"Default device set to '{device}'")

    if toggle_order:
        raw_modes = [m.strip() for m in toggle_order.split(",")]
        resolved = []
        for raw in raw_modes:
            try:
                resolved.append(modes.resolve_mode(raw))
            except ValueError as e:
                utils.error(str(e))
                return
        config.set_value("toggle_order", resolved)
        utils.success(f"Toggle order set to: {' \u2192 '.join(modes.display_name(m) for m in resolved)}")

    if not device and not toggle_order and not reset and not show:
        click.echo("No options given. Run with --help to see available options.")
        click.echo("  airpods config --show         View current config")
        click.echo("  airpods config --device NAME  Set default device")
        click.echo("  airpods config --reset        Reset to defaults")
