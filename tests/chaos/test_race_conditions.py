import asyncio
import httpx
import pytest
from src.database.db_client import DatabaseClient

PRODUCT_ID = "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11"
USER_ID = "b1eebc99-9c0b-4ef8-bb6d-6bb9bd380a22"
BASE_URL = "http://127.0.0.1:8000"


@pytest.fixture(autouse=True)
def setup_teardown_state():
    db = DatabaseClient()
    # Ensure test user exists to satisfy foreign key constraints
    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO users (user_id, username, email, wallet_balance)
                VALUES (%s, 'chaos_tester', 'chaos@engine.com', 500.00)
                ON CONFLICT (user_id) DO NOTHING;
                """,
                (USER_ID,)
            )
        conn.commit()

    db.reset_product_stock(PRODUCT_ID, stock=1)
    yield
    db.reset_product_stock(PRODUCT_ID, stock=1)

    # Clean up test orders created during tests
    with db.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM orders WHERE user_id = %s;", (USER_ID,))
            cur.execute("DELETE FROM users WHERE user_id = %s;", (USER_ID,))
        conn.commit()


@pytest.mark.asyncio
async def test_concurrent_purchases_prevent_overselling():
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
        payload = {"user_id": USER_ID, "product_id": PRODUCT_ID}

        # Fire 10 simultaneous requests
        tasks = [client.post("/api/v1/orders/purchase", json=payload) for _ in range(10)]
        responses = await asyncio.gather(*tasks)

    status_codes = [r.status_code for r in responses]

    # Assert exactly 1 acquisition and 9 rejections
    assert status_codes.count(201) == 1, f"Expected exactly one 201, got: {status_codes}"
    assert status_codes.count(409) == 9, f"Expected nine 409s, got: {status_codes}"

    # Assert absolute zero inventory in DB
    db = DatabaseClient()
    assert db.get_product_stock(PRODUCT_ID) == 0


def test_serialized_purchases_baseline():
    """Validates serialized order handling as a baseline comparison."""
    db = DatabaseClient()
    with httpx.Client(base_url=BASE_URL) as client:
        responses = [
            client.post(
                "/api/v1/orders/purchase",
                json={"user_id": USER_ID, "product_id": PRODUCT_ID},
            )
            for _ in range(2)
        ]
    assert responses[0].status_code == 201
    assert responses[1].status_code == 409
    assert db.get_product_stock(PRODUCT_ID) == 0