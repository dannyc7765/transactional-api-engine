import os
import time
import httpx
import jwt
import pytest

BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")


def test_rate_limiting_enforcement():
    with httpx.Client(base_url=BASE_URL, timeout=5.0) as client:
        status_codes = [client.get("/api/v1/limited/resource").status_code for _ in range(60)]

    assert 429 in status_codes, "Rate limiter failed to trigger 429 Too Many Requests"
    assert 200 in status_codes, "Initial requests in window should succeed with 200 OK"
    # 30 allowed per 2.0s window -> exactly 30 allowed, remaining 30 rejected
    assert status_codes.count(429) >= 25, f"Expected at least 25 rate-limited responses, got: {status_codes.count(429)}"


@pytest.mark.parametrize(
    "invalid_header",
    [
        "",
        "Bearer",
        "Bearer null",
        "Bearer malformed.token.signature",
        "Basic dXNlcjpwYXNz",
    ],
)
def test_invalid_token_boundary_faults(invalid_header: str):
    headers = {"Authorization": invalid_header} if invalid_header else {}
    with httpx.Client(base_url=BASE_URL, timeout=5.0) as client:
        response = client.get("/api/v1/secure/data", headers=headers)
        assert response.status_code == 401, f"Expected 401 for header '{invalid_header}', got {response.status_code}"


def test_malformed_json_payload_rejection():
    with httpx.Client(base_url=BASE_URL, timeout=5.0) as client:
        response = client.post(
            "/api/v1/orders/purchase",
            content=b'{"user_id": "b1eebc99", "product_id": ',
            headers={"Content-Type": "application/json"},
        )
        assert response.status_code == 422


def test_missing_required_payload_fields():
    with httpx.Client(base_url=BASE_URL, timeout=5.0) as client:
        response = client.post(
            "/api/v1/orders/purchase",
            json={"user_id": "b1eebc99-9c0b-4ef8-bb6d-6bb9bd380a22"},
        )
        assert response.status_code == 422


def test_client_timeout_handling():
    with httpx.Client(base_url=BASE_URL, timeout=0.5) as client:
        with pytest.raises(httpx.TimeoutException):
            client.get("/api/v1/chaos/delay")


def _get_secure(token: str) -> httpx.Response:
    with httpx.Client(base_url=BASE_URL, timeout=5.0) as client:
        return client.get("/api/v1/secure/data", headers={"Authorization": f"Bearer {token}"})


@pytest.mark.chaos
def test_expired_token_rejected_while_valid_one_passes(make_token):
    # Same secret and claims. Expiry is the ONLY difference, so the 401 can only come from expiry.
    assert _get_secure(make_token()).status_code == 200
    assert _get_secure(make_token(exp=int(time.time()) - 3600)).status_code == 401


@pytest.mark.chaos
def test_token_signed_with_wrong_secret_rejected(make_token):
    assert _get_secure(make_token(secret="x" * 40)).status_code == 401


@pytest.mark.chaos
def test_alg_none_token_rejected():
    forged = jwt.encode({"sub": "attacker", "exp": int(time.time()) + 3600}, "", algorithm="none")
    assert _get_secure(forged).status_code == 401