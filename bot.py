"""Telegram-бот рецептов на TheMealDB."""

from __future__ import annotations

import logging
import os
from functools import lru_cache

from dotenv import load_dotenv
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    Update,
)
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from formatters import (
    ingredients_html,
    instructions_html,
    recipe_caption,
    search_results_html,
    split_text,
)
from i18n import area_label, category_label
from mealdb import Meal, MealDBClient, MealSummary

load_dotenv()

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("recipe-bot")

BTN_RANDOM = "Случайный рецепт"
BTN_CATEGORIES = "Категории"
BTN_AREAS = "Кухни мира"
PAGE_SIZE = 8


@lru_cache(maxsize=1)
def mealdb() -> MealDBClient:
    return MealDBClient()


def main_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton(BTN_RANDOM)],
            [KeyboardButton(BTN_CATEGORIES), KeyboardButton(BTN_AREAS)],
        ],
        resize_keyboard=True,
    )


def meal_buttons(meal: Meal) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    links: list[InlineKeyboardButton] = []
    if meal.youtube:
        links.append(InlineKeyboardButton("YouTube", url=meal.youtube))
    if meal.source:
        links.append(InlineKeyboardButton("Источник", url=meal.source))
    if links:
        rows.append(links)
    rows.append([InlineKeyboardButton("Ещё случайный", callback_data="rand")])
    return InlineKeyboardMarkup(rows)


def meal_list_buttons(
    meals: list[Meal] | list[MealSummary],
    *,
    prefix: str | None = None,
    page: int = 0,
) -> InlineKeyboardMarkup:
    start = page * PAGE_SIZE
    chunk = meals[start : start + PAGE_SIZE]
    rows = [
        [InlineKeyboardButton(meal.name[:64], callback_data=f"m:{meal.id}")]
        for meal in chunk
    ]
    nav: list[InlineKeyboardButton] = []
    if prefix and page > 0:
        nav.append(InlineKeyboardButton("Назад", callback_data=f"{prefix}:{page - 1}"))
    if prefix and start + PAGE_SIZE < len(meals):
        nav.append(InlineKeyboardButton("Ещё", callback_data=f"{prefix}:{page + 1}"))
    if nav:
        rows.append(nav)
    return InlineKeyboardMarkup(rows)


def category_buttons() -> InlineKeyboardMarkup:
    categories = mealdb().categories()
    rows = [
        [
            InlineKeyboardButton(
                category_label(item.name),
                callback_data=f"c:{item.name}:0",
            )
        ]
        for item in categories
    ]
    return InlineKeyboardMarkup(rows)


def area_buttons() -> InlineKeyboardMarkup:
    areas = mealdb().list_areas()
    rows: list[list[InlineKeyboardButton]] = []
    row: list[InlineKeyboardButton] = []
    for area in areas:
        row.append(InlineKeyboardButton(area_label(area), callback_data=f"a:{area}:0"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    return InlineKeyboardMarkup(rows)


async def send_meal(update: Update, meal: Meal) -> None:
    caption = recipe_caption(meal)
    markup = meal_buttons(meal)
    message = update.effective_message
    if message is None:
        return

    if meal.image_url:
        await message.reply_photo(
            photo=meal.image_url,
            caption=caption,
            parse_mode=ParseMode.HTML,
            reply_markup=markup,
        )
    else:
        await message.reply_html(caption, reply_markup=markup)

    await message.reply_html(ingredients_html(meal))
    for chunk in split_text(instructions_html(meal)):
        await message.reply_html(chunk)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    del context
    if update.message is None:
        return
    await update.message.reply_html(
        "Привет! Я бот рецептов.\n\n"
        "Беру блюда и картинки из <b>TheMealDB</b>.\n"
        "Напиши название блюда, выбери категорию или попроси случайный рецепт.",
        reply_markup=main_keyboard(),
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    del context
    if update.message is None:
        return
    await update.message.reply_html(
        "<b>Как пользоваться</b>\n"
        "• Напиши название блюда — например, <code>pasta</code> или <code>chicken</code>\n"
        "• /random — случайный рецепт с фото\n"
        "• /categories — категории TheMealDB\n"
        "• /areas — кухни мира\n"
        "• /search pizza — поиск по названию",
        reply_markup=main_keyboard(),
    )


async def random_recipe(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    del context
    meal = mealdb().random()
    if meal is None:
        if update.effective_message:
            await update.effective_message.reply_text("Не удалось получить рецепт. Попробуй ещё раз.")
        return
    await send_meal(update, meal)


async def show_categories(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    del context
    if update.effective_message is None:
        return
    await update.effective_message.reply_text(
        "Выбери категорию:",
        reply_markup=category_buttons(),
    )


async def show_areas(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    del context
    if update.effective_message is None:
        return
    await update.effective_message.reply_text(
        "Выбери кухню:",
        reply_markup=area_buttons(),
    )


async def search_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = " ".join(context.args or []).strip()
    if not query:
        if update.message:
            await update.message.reply_text("Напиши запрос так: /search pasta")
        return
    await reply_search(update, query)


async def text_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None or not update.message.text:
        return
    text = update.message.text.strip()
    if text == BTN_RANDOM:
        await random_recipe(update, context)
        return
    if text == BTN_CATEGORIES:
        await show_categories(update, context)
        return
    if text == BTN_AREAS:
        await show_areas(update, context)
        return
    await reply_search(update, text)


async def reply_search(update: Update, query: str) -> None:
    meals = mealdb().search(query)
    if update.effective_message is None:
        return
    if len(meals) == 1:
        await send_meal(update, meals[0])
        return
    await update.effective_message.reply_html(
        search_results_html(query, meals),
        reply_markup=meal_list_buttons(meals),
    )


async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    del context
    query = update.callback_query
    if query is None or not query.data:
        return
    await query.answer()
    data = query.data

    if data == "rand":
        meal = mealdb().random()
        if meal is None:
            await query.message.reply_text("Не удалось получить рецепт.")
            return
        await send_meal(update, meal)
        return

    if data.startswith("m:"):
        meal = mealdb().lookup(data.split(":", 1)[1])
        if meal is None:
            await query.message.reply_text("Рецепт не найден.")
            return
        await send_meal(update, meal)
        return

    if data.startswith("c:"):
        _, category, page_raw = data.split(":", 2)
        page = int(page_raw)
        meals = mealdb().filter_by_category(category)
        await query.message.reply_html(
            f"Категория: <b>{category_label(category)}</b> ({len(meals)})",
            reply_markup=meal_list_buttons(meals, prefix=f"c:{category}", page=page),
        )
        return

    if data.startswith("a:"):
        _, area, page_raw = data.split(":", 2)
        page = int(page_raw)
        meals = mealdb().filter_by_area(area)
        await query.message.reply_html(
            f"Кухня: <b>{area_label(area)}</b> ({len(meals)})",
            reply_markup=meal_list_buttons(meals, prefix=f"a:{area}", page=page),
        )


def build_application(token: str) -> Application:
    application = Application.builder().token(token).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("random", random_recipe))
    application.add_handler(CommandHandler("categories", show_categories))
    application.add_handler(CommandHandler("areas", show_areas))
    application.add_handler(CommandHandler("search", search_command))
    application.add_handler(CallbackQueryHandler(on_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_search))
    return application


def main() -> None:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token:
        raise SystemExit(
            "Не задан TELEGRAM_BOT_TOKEN. Создай бота в @BotFather и добавь токен в .env"
        )
    logger.info("Запускаю бота рецептов TheMealDB")
    build_application(token).run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
