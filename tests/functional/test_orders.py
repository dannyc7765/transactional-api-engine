import pytest
from uuid import UUID, uuid4
from src.models.user import UserCreateRequest, UserResponse
from src.models.order import OrderCreateRequest, OrderResponse, OrderStatus

@pytest.fixture
def created_user(api_client, db_client):
    created_user_ids = []
    created_order_ids = []

    def _create(balance: float):
        unique_suffix = uuid4().hex[:8]
        req = UserCreateRequest(
            username=f"user_{unique_suffix}",
            email=f"user_{unique_suffix}@example.com",
            initial_deposit=balance
        )
        _, user = api_client.post("/users", payload=req, response_model=UserResponse)
        user_uuid = UUID(str(user.user_id))
        created_user_ids.append(user_uuid)
        return user, user_uuid

    yield _create, created_order_ids

    # Teardown isolation
    for oid in created_order_ids:
        db_client.delete_order(oid)
    for uid in created_user_ids:
        db_client.delete_user(uid)

def test_order_placement_transactional_integrity(api_client, db_client, created_user):
    create_user_fn, tracked_orders = created_user
    user, user_uuid = create_user_fn(balance=100.00)

    order_req = OrderCreateRequest(
        user_id=user_uuid,
        item_id="item-sku-001",
        quantity=2,
        price=20.00
    )
    res, order = api_client.post("/orders", payload=order_req, response_model=OrderResponse)
    order_uuid = UUID(str(order.order_id))
    tracked_orders.append(order_uuid)

    # 1. API Verification
    assert res.status_code == 201
    assert order.status == OrderStatus.CONFIRMED
    assert order.total_amount == 40.00

    # 2. Database Dual-Verification
    db_balance = db_client.get_user_balance(user_uuid)
    assert db_balance == 60.00

    db_order = db_client.get_order_by_id(order_uuid)
    assert db_order is not None
    assert float(db_order["total_amount"]) == 40.00
    assert db_order["status"] == "CONFIRMED"

def test_insufficient_funds_state_rollback(api_client, db_client, created_user):
    create_user_fn, _ = created_user
    user, user_uuid = create_user_fn(balance=25.00)

    order_req = OrderCreateRequest(
        user_id=user_uuid,
        item_id="item-sku-002",
        quantity=2,
        price=20.00  # Total 40.00 > 25.00
    )

    # 1. API Verification (Client should return HTTP 400)
    res = api_client._client.post("/orders", json=order_req.model_dump(mode="json"))
    assert res.status_code == 400

    # 2. Database Dual-Verification (Balance unchanged, no orders persisted)
    db_balance = db_client.get_user_balance(user_uuid)
    assert db_balance == 25.00

    with db_client.get_cursor() as cursor:
        cursor.execute("SELECT order_id FROM orders WHERE user_id = %s;", (str(user_uuid),))
        orders = cursor.fetchall()
        assert len(orders) == 0
