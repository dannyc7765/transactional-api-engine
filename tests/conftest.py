import time
import jwt
import uuid
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


@pytest.fixture
def make_token():
    default_secret = os.environ["JWT_SECRET"]

    def _make(secret: str | None = None, **claims) -> str:
        payload = {"sub": "test-user", "exp": int(time.time()) + 3600, **claims}
        return jwt.encode(payload, secret or default_secret, algorithm="HS256")

    return _make

@pytest.fixture
def make_db_user(db_client: DatabaseClient):
    created: list[str] = []

    def _make(balance: str = "100.00") -> str:
        user_id = str(uuid.uuid4())
        name = f"w_{user_id[:8]}"
        with db_client.get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO users (user_id, username, email, wallet_balance) VALUES (%s, %s, %s, %s);",
                    (user_id, name, f"{name}@engine.com", balance),
                )
            conn.commit()
        created.append(user_id)
        return user_id

    yield _make

    with db_client.get_connection() as conn:
        with conn.cursor() as cur:
            for user_id in created:
                cur.execute("DELETE FROM orders WHERE user_id = %s;", (user_id,))
                cur.execute("DELETE FROM users WHERE user_id = %s;", (user_id,))
        conn.commit()


@pytest.fixture
def limited_item(db_client: DatabaseClient):
    product_id = "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11"
    db_client.reset_product_stock(product_id, stock=1)
    yield product_id
    db_client.reset_product_stock(product_id, stock=1)


def pytest_collection_modifyitems(items):
    """Tag every test by its directory so `pytest -m chaos` works and Allure groups by suite."""
    for item in items:
        for suite in ("chaos", "contract", "functional"):
            if item.nodeid.startswith(f"tests/{suite}/"):
                if item.get_closest_marker(suite) is None:
                    item.add_marker(getattr(pytest.mark, suite))
                item.add_marker(pytest.mark.allure_label(suite.capitalize(), label_type="feature"))