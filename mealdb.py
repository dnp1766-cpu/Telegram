"""Клиент TheMealDB: рецепты, ингредиенты и картинки блюд."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import quote

import httpx

DEFAULT_API_KEY = "1"
DEFAULT_BASE_URL = "https://www.themealdb.com/api/json/v1"
INGREDIENT_IMAGE_BASE = "https://www.themealdb.com/images/ingredients"


class MealDBError(RuntimeError):
    """Ошибка запроса к TheMealDB."""


@dataclass(frozen=True)
class Ingredient:
    name: str
    measure: str

    @property
    def image_url(self) -> str:
        return f"{INGREDIENT_IMAGE_BASE}/{quote(self.name)}.png"

    def sized_image_url(self, size: str = "small") -> str:
        suffix = {"small": "-small", "medium": "-medium", "large": "-large"}.get(size, "")
        return f"{INGREDIENT_IMAGE_BASE}/{quote(self.name)}{suffix}.png"


@dataclass(frozen=True)
class MealSummary:
    id: str
    name: str
    thumbnail: str | None = None

    @property
    def image_url(self) -> str | None:
        return self.thumbnail

    def sized_image_url(self, size: str = "medium") -> str | None:
        if not self.thumbnail:
            return None
        return f"{self.thumbnail.rstrip('/')}/{size}"


@dataclass(frozen=True)
class Category:
    id: str
    name: str
    thumbnail: str | None = None
    description: str | None = None


@dataclass(frozen=True)
class Meal:
    id: str
    name: str
    category: str | None = None
    area: str | None = None
    instructions: str | None = None
    thumbnail: str | None = None
    youtube: str | None = None
    source: str | None = None
    tags: list[str] = field(default_factory=list)
    ingredients: list[Ingredient] = field(default_factory=list)

    @property
    def image_url(self) -> str | None:
        return self.thumbnail

    def sized_image_url(self, size: str = "medium") -> str | None:
        if not self.thumbnail:
            return None
        return f"{self.thumbnail.rstrip('/')}/{size}"

    def to_summary(self) -> MealSummary:
        return MealSummary(id=self.id, name=self.name, thumbnail=self.thumbnail)

    def to_payload(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "area": self.area,
            "instructions": self.instructions,
            "thumbnail": self.thumbnail,
            "youtube": self.youtube,
            "source": self.source,
            "tags": list(self.tags),
            "ingredients": [
                {"name": item.name, "measure": item.measure} for item in self.ingredients
            ],
        }

    @staticmethod
    def from_payload(data: dict[str, Any]) -> Meal:
        ingredients = [
            Ingredient(name=str(item.get("name") or ""), measure=str(item.get("measure") or ""))
            for item in data.get("ingredients") or []
            if item.get("name")
        ]
        return Meal(
            id=str(data.get("id") or ""),
            name=_clean(data.get("name")) or "Без названия",
            category=_clean(data.get("category")),
            area=_clean(data.get("area")),
            instructions=_clean(data.get("instructions")),
            thumbnail=_clean(data.get("thumbnail")),
            youtube=_clean(data.get("youtube")),
            source=_clean(data.get("source")),
            tags=[str(tag) for tag in data.get("tags") or []],
            ingredients=ingredients,
        )


def _clean(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def parse_meal(raw: dict[str, Any]) -> Meal:
    ingredients: list[Ingredient] = []
    for index in range(1, 21):
        name = _clean(raw.get(f"strIngredient{index}"))
        if not name:
            continue
        measure = _clean(raw.get(f"strMeasure{index}")) or ""
        ingredients.append(Ingredient(name=name, measure=measure))

    tags_raw = _clean(raw.get("strTags"))
    tags = [tag.strip() for tag in tags_raw.split(",") if tag.strip()] if tags_raw else []

    return Meal(
        id=str(raw.get("idMeal") or ""),
        name=_clean(raw.get("strMeal")) or "Без названия",
        category=_clean(raw.get("strCategory")),
        area=_clean(raw.get("strArea")),
        instructions=_clean(raw.get("strInstructions")),
        thumbnail=_clean(raw.get("strMealThumb")),
        youtube=_clean(raw.get("strYoutube")),
        source=_clean(raw.get("strSource")),
        tags=tags,
        ingredients=ingredients,
    )


def parse_meal_summary(raw: dict[str, Any]) -> MealSummary:
    return MealSummary(
        id=str(raw.get("idMeal") or ""),
        name=_clean(raw.get("strMeal")) or "Без названия",
        thumbnail=_clean(raw.get("strMealThumb")),
    )


class MealDBClient:
    """Синхронный клиент TheMealDB JSON API."""

    def __init__(
        self,
        api_key: str | None = None,
        *,
        base_url: str = DEFAULT_BASE_URL,
        timeout: float = 15.0,
    ) -> None:
        self.api_key = api_key or os.getenv("MEALDB_API_KEY") or DEFAULT_API_KEY
        self.base_url = f"{base_url.rstrip('/')}/{self.api_key}"
        self._client = httpx.Client(
            timeout=timeout,
            headers={"User-Agent": "telegram-recipe-bot/1.0"},
            follow_redirects=True,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> MealDBClient:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def _get(self, path: str, **params: str) -> dict[str, Any]:
        url = f"{self.base_url}/{path.lstrip('/')}"
        try:
            response = self._client.get(url, params=params)
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise MealDBError(f"Не удалось запросить TheMealDB: {exc}") from exc
        try:
            payload = response.json()
        except ValueError as exc:
            raise MealDBError("TheMealDB вернул не-JSON ответ") from exc
        if not isinstance(payload, dict):
            raise MealDBError("TheMealDB вернул неожиданный формат")
        return payload

    def search(self, query: str) -> list[Meal]:
        payload = self._get("search.php", s=query.strip())
        return [parse_meal(item) for item in payload.get("meals") or []]

    def search_by_letter(self, letter: str) -> list[Meal]:
        payload = self._get("search.php", f=letter[:1])
        return [parse_meal(item) for item in payload.get("meals") or []]

    def lookup(self, meal_id: str) -> Meal | None:
        payload = self._get("lookup.php", i=str(meal_id))
        meals = payload.get("meals") or []
        return parse_meal(meals[0]) if meals else None

    def random(self) -> Meal | None:
        payload = self._get("random.php")
        meals = payload.get("meals") or []
        return parse_meal(meals[0]) if meals else None

    def filter_by_category(self, category: str) -> list[MealSummary]:
        payload = self._get("filter.php", c=category)
        return [parse_meal_summary(item) for item in payload.get("meals") or []]

    def filter_by_area(self, area: str) -> list[MealSummary]:
        payload = self._get("filter.php", a=area)
        return [parse_meal_summary(item) for item in payload.get("meals") or []]

    def filter_by_ingredient(self, ingredient: str) -> list[MealSummary]:
        payload = self._get("filter.php", i=ingredient)
        return [parse_meal_summary(item) for item in payload.get("meals") or []]

    def list_categories(self) -> list[str]:
        payload = self._get("list.php", c="list")
        return [
            name
            for item in payload.get("meals") or []
            if (name := _clean(item.get("strCategory")))
        ]

    def list_areas(self) -> list[str]:
        payload = self._get("list.php", a="list")
        return [
            name
            for item in payload.get("meals") or []
            if (name := _clean(item.get("strArea")))
        ]

    def categories(self) -> list[Category]:
        payload = self._get("categories.php")
        result: list[Category] = []
        for item in payload.get("categories") or []:
            name = _clean(item.get("strCategory"))
            if not name:
                continue
            result.append(
                Category(
                    id=str(item.get("idCategory") or ""),
                    name=name,
                    thumbnail=_clean(item.get("strCategoryThumb")),
                    description=_clean(item.get("strCategoryDescription")),
                )
            )
        return result
