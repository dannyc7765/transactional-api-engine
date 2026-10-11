import asyncio
import os
import uuid

import allure
import httpx
import pytest

BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")


def _order_count(db_client, user_id: str) -> int:
    with db_client.get_cursor() as cur:
        cur.execute("SELECT count(*) AS n FROM orders WHERE user_id = %s;", (user_id,))
        return cur.fetchone()["n"]


@allure.severity(allure.severity_level.BLOCKER)
@allure.title("10 concurrent $30 orders on a $100 wallet: exactly 3 succeed, balance ends at $10")
@pytest.mark.asyncio
async def test_concurrent_orders_never_overdraw_wallet(make_db_user, db_client):
    user_id = make_db_user("100.00")
    body = {"user_id": user_id, "item_id": "item-x", "quantity": 1, "price": "30.00"}

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
        responses = await asyncio.gather(*[client.post("/orders", json=body) for _ in range(10)])

    codes = [r.status_code for r in responses]
    assert codes.count(201) == 3, codes
    assert codes.count(400) == 7, codes
    assert db_client.get_user_balance(uuid.UUID(user_id)) == 10.00
    assert _order_count(db_client, user_id) == 3


@allure.severity(allure.severity_level.BLOCKER)
@allure.title("8 different users race for 1 item: exactly one is charged, seven are not")
@pytest.mark.asyncio
async def test_concurrent_purchases_by_different_users_charge_exactly_one(
    make_db_user, db_client, limited_item
):
    users = [make_db_user("100.00") for _ in range(8)]

    async with httpx.AsyncClient(base_url=BASE_URL, timeout=10.0) as client:
        responses = await asyncio.gather(
            *[
                client.post("/api/v1/orders/purchase", json={"user_id": u, "product_id": limited_item})
                for u in users
            ]
        )

    codes = [r.status_code for r in responses]
    assert codes.count(201) == 1, codes
    assert codes.count(409) == 7, codes
    balances = sorted(db_client.get_user_balance(uuid.UUID(u)) for u in users)
    assert balances == [90.0] + [100.0] * 7
    assert db_client.get_product_stock(limited_item) == 0