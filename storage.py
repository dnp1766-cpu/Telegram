"""Локальная база избранных рецептов (SQLite)."""

from __future__ import annotations

import json
import os
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from mealdb import Meal

DEFAULT_DB_PATH = "data/favorites.sqlite"


@dataclass(frozen=True)
class Favorite:
    meal: Meal
    rating: int = 0


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
                rating INTEGER NOT NULL DEFAULT 0,
                PRIMARY KEY (user_id, meal_id)
            )
            """
        )
        columns = {
            row["name"] for row in self._conn.execute("PRAGMA table_info(favorites)")
        }
        if "rating" not in columns:
            self._conn.execute(
                "ALTER TABLE favorites ADD COLUMN rating INTEGER NOT NULL DEFAULT 0"
            )
        self._conn.commit()

    def add(self, user_id: int, meal: Meal, rating: int = 0) -> bool:
        if not meal.id:
            return False
        if self.is_favorite(user_id, meal.id):
            return False
        if rating and rating not in range(1, 6):
            rating = 0
        self._conn.execute(
            "INSERT INTO favorites (user_id, meal_id, payload, rating) VALUES (?, ?, ?, ?)",
            (user_id, meal.id, json.dumps(meal.to_payload(), ensure_ascii=False), rating),
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
        favorite = self.get_favorite(user_id, meal_id)
        return favorite.meal if favorite else None

    def get_favorite(self, user_id: int, meal_id: str) -> Favorite | None:
        row = self._conn.execute(
            "SELECT payload, rating FROM favorites WHERE user_id = ? AND meal_id = ?",
            (user_id, meal_id),
        ).fetchone()
        if row is None:
            return None
        return Favorite(meal=Meal.from_payload(json.loads(row["payload"])), rating=int(row["rating"] or 0))

    def get_rating(self, user_id: int, meal_id: str) -> int:
        favorite = self.get_favorite(user_id, meal_id)
        return favorite.rating if favorite else 0

    def set_rating(self, user_id: int, meal: Meal, rating: int) -> bool:
        if rating not in range(1, 6) or not meal.id:
            return False
        if not self.is_favorite(user_id, meal.id):
            self.add(user_id, meal, rating=rating)
            return True
        self._conn.execute(
            "UPDATE favorites SET rating = ? WHERE user_id = ? AND meal_id = ?",
            (rating, user_id, meal.id),
        )
        self._conn.commit()
        return True

    def list_for_user(self, user_id: int) -> list[Favorite]:
        rows = self._conn.execute(
            """
            SELECT payload, rating FROM favorites
            WHERE user_id = ?
            ORDER BY rating DESC, created_at DESC
            """,
            (user_id,),
        ).fetchall()
        return [
            Favorite(meal=Meal.from_payload(json.loads(row["payload"])), rating=int(row["rating"] or 0))
            for row in rows
        ]
