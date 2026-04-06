from __future__ import annotations

from datetime import datetime, timezone


def utc_now_iso(*, seconds_precision: bool = False, z_suffix: bool = False) -> str:
    now = datetime.now(timezone.utc)
    if seconds_precision:
        now = now.replace(microsecond=0)

    value = now.isoformat()
    if z_suffix:
        value = value.replace("+00:00", "Z")
    return value
