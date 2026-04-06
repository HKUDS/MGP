from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Union


@dataclass
class ApiKeyAuth:
    token: str
    header_name: str = "X-MGP-API-Key"


@dataclass
class BearerAuth:
    token: str


@dataclass
class TLSConfig:
    verify: bool | str = True
    cert: str | tuple[str, str] | None = None


AuthConfig = Union[ApiKeyAuth, BearerAuth]


def apply_auth_headers(headers: dict[str, str], auth: AuthConfig | None) -> dict[str, str]:
    effective = dict(headers)
    if auth is None:
        return effective
    if isinstance(auth, ApiKeyAuth):
        effective[auth.header_name] = auth.token
    elif isinstance(auth, BearerAuth):
        effective["Authorization"] = f"Bearer {auth.token}"
    return effective


def httpx_tls_kwargs(tls: TLSConfig | None) -> dict[str, Any]:
    if tls is None:
        return {}
    kwargs: dict[str, Any] = {"verify": tls.verify}
    if tls.cert is not None:
        kwargs["cert"] = tls.cert
    return kwargs
