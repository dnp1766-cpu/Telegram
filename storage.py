"""Локальная база избранных рецептов (SQLite)."""

from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

from mealdb import Meal

DEFAULT_DB_PATH = "data/favorites.sqlite"


class FavoriteStore:
    def __init__(self, path: str | Path | None = None) -> None:
        raw = path or os.getenv("DATABASE_PATH") or DEFAULT_DB_PATH
        self.path = Path(raw) if raw != ":memory:" else Path(":memory:")
        self._uri = ":memory:" if raw == ":memory:" else str(self.path)
        if self._uri != ":memory:":
            self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self._uri)
        self._conn.row_factory = sqlite3.Row
        self._init()

    def close(self) -> None:
        self._conn.close()

    def _init(self) -> None:
        self._conn.execute(
            """
            CREATE TABLE IF NOT EXISTS favorites (
                user_id INTEGER NOT NULL,
                meal_id TEXT NOT NULL,
                payload TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                PRIMARY KEY (user_id, meal_id)
            )
            """
        )
        self._conn.commit()

    def add(self, user_id: int, meal: Meal) -> bool:
        if not meal.id:
            return False
        if self.is_favorite(user_id, meal.id):
            return False
        self._conn.execute(
            "INSERT INTO favorites (user_id, meal_id, payload) VALUES (?, ?, ?)",
            (user_id, meal.id, json.dumps(meal.to_payload(), ensure_ascii=False)),
        )
        self._conn.commit()
        return True

    def remove(self, user_id: int, meal_id: str) -> bool:
        cursor = self._conn.execute(
            "DELETE FROM favorites WHERE user_id = ? AND meal_id = ?",
            (user_id, meal_id),
        )
        self._conn.commit()
        return cursor.rowcount > 0

    def is_favorite(self, user_id: int, meal_id: str) -> bool:
        row = self._conn.execute(
            "SELECT 1 FROM favorites WHERE user_id = ? AND meal_id = ?",
            (user_id, meal_id),
        ).fetchone()
        return row is not None

    def get(self, user_id: int, meal_id: str) -> Meal | None:
        row = self._conn.execute(
            "SELECT payload FROM favorites WHERE user_id = ? AND meal_id = ?",
            (user_id, meal_id),
        ).fetchone()
        if row is None:
            return None
        return Meal.from_payload(json.loads(row["payload"]))

    def list_for_user(self, user_id: int) -> list[Meal]:
        rows = self._conn.execute(
            """
            SELECT payload FROM favorites
            WHERE user_id = ?
            ORDER BY created_at DESC
            """,
            (user_id,),
        ).fetchall()
        return [Meal.from_payload(json.loads(row["payload"])) for row in rows]
