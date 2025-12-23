"""
PostgreSQL-backed repository implementations.

Uses psycopg 3 sync interface. Matches the Protocol interfaces in ports.py.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

import psycopg

from app.domain.models import (
    Summary,
    Transaction,
    TransactionStatus,
    TransactionType,
    with_transaction_status,
)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class PostgresTransactionRepo:
    conn: psycopg.Connection

    def clear(self) -> None:
        with self.conn.cursor() as cur:
            cur.execute("DELETE FROM transactions;")
        self.conn.commit()

    def add(self, tx: Transaction) -> None:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO transactions (id, user_id, monto, tipo, status, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s);
                """,
                (
                    tx.id,
                    tx.user_id,
                    tx.monto,
                    tx.tipo.value,
                    tx.status.value,
                    tx.created_at,
                    tx.updated_at,
                ),
            )
        self.conn.commit()

    def get(self, tx_id: UUID) -> Transaction | None:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, user_id, monto, tipo, status, created_at, updated_at
                FROM transactions WHERE id = %s;
                """,
                (tx_id,),
            )
            row = cur.fetchone()

        if row is None:
            return None

        return Transaction(
            id=row["id"],
            user_id=row["user_id"],
            monto=Decimal(row["monto"]),
            tipo=TransactionType(row["tipo"]),
            status=TransactionStatus(row["status"]),
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    def update_status(self, tx_id: UUID, new_status: TransactionStatus) -> Transaction:
        existing = self.get(tx_id)
        if existing is None:
            raise KeyError(f"transaction not found: {tx_id}")

        updated = with_transaction_status(existing, new_status=new_status)
        with self.conn.cursor() as cur:
            cur.execute(
                "UPDATE transactions SET status = %s, updated_at = %s WHERE id = %s;",
                (updated.status.value, updated.updated_at, tx_id),
            )
        self.conn.commit()
        return updated

    def list_all(self, limit: int = 50, offset: int = 0) -> list[Transaction]:
        """Return transactions sorted by created_at descending."""
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, user_id, monto, tipo, status, created_at, updated_at
                FROM transactions
                ORDER BY created_at DESC
                LIMIT %s OFFSET %s;
                """,
                (limit, offset),
            )
            rows = cur.fetchall()

        return [
            Transaction(
                id=row["id"],
                user_id=row["user_id"],
                monto=Decimal(row["monto"]),
                tipo=TransactionType(row["tipo"]),
                status=TransactionStatus(row["status"]),
                created_at=row["created_at"],
                updated_at=row["updated_at"],
            )
            for row in rows
        ]


@dataclass
class PostgresIdempotencyStore:
    conn: psycopg.Connection

    def clear(self) -> None:
        with self.conn.cursor() as cur:
            cur.execute("DELETE FROM idempotency_keys;")
        self.conn.commit()

    def get(self, key: str) -> str | None:
        with self.conn.cursor() as cur:
            cur.execute(
                "SELECT transaction_id FROM idempotency_keys WHERE key = %s;",
                (key,),
            )
            row = cur.fetchone()

        if row is None:
            return None
        return str(row["transaction_id"])

    def put(self, key: str, transaction_id: str) -> None:
        # ON CONFLICT DO NOTHING keeps the first value stable (idempotency semantics).
        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO idempotency_keys (key, transaction_id, created_at)
                VALUES (%s, %s, %s)
                ON CONFLICT (key) DO NOTHING;
                """,
                (key, transaction_id, _utcnow()),
            )
        self.conn.commit()


@dataclass
class PostgresSummaryRepo:
    conn: psycopg.Connection

    def clear(self) -> None:
        with self.conn.cursor() as cur:
            cur.execute("DELETE FROM summaries;")
        self.conn.commit()

    def add(self, s: Summary) -> None:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO summaries (id, text, summary, model, request_id, created_at)
                VALUES (%s, %s, %s, %s, %s, %s);
                """,
                (
                    s.id,
                    s.text,
                    s.summary,
                    s.model,
                    s.request_id,
                    s.created_at,
                ),
            )
        self.conn.commit()

    def get(self, summary_id: UUID) -> Summary | None:
        with self.conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, text, summary, model, request_id, created_at
                FROM summaries WHERE id = %s;
                """,
                (summary_id,),
            )
            row = cur.fetchone()

        if row is None:
            return None

        return Summary(
            id=row["id"],
            text=row["text"],
            summary=row["summary"],
            model=row["model"],
            request_id=row["request_id"],
            created_at=row["created_at"],
        )

