"""User-level autostart for Holix Link daemon."""

from __future__ import annotations

import os
import plistlib
import shutil
import subprocess
import sys
from pathlib import Path

SERVICE_LABEL = "ru.holix.link"
SYSTEMD_UNIT_NAME = "holix-link.service"
WINDOWS_TASK_NAME = "HolixLink"


class ServiceError(RuntimeError):
    """Raised when service install/uninstall fails."""


def resolve_daemon_command() -> list[str]:
    executable = shutil.which("holix-link")
    if executable:
        return [executable, "daemon", "--foreground"]
    return [sys.executable, "-m", "holix_link.cli.main", "daemon", "--foreground"]


def _command_line() -> str:
    return subprocess.list2cmdline(resolve_daemon_command())


def _systemd_unit_path() -> Path:
    return Path.home() / ".config" / "systemd" / "user" / SYSTEMD_UNIT_NAME


def _launch_agent_path() -> Path:
    return Path.home() / "Library" / "LaunchAgents" / f"{SERVICE_LABEL}.plist"


def install_service() -> str:
    if sys.platform == "darwin":
        return _install_launch_agent()
    if sys.platform == "win32":
        return _install_windows_task()
    return _install_systemd_user()


def uninstall_service() -> str:
    if sys.platform == "darwin":
        return _uninstall_launch_agent()
    if sys.platform == "win32":
        return _uninstall_windows_task()
    return _uninstall_systemd_user()


def _install_systemd_user() -> str:
    unit_path = _systemd_unit_path()
    unit_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = " ".join(resolve_daemon_command())
    unit_path.write_text(
        "\n".join(
            [
                "[Unit]",
                "Description=Holix Link remote folder client",
                "After=network-online.target",
                "",
                "[Service]",
                "Type=simple",
                f"ExecStart={cmd}",
                "Restart=on-failure",
                "RestartSec=5",
                "",
                "[Install]",
                "WantedBy=default.target",
                "",
            ]
        ),
        encoding="utf-8",
    )
    _run(["systemctl", "--user", "daemon-reload"])
    _run(["systemctl", "--user", "enable", "--now", SYSTEMD_UNIT_NAME])
    return f"systemd user service installed: {unit_path}"


def _uninstall_systemd_user() -> str:
    try:
        _run(["systemctl", "--user", "disable", "--now", SYSTEMD_UNIT_NAME], check=False)
    except ServiceError:
        pass
    path = _systemd_unit_path()
    if path.is_file():
        path.unlink()
        _run(["systemctl", "--user", "daemon-reload"], check=False)
    return "systemd user service removed"


def _install_launch_agent() -> str:
    plist_path = _launch_agent_path()
    plist_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = resolve_daemon_command()
    payload = {
        "Label": SERVICE_LABEL,
        "ProgramArguments": cmd,
        "RunAtLoad": True,
        "KeepAlive": True,
        "StandardOutPath": str(Path.home() / ".holix-link" / "link.log"),
        "StandardErrorPath": str(Path.home() / ".holix-link" / "link.log"),
    }
    with open(plist_path, "wb") as handle:
        plistlib.dump(payload, handle)
    _run(["launchctl", "bootout", f"gui/{os.getuid()}", str(plist_path)], check=False)
    _run(["launchctl", "bootstrap", f"gui/{os.getuid()}", str(plist_path)])
    _run(["launchctl", "enable", f"gui/{os.getuid()}/{SERVICE_LABEL}"])
    _run(["launchctl", "kickstart", "-k", f"gui/{os.getuid()}/{SERVICE_LABEL}"], check=False)
    return f"LaunchAgent installed: {plist_path}"


def _uninstall_launch_agent() -> str:
    plist_path = _launch_agent_path()
    _run(["launchctl", "bootout", f"gui/{os.getuid()}", str(plist_path)], check=False)
    if plist_path.is_file():
        plist_path.unlink()
    return "LaunchAgent removed"


def _install_windows_task() -> str:
    cmd = _command_line()
    _run(
        [
            "schtasks",
            "/Create",
            "/SC",
            "ONLOGON",
            "/TN",
            WINDOWS_TASK_NAME,
            "/TR",
            cmd,
            "/F",
        ]
    )
    return f"Task Scheduler job created: {WINDOWS_TASK_NAME}"


def _uninstall_windows_task() -> str:
    _run(["schtasks", "/Delete", "/TN", WINDOWS_TASK_NAME, "/F"], check=False)
    return "Task Scheduler job removed"


def _run(args: list[str], *, check: bool = True) -> None:
    try:
        subprocess.run(args, check=check, capture_output=True, text=True)
    except FileNotFoundError as exc:
        raise ServiceError(f"Command not found: {args[0]}") from exc
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or exc.stdout or "").strip()
        raise ServiceError(stderr or f"Command failed: {' '.join(args)}") from exc