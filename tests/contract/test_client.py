import pytest
import httpx
from src.client.api_client import ApiClient, APIClientError, SchemaValidationError
from src.models.user import UserResponse

def test_client_raises_api_client_error_on_connection_drop():
    # Target an unreachable port to trigger connection drop
    client = ApiClient(base_url="http://127.0.0.1:59999", timeout=0.5)
    with pytest.raises(APIClientError):
        client.get("/nonexistent")
    client.close()

def test_client_schema_validation_error_on_mismatched_response(monkeypatch):
    client = ApiClient(base_url="http://mock-api.local")
    
    # Mock httpx.Client.request to return 200 with invalid contract payload
    invalid_payload = {"invalid_key": "data"}
    mock_resp = httpx.Response(
        status_code=200, 
        json=invalid_payload, 
        request=httpx.Request("GET", "http://mock-api.local/users/1")
    )
    monkeypatch.setattr(client._client, "request", lambda *args, **kwargs: mock_resp)

    with pytest.raises(SchemaValidationError):
        client.get("/users/1", response_model=UserResponse)
    client.close()
