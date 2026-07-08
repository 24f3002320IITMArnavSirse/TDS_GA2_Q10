import uuid

from fastapi.testclient import TestClient

from main import ASSIGNED_ORIGIN, RATE_LIMIT, app


client = TestClient(app)


def test_supplied_request_id_is_reused_in_body_and_header():
    response = client.get(
        "/ping",
        headers={
            "X-Request-ID": "fixed-test-request-id",
            "X-Client-Id": "request-id-test-client",
        },
    )

    assert response.status_code == 200
    assert response.json()["request_id"] == "fixed-test-request-id"
    assert response.headers["X-Request-ID"] == "fixed-test-request-id"
    assert response.json()["request_id"] == response.headers["X-Request-ID"]


def test_generated_request_ids_are_unique_and_returned_in_body_and_header():
    response_1 = client.get("/ping", headers={"X-Client-Id": "generated-id-client-1"})
    response_2 = client.get("/ping", headers={"X-Client-Id": "generated-id-client-2"})

    assert response_1.status_code == 200
    assert response_2.status_code == 200

    request_id_1 = response_1.json()["request_id"]
    request_id_2 = response_2.json()["request_id"]

    assert request_id_1
    assert request_id_2
    assert request_id_1 == response_1.headers["X-Request-ID"]
    assert request_id_2 == response_2.headers["X-Request-ID"]
    assert request_id_1 != request_id_2
    uuid.UUID(request_id_1)
    uuid.UUID(request_id_2)


def test_per_client_rate_limit_is_independent():
    for index in range(RATE_LIMIT):
        response = client.get("/ping", headers={"X-Client-Id": "grader-client-a"})
        assert response.status_code == 200, index

    limited_response = client.get("/ping", headers={"X-Client-Id": "grader-client-a"})
    assert limited_response.status_code == 429

    other_client_response = client.get(
        "/ping", headers={"X-Client-Id": "grader-client-b"}
    )
    assert other_client_response.status_code == 200


def test_allowed_cors_origin_receives_acao_header():
    response = client.get(
        "/ping",
        headers={
            "Origin": ASSIGNED_ORIGIN,
            "X-Client-Id": "allowed-cors-client",
        },
    )

    assert response.status_code == 200
    assert response.headers["Access-Control-Allow-Origin"] == ASSIGNED_ORIGIN


def test_disallowed_cors_origin_does_not_receive_acao_header():
    response = client.get(
        "/ping",
        headers={
            "Origin": "https://evil.example.com",
            "X-Client-Id": "disallowed-cors-client",
        },
    )

    assert response.status_code == 200
    assert "Access-Control-Allow-Origin" not in response.headers


def test_cors_preflight_succeeds_for_allowed_origin():
    response = client.options(
        "/ping",
        headers={
            "Origin": ASSIGNED_ORIGIN,
            "Access-Control-Request-Method": "GET",
            "Access-Control-Request-Headers": "X-Request-ID,X-Client-Id",
        },
    )

    assert 200 <= response.status_code < 300
    assert response.headers["Access-Control-Allow-Origin"] == ASSIGNED_ORIGIN
    assert "GET" in response.headers["Access-Control-Allow-Methods"]
    assert "X-Request-ID" in response.headers["Access-Control-Allow-Headers"]
    assert "X-Client-Id" in response.headers["Access-Control-Allow-Headers"]


def test_options_preflight_does_not_consume_rate_limit_bucket():
    headers = {
        "Origin": ASSIGNED_ORIGIN,
        "Access-Control-Request-Method": "GET",
        "Access-Control-Request-Headers": "X-Request-ID,X-Client-Id",
        "X-Client-Id": "preflight-rate-client",
    }

    for _ in range(RATE_LIMIT + 5):
        response = client.options("/ping", headers=headers)
        assert 200 <= response.status_code < 300

    for index in range(RATE_LIMIT):
        response = client.get("/ping", headers={"X-Client-Id": "preflight-rate-client"})
        assert response.status_code == 200, index

    limited_response = client.get(
        "/ping", headers={"X-Client-Id": "preflight-rate-client"}
    )
    assert limited_response.status_code == 429
