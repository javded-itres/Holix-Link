"""Pairing flow tests."""

from __future__ import annotations

import pytest

from holix_link.config import load_config
from holix_link.credentials import load_credentials
from holix_link.pairing import PairingError, exchange_pair_code, validate_folder


def test_validate_folder_missing(tmp_path) -> None:
    with pytest.raises(PairingError, match="does not exist"):
        validate_folder(str(tmp_path / "missing"))


def test_validate_folder_success(tmp_path) -> None:
    folder = tmp_path / "work"
    folder.mkdir()
    resolved = validate_folder(str(folder))
    assert resolved == folder.resolve()


def test_exchange_pair_code(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("HOLIX_LINK_HOME", str(tmp_path))
    folder = tmp_path / "shared"
    folder.mkdir()

    class FakeResponse:
        status_code = 200

        @staticmethod
        def json() -> dict:
            return {
                "link_id": "link_abc123",
                "gateway_ws_url": "ws://127.0.0.1:8000/v1/link/ws",
                "server_fingerprint": "fp1234567890abcd",
                "permissions": {"read": True, "write": False, "mkdir": False, "delete": False},
            }

    monkeypatch.setattr("holix_link.pairing.httpx.post", lambda *args, **kwargs: FakeResponse())

    config, creds = exchange_pair_code(
        code="LINK-AAAA-BBBB",
        folder=str(folder),
        server="http://127.0.0.1:8000",
    )
    assert config.link_id == "link_abc123"
    assert config.gateway_ws_url.endswith("/v1/link/ws")
    assert creds.device_public_key_b64
    assert creds.device_private_key_b64
    assert load_config().link_id == "link_abc123"
    assert load_credentials() is not None