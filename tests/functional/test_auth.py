import os

import httpx
import pytest

BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")


@pytest.mark.functional
def test_valid_token_returns_data_and_subject(make_token):
    token = make_token(sub="alice")
    response = httpx.get(
        f"{BASE_URL}/api/v1/secure/data",
        headers={"Authorization": f"Bearer {token}"},
        timeout=5.0,
    )
    assert response.status_code == 200
    assert response.json() == {"data": "classified", "user": "alice"}