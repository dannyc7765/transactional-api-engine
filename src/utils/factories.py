import uuid
from faker import Faker
from src.models.user import UserCreateRequest
from src.models.order import OrderCreateRequest

fake = Faker()

class DataFactory:
    @staticmethod
    def create_user_payload(**overrides) -> UserCreateRequest:
        payload = {
            "username": fake.user_name()[:40],
            "email": fake.unique.email(),
            "initial_deposit": round(fake.pyfloat(min_value=10.0, max_value=1000.0, right_digits=2), 2)
        }
        payload.update(overrides)
        return UserCreateRequest(**payload)

    @staticmethod
    def create_order_payload(user_id: uuid.UUID = None, **overrides) -> OrderCreateRequest:
        payload = {
            "user_id": user_id or uuid.uuid4(),
            "item_id": f"item_{fake.bothify(text='???-####')}",
            "quantity": fake.random_int(min=1, max=10),
            "price": round(fake.pyfloat(min_value=5.0, max_value=250.0, right_digits=2), 2)
        }
        payload.update(overrides)
        return OrderCreateRequest(**payload)
