from __future__ import annotations

import json


def test_audit_event_includes_request_and_correlation_ids(mgp_post, make_memory, make_request, audit_log_path):
    memory = make_memory(
        memory_type="semantic_fact",
        content={"statement": "Remember this fact: audit token omega.", "fact": "audit token omega."},
    )
    payload = make_request(action="write", payload={"memory": memory})
    payload["policy_context"]["correlation_id"] = "trace_audit_1"

    response = mgp_post("/mgp/write", payload)
    assert response.status_code == 200

    lines = [json.loads(line) for line in audit_log_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    assert lines
    event = lines[-1]
    assert event["request_id"] == payload["request_id"]
    assert event["correlation_id"] == "trace_audit_1"
    assert event["policy_context"]["correlation_id"] == "trace_audit_1"
