from psycopg_pool import ConnectionPool
from contextlib import contextmanager

from app.config import settings


pool = ConnectionPool(
    conninfo=settings.database_url,
    min_size=1,
    max_size=5,
    open=False,
)


def open_pool():
    pool.open()


def close_pool():
    pool.close()


def fetch_one(query: str, params: tuple | dict | None = None):
    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            return cur.fetchone()


def fetch_all(query: str, params: tuple | dict | None = None):
    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
            return cur.fetchall()


def execute(query: str, params: tuple | dict | None = None):
    with pool.connection() as conn:
        with conn.cursor() as cur:
            cur.execute(query, params)
        conn.commit()


@contextmanager
def transaction():
    with pool.connection() as conn:
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
