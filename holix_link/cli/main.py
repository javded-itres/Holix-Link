"""Holix Link CLI entry point."""

from __future__ import annotations

import typer
from rich.console import Console

from holix_link import __version__
from holix_link.config import get_link_home, load_config

app = typer.Typer(
    name="holix-link",
    help="Holix Link — remote folder client for Holix gateway.",
    no_args_is_help=True,
)
console = Console()


@app.callback()
def main_callback() -> None:
    """Holix Link client."""


@app.command()
def version() -> None:
    """Show client version."""
    console.print(f"holix-link {__version__}")


@app.command()
def wizard() -> None:
    """Interactive pairing wizard (folder + pair code)."""
    console.print("[yellow]wizard: not implemented yet (PR-4)[/yellow]")


@app.command()
def pair(
    code: str = typer.Argument(..., help="One-time pairing code, e.g. LINK-7K3M-9Q2P"),
    folder: str = typer.Option(..., "--folder", "-f", help="Folder to share"),
    server: str = typer.Option("", "--server", "-s", help="Gateway base URL"),
) -> None:
    """Pair this machine with a Holix gateway link code."""
    console.print(f"[yellow]pair {code} --folder {folder}: not implemented yet (PR-4)[/yellow]")
    if server:
        console.print(f"  server override: {server}")


@app.command()
def status() -> None:
    """Show link connection and folder status."""
    home = get_link_home()
    cfg = load_config()
    console.print(f"Data dir: {home}")
    if cfg.link_id:
        console.print(f"Link ID:  {cfg.link_id}")
        console.print(f"Folder:   {cfg.folder or cfg.folder_portable}")
        console.print(f"Server:   {cfg.server_url or '(not set)'}")
        console.print(f"Notify:   {'on' if cfg.notifications.enabled else 'off'}")
    else:
        console.print("[dim]Not paired. Run: holix-link pair CODE --folder PATH[/dim]")


@app.command()
def disconnect() -> None:
    """Disconnect and remove local credentials."""
    console.print("[yellow]disconnect: not implemented yet (PR-4)[/yellow]")


@app.command("install-service")
def install_service() -> None:
    """Install user-level autostart (systemd / LaunchAgent / Task Scheduler)."""
    console.print("[yellow]install-service: not implemented yet (PR-5)[/yellow]")


@app.command("uninstall-service")
def uninstall_service() -> None:
    """Remove autostart service."""
    console.print("[yellow]uninstall-service: not implemented yet (PR-5)[/yellow]")


@app.command()
def daemon(
    foreground: bool = typer.Option(False, "--foreground", "-f", help="Run in foreground"),
) -> None:
    """Run the link daemon (normally started by the service)."""
    console.print("[yellow]daemon: not implemented yet (PR-4)[/yellow]")
    if foreground:
        console.print("  mode: foreground")


if __name__ == "__main__":
    app()