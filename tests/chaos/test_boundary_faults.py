import time
import httpx
import jwt
import pytest

BASE_URL = "http://127.0.0.1:8000"
JWT_SECRET = "super-secret-key-m3-must-be-at-least-32-bytes-long"


def test_rate_limiting_enforcement():
    with httpx.Client(base_url=BASE_URL) as client:
        status_codes = []
        start_time = time.time()
        for _ in range(100):
            response = client.get("/api/v1/limited/resource")
            status_codes.append(response.status_code)
            if time.time() - start_time > 2.0:
                break

        assert 429 in status_codes, "Rate limiter failed to trigger 429 Too Many Requests"
        assert status_codes.count(429) >= 50, f"Expected high 429 volume, got: {status_codes.count(429)}"


@pytest.mark.parametrize(
    "invalid_header",
    [
        "",
        "Bearer",
        "Bearer null",
        "Bearer malformed.token.signature",
        f"Bearer {jwt.encode({'sub': 'test', 'exp': time.time() - 3600}, JWT_SECRET, algorithm='HS256')}",
        "Basic dXNlcjpwYXNz",
    ],
)
def test_invalid_token_boundary_faults(invalid_header):
    headers = {"Authorization": invalid_header} if invalid_header else {}
    with httpx.Client(base_url=BASE_URL) as client:
        response = client.get("/api/v1/secure/data", headers=headers)
        assert response.status_code == 401, f"Expected 401 for header '{invalid_header}', got {response.status_code}"