"""Слой работы с SQLite (aiosqlite). Одна база — две таблицы: users и orders."""

from dataclasses import dataclass
from pathlib import Path

import aiosqlite

SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    user_id    INTEGER PRIMARY KEY,
    username   TEXT,
    first_seen TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS orders (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id    INTEGER NOT NULL,
    username   TEXT,
    service    TEXT NOT NULL,
    details    TEXT NOT NULL,
    phone      TEXT NOT NULL,
    status     TEXT NOT NULL DEFAULT 'new',
    paid       INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""


@dataclass
class Order:
    id: int
    user_id: int
    username: str | None
    service: str
    details: str
    phone: str
    status: str
    paid: bool
    created_at: str


def _row_to_order(row: aiosqlite.Row) -> Order:
    return Order(
        id=row["id"],
        user_id=row["user_id"],
        username=row["username"],
        service=row["service"],
        details=row["details"],
        phone=row["phone"],
        status=row["status"],
        paid=bool(row["paid"]),
        created_at=row["created_at"],
    )


class Database:
    def __init__(self, path: str) -> None:
        self._path = path

    async def init(self) -> None:
        Path(self._path).parent.mkdir(parents=True, exist_ok=True)
        async with aiosqlite.connect(self._path) as db:
            await db.executescript(SCHEMA)
            await db.commit()

    async def upsert_user(self, user_id: int, username: str | None) -> None:
        async with aiosqlite.connect(self._path) as db:
            await db.execute(
                "INSERT INTO users (user_id, username) VALUES (?, ?) "
                "ON CONFLICT(user_id) DO UPDATE SET username = excluded.username",
                (user_id, username),
            )
            await db.commit()

    async def all_user_ids(self) -> list[int]:
        async with aiosqlite.connect(self._path) as db:
            async with db.execute("SELECT user_id FROM users") as cur:
                return [row[0] async for row in cur]

    async def add_order(
        self, user_id: int, username: str | None, service: str, details: str, phone: str
    ) -> int:
        async with aiosqlite.connect(self._path) as db:
            cur = await db.execute(
                "INSERT INTO orders (user_id, username, service, details, phone) "
                "VALUES (?, ?, ?, ?, ?)",
                (user_id, username, service, details, phone),
            )
            await db.commit()
            return cur.lastrowid

    async def get_order(self, order_id: int) -> Order | None:
        async with aiosqlite.connect(self._path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute("SELECT * FROM orders WHERE id = ?", (order_id,)) as cur:
                row = await cur.fetchone()
                return _row_to_order(row) if row else None

    async def orders_by_status(self, status: str, limit: int = 10) -> list[Order]:
        async with aiosqlite.connect(self._path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM orders WHERE status = ? ORDER BY id DESC LIMIT ?",
                (status, limit),
            ) as cur:
                return [_row_to_order(row) async for row in cur]

    async def orders_by_user(self, user_id: int, limit: int = 10) -> list[Order]:
        async with aiosqlite.connect(self._path) as db:
            db.row_factory = aiosqlite.Row
            async with db.execute(
                "SELECT * FROM orders WHERE user_id = ? ORDER BY id DESC LIMIT ?",
                (user_id, limit),
            ) as cur:
                return [_row_to_order(row) async for row in cur]

    async def set_status(self, order_id: int, status: str) -> None:
        async with aiosqlite.connect(self._path) as db:
            await db.execute("UPDATE orders SET status = ? WHERE id = ?", (status, order_id))
            await db.commit()

    async def set_paid(self, order_id: int) -> None:
        async with aiosqlite.connect(self._path) as db:
            await db.execute("UPDATE orders SET paid = 1 WHERE id = ?", (order_id,))
            await db.commit()

    async def stats(self) -> dict[str, int]:
        async with aiosqlite.connect(self._path) as db:
            result: dict[str, int] = {}
            async with db.execute("SELECT COUNT(*) FROM users") as cur:
                result["users"] = (await cur.fetchone())[0]
            async with db.execute(
                "SELECT status, COUNT(*) FROM orders GROUP BY status"
            ) as cur:
                async for status, count in cur:
                    result[status] = count
            return result
