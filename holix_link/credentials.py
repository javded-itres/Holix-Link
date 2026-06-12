"""Local device credentials for Holix Link."""

from __future__ import annotations

import json
import sys
from typing import Any

from pydantic import BaseModel, Field

from holix_link.config import credentials_path, ensure_link_home
from holix_link.protocol import LinkPermissions


class DeviceCredentials(BaseModel):
    device_public_key_b64: str
    device_private_key_b64: str
    server_fingerprint: str = ""
    trusted_fingerprint: bool = False
    permissions: LinkPermissions = Field(default_factory=LinkPermissions)


def load_credentials() -> DeviceCredentials | None:
    path = credentials_path()
    if not path.is_file():
        return None
    data: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return DeviceCredentials.model_validate(data)


def save_credentials(credentials: DeviceCredentials) -> None:
    ensure_link_home()
    path = credentials_path()
    path.write_text(
        json.dumps(credentials.model_dump(), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    if sys.platform != "win32":
        path.chmod(0o600)


def clear_credentials() -> None:
    path = credentials_path()
    if path.is_file():
        path.unlink()