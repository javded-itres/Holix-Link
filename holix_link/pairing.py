"""Holix Link pairing against gateway control plane."""

from __future__ import annotations

from pathlib import Path

import httpx

from holix_link.config import ClientConfig, save_config
from holix_link.credentials import DeviceCredentials, save_credentials
from holix_link.crypto import generate_device_keypair
from holix_link.paths import resolve_folder_root
from holix_link.protocol import PairExchangeRequest, PairExchangeResponse
from holix_link.server import pair_endpoint, resolve_server_url


class PairingError(RuntimeError):
    """Raised when pairing with the gateway fails."""


def validate_folder(folder: str) -> Path:
    raw = folder.strip()
    if not raw:
        raise PairingError("Folder path is required")
    try:
        resolved = resolve_folder_root(Path(raw))
    except OSError as exc:
        raise PairingError(f"Cannot access folder: {folder}") from exc
    if not resolved.exists():
        raise PairingError(f"Folder does not exist: {resolved}")
    if not resolved.is_dir():
        raise PairingError(f"Path is not a directory: {resolved}")
    return resolved


def exchange_pair_code(
    *,
    code: str,
    folder: str,
    server: str | None = None,
    trust_fingerprint: bool = False,
    timeout: float = 30.0,
) -> tuple[ClientConfig, DeviceCredentials]:
    """Pair this device with a one-time link code."""
    pair_code = code.strip().upper()
    if not pair_code:
        raise PairingError("Pairing code is required")

    folder_path = validate_folder(folder)
    server_url = resolve_server_url(server)
    public_b64, private_b64 = generate_device_keypair()

    request = PairExchangeRequest(
        code=pair_code,
        folder=str(folder_path),
        device_public_key_b64=public_b64,
    )
    endpoint = pair_endpoint(server_url)

    try:
        response = httpx.post(
            endpoint,
            json=request.model_dump(),
            timeout=timeout,
            follow_redirects=True,
        )
    except httpx.HTTPError as exc:
        raise PairingError(f"Cannot reach gateway at {server_url}: {exc}") from exc

    if response.status_code >= 400:
        detail = response.text.strip() or response.reason_phrase
        try:
            payload = response.json()
            if isinstance(payload, dict) and payload.get("detail"):
                detail = str(payload["detail"])
        except Exception:
            pass
        raise PairingError(f"Pairing failed ({response.status_code}): {detail}")

    exchange = PairExchangeResponse.model_validate(response.json())
    credentials = DeviceCredentials(
        device_public_key_b64=public_b64,
        device_private_key_b64=private_b64,
        server_fingerprint=exchange.server_fingerprint,
        trusted_fingerprint=trust_fingerprint,
        permissions=exchange.permissions,
    )
    config = ClientConfig(
        server_url=server_url,
        link_id=exchange.link_id,
        folder=str(folder_path),
        folder_portable=str(folder_path),
        gateway_ws_url=exchange.gateway_ws_url,
    )
    save_credentials(credentials)
    save_config(config)
    return config, credentials


def fingerprint_trusted(stored: str | None, observed: str) -> bool:
    if not stored:
        return False
    return stored.strip() == observed.strip()