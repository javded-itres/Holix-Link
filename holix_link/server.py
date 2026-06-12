"""Gateway URL helpers."""

from __future__ import annotations

import os


class ServerUrlError(ValueError):
    """Raised when a gateway URL cannot be resolved."""


def normalize_server_url(raw: str) -> str:
    url = raw.strip().rstrip("/")
    if not url:
        raise ServerUrlError("Gateway server URL is empty")
    if not url.startswith(("http://", "https://")):
        url = f"https://{url}"
    return url


def resolve_server_url(explicit: str | None = None) -> str:
    if explicit and explicit.strip():
        return normalize_server_url(explicit)
    env = os.environ.get("HOLIX_LINK_SERVER", "").strip()
    if env:
        return normalize_server_url(env)
    raise ServerUrlError(
        "Gateway URL is required. Pass --server or set HOLIX_LINK_SERVER."
    )


def pair_endpoint(server_url: str) -> str:
    return f"{normalize_server_url(server_url)}/v1/link/pair"