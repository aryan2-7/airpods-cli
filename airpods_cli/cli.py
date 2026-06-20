"""CLI entry point — all commands are registered here."""

import click


@click.group()
@click.version_option(package_name="airpods-cli")
def cli():
    """Switch AirPods listening modes from your terminal."""
    pass


# Commands will be added in phase 3
# from airpods_cli import mode, status, devices, config
