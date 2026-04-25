from __future__ import annotations

import os
from importlib.metadata import PackageNotFoundError, version

DEFAULT_GATEWAY_VERSION = "0.1.1"
PROTOCOL_VERSION = "0.1.1"
PACKAGE_NAME = "mgp-gateway"
APP_NAME = "mgp-reference-gateway"
APP_TITLE = "MGP Reference Gateway"


def gateway_version() -> str:
    override = os.getenv("MGP_GATEWAY_VERSION_OVERRIDE")
    if override:
        return override
    try:
        return version(PACKAGE_NAME)
    except PackageNotFoundError:
        return DEFAULT_GATEWAY_VERSION
