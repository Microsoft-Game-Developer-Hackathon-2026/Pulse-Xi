"""Deployment-verifier failure cases use fake sockets and never contact a service."""
import importlib.util
from pathlib import Path
import sys

import pytest


@pytest.fixture
def smoke_module():
    script = Path(__file__).resolve().parents[2] / "scripts" / "container-smoke.py"
    spec = importlib.util.spec_from_file_location("pulse_container_smoke", script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("url", [
    "http://example.invalid",
    "https://example.invalid/path",
    "https:///",
    "https://example.invalid?token=not-a-secret",
    "https://example.invalid?",
    "https://example.invalid#fragment",
    "https://example.invalid#",
    "https://user:password@example.invalid",
    "https://user@example.invalid",
])
def test_deployed_smoke_rejects_non_origin_before_network(smoke_module, monkeypatch, url):
    def forbidden(*args, **kwargs):
        pytest.fail("Invalid origin reached a network operation")
    monkeypatch.setattr(sys, "argv", ["container-smoke.py", "--url", url])
    monkeypatch.setattr(smoke_module, "get", forbidden)
    with pytest.raises(ValueError, match="HTTPS origin"):
        smoke_module.main()


class FakeSocket:
    def __init__(self, chunks):
        self.chunks = iter(chunks)
        self.eof = False

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def settimeout(self, timeout):
        pass

    def sendall(self, data):
        pass

    def recv(self, size):
        # Fail fast against the old infinite-EOF loop instead of hanging pytest.
        if self.eof:
            raise AssertionError("Verifier read again after receiving EOF")
        chunk = next(self.chunks, b"")
        self.eof = not chunk
        return chunk


UPGRADE = b"HTTP/1.1 101 Switching Protocols\r\nUpgrade: websocket\r\n\r\n"


def fake_connection(module, monkeypatch, chunks):
    connection = FakeSocket(chunks)
    monkeypatch.setattr(module.socket, "create_connection", lambda *args, **kwargs: connection)


@pytest.mark.parametrize("partial", [
    b"",
    UPGRADE + b"\x81",
    UPGRADE + b"\x81\x7e\x00",
    UPGRADE + b"\x81\x7f" + b"\x00" * 7,
    UPGRADE + b"\x81\x03{",
])
def test_websocket_smoke_fails_on_eof(smoke_module, monkeypatch, partial):
    fake_connection(smoke_module, monkeypatch, [partial])
    with pytest.raises(ConnectionError, match="closed before a complete snapshot"):
        smoke_module.websocket_snapshot("example.invalid", 443)


@pytest.mark.parametrize("chunks,reason", [
    ([b"X" * 4096] * 17, "headers exceed"),
    ([UPGRADE + b"\x81\x7f" + (2_000_001).to_bytes(8, "big")], "snapshot exceeds"),
])
def test_websocket_smoke_bounds_response(smoke_module, monkeypatch, chunks, reason):
    fake_connection(smoke_module, monkeypatch, chunks)
    with pytest.raises(AssertionError, match=reason):
        smoke_module.websocket_snapshot("example.invalid", 443)


def test_websocket_smoke_accepts_snapshot_across_tcp_chunks(smoke_module, monkeypatch):
    payload = b'{"kind":"snapshot","match":{"match_id":"comeback-1107"}}'
    frame = b"\x81" + bytes([len(payload)]) + payload
    fake_connection(smoke_module, monkeypatch, [UPGRADE[:7], UPGRADE[7:] + frame[:1], frame[1:]])
    packet = smoke_module.websocket_snapshot("example.invalid", 443)
    assert packet == {"kind": "snapshot", "match": {"match_id": "comeback-1107"}}
