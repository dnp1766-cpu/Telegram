from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from mealdb import Meal, parse_meal
from storage import FavoriteStore
from tests.test_mealdb import SAMPLE_MEAL


class FavoriteStoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.store = FavoriteStore(Path(self.tmp.name) / "favorites.sqlite")
        self.meal = parse_meal(SAMPLE_MEAL)

    def tearDown(self) -> None:
        self.store.close()
        self.tmp.cleanup()

    def test_add_list_and_remove(self) -> None:
        self.assertTrue(self.store.add(10, self.meal))
        self.assertFalse(self.store.add(10, self.meal))
        self.assertTrue(self.store.is_favorite(10, self.meal.id))
        self.assertFalse(self.store.is_favorite(99, self.meal.id))

        saved = self.store.list_for_user(10)
        self.assertEqual(len(saved), 1)
        self.assertEqual(saved[0].meal.name, "Spicy Arrabiata Penne")
        self.assertEqual(saved[0].rating, 0)
        self.assertEqual(saved[0].meal.image_url, self.meal.image_url)
        self.assertEqual(saved[0].meal.ingredients[0].name, "penne rigate")

        other = self.store.list_for_user(99)
        self.assertEqual(other, [])

        self.assertTrue(self.store.remove(10, self.meal.id))
        self.assertFalse(self.store.is_favorite(10, self.meal.id))
        self.assertEqual(self.store.list_for_user(10), [])

    def test_ratings_sort_five_stars_first(self) -> None:
        low = parse_meal({**SAMPLE_MEAL, "idMeal": "1", "strMeal": "Low"})
        high = parse_meal({**SAMPLE_MEAL, "idMeal": "2", "strMeal": "High"})
        mid = parse_meal({**SAMPLE_MEAL, "idMeal": "3", "strMeal": "Mid"})
        unrated = parse_meal({**SAMPLE_MEAL, "idMeal": "4", "strMeal": "Unrated"})
        self.store.add(7, low)
        self.store.add(7, high)
        self.store.add(7, mid)
        self.store.add(7, unrated)
        self.assertTrue(self.store.set_rating(7, low, 2))
        self.assertTrue(self.store.set_rating(7, high, 5))
        self.assertTrue(self.store.set_rating(7, mid, 4))
        self.assertFalse(self.store.set_rating(7, high, 9))

        names = [item.meal.name for item in self.store.list_for_user(7)]
        self.assertEqual(names, ["High", "Mid", "Low", "Unrated"])
        self.assertEqual(self.store.get_rating(7, "2"), 5)

    def test_rating_adds_missing_favorite(self) -> None:
        self.assertTrue(self.store.set_rating(3, self.meal, 5))
        self.assertTrue(self.store.is_favorite(3, self.meal.id))
        self.assertEqual(self.store.get_rating(3, self.meal.id), 5)

    def test_payload_roundtrip(self) -> None:
        restored = Meal.from_payload(self.meal.to_payload())
        self.assertEqual(restored.id, self.meal.id)
        self.assertEqual(restored.name, self.meal.name)
        self.assertEqual(restored.thumbnail, self.meal.thumbnail)
        self.assertEqual(len(restored.ingredients), len(self.meal.ingredients))
