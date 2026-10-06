import os
import asyncio
import uuid
import httpx
import pytest
from src.database.db_client import DatabaseClient

PRODUCT_ID = "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11"
BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")


@pytest.fixture
def chaos_user(db_client: DatabaseClient):
    user_id = str(uuid.uuid4())
    username = f"chaos_{user_id[:8]}"
    email = f"{username}@engine.com"

    with db_client.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO users (user_id, username, email, wallet_balance)
                VALUES (%s, %s, %s, 1000.00);
                """,
                (user_id, username, email),
            )
        conn.commit()

    db_client.reset_product_stock(PRODUCT_ID, stock=1)
    yield user_id

    # Teardown: clear orders before deleting user
    with db_client.get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM orders WHERE user_id = %s;", (user_id,))
            cur.execute("DELETE FROM users WHERE user_id = %s;", (user_id,))
        conn.commit()
    db_client.reset_product_stock(PRODUCT_ID, stock=1)


@pytest.mark.asyncio
async def test_concurrent_purchases_prevent_overselling(chaos_user: str, db_client: DatabaseClient):
    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
        payload = {"user_id": chaos_user, "product_id": PRODUCT_ID}
        tasks = [client.post("/api/v1/orders/purchase", json=payload) for _ in range(10)]
        responses = await asyncio.gather(*tasks)

    status_codes = [r.status_code for r in responses]

    assert status_codes.count(201) == 1, f"Expected exactly one 201, got: {status_codes}"
    assert status_codes.count(409) == 9, f"Expected nine 409s, got: {status_codes}"
    assert db_client.get_product_stock(PRODUCT_ID) == 0


def test_serialized_purchases_baseline(chaos_user: str, db_client: DatabaseClient):
    with httpx.Client(base_url=BASE_URL, timeout=5.0) as client:
        responses = [
            client.post(
                "/api/v1/orders/purchase",
                json={"user_id": chaos_user, "product_id": PRODUCT_ID},
            )
            for _ in range(2)
        ]

    assert responses[0].status_code == 201
    assert responses[1].status_code == 409
    assert db_client.get_product_stock(PRODUCT_ID) == 0