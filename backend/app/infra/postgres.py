"""
PostgreSQL connection and schema initialization.

Uses psycopg 3 (sync interface) for simplicity; can be swapped to async later.
"""
from __future__ import annotations

from dataclasses import dataclass

import psycopg
from psycopg.rows import dict_row


@dataclass(frozen=True, slots=True)
class PostgresConfig:
    dsn: str  # e.g. "postgresql://user:pass@host:5432/db"


def connect_postgres(cfg: PostgresConfig) -> psycopg.Connection:
    conn = psycopg.connect(cfg.dsn, row_factory=dict_row, autocommit=False)
    return conn


def init_postgres(conn: psycopg.Connection) -> None:
    """
    Create tables if they don't exist.
    In production, use a migration tool (Alembic). This is for dev/test simplicity.
    """
    with conn.cursor() as cur:
        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS transactions (
                id UUID PRIMARY KEY,
                user_id UUID NOT NULL,
                monto NUMERIC(18, 2) NOT NULL,
                tipo TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TIMESTAMPTZ NOT NULL,
                updated_at TIMESTAMPTZ NOT NULL
            );
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS idempotency_keys (
                key TEXT PRIMARY KEY,
                transaction_id UUID NOT NULL,
                created_at TIMESTAMPTZ NOT NULL
            );
            """
        )

        cur.execute(
            """
            CREATE TABLE IF NOT EXISTS summaries (
                id UUID PRIMARY KEY,
                text TEXT NOT NULL,
                summary TEXT NOT NULL,
                model TEXT,
                request_id TEXT,
                created_at TIMESTAMPTZ NOT NULL
            );
            """
        )

    conn.commit()

