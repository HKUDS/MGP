from __future__ import annotations


def test_initialize_returns_ready_state(mgp_post):
    response = mgp_post(
        "/mgp/initialize",
        {
            "request_id": "req_init_ready",
            "supported_versions": ["0.1.0"],
            "client": {
                "name": "pytest-client",
                "version": "1.0.0",
                "title": "Pytest Client",
            },
            "requested_profiles": ["core-memory", "lifecycle"],
            "transport_profile": "stateless_http",
            "runtime_capabilities": {
                "supports_consumable_text": True,
                "supports_redaction_info": True,
                "supports_mixed_return_modes": True,
                "supports_partial_failure": True,
                "supports_search_explanations": True,
                "supports_prompt_view": True,
                "supported_profiles": ["core-memory", "lifecycle"],
                "accepted_transport_profiles": ["stateless_http"],
                "preferred_return_modes": ["summary", "masked"],
            },
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["data"]["lifecycle_phase"] == "ready"
    assert body["data"]["chosen_version"] == "0.1.0"
    assert body["data"]["supported_versions"] == ["0.1.0"]
    assert body["data"]["session_mode"] == "stateless"
    assert body["data"]["transport_profile"] == "stateless_http"
    assert body["data"]["protocol_capabilities"]["supports_initialize"] is True
    assert body["data"]["protocol_capabilities"]["supports_runtime_capability_negotiation"] is True
    assert body["data"]["protocol_capabilities"]["requires_initialize"] is False
    assert body["data"]["negotiated_capabilities"]["runtime_capabilities_received"] is True
    assert body["data"]["negotiated_capabilities"]["supports_prompt_view"] is True
    assert body["data"]["negotiated_capabilities"]["effective_return_modes"] == ["summary", "masked"]
    assert "lifecycle" in body["data"]["negotiated_profiles"]


def test_initialize_invalid_payload_returns_bad_request(mgp_post):
    response = mgp_post(
        "/mgp/initialize",
        {
            "request_id": "req_init_invalid",
            "protocol_version": "0.1.0",
        },
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "MGP_INVALID_OBJECT"


def test_initialize_negotiates_first_mutual_version(mgp_post):
    response = mgp_post(
        "/mgp/initialize",
        {
            "request_id": "req_init_negotiate",
            "supported_versions": ["0.3.0", "0.1.0"],
            "preferred_version": "0.3.0",
            "client": {
                "name": "pytest-client",
                "version": "1.0.0",
            },
        },
    )

    assert response.status_code == 200
    body = response.json()
    assert body["data"]["chosen_version"] == "0.1.0"
    assert body["data"]["minimum_supported_version"] == "0.1.0"


def test_initialize_negotiates_runtime_capabilities(mgp_post):
    response = mgp_post(
        "/mgp/initialize",
        {
            "request_id": "req_init_caps",
            "supported_versions": ["0.1.0"],
            "client": {
                "name": "pytest-client",
                "version": "1.0.0",
            },
            "runtime_capabilities": {
                "supports_consumable_text": True,
                "supports_redaction_info": True,
                "supports_mixed_return_modes": True,
                "supports_partial_failure": True,
                "supports_search_explanations": False,
                "supports_prompt_view": False,
                "accepted_transport_profiles": ["stateless_http"],
            },
        },
    )

    assert response.status_code == 200
    negotiated = response.json()["data"]["negotiated_capabilities"]
    assert negotiated["supports_consumable_text"] is True
    assert negotiated["supports_search_explanations"] is False
    assert negotiated["supports_prompt_view"] is False


def test_initialize_unsupported_transport_returns_not_implemented(mgp_post):
    response = mgp_post(
        "/mgp/initialize",
        {
            "request_id": "req_init_transport",
            "protocol_version": "0.1.0",
            "client": {
                "name": "pytest-client",
                "version": "1.0.0",
            },
            "requested_profiles": ["core-memory"],
            "transport_profile": "streamable_http",
        },
    )

    assert response.status_code == 501
    assert response.json()["error"]["code"] == "MGP_UNSUPPORTED_CAPABILITY"


def test_initialize_without_mutual_version_returns_bad_request(mgp_post):
    response = mgp_post(
        "/mgp/initialize",
        {
            "request_id": "req_init_no_version",
            "supported_versions": ["0.3.0", "0.2.0"],
            "preferred_version": "0.3.0",
            "client": {
                "name": "pytest-client",
                "version": "1.0.0",
            },
        },
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "MGP_UNSUPPORTED_VERSION"


def test_initialize_runtime_rejects_transport_returns_not_implemented(mgp_post):
    response = mgp_post(
        "/mgp/initialize",
        {
            "request_id": "req_init_runtime_transport",
            "supported_versions": ["0.1.0"],
            "client": {
                "name": "pytest-client",
                "version": "1.0.0",
            },
            "runtime_capabilities": {
                "accepted_transport_profiles": ["streamable_http"],
            },
        },
    )

    assert response.status_code == 501
    assert response.json()["error"]["code"] == "MGP_UNSUPPORTED_CAPABILITY"


def test_capabilities_is_discovery_only(mgp_get):
    response = mgp_get("/mgp/capabilities")
    assert response.status_code == 200
    body = response.json()
    assert "manifest" in body
    assert "protocol_capabilities" in body
    assert "negotiated_capabilities" not in body


def test_initialize_returns_negotiated_surface_distinct_from_capabilities(mgp_post):
    response = mgp_post(
        "/mgp/initialize",
        {
            "request_id": "req_init_distinct",
            "supported_versions": ["0.1.0"],
            "client": {
                "name": "pytest-client",
                "version": "1.0.0",
            },
            "runtime_capabilities": {
                "supports_prompt_view": True,
                "accepted_transport_profiles": ["stateless_http"],
            },
        },
    )

    assert response.status_code == 200
    body = response.json()["data"]
    assert "protocol_capabilities" in body
    assert "negotiated_capabilities" in body
    assert body["discovery"]["capabilities_uri"] == "/mgp/capabilities"
