from typing import Generator
import pytest
from src.client.api_client import ApiClient
from src.database.db_client import DatabaseClient
from src.utils.factories import DataFactory


@pytest.fixture(scope="session")
def api_client() -> Generator[ApiClient, None, None]:
    client = ApiClient(base_url="http://localhost:8000")
    yield client
    client.close()


@pytest.fixture(scope="session")
def db_client() -> Generator[DatabaseClient, None, None]:
    db = DatabaseClient(
        host="localhost",
        port=5432,
        dbname="engine_db",
        user="test_user",
        password="test_password",
    )
    yield db
    db.close()


@pytest.fixture
def user_tracker(db_client: DatabaseClient) -> Generator[list, None, None]:
    created_user_ids = []
    yield created_user_ids
    for user_id in reversed(created_user_ids):
        db_client.delete_user(user_id)


@pytest.fixture
def order_tracker(db_client: DatabaseClient) -> Generator[list, None, None]:
    created_order_ids = []
    yield created_order_ids
    for order_id in reversed(created_order_ids):
        db_client.delete_order(order_id)