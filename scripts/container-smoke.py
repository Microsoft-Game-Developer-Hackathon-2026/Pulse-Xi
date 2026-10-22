#!/usr/bin/env python3
"""Build and smoke-test the public-demo container using only local Docker."""
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import socket
import ssl
import subprocess
import sys
import time
import urllib.error
import urllib.request
from uuid import uuid4


def run(*args: str, capture: bool = False) -> str:
    result = subprocess.run(args, check=True, text=True, capture_output=capture)
    return (result.stdout or "").strip()


def get(url: str, expected: int = 200) -> tuple[bytes, dict[str, str]]:
    try:
        with urllib.request.urlopen(url, timeout=3) as response:
            body, headers, status = response.read(), dict(response.headers), response.status
    except urllib.error.HTTPError as error:
        body, headers, status = error.read(), dict(error.headers), error.code
    if status != expected:
        raise AssertionError(f"GET {url}: expected {expected}, got {status}: {body[:300]!r}")
    return body, headers


def websocket_snapshot(host: str, port: int, secure: bool = False) -> dict:
    key = base64.b64encode(os.urandom(16)).decode("ascii")
    with socket.create_connection((host, port), timeout=5) as connection:
        if secure:
            connection = ssl.create_default_context().wrap_socket(connection, server_hostname=host)
        connection.settimeout(5)
        connection.sendall(("GET /ws/matches/comeback-1107 HTTP/1.1\r\n"
                            f"Host: {host}:{port}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\n"
                            f"Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n").encode())
        data = b""
        while b"\r\n\r\n" not in data:
            data += connection.recv(4096)
        headers, data = data.split(b"\r\n\r\n", 1)
        if not headers.startswith(b"HTTP/1.1 101"):
            raise AssertionError(f"WebSocket upgrade failed: {headers!r}")
        while len(data) < 2:
            data += connection.recv(4096)
        first, second = data[0], data[1]
        if first & 0x0F != 1 or second & 0x80:
            raise AssertionError("Expected an unmasked server text frame")
        length, offset = second & 0x7F, 2
        if length == 126:
            while len(data) < 4:
                data += connection.recv(4096)
            length, offset = int.from_bytes(data[2:4], "big"), 4
        elif length == 127:
            while len(data) < 10:
                data += connection.recv(4096)
            length, offset = int.from_bytes(data[2:10], "big"), 10
        while len(data) < offset + length:
            data += connection.recv(4096)
        packet = json.loads(data[offset:offset + length])
        if packet.get("kind") != "snapshot" or packet.get("match", {}).get("match_id") != "comeback-1107":
            raise AssertionError("WebSocket did not begin with the expected fixture snapshot")
        return packet


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--image", default="pulse-xi:container-smoke")
    parser.add_argument("--skip-build", action="store_true")
    parser.add_argument("--url", help="Smoke-test an already deployed HTTPS URL; no Azure resources are changed")
    args = parser.parse_args()
    name = f"pulse-xi-smoke-{uuid4().hex[:10]}"
    remote = args.url is not None
    try:
        if remote:
            from urllib.parse import urlsplit
            parsed = urlsplit(args.url)
            if parsed.scheme != "https" or not parsed.hostname or parsed.path not in ("", "/"):
                raise ValueError("--url must be an HTTPS origin with no path, query or fragment")
            base, host, port, secure = args.url.rstrip("/"), parsed.hostname, parsed.port or 443, True
        elif not args.skip_build:
            run("docker", "build", "--tag", args.image, ".")
        if not remote:
            image_config = json.loads(run("docker", "image", "inspect", "--format", "{{json .Config}}", args.image, capture=True))
            image_env = image_config.get("Env", [])
            image_cmd = " ".join(image_config.get("Cmd", []))
            if image_config.get("User") != "10001:10001":
                raise AssertionError("Runtime image is not configured for its non-root UID/GID")
            secrets = ("PULSE_RUNTIME_TOKEN", "PULSE_IMPORT_TOKEN", "PULSE_FOUNDRY_ADMIN_TOKEN", "FOUNDRY_PROJECT_ENDPOINT")
            if any(name in entry for entry in image_env for name in secrets):
                raise AssertionError("Runtime image config contains a privileged/provider credential variable")
            if "0.0.0.0" not in image_cmd or "--limit-concurrency 32" not in image_cmd:
                raise AssertionError("Runtime command is not bound to the container interface with a concurrency bound")
            run("docker", "run", "--detach", "--rm", "--name", name,
                "--publish", "127.0.0.1::8080", args.image)
            binding = run("docker", "port", name, "8080/tcp", capture=True).splitlines()[0]
            port = int(binding.rsplit(":", 1)[1])
            host, base, secure = "127.0.0.1", f"http://127.0.0.1:{port}", False
            deadline = time.monotonic() + 90
            while True:
                try:
                    get(base + "/ready")
                    break
                except (OSError, AssertionError):
                    if time.monotonic() >= deadline:
                        logs = run("docker", "logs", name, capture=True)
                        raise RuntimeError(f"Container did not become ready. Container logs:\n{logs}")
                    time.sleep(0.25)
        page, _ = get(base + "/")
        html = page.decode("utf-8")
        asset_urls = re.findall(r'(?:src|href)="(/assets/[^" ]+)"', html)
        if not asset_urls:
            raise AssertionError("Built frontend did not reference bundled assets")
        for url in asset_urls:
            get(base + url)
        health, _ = get(base + "/health")
        if json.loads(health).get("status") != "ok":
            raise AssertionError("Unexpected liveness response")
        matches, _ = get(base + "/api/matches")
        if "comeback-1107" not in matches.decode():
            raise AssertionError("Seeded fixture missing")
        deny = urllib.request.Request(base + "/api/matches/ingest", data=b"{}", method="POST",
                                      headers={"Content-Type": "application/json"})
        try:
            urllib.request.urlopen(deny, timeout=3)
        except urllib.error.HTTPError as error:
            if error.code != 403:
                raise AssertionError(f"Public import denial returned {error.code}") from error
        else:
            raise AssertionError("Anonymous import unexpectedly succeeded")
        snapshot = websocket_snapshot(host, port, secure)
        target = args.url if remote else args.image
        print(f"container smoke passed: target={target}, root/assets/health/readiness/API/import-denial/WebSocket snapshot")
        print(f"WebSocket snapshot fixture={snapshot['match']['match_id']}; no Azure credentials or resources used")
        return 0
    finally:
        if not remote:
            subprocess.run(["docker", "stop", name], check=False, capture_output=True, text=True)


if __name__ == "__main__":
    sys.exit(main())
