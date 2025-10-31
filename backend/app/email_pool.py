"""Simple SMTP connection pooling for FastAPI."""
from __future__ import annotations

import contextlib
import smtplib
from queue import Empty, Queue
from threading import Lock
from typing import Iterator, Optional

from .config import settings


class SMTPConnectionPool:
    """Maintain a pool of reusable SMTP connections."""

    def __init__(
        self,
        host: str,
        port: int,
        *,
        username: Optional[str] = None,
        password: Optional[str] = None,
        use_tls: bool = False,
        timeout: int = 30,
        max_connections: int = 5,
    ) -> None:
        self._host = host
        self._port = port
        self._username = username
        self._password = password
        self._use_tls = use_tls
        self._timeout = timeout
        self._queue: Queue[smtplib.SMTP] = Queue(max_connections)
        self._lock = Lock()
        self._max_connections = max_connections
        self._created = 0

    def warmup(self) -> None:
        """Pre-create the pool connections."""

        with self._lock:
            while self._created < self._max_connections:
                self._queue.put(self._create_connection())
                self._created += 1

    def close(self) -> None:
        """Close all pooled connections."""

        while True:
            try:
                conn = self._queue.get_nowait()
            except Empty:
                break
            try:
                conn.quit()
            except Exception:
                pass

    def _create_connection(self) -> smtplib.SMTP:
        conn = smtplib.SMTP(self._host, self._port, timeout=self._timeout)
        if self._use_tls:
            conn.starttls()
        if self._username:
            conn.login(self._username, self._password or "")
        return conn

    def _get_connection(self) -> smtplib.SMTP:
        try:
            conn = self._queue.get_nowait()
        except Empty:
            with self._lock:
                if self._created < self._max_connections:
                    conn = self._create_connection()
                    self._created += 1
                else:
                    conn = self._queue.get()
        return conn

    def _release(self, conn: smtplib.SMTP) -> None:
        try:
            self._queue.put_nowait(conn)
        except Exception:
            try:
                conn.quit()
            except Exception:
                pass

    @contextlib.contextmanager
    def acquire(self) -> Iterator[smtplib.SMTP]:
        conn = self._get_connection()
        try:
            yield conn
        except Exception:
            # Drop the connection on error to avoid reusing broken sessions.
            try:
                conn.quit()
            except Exception:
                pass
            with self._lock:
                self._created = max(0, self._created - 1)
        else:
            self._release(conn)


pool = SMTPConnectionPool(
    settings.smtp_host,
    settings.smtp_port,
    username=settings.smtp_username,
    password=settings.smtp_password,
    use_tls=settings.smtp_use_tls,
    timeout=settings.smtp_timeout,
    max_connections=settings.smtp_pool_size,
)
