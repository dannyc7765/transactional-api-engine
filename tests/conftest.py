import pytest
from src.client.api_client import ApiClient
from src.utils.factories import DataFactory

@pytest.fixture(scope="session")
def api_client():
    client = ApiClient(base_url="http://localhost:8000", auth_token="test_token_xyz")
    yield client
    client.close()

@pytest.fixture
def factory():
    return DataFactory
