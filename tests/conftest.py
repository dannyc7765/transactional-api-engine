import os
from typing import Generator
import pytest
from src.client.api_client import ApiClient
from src.database.db_client import DatabaseClient
from src.utils.factories import DataFactory


@pytest.fixture(scope="session")
def api_client() -> Generator[ApiClient, None, None]:
    base_url = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")
    client = ApiClient(base_url=base_url)
    yield client
    client.close()


@pytest.fixture(scope="session")
def db_client() -> Generator[DatabaseClient, None, None]:
    db = DatabaseClient()
    yield db
    db.close()


@pytest.fixture
def entity_tracker(db_client: DatabaseClient) -> Generator[dict, None, None]:
    tracker = {"orders": [], "users": []}
    yield tracker
    # Delete orders first to satisfy foreign key constraints
    for order_id in reversed(tracker["orders"]):
        try:
            db_client.delete_order(order_id)
        except Exception:
            pass

    for user_id in reversed(tracker["users"]):
        try:
            db_client.delete_user(user_id)
        except Exception:
            pass


@pytest.fixture
def user_tracker(entity_tracker: dict) -> list:
    return entity_tracker["users"]


@pytest.fixture
def order_tracker(entity_tracker: dict) -> list:
    return entity_tracker["orders"]


@pytest.fixture
def factory() -> DataFactory:
    return DataFactory()