from __future__ import annotations

import json
import socket
import time
from typing import Any, Callable
from urllib import error, request


def allocate_port(host: str = "127.0.0.1") -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind((host, 0))
        sock.listen(1)
        return int(sock.getsockname()[1])


def request_json(
    method: str,
    url: str,
    payload: dict[str, Any] | None = None,
    *,
    timeout_seconds: float = 5.0,
) -> tuple[int, Any]:
    body = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        body = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = request.Request(url, data=body, headers=headers, method=method.upper())
    try:
        with request.urlopen(req, timeout=timeout_seconds) as response:
            raw = response.read().decode("utf-8")
            data = json.loads(raw) if raw else None
            return int(response.status), data
    except error.HTTPError as http_error:
        raw = http_error.read().decode("utf-8")
        data = json.loads(raw) if raw else None
        return int(http_error.code), data


def wait_for_ready(
    base_url: str,
    timeout_seconds: float,
    *,
    ready_path: str = "/readyz",
    is_process_running: Callable[[], bool] | None = None,
) -> None:
    deadline = time.time() + timeout_seconds
    last_error: Exception | None = None
    while time.time() < deadline:
        if is_process_running is not None and not is_process_running():
            raise RuntimeError("gateway exited before becoming ready")
        try:
            status, payload = request_json("GET", f"{base_url}{ready_path}", timeout_seconds=1.0)
            if status == 200 and payload and payload.get("status") == "ready":
                return
        except Exception as error_value:  # pragma: no cover - readiness polling
            last_error = error_value
        time.sleep(0.2)

    message = f"gateway did not become ready within {timeout_seconds:.1f}s"
    if last_error is not None:
        message = f"{message}: {last_error}"
    raise RuntimeError(message)
