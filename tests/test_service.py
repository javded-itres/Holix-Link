"""Autostart service helpers."""

from __future__ import annotations

import sys
from unittest.mock import patch

from holix_link.service import (
    SYSTEMD_UNIT_NAME,
    _install_systemd_user,
    resolve_daemon_command,
)


def test_resolve_daemon_command_prefers_entrypoint() -> None:
    with patch("holix_link.service.shutil.which", return_value="/usr/local/bin/holix-link"):
        assert resolve_daemon_command() == ["/usr/local/bin/holix-link", "daemon", "--foreground"]


def test_install_systemd_user_writes_unit(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr("holix_link.service.Path.home", lambda: tmp_path)
    monkeypatch.setattr(sys, "platform", "linux")
    with patch("holix_link.service._run") as run_mock:
        with patch(
            "holix_link.service.resolve_daemon_command",
            return_value=["holix-link", "daemon", "--foreground"],
        ):
            message = _install_systemd_user()
    unit = tmp_path / ".config" / "systemd" / "user" / SYSTEMD_UNIT_NAME
    assert unit.is_file()
    assert "holix-link daemon --foreground" in unit.read_text(encoding="utf-8")
    assert "systemctl" in message or "systemd" in message
    assert run_mock.called