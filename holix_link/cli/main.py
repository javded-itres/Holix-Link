"""Holix Link CLI entry point."""

from __future__ import annotations

import asyncio
import os

import typer
from rich.console import Console
from rich.prompt import Confirm

from holix_link import __version__
from holix_link.config import clear_paired_config, get_link_home, load_config
from holix_link.credentials import clear_credentials, load_credentials
from holix_link.daemon import is_daemon_running, run_daemon
from holix_link.pairing import PairingError, exchange_pair_code, fingerprint_trusted
from holix_link.server import ServerUrlError

app = typer.Typer(
    name="holix-link",
    help="Holix Link — remote folder client for Holix gateway.",
    no_args_is_help=True,
)
console = Console()


def _trusted_fingerprint(observed: str) -> bool:
    env = os.environ.get("HOLIX_LINK_TRUSTED_FP", "").strip()
    if env and env == observed:
        return True
    creds = load_credentials()
    if creds and creds.trusted_fingerprint:
        return fingerprint_trusted(creds.server_fingerprint, observed)
    return False


@app.callback()
def main_callback() -> None:
    """Holix Link client."""


@app.command()
def version() -> None:
    """Show client version."""
    console.print(f"holix-link {__version__}")


@app.command()
def wizard(
    server: str = typer.Option("", "--server", "-s", help="Gateway base URL"),
) -> None:
    """Interactive pairing wizard (folder + pair code)."""
    code = typer.prompt("Pairing code (LINK-XXXX-YYYY)")
    folder = typer.prompt("Folder to share")
    _run_pair(code=code, folder=folder, server=server or None, yes=False)


@app.command()
def pair(
    code: str = typer.Argument(..., help="One-time pairing code, e.g. LINK-7K3M-9Q2P"),
    folder: str = typer.Option(..., "--folder", "-f", help="Folder to share"),
    server: str = typer.Option("", "--server", "-s", help="Gateway base URL"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip server fingerprint confirmation"),
) -> None:
    """Pair this machine with a Holix gateway link code."""
    _run_pair(code=code, folder=folder, server=server or None, yes=yes)


def _run_pair(*, code: str, folder: str, server: str | None, yes: bool) -> None:
    try:
        config, credentials = exchange_pair_code(
            code=code,
            folder=folder,
            server=server,
            trust_fingerprint=yes or _trusted_fingerprint(
                os.environ.get("HOLIX_LINK_TRUSTED_FP", "")
            ),
        )
    except ServerUrlError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        raise typer.Exit(1) from exc
    except PairingError as exc:
        console.print(f"[red]Pairing failed:[/red] {exc}")
        raise typer.Exit(1) from exc

    observed_fp = credentials.server_fingerprint
    if not yes and not _trusted_fingerprint(observed_fp):
        console.print(f"Server fingerprint: [bold]{observed_fp}[/bold]")
        if not Confirm.ask("Trust this server and save pairing?", default=True):
            clear_credentials()
            clear_paired_config()
            console.print("[yellow]Pairing cancelled.[/yellow]")
            raise typer.Exit(1)
        credentials.trusted_fingerprint = True
        from holix_link.credentials import save_credentials

        save_credentials(credentials)

    console.print("[green]Paired successfully.[/green]")
    console.print(f"  Link ID: {config.link_id}")
    console.print(f"  Folder:  {config.folder}")
    console.print(f"  Server:  {config.server_url}")
    console.print("Start daemon: [bold]holix-link daemon --foreground[/bold]")


@app.command()
def status() -> None:
    """Show link connection and folder status."""
    home = get_link_home()
    cfg = load_config()
    creds = load_credentials()
    console.print(f"Data dir: {home}")
    if cfg.link_id:
        console.print(f"Link ID:  {cfg.link_id}")
        console.print(f"Folder:   {cfg.folder or cfg.folder_portable}")
        console.print(f"Server:   {cfg.server_url or '(not set)'}")
        console.print(f"WS:       {cfg.gateway_ws_url or '(not set)'}")
        if creds:
            perms = creds.permissions
            console.print(
                f"Perms:    read={perms.read} write={perms.write} "
                f"mkdir={perms.mkdir} delete={perms.delete}"
            )
        console.print(f"Notify:   {'on' if cfg.notifications.enabled else 'off'}")
        console.print(f"Daemon:   {'running' if is_daemon_running() else 'stopped'}")
    else:
        console.print("[dim]Not paired. Run: holix-link pair CODE --folder PATH[/dim]")


@app.command()
def disconnect() -> None:
    """Disconnect and remove local credentials."""
    if is_daemon_running():
        console.print("[yellow]Daemon is running. Stop it before disconnecting.[/yellow]")
        raise typer.Exit(1)
    clear_credentials()
    clear_paired_config()
    console.print("[green]Local pairing removed.[/green]")
    console.print("Revoke on server if needed: [bold]holix link revoke <id>[/bold]")


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
    foreground: bool = typer.Option(
        True,
        "--foreground/--background",
        "-f/-b",
        help="Run in foreground",
    ),
) -> None:
    """Run the link daemon (normally started by the service)."""
    if not foreground:
        console.print(
            "[yellow]Background mode requires install-service (PR-5). "
            "Use --foreground.[/yellow]"
        )
        raise typer.Exit(1)
    try:
        asyncio.run(run_daemon(foreground=True))
    except RuntimeError as exc:
        console.print(f"[red]Daemon error:[/red] {exc}")
        raise typer.Exit(1) from exc
    except KeyboardInterrupt:
        console.print("\n[dim]Daemon stopped.[/dim]")


if __name__ == "__main__":
    app()