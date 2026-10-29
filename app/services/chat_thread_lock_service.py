"""Cross-worker lock for one chat thread's read, execution and state write."""
from __future__ import annotations

import hashlib
import time

import psycopg
from fastapi import HTTPException

from app.config import settings


class ChatThreadLock:
    def __init__(self, thread_id: str, timeout_seconds: float = 5.0):
        self._key = int.from_bytes(hashlib.sha256(thread_id.encode()).digest()[:8], "big", signed=True)
        self._timeout_seconds = timeout_seconds
        self._conn: psycopg.Connection | None = None

    def acquire(self) -> "ChatThreadLock":
        deadline = time.monotonic() + self._timeout_seconds
        try:
            self._conn = psycopg.connect(settings.database_url, autocommit=True, connect_timeout=3)
            while True:
                row = self._conn.execute("SELECT pg_try_advisory_lock(%s)", (self._key,)).fetchone()
                if row and row[0]:
                    return self
                if time.monotonic() >= deadline:
                    raise HTTPException(
                        status_code=423,
                        detail="此会话正在处理上一条消息，请稍后重试",
                        headers={"Retry-After": "1"},
                    )
                time.sleep(0.05)
        except BaseException:
            self.release()
            raise

    def release(self) -> None:
        conn, self._conn = self._conn, None
        if conn is not None:
            try:
                conn.execute("SELECT pg_advisory_unlock(%s)", (self._key,))
            finally:
                conn.close()

    def __enter__(self) -> "ChatThreadLock":
        return self.acquire()

    def __exit__(self, *_exc: object) -> None:
        self.release()
