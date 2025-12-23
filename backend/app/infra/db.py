import sqlite3
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SqliteConfig:
    path: str = ":memory:"


def connect_sqlite(cfg: SqliteConfig) -> sqlite3.Connection:
    # check_same_thread=False is important because FastAPI TestClient executes
    # requests in a different thread than the test thread.
    conn = sqlite3.connect(cfg.path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn


def init_sqlite(conn: sqlite3.Connection) -> None:
    # Minimal schema for Phase 1.
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS transactions (
            id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            monto TEXT NOT NULL,
            tipo TEXT NOT NULL,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );
        """
    )

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS idempotency_keys (
            key TEXT PRIMARY KEY,
            transaction_id TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        """
    )

    conn.commit()



