import uuid
import pytest
from pydantic import ValidationError
from src.models.order import OrderResponse
from src.models.user import UserCreateRequest

@pytest.mark.contract
class TestContractIntegrity:

    def test_factory_generates_valid_pydantic_instance(self, factory):
        payload = factory.create_user_payload()
        assert isinstance(payload, UserCreateRequest)
        assert payload.initial_deposit > 0

    def test_schema_fails_on_extra_unexpected_field(self):
        raw_response = {
            "order_id": uuid.uuid4(),
            "user_id": uuid.uuid4(),
            "item_id": "item_123",
            "quantity": 2,
            "total_amount": 100.0,
            "status": "CONFIRMED",
            "unexpected_injected_field": "corrupted_payload"
        }
        with pytest.raises(ValidationError) as exc:
            OrderResponse.model_validate(raw_response)
        
        errors = exc.value.errors()
        error_types = [e["type"] for e in errors]
        assert "extra_forbidden" in error_types

    def test_schema_fails_on_type_mismatch(self):
        raw_response = {
            "order_id": uuid.uuid4(),
            "user_id": uuid.uuid4(),
            "item_id": "item_123",
            "quantity": 2,
            "total_amount": "fifty_dollars",
            "status": "CONFIRMED"
        }
        with pytest.raises(ValidationError) as exc:
            OrderResponse.model_validate(raw_response)

        errors = exc.value.errors()
        failed_fields = [e["loc"][0] for e in errors]
        assert "total_amount" in failed_fields

    def test_schema_fails_on_invalid_enum_state(self):
        raw_response = {
            "order_id": uuid.uuid4(),
            "user_id": uuid.uuid4(),
            "item_id": "item_123",
            "quantity": 1,
            "total_amount": 25.0,
            "status": "SHIPPED"
        }
        with pytest.raises(ValidationError) as exc:
            OrderResponse.model_validate(raw_response)

        errors = exc.value.errors()
        failed_fields = [e["loc"][0] for e in errors]
        assert "status" in failed_fields
