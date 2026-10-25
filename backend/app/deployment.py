"""Deployment-mode validation and the deliberately narrow public-demo boundary."""
from __future__ import annotations

import math
import os
import re
import tempfile
import time
from pathlib import Path
from threading import Lock

from starlette.responses import JSONResponse


PUBLIC_READ_PATHS = frozenset(("/", "/health", "/ready", "/api/deployment", "/api/matches", "/api/data-hub"))
PUBLIC_MATCH_PATH = re.compile(r"^/api/matches/[A-Za-z0-9][A-Za-z0-9_.:-]{0,159}(?:/.*)?$")
PUBLIC_MATCH_SOCKET = re.compile(r"^/ws/matches/[A-Za-z0-9][A-Za-z0-9_.:-]{0,159}$")
PUBLIC_POST_PATHS = frozenset(("/api/matches/generate",))
PUBLIC_RECAP_PATH = re.compile(r"^/api/matches/[A-Za-z0-9][A-Za-z0-9_.:-]{0,159}/recap$")
PUBLIC_OPERATION_LIMIT = 30


class PublicOperationQuota:
    """Constant-space, process-wide POST budget; no client/proxy identity keys."""

    def __init__(self, limit=30, window_seconds=60, clock=time.monotonic):
        self.limit = limit
        self.window_seconds = window_seconds
        self.clock = clock
        self._started = None
        self._used = 0
        self._lock = Lock()

    def retry_after(self) -> int:
        with self._lock:
            now = self.clock()
            if self._started is None or now - self._started >= self.window_seconds:
                self._started, self._used = now, 0
            if self._used >= self.limit:
                elapsed = max(0, now - self._started)
                return max(1, math.ceil(self.window_seconds - elapsed))
            self._used += 1
            return 0


def deployment_mode() -> str:
    mode = os.getenv("PULSE_DEPLOYMENT_MODE", "local")
    if mode not in {"local", "public-readonly"}:
        raise RuntimeError("PULSE_DEPLOYMENT_MODE must be 'local' or 'public-readonly'")
    return mode


def validate_deployment_config() -> None:
    """Fail closed for unsafe public-mode settings; local defaults stay unchanged."""
    if deployment_mode() != "public-readonly":
        return
    forbidden = (
        "PULSE_RUNTIME_TOKEN", "PULSE_RUNTIME_TOKENS", "PULSE_IMPORT_TOKEN",
        "PULSE_FOUNDRY_ADMIN_TOKEN", "PULSE_STUDIO_PRODUCER_TOKEN",
        "FOUNDRY_PROJECT_ENDPOINT", "FOUNDRY_MODEL",
    )
    if any(os.getenv(name) for name in forbidden):
        raise RuntimeError("public-readonly mode cannot be configured with privileged tokens or hosted inference")
    if os.getenv("PULSE_ENABLE_FOUNDRY", "false").lower() not in {"", "0", "false", "no", "off"}:
        raise RuntimeError("public-readonly mode requires PULSE_ENABLE_FOUNDRY to be false")
    if os.getenv("PULSE_RUNTIME_DRIVER", "0") != "0":
        raise RuntimeError("public-readonly mode requires PULSE_RUNTIME_DRIVER=0")
    if os.getenv("PULSE_ENABLE_LOCAL_DATA_ADMIN", "0") == "1":
        raise RuntimeError("public-readonly mode cannot enable local dataset administration")
    paths = [Path(os.getenv(name, "")).resolve() for name in ("PULSE_DB_PATH", "PULSE_RUNTIME_DB_PATH")]
    temp_root = Path(tempfile.gettempdir()).resolve()
    if not all(path != temp_root and temp_root in path.parents for path in paths):
        raise RuntimeError("public-readonly mode requires both disposable database paths below the operating-system temporary directory")
    if paths[0] == paths[1]:
        raise RuntimeError("public-readonly imported and runtime database paths must be distinct")


class PublicDemoBoundary:
    """Allow synthetic reads and bounded seed generation, deny every other write."""

    def __init__(self, app, quota=None):
        self.app = app
        self.quota = quota if quota is not None else PublicOperationQuota(limit=PUBLIC_OPERATION_LIMIT)

    async def __call__(self, scope, receive, send):
        if scope["type"] == "websocket":
            if deployment_mode() == "public-readonly" and not PUBLIC_MATCH_SOCKET.fullmatch(scope.get("path", "")):
                await send({"type": "websocket.close", "code": 1008})
                return
            return await self.app(scope, receive, send)
        if scope["type"] != "http" or deployment_mode() != "public-readonly":
            return await self.app(scope, receive, send)
        method, path = scope.get("method", "GET"), scope.get("path", "")
        allowed_post = method == "POST" and (path in PUBLIC_POST_PATHS or PUBLIC_RECAP_PATH.fullmatch(path))
        allowed_read = method in {"GET", "HEAD"} and (path in PUBLIC_READ_PATHS or
                       path.startswith("/assets/") or PUBLIC_MATCH_PATH.fullmatch(path))
        if not (allowed_post or allowed_read):
            response = JSONResponse({"detail": "This public demo is read-only."}, status_code=403,
                                    headers={"Cache-Control": "no-store"})
            await response(scope, receive, send)
            return
        if allowed_post and (retry := self.quota.retry_after()):
            response = JSONResponse({"detail": "Public operation budget exhausted; retry later."},
                                    status_code=429, headers={"Cache-Control": "no-store",
                                                             "Retry-After": str(retry)})
            await response(scope, receive, send)
            return
        await self.app(scope, receive, send)
