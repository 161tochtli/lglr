from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal
from uuid import UUID

from app.domain.models import (
    Transaction,
    TransactionStatus,
    TransactionType,
    with_transaction_status,
)


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_dt(value: str) -> datetime:
    # Stored as ISO-8601 with timezone
    return datetime.fromisoformat(value)


@dataclass
class SqliteTransactionRepo:
    conn: sqlite3.Connection

    def clear(self) -> None:
        self.conn.execute("DELETE FROM transactions;")
        self.conn.commit()

    def add(self, tx: Transaction) -> None:
        self.conn.execute(
            """
            INSERT INTO transactions (id, user_id, monto, tipo, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?);
            """,
            (
                str(tx.id),
                str(tx.user_id),
                str(tx.monto),
                tx.tipo.value,
                tx.status.value,
                tx.created_at.isoformat(),
                tx.updated_at.isoformat(),
            ),
        )
        self.conn.commit()

    def get(self, tx_id: UUID) -> Transaction | None:
        row = self.conn.execute(
            "SELECT id, user_id, monto, tipo, status, created_at, updated_at FROM transactions WHERE id = ?;",
            (str(tx_id),),
        ).fetchone()
        if row is None:
            return None

        return Transaction(
            id=UUID(row["id"]),
            user_id=UUID(row["user_id"]),
            monto=Decimal(row["monto"]),
            tipo=TransactionType(row["tipo"]),
            status=TransactionStatus(row["status"]),
            created_at=_parse_dt(row["created_at"]),
            updated_at=_parse_dt(row["updated_at"]),
        )

    def update_status(self, tx_id: UUID, new_status: TransactionStatus) -> Transaction:
        existing = self.get(tx_id)
        if existing is None:
            raise KeyError(f"transaction not found: {tx_id}")

        updated = with_transaction_status(existing, new_status=new_status)
        self.conn.execute(
            "UPDATE transactions SET status = ?, updated_at = ? WHERE id = ?;",
            (updated.status.value, updated.updated_at.isoformat(), str(tx_id)),
        )
        self.conn.commit()
        return updated

    def list_all(self, limit: int = 50, offset: int = 0) -> list[Transaction]:
        """Return transactions sorted by created_at descending."""
        rows = self.conn.execute(
            """
            SELECT id, user_id, monto, tipo, status, created_at, updated_at
            FROM transactions
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?;
            """,
            (limit, offset),
        ).fetchall()
        return [
            Transaction(
                id=UUID(row["id"]),
                user_id=UUID(row["user_id"]),
                monto=Decimal(row["monto"]),
                tipo=TransactionType(row["tipo"]),
                status=TransactionStatus(row["status"]),
                created_at=_parse_dt(row["created_at"]),
                updated_at=_parse_dt(row["updated_at"]),
            )
            for row in rows
        ]


@dataclass
class SqliteIdempotencyStore:
    conn: sqlite3.Connection

    def clear(self) -> None:
        self.conn.execute("DELETE FROM idempotency_keys;")
        self.conn.commit()

    def get(self, key: str) -> str | None:
        row = self.conn.execute(
            "SELECT transaction_id FROM idempotency_keys WHERE key = ?;",
            (key,),
        ).fetchone()
        if row is None:
            return None
        return str(row["transaction_id"])

    def put(self, key: str, transaction_id: str) -> None:
        # If key already exists, keep the first value stable (idempotency semantics).
        self.conn.execute(
            """
            INSERT OR IGNORE INTO idempotency_keys (key, transaction_id, created_at)
            VALUES (?, ?, ?);
            """,
            (key, transaction_id, _utcnow_iso()),
        )
        self.conn.commit()



