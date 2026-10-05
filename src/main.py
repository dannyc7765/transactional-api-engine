import os
from uuid import UUID, uuid4
from fastapi import FastAPI, HTTPException, status
import psycopg2
from psycopg2.extras import RealDictCursor
from src.models.user import UserCreateRequest, UserResponse
from src.models.order import OrderCreateRequest, OrderResponse, OrderStatus

app = FastAPI()

DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("DB_PORT", "5439"))
DB_NAME = os.getenv("DB_NAME", "engine_db")
DB_USER = os.getenv("DB_USER", "test_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "test_password")

def get_db():
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD
    )

@app.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreateRequest):
    user_id = uuid4()
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO users (user_id, username, email, wallet_balance) VALUES (%s, %s, %s, %s);",
                (str(user_id), payload.username, payload.email, payload.initial_deposit)
            )
        conn.commit()
    return UserResponse(
        user_id=user_id,
        username=payload.username,
        email=payload.email,
        wallet_balance=payload.initial_deposit
    )

@app.post("/orders", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
def create_order(payload: OrderCreateRequest):
    order_id = uuid4()
    total_amount = round(payload.quantity * payload.price, 2)
    with get_db() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("SELECT wallet_balance FROM users WHERE user_id = %s FOR UPDATE;", (str(payload.user_id),))
            user = cur.fetchone()
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            if float(user["wallet_balance"]) < total_amount:
                raise HTTPException(status_code=400, detail="Insufficient funds")

            new_balance = float(user["wallet_balance"]) - total_amount
            cur.execute("UPDATE users SET wallet_balance = %s WHERE user_id = %s;", (new_balance, str(payload.user_id)))
            cur.execute(
                "INSERT INTO orders (order_id, user_id, item_id, quantity, total_amount, status) VALUES (%s, %s, %s, %s, %s, %s);",
                (str(order_id), str(payload.user_id), payload.item_id, payload.quantity, total_amount, OrderStatus.CONFIRMED.value)
            )
        conn.commit()

    return OrderResponse(
        order_id=order_id,
        user_id=payload.user_id,
        item_id=payload.item_id,
        quantity=payload.quantity,
        total_amount=total_amount,
        status=OrderStatus.CONFIRMED
    )
