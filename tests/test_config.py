"""Client config path tests."""

from __future__ import annotations

import json
import sys
from unittest.mock import patch

from holix_link.config import ClientConfig, get_link_home, load_config, save_config


def test_default_link_home_unix() -> None:
    with patch.object(sys, "platform", "linux"):
        home = get_link_home()
        assert home.name == ".holix-link"


def test_link_home_override(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("HOLIX_LINK_HOME", str(tmp_path / "custom"))
    assert get_link_home() == tmp_path / "custom"


def test_save_and_load_config(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("HOLIX_LINK_HOME", str(tmp_path))
    cfg = ClientConfig(
        server_url="https://gw.example.com",
        link_id="link-abc",
        folder="/home/user/work",
        notifications={"enabled": True},
    )
    save_config(cfg)
    loaded = load_config()
    assert loaded.link_id == "link-abc"
    assert loaded.notifications.enabled is True
    data = json.loads((tmp_path / "config.json").read_text(encoding="utf-8"))
    assert data["server_url"] == "https://gw.example.com"