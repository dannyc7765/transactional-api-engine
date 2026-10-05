import pytest
from src.client.api_client import ApiClient
from src.database.db_client import DatabaseClient
from src.models.order import OrderCreateRequest, OrderResponse, OrderStatus
from src.models.user import UserCreateRequest, UserResponse
from src.utils.factories import DataFactory


@pytest.mark.functional
def test_order_placement_transactional_integrity(
    api_client: ApiClient,
    db_client: DatabaseClient,
    user_tracker: list,
    order_tracker: list,
) -> None:
    # 1. Arrange & Provision User ($100 balance)
    user_payload: UserCreateRequest = DataFactory.create_user_payload(initial_deposit=100.0)
    user_res, user_data = api_client.post(
        endpoint="/users",
        payload=user_payload,
        response_model=UserResponse,
    )
    assert user_res.status_code == 201
    assert user_data is not None
    user_id = user_data.user_id
    user_tracker.append(user_id)

    # Database Pre-condition State Verification
    db_initial_balance = db_client.get_user_balance(user_id)
    assert db_initial_balance == 100.00

    # 2. Arrange & Execute Order ($40 total: 2 x $20)
    order_payload: OrderCreateRequest = DataFactory.create_order_payload(
        user_id=user_id,
        quantity=2,
        price=20.0,
    )
    order_res, order_data = api_client.post(
        endpoint="/orders",
        payload=order_payload,
        response_model=OrderResponse,
    )

    # 3. HTTP Layer Contract Verification
    assert order_res.status_code == 201
    assert order_data is not None
    assert order_data.user_id == user_id
    assert order_data.total_amount == 40.00
    assert order_data.status == OrderStatus.CONFIRMED
    order_tracker.append(order_data.order_id)

    # 4. Direct Database Dual-Verification State Assertions
    persisted_order = db_client.get_order_by_id(order_data.order_id)
    assert persisted_order is not None
    assert persisted_order["status"] == "CONFIRMED"
    assert float(persisted_order["total_amount"]) == 40.00
    assert str(persisted_order["user_id"]) == str(user_id)

    db_updated_balance = db_client.get_user_balance(user_id)
    assert db_updated_balance == 60.00