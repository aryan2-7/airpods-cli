"""Shared helpers — output formatting, validation, subprocess wrapper."""

import subprocess
import sys

import click


def success(message: str) -> None:
    """Print a green success message."""
    click.echo(click.style(f"✓ {message}", fg="green"))


def error(message: str, exit_code: int = 1) -> None:
    """Print a red error message and exit."""
    click.echo(click.style(f"✗ {message}", fg="red"), err=True)
    sys.exit(exit_code)


def warn(message: str) -> None:
    """Print a yellow warning (doesn't exit)."""
    click.echo(click.style(f"⚠ {message}", fg="yellow"))


def info(message: str) -> None:
    """Print a muted info line."""
    click.echo(click.style(message, fg="bright_black"))


def run_osascript(script: str) -> tuple[str, int]:
    """
    Run an AppleScript string via osascript.
    Returns (stdout, return_code).
    """
    result = subprocess.run(
        ["osascript", "-e", script],
        capture_output=True,
        text=True,
    )
    return result.stdout.strip(), result.returncode
