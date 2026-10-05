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
        host: str = "localhost",
        port: int = 5432,
        dbname: str = "engine_db",
        user: str = "test_user",
        password: str = "test_password",
        minconn: int = 1,
        maxconn: int = 10,
    ) -> None:
        self._pool = SimpleConnectionPool(
            minconn=minconn,
            maxconn=maxconn,
            host=host,
            port=port,
            dbname=dbname,
            user=user,
            password=password,
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