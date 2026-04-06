from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SDK_PATH = ROOT / "sdk" / "python"
if str(SDK_PATH) not in sys.path:
    sys.path.insert(0, str(SDK_PATH))

from mgp_client import AuditQuery, MGPClient, PolicyContextBuilder


def main() -> None:
    base_url = os.getenv("MGP_BASE_URL", "http://127.0.0.1:8080")
    context = PolicyContextBuilder(actor_agent="audit/demo", subject_id="user_audit_demo", tenant_id="tenant_audit")

    with MGPClient(base_url) as client:
        audit = client.query_audit(
            context.build("read"),
            AuditQuery(action="write", limit=10),
        )

    print(json.dumps({"audit": audit.data}, indent=2))


if __name__ == "__main__":
    main()
