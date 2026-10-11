import uuid

import allure

PURCHASE = "/api/v1/orders/purchase"


@allure.severity(allure.severity_level.CRITICAL)
def test_purchase_charges_wallet_and_decrements_stock(api_client, make_db_user, db_client, limited_item):
    user_id = make_db_user("100.00")

    res = api_client._client.post(PURCHASE, json={"user_id": user_id, "product_id": limited_item})

    assert res.status_code == 201
    assert db_client.get_user_balance(uuid.UUID(user_id)) == 90.00
    assert db_client.get_product_stock(limited_item) == 0
    order = db_client.get_order_by_id(uuid.UUID(res.json()["order_id"]))
    assert float(order["total_amount"]) == 10.00


@allure.severity(allure.severity_level.CRITICAL)
def test_purchase_with_insufficient_funds_changes_nothing(api_client, make_db_user, db_client, limited_item):
    user_id = make_db_user("5.00")

    res = api_client._client.post(PURCHASE, json={"user_id": user_id, "product_id": limited_item})

    assert res.status_code == 400
    assert db_client.get_user_balance(uuid.UUID(user_id)) == 5.00
    assert db_client.get_product_stock(limited_item) == 1
    with db_client.get_cursor() as cur:
        cur.execute("SELECT count(*) AS n FROM orders WHERE user_id = %s;", (user_id,))
        assert cur.fetchone()["n"] == 0