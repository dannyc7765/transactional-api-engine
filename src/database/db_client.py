import os
import logging
from contextlib import contextmanager
from typing import Any, Dict, Generator, Optional
from uuid import UUID
import psycopg2
from psycopg2.extras import RealDictCursor
from psycopg2.pool import SimpleConnectionPool

logger = logging.getLogger("database_client")


class DatabaseClient:
    def __init__(
        self,
        host: Optional[str] = None,
        port: Optional[int] = None,
        dbname: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None,
        minconn: int = 1,
        maxconn: int = 10,
    ) -> None:
        self.host = host or os.getenv("DB_HOST", "127.0.0.1")
        self.port = port or int(os.getenv("DB_PORT", "5439"))
        self.dbname = dbname or os.getenv("DB_NAME", "engine_db")
        self.user = user or os.getenv("DB_USER", "test_user")
        self.password = password or os.getenv("DB_PASSWORD", "test_password")

        self._pool = SimpleConnectionPool(
            minconn=minconn,
            maxconn=maxconn,
            host=self.host,
            port=self.port,
            dbname=self.dbname,
            user=self.user,
            password=self.password,
        )

    def close(self) -> None:
        if self._pool and not self._pool.closed:
            self._pool.closeall()
            logger.info("Database connection pool closed.")

    @contextmanager
    def get_connection(self) -> Generator[psycopg2.extensions.connection, None, None]:
        conn = self._pool.getconn()
        try:
            yield conn
        finally:
            self._pool.putconn(conn)

    @contextmanager
    def get_cursor(self) -> Generator[RealDictCursor, None, None]:
        with self.get_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cursor:
                yield cursor

    def get_user_balance(self, user_id: UUID) -> Optional[float]:
        query = "SELECT wallet_balance FROM users WHERE user_id = %s;"
        with self.get_cursor() as cursor:
            cursor.execute(query, (str(user_id),))
            row = cursor.fetchone()
            if row is not None:
                return float(row["wallet_balance"])
            return None

    def get_order_by_id(self, order_id: UUID) -> Optional[Dict[str, Any]]:
        query = "SELECT order_id, user_id, item_id, quantity, total_amount, status FROM orders WHERE order_id = %s;"
        with self.get_cursor() as cursor:
            cursor.execute(query, (str(order_id),))
            row = cursor.fetchone()
            if row is not None:
                return dict(row)
            return None

    def delete_order(self, order_id: UUID) -> None:
        query = "DELETE FROM orders WHERE order_id = %s;"
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, (str(order_id),))
            conn.commit()

    def delete_user(self, user_id: UUID) -> None:
        query = "DELETE FROM users WHERE user_id = %s;"
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(query, (str(user_id),))
            conn.commit()

    def get_product_stock(self, product_id: str) -> int:
        with self.get_cursor() as cursor:
            cursor.execute("SELECT stock FROM products WHERE product_id = %s;", (str(product_id),))
            row = cursor.fetchone()
            if not row:
                raise ValueError(f"Product {product_id} not found")
            return int(row["stock"])

    def reset_product_stock(self, product_id: str, stock: int = 1) -> None:
        with self.get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "UPDATE products SET stock = %s WHERE product_id = %s;",
                    (stock, str(product_id)),
                )
            conn.commit()