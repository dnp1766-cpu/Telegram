"""Telegram-бот: поиск рецептов в TheMealDB и избранное в SQLite."""

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
    favorites_html,
    ingredients_html,
    instructions_html,
    recipe_caption,
    search_results_html,
    split_text,
)
from mealdb import Meal, MealDBClient
from storage import FavoriteStore

load_dotenv()

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    level=logging.INFO,
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logger = logging.getLogger("recipe-bot")

BTN_SEARCH = "Поиск рецептов"
BTN_FAVORITES = "Мои рецепты"
STATE_SEARCH = "awaiting_search"
PAGE_SIZE = 8


@lru_cache(maxsize=1)
def mealdb() -> MealDBClient:
    return MealDBClient()


def store() -> FavoriteStore:
    existing = getattr(store, "_instance", None)
    if existing is None:
        existing = FavoriteStore()
        setattr(store, "_instance", existing)
    return existing


def set_store(instance: FavoriteStore | None) -> None:
    setattr(store, "_instance", instance)


def main_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton(BTN_SEARCH)],
            [KeyboardButton(BTN_FAVORITES)],
        ],
        resize_keyboard=True,
    )


def meal_buttons(meal: Meal, *, is_favorite: bool) -> InlineKeyboardMarkup:
    if is_favorite:
        button = InlineKeyboardButton("Убрать из избранного", callback_data=f"unfav:{meal.id}")
    else:
        button = InlineKeyboardButton("В избранное", callback_data=f"fav:{meal.id}")
    return InlineKeyboardMarkup([[button]])


def meal_list_buttons(meals: list[Meal], *, page: int = 0, prefix: str = "list") -> InlineKeyboardMarkup:
    start = page * PAGE_SIZE
    chunk = meals[start : start + PAGE_SIZE]
    rows = [[InlineKeyboardButton(meal.name[:64], callback_data=f"m:{meal.id}")] for meal in chunk]
    nav: list[InlineKeyboardButton] = []
    if page > 0:
        nav.append(InlineKeyboardButton("Назад", callback_data=f"{prefix}:{page - 1}"))
    if start + PAGE_SIZE < len(meals):
        nav.append(InlineKeyboardButton("Ещё", callback_data=f"{prefix}:{page + 1}"))
    if nav:
        rows.append(nav)
    return InlineKeyboardMarkup(rows)


def user_id_of(update: Update) -> int | None:
    user = update.effective_user
    return user.id if user else None


async def send_meal(update: Update, meal: Meal, user_id: int | None = None) -> None:
    message = update.effective_message
    if message is None:
        return
    current_user = user_id or user_id_of(update)
    is_favorite = bool(current_user and store().is_favorite(current_user, meal.id))
    markup = meal_buttons(meal, is_favorite=is_favorite)
    caption = recipe_caption(meal)

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
    if update.message is None:
        return
    context.user_data["state"] = None
    await update.message.reply_html(
        "Привет! Я бот рецептов.\n\n"
        "Ищу блюда в <b>TheMealDB</b> и сохраняю избранное у тебя в базе.\n"
        "Выбери действие:",
        reply_markup=main_keyboard(),
    )


async def ask_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.effective_message is None:
        return
    context.user_data["state"] = STATE_SEARCH
    await update.effective_message.reply_text(
        "Напиши название блюда — например, pasta или cake.",
        reply_markup=main_keyboard(),
    )


async def show_favorites(update: Update, context: ContextTypes.DEFAULT_TYPE, page: int = 0) -> None:
    del context
    message = update.effective_message
    if message is None:
        return
    user_id = user_id_of(update)
    if user_id is None:
        await message.reply_text("Не удалось определить пользователя.")
        return
    meals = store().list_for_user(user_id)
    if not meals:
        await message.reply_html(
            "Пока нет избранных рецептов.\n"
            "Найди блюдо через «Поиск рецептов» и нажми <b>В избранное</b>.",
            reply_markup=main_keyboard(),
        )
        return
    await message.reply_html(
        favorites_html(meals),
        reply_markup=meal_list_buttons(meals, page=page, prefix="favs"),
    )


async def reply_search(update: Update, context: ContextTypes.DEFAULT_TYPE, query: str) -> None:
    message = update.effective_message
    if message is None:
        return
    meals = mealdb().search(query)
    context.user_data["last_search"] = [item.to_payload() for item in meals]
    context.user_data["last_query"] = query
    if len(meals) == 1:
        await send_meal(update, meals[0])
        return
    await message.reply_html(
        search_results_html(query, meals),
        reply_markup=meal_list_buttons(meals, prefix="list") if meals else None,
    )


async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message is None or not update.message.text:
        return
    text = update.message.text.strip()
    if text == BTN_SEARCH:
        await ask_search(update, context)
        return
    if text == BTN_FAVORITES:
        context.user_data["state"] = None
        await show_favorites(update, context)
        return
    if context.user_data.get("state") == STATE_SEARCH:
        await reply_search(update, context, text)
        return
    await update.message.reply_text(
        "Выбери действие на клавиатуре: «Поиск рецептов» или «Мои рецепты».",
        reply_markup=main_keyboard(),
    )


async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query is None or not query.data:
        return
    user_id = user_id_of(update)
    data = query.data

    if data.startswith("favs:"):
        await query.answer()
        await show_favorites(update, context, page=int(data.split(":", 1)[1]))
        return

    if data.startswith("list:"):
        await query.answer()
        page = int(data.split(":", 1)[1])
        meals = [Meal.from_payload(item) for item in context.user_data.get("last_search") or []]
        last_query = context.user_data.get("last_query") or "поиск"
        if update.effective_message:
            await update.effective_message.reply_html(
                search_results_html(last_query, meals),
                reply_markup=meal_list_buttons(meals, page=page, prefix="list"),
            )
        return

    if data.startswith("m:"):
        await query.answer()
        meal_id = data.split(":", 1)[1]
        meal = (store().get(user_id, meal_id) if user_id else None) or mealdb().lookup(meal_id)
        if meal is None:
            if query.message:
                await query.message.reply_text("Рецепт не найден.")
            return
        await send_meal(update, meal, user_id)
        return

    if data.startswith("fav:") or data.startswith("unfav:"):
        if user_id is None:
            await query.answer("Не удалось определить пользователя.", show_alert=True)
            return
        meal_id = data.split(":", 1)[1]
        meal = store().get(user_id, meal_id) or mealdb().lookup(meal_id)
        if meal is None:
            await query.answer("Рецепт не найден.", show_alert=True)
            return
        if data.startswith("fav:"):
            store().add(user_id, meal)
            await query.answer("Сохранено в избранное")
            await query.edit_message_reply_markup(meal_buttons(meal, is_favorite=True))
        else:
            store().remove(user_id, meal_id)
            await query.answer("Убрано из избранного")
            await query.edit_message_reply_markup(meal_buttons(meal, is_favorite=False))


def build_application(token: str) -> Application:
    application = Application.builder().token(token).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(on_callback))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))
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
