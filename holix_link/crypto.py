"""Device key helpers for Holix Link pairing."""

from __future__ import annotations

import base64

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey


def generate_device_keypair() -> tuple[str, str]:
    """Return (public_key_b64, private_key_b64) for a new Ed25519 device key."""
    private_key = Ed25519PrivateKey.generate()
    public_key = private_key.public_key()
    public_b64 = base64.b64encode(
        public_key.public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
    ).decode("ascii")
    private_b64 = base64.b64encode(
        private_key.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption(),
        )
    ).decode("ascii")
    return public_b64, private_b64