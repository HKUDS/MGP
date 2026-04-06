from __future__ import annotations

from reference.policy.hook import PolicyHook


def test_restricted_memory_returns_metadata_only(mgp_post, make_memory, make_request):
    memory = make_memory(content={"secret": "top-secret"}, sensitivity="restricted")
    mgp_post("/mgp/write", make_request(action="write", payload={"memory": memory}))

    response = mgp_post("/mgp/get", make_request(action="read", payload={"memory_id": memory["memory_id"]}))
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["return_mode"] == "metadata_only"
    assert body["data"]["memory"]["content"]["statement"].endswith("metadata only")
    assert body["data"]["consumable_text"].endswith("metadata only")
    assert body["data"]["memory"]["evidence"] == []
    assert body["data"]["memory"]["evidence_refs"] == []


def test_confidential_memory_is_masked(mgp_post, make_memory, make_request):
    memory = make_memory(content={"secret": "visible-text"}, sensitivity="confidential")
    mgp_post("/mgp/write", make_request(action="write", payload={"memory": memory}))

    response = mgp_post("/mgp/get", make_request(action="read", payload={"memory_id": memory["memory_id"]}))
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["return_mode"] == "masked"
    assert body["data"]["memory"]["content"]["secret"] == "***"
    assert "visible-text" not in body["data"]["consumable_text"]


def test_summary_transform_returns_schema_safe_placeholder(make_memory):
    policy = PolicyHook()
    memory = make_memory(
        memory_type="semantic_fact",
        content={
            "statement": "Remember this fact: hidden token is kiwi-42.",
            "summary": "Hidden token is present.",
            "fact": "hidden token is kiwi-42.",
        },
    )

    transformed, redaction = policy.transform_memory(
        memory,
        {
            "decision": "summarize",
            "reason_code": "summary_required_by_policy",
            "applied_rules": ["summary_required_by_policy"],
            "return_mode": "summary",
        },
    )

    assert transformed["content"]["statement"] == "Hidden token is present."
    assert transformed["content"]["summary"] == "Hidden token is present."
    assert "kiwi-42" not in transformed["content"]["statement"]
    assert redaction["summary_generated"] is True


def test_tenant_mismatch_returns_policy_denied(mgp_post, make_memory, make_request):
    memory = make_memory(content={"city": "shanghai"}, tenant_id="tenant_a")
    mgp_post("/mgp/write", make_request(action="write", payload={"memory": memory}, tenant_id="tenant_a"))

    response = mgp_post(
        "/mgp/get",
        make_request(action="read", payload={"memory_id": memory["memory_id"]}, tenant_id="tenant_b"),
    )
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "MGP_POLICY_DENIED"


def test_internal_memory_returns_full_content(mgp_post, make_memory, make_request):
    memory = make_memory(content={"city": "hangzhou"}, sensitivity="internal")
    mgp_post("/mgp/write", make_request(action="write", payload={"memory": memory}))

    response = mgp_post("/mgp/get", make_request(action="read", payload={"memory_id": memory["memory_id"]}))
    assert response.status_code == 200
    body = response.json()
    assert body["data"]["return_mode"] == "raw"
    assert body["data"]["memory"]["content"]["city"] == "hangzhou"
