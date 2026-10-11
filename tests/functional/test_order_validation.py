from uuid import UUID, uuid4

import pytest

from src.models.user import UserResponse

PRODUCT_ID = "a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11"
START_BALANCE = 100.00


@pytest.fixture
def funded_user(api_client, factory, user_tracker) -> UUID:
    payload = factory.create_user_payload(initial_deposit=START_BALANCE)
    _, user = api_client.post("/users", payload=payload, response_model=UserResponse)
    user_id = UUID(str(user.user_id))
    user_tracker.append(user_id)
    return user_id


@pytest.mark.functional
@pytest.mark.parametrize(
    "price,quantity",
    [(-1000.00, 1), (0, 1), (10.00, 0), (10.00, -1)],
    ids=["negative_price", "zero_price", "zero_quantity", "negative_quantity"],
)
def test_order_rejects_invalid_amounts_and_never_changes_balance(
    api_client, db_client, funded_user, price, quantity
):
    res = api_client._client.post(
        "/orders",
        json={"user_id": str(funded_user), "item_id": "item-x", "quantity": quantity, "price": price},
    )
    assert res.status_code == 422
    assert db_client.get_user_balance(funded_user) == START_BALANCE


@pytest.mark.functional
def test_order_for_unknown_user_returns_404(api_client):
    res = api_client._client.post(
        "/orders",
        json={"user_id": str(uuid4()), "item_id": "item-x", "quantity": 1, "price": 5.00},
    )
    assert res.status_code == 404


@pytest.mark.functional
def test_duplicate_username_returns_409(api_client, factory, funded_user, db_client):
    with db_client.get_cursor() as cur:
        cur.execute("SELECT username FROM users WHERE user_id = %s;", (str(funded_user),))
        existing_username = cur.fetchone()["username"]

    dupe = factory.create_user_payload(username=existing_username)
    res = api_client._client.post("/users", json=dupe.model_dump(mode="json"))
    assert res.status_code == 409


@pytest.mark.functional
def test_purchase_by_unknown_user_returns_404_and_keeps_stock(api_client, db_client):
    db_client.reset_product_stock(PRODUCT_ID, stock=1)
    res = api_client._client.post(
        "/api/v1/orders/purchase", json={"user_id": str(uuid4()), "product_id": PRODUCT_ID}
    )
    assert res.status_code == 404
    assert db_client.get_product_stock(PRODUCT_ID) == 1


@pytest.mark.functional
def test_purchase_with_non_uuid_user_id_returns_422(api_client):
    res = api_client._client.post(
        "/api/v1/orders/purchase", json={"user_id": "not-a-uuid", "product_id": PRODUCT_ID}
    )
    assert res.status_code == 422