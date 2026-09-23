"""Форматирование рецептов TheMealDB для Telegram."""

from __future__ import annotations

import html

from i18n import area_label, category_label
from mealdb import Meal, MealSummary

TELEGRAM_CAPTION_LIMIT = 1024
TELEGRAM_MESSAGE_LIMIT = 4000


def escape(text: str) -> str:
    return html.escape(text, quote=False)


def split_text(text: str, limit: int = TELEGRAM_MESSAGE_LIMIT) -> list[str]:
    if len(text) <= limit:
        return [text] if text else []

    chunks: list[str] = []
    remaining = text
    while remaining:
        if len(remaining) <= limit:
            chunks.append(remaining)
            break
        cut = remaining.rfind("\n", 0, limit)
        if cut < limit // 2:
            cut = remaining.rfind(" ", 0, limit)
        if cut < limit // 2:
            cut = limit
        chunks.append(remaining[:cut].rstrip())
        remaining = remaining[cut:].lstrip()
    return chunks


def recipe_caption(meal: Meal) -> str:
    lines = [f"<b>{escape(meal.name)}</b>"]
    meta: list[str] = []
    if meal.category:
        meta.append(category_label(meal.category))
    if meal.area:
        meta.append(area_label(meal.area))
    if meta:
        lines.append(" · ".join(escape(part) for part in meta))
    if meal.tags:
        lines.append("Теги: " + ", ".join(escape(tag) for tag in meal.tags))
    return "\n".join(lines)[:TELEGRAM_CAPTION_LIMIT]


def ingredients_html(meal: Meal) -> str:
    if not meal.ingredients:
        return "<b>Ингредиенты</b>\nНе указаны."
    lines = ["<b>Ингредиенты</b>"]
    for item in meal.ingredients:
        measure = f" — {escape(item.measure)}" if item.measure else ""
        lines.append(f"• {escape(item.name)}{measure}")
    return "\n".join(lines)


def instructions_html(meal: Meal) -> str:
    text = meal.instructions or "Инструкция не указана."
    return "<b>Приготовление</b>\n" + escape(text)


def search_results_html(query: str, meals: list[Meal] | list[MealSummary]) -> str:
    if not meals:
        return f"По запросу <b>{escape(query)}</b> ничего не найдено."
    lines = [f"Найдено <b>{len(meals)}</b> рецепт(ов) по запросу «{escape(query)}»:"]
    for index, meal in enumerate(meals[:8], start=1):
        lines.append(f"{index}. {escape(meal.name)}")
    if len(meals) > 8:
        lines.append(f"\nПоказаны первые 8 из {len(meals)}.")
    return "\n".join(lines)


def stars_text(rating: int) -> str:
    if rating <= 0:
        return "без оценки"
    return "⭐" * rating


def rating_prompt(rating: int = 0) -> str:
    if rating:
        return f"Твоя оценка: {stars_text(rating)}\nМожно поставить новую:"
    return "Оцени рецепт от 1 до 5 звёзд:"


def favorites_html(favorites: list) -> str:
    if not favorites:
        return "Пока нет избранных рецептов."
    lines = [f"Мои рецепты: <b>{len(favorites)}</b> — сначала с высокой оценкой"]
    for index, item in enumerate(favorites[:8], start=1):
        meal = getattr(item, "meal", item)
        rating = getattr(item, "rating", 0)
        lines.append(f"{index}. {stars_text(rating)} — {escape(meal.name)}")
    if len(favorites) > 8:
        lines.append(f"\nПоказаны первые 8 из {len(favorites)}.")
    return "\n".join(lines)
