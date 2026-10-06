import asyncio
import os
import time
from collections import defaultdict
from uuid import UUID, uuid4

import jwt
import psycopg2
from fastapi import FastAPI, Header, HTTPException, Request, status
from fastapi.responses import JSONResponse
from psycopg2.extras import RealDictCursor

from src.models.order import OrderCreateRequest, OrderResponse, OrderStatus
from src.models.product import PurchaseRequest
from src.models.user import UserCreateRequest, UserResponse

app = FastAPI(title="Transactional API Engine")

DB_HOST = os.getenv("DB_HOST", "127.0.0.1")
DB_PORT = int(os.getenv("DB_PORT", "5439"))
DB_NAME = os.getenv("DB_NAME", "engine_db")
DB_USER = os.getenv("DB_USER", "test_user")
DB_PASSWORD = os.getenv("DB_PASSWORD", "test_password")

JWT_SECRET = os.getenv("JWT_SECRET", "super-secret-key-m3-must-be-at-least-32-bytes-long")
JWT_ALGORITHM = "HS256"

RATE_LIMIT_STORE = defaultdict(list)
RATE_LIMIT_CAPACITY = 30
RATE_LIMIT_WINDOW = 2.0


def get_db():
    return psycopg2.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
    )


@app.middleware("http")
async def rate_limiting_middleware(request: Request, call_next):
    if request.url.path.startswith("/api/v1/limited"):
        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        timestamps = RATE_LIMIT_STORE[client_ip]
        RATE_LIMIT_STORE[client_ip] = [ts for ts in timestamps if now - ts < RATE_LIMIT_WINDOW]

        if len(RATE_LIMIT_STORE[client_ip]) >= RATE_LIMIT_CAPACITY:
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": "Rate limit exceeded"},
            )
        RATE_LIMIT_STORE[client_ip].append(now)

    response = await call_next(request)
    return response


# --- Milestone 1 & 2 Endpoints ---

@app.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(payload: UserCreateRequest):
    user_id = uuid4()
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO users (user_id, username, email, wallet_balance) VALUES (%s, %s, %s, %s);",
                (str(user_id), payload.username, payload.email, payload.initial_deposit),
            )
        conn.commit()
    return UserResponse(
        user_id=user_id,
        username=payload.username,
        email=payload.email,
        wallet_balance=payload.initial_deposit,
    )


@app.post("/orders", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
def create_order(payload: OrderCreateRequest):
    order_id = uuid4()
    total_amount = round(payload.quantity * payload.price, 2)
    with get_db() as conn:
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute(
                "SELECT wallet_balance FROM users WHERE user_id = %s FOR UPDATE;",
                (str(payload.user_id),),
            )
            user = cur.fetchone()
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            if float(user["wallet_balance"]) < total_amount:
                raise HTTPException(status_code=400, detail="Insufficient funds")

            new_balance = float(user["wallet_balance"]) - total_amount
            cur.execute(
                "UPDATE users SET wallet_balance = %s WHERE user_id = %s;",
                (new_balance, str(payload.user_id)),
            )
            cur.execute(
                "INSERT INTO orders (order_id, user_id, item_id, quantity, total_amount, status) VALUES (%s, %s, %s, %s, %s, %s);",
                (
                    str(order_id),
                    str(payload.user_id),
                    payload.item_id,
                    payload.quantity,
                    total_amount,
                    OrderStatus.CONFIRMED.value,
                ),
            )
        conn.commit()

    return OrderResponse(
        order_id=order_id,
        user_id=payload.user_id,
        item_id=payload.item_id,
        quantity=payload.quantity,
        total_amount=total_amount,
        status=OrderStatus.CONFIRMED,
    )


# --- Milestone 3 Endpoints ---

@app.post("/api/v1/orders/purchase", status_code=status.HTTP_201_CREATED)
def purchase_product(request: PurchaseRequest):
    conn = get_db()
    try:
        with conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    "SELECT stock, price FROM products WHERE product_id = %s FOR UPDATE;",
                    (str(request.product_id),),
                )
                product = cur.fetchone()
                if not product:
                    raise HTTPException(status_code=404, detail="Product not found")

                if product["stock"] <= 0:
                    raise HTTPException(
                        status_code=status.HTTP_409_CONFLICT,
                        detail="Item out of stock",
                    )

                cur.execute(
                    "UPDATE products SET stock = stock - 1 WHERE product_id = %s;",
                    (str(request.product_id),),
                )

                order_id = uuid4()
                cur.execute(
                    """
                    INSERT INTO orders (order_id, user_id, item_id, quantity, total_amount, status)
                    VALUES (%s, %s, %s, 1, %s, 'CONFIRMED');
                    """,
                    (str(order_id), str(request.user_id), str(request.product_id), product["price"]),
                )
        return {"order_id": str(order_id), "status": "CONFIRMED"}
    except HTTPException:
        raise
    except Exception as e:
        conn.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        conn.close()


@app.get("/api/v1/limited/resource")
def rate_limited_endpoint():
    return {"message": "Success within quota"}


@app.get("/api/v1/secure/data")
def secure_endpoint(authorization: str | None = Header(default=None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or malformed Authorization header",
        )
    token = authorization.split(" ")[1].strip()
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Empty token")
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return {"data": "classified", "user": payload.get("sub")}
    except jwt.PyJWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token"
        )


@app.get("/api/v1/chaos/delay")
async def delayed_endpoint():
    await asyncio.sleep(2.0)
    return {"status": "delayed_ok"}