"""Tests for Holix Link protocol models."""

from __future__ import annotations

import pytest

from holix_link.protocol import (
    AuthMessage,
    PairCreateRequest,
    RpcCall,
    RpcOp,
    RpcResult,
    WsMessageType,
    parse_ws_message,
)


def test_rpc_call_roundtrip() -> None:
    msg = RpcCall(id="abc-123", op=RpcOp.LIST_DIR, path="src", limit=50)
    data = msg.model_dump()
    assert data["type"] == WsMessageType.RPC_CALL
    parsed = parse_ws_message(data)
    assert isinstance(parsed, RpcCall)
    assert parsed.op == RpcOp.LIST_DIR
    assert parsed.path == "src"


def test_rpc_result_success() -> None:
    msg = RpcResult(id="x", ok=True, payload={"entries": []})
    data = msg.model_dump()
    parsed = parse_ws_message(data)
    assert isinstance(parsed, RpcResult)
    assert parsed.ok is True


def test_rpc_result_error() -> None:
    msg = RpcResult(id="x", ok=False, error="permission denied")
    assert msg.error == "permission denied"


def test_auth_message() -> None:
    msg = AuthMessage(
        link_id="link-1",
        device_public_key_b64="cHVibGlj",
        nonce="n1",
    )
    parsed = parse_ws_message(msg.model_dump())
    assert isinstance(parsed, AuthMessage)
    assert parsed.link_id == "link-1"


def test_pair_create_request_defaults() -> None:
    req = PairCreateRequest(profile="support")
    assert req.ttl_seconds == 600


def test_rpc_call_rejects_empty_id() -> None:
    with pytest.raises(ValueError):
        RpcCall(id="  ", op=RpcOp.STAT)


def test_parse_unknown_type() -> None:
    with pytest.raises(ValueError, match="Unknown"):
        parse_ws_message({"type": "bogus"})