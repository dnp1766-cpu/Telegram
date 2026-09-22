from __future__ import annotations

import unittest
from unittest.mock import MagicMock, patch

import httpx

from formatters import ingredients_html, recipe_caption, split_text
from i18n import area_label, category_label
from mealdb import MealDBClient, MealDBError, parse_meal


SAMPLE_MEAL = {
    "idMeal": "52771",
    "strMeal": "Spicy Arrabiata Penne",
    "strCategory": "Vegetarian",
    "strArea": "Italian",
    "strInstructions": "Boil pasta.\nAdd sauce.",
    "strMealThumb": "https://www.themealdb.com/images/media/meals/ustsqw1468250014.jpg",
    "strYoutube": "https://www.youtube.com/watch?v=1IszT_guI08",
    "strSource": "https://example.com",
    "strTags": "Pasta,Curry",
    "strIngredient1": "penne rigate",
    "strMeasure1": "1 pound",
    "strIngredient2": "olive oil",
    "strMeasure2": "1/4 cup",
    "strIngredient3": "",
    "strMeasure3": "",
}


class ParseMealTests(unittest.TestCase):
    def test_parse_meal_extracts_image_and_ingredients(self) -> None:
        meal = parse_meal(SAMPLE_MEAL)
        self.assertEqual(meal.id, "52771")
        self.assertEqual(meal.name, "Spicy Arrabiata Penne")
        self.assertEqual(meal.image_url, SAMPLE_MEAL["strMealThumb"])
        self.assertEqual(
            meal.sized_image_url("medium"),
            SAMPLE_MEAL["strMealThumb"] + "/medium",
        )
        self.assertEqual(len(meal.ingredients), 2)
        self.assertEqual(meal.ingredients[0].name, "penne rigate")
        self.assertIn("penne", meal.ingredients[0].image_url)
        self.assertEqual(meal.tags, ["Pasta", "Curry"])

    def test_caption_and_ingredients_use_russian_labels(self) -> None:
        meal = parse_meal(SAMPLE_MEAL)
        caption = recipe_caption(meal)
        self.assertIn("Spicy Arrabiata Penne", caption)
        self.assertIn("Вегетарианское", caption)
        self.assertIn("Итальянская", caption)
        ingredients = ingredients_html(meal)
        self.assertIn("penne rigate", ingredients)
        self.assertIn("1 pound", ingredients)

    def test_split_text_keeps_short_messages(self) -> None:
        self.assertEqual(split_text("hello", 10), ["hello"])
        parts = split_text("one\n" + ("x" * 20), 12)
        self.assertGreaterEqual(len(parts), 2)


class ClientMockTests(unittest.TestCase):
    def test_search_maps_meals(self) -> None:
        client = MealDBClient(api_key="1")
        client._get = MagicMock(return_value={"meals": [SAMPLE_MEAL]})  # type: ignore[method-assign]
        meals = client.search("arrabiata")
        self.assertEqual(len(meals), 1)
        self.assertEqual(meals[0].name, "Spicy Arrabiata Penne")
        client._get.assert_called_once_with("search.php", s="arrabiata")

    def test_search_empty_results(self) -> None:
        client = MealDBClient(api_key="1")
        client._get = MagicMock(return_value={"meals": None})  # type: ignore[method-assign]
        self.assertEqual(client.search("zzzz"), [])

    def test_http_error_becomes_mealdb_error(self) -> None:
        client = MealDBClient(api_key="1")
        with patch.object(client._client, "get", side_effect=httpx.ConnectError("offline")):
            with self.assertRaises(MealDBError):
                client._get("search.php", s="x")
        client.close()


class LiveMealDBTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = MealDBClient()

    @classmethod
    def tearDownClass(cls) -> None:
        cls.client.close()

    def test_search_arrabiata_has_image(self) -> None:
        meals = self.client.search("Arrabiata")
        self.assertTrue(meals)
        meal = meals[0]
        self.assertTrue(meal.image_url)
        self.assertTrue(meal.image_url.startswith("https://www.themealdb.com/images/"))
        self.assertGreater(len(meal.ingredients), 0)
        self.assertTrue(meal.instructions)

    def test_lookup_and_random_return_images(self) -> None:
        meal = self.client.lookup("52771")
        self.assertIsNotNone(meal)
        assert meal is not None
        self.assertEqual(meal.name, "Spicy Arrabiata Penne")
        self.assertTrue(meal.thumbnail)

        random_meal = self.client.random()
        self.assertIsNotNone(random_meal)
        assert random_meal is not None
        self.assertTrue(random_meal.id)
        self.assertTrue(random_meal.image_url)

    def test_categories_include_thumbnails(self) -> None:
        categories = self.client.categories()
        self.assertGreaterEqual(len(categories), 5)
        self.assertTrue(any(item.thumbnail for item in categories))
        chicken = self.client.filter_by_category("Chicken")
        self.assertTrue(chicken)
        self.assertTrue(chicken[0].thumbnail)


class I18nTests(unittest.TestCase):
    def test_known_and_unknown_labels(self) -> None:
        self.assertEqual(category_label("Chicken"), "Курица")
        self.assertEqual(area_label("Russian"), "Русская")
        self.assertEqual(category_label("Custom"), "Custom")


if __name__ == "__main__":
    unittest.main()
