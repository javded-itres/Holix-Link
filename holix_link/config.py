"""Holix Link local data paths and config helpers."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field


class ClientNotifications(BaseModel):
    enabled: bool = False
    on_read: bool = True
    on_write: bool = True
    on_delete: bool = True


class ClientConfig(BaseModel):
    server_url: str = ""
    link_id: str = ""
    folder: str = ""
    folder_portable: str = ""
    notifications: ClientNotifications = Field(default_factory=ClientNotifications)


def get_link_home() -> Path:
    override = os.environ.get("HOLIX_LINK_HOME", "").strip()
    if override:
        return Path(override).expanduser()
    if sys.platform == "win32":
        local = os.environ.get("LOCALAPPDATA", "")
        if local:
            return Path(local) / "HolixLink"
    return Path.home() / ".holix-link"


def config_path() -> Path:
    return get_link_home() / "config.json"


def credentials_path() -> Path:
    return get_link_home() / "credentials.json"


def ensure_link_home() -> Path:
    home = get_link_home()
    home.mkdir(parents=True, exist_ok=True)
    return home


def load_config() -> ClientConfig:
    path = config_path()
    if not path.is_file():
        return ClientConfig()
    data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return ClientConfig.model_validate(data)


def save_config(config: ClientConfig) -> Path:
    ensure_link_home()
    path = config_path()
    path.write_text(
        json.dumps(config.model_dump(), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    if sys.platform != "win32":
        path.chmod(0o600)
    return path