from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
import unittest.mock
from unittest.mock import AsyncMock, MagicMock

from telegram.ext import CallbackQueryHandler, CommandHandler, MessageHandler

import bot
from mealdb import parse_meal
from storage import FavoriteStore
from tests.test_mealdb import SAMPLE_MEAL


class BotWiringTests(unittest.TestCase):
    def test_application_registers_handlers(self) -> None:
        application = bot.build_application("123456:TEST_TOKEN")
        handler_types = {type(handler) for handler in application.handlers[0]}
        self.assertIn(CommandHandler, handler_types)
        self.assertIn(CallbackQueryHandler, handler_types)
        self.assertIn(MessageHandler, handler_types)

    def test_start_keyboard_has_only_two_actions(self) -> None:
        markup = bot.main_keyboard()
        labels = [button.text for row in markup.keyboard for button in row]
        self.assertEqual(labels, ["Поиск рецептов", "Мои рецепты"])

    def test_recipe_has_favorite_button(self) -> None:
        meal = parse_meal(SAMPLE_MEAL)
        add_labels = [button.text for row in bot.meal_buttons(meal, is_favorite=False).inline_keyboard for button in row]
        remove_labels = [button.text for row in bot.meal_buttons(meal, is_favorite=True).inline_keyboard for button in row]
        self.assertEqual(add_labels, ["В избранное"])
        self.assertEqual(remove_labels, ["Убрать из избранного"])

    def test_rating_buttons_are_one_to_five_stars(self) -> None:
        meal = parse_meal(SAMPLE_MEAL)
        labels = [button.text for row in bot.rating_buttons(meal.id).inline_keyboard for button in row]
        callbacks = [button.callback_data for row in bot.rating_buttons(meal.id).inline_keyboard for button in row]
        self.assertEqual(labels, ["1⭐", "2⭐", "3⭐", "4⭐", "5⭐"])
        self.assertEqual(callbacks, [f"rate:{meal.id}:1", f"rate:{meal.id}:2", f"rate:{meal.id}:3", f"rate:{meal.id}:4", f"rate:{meal.id}:5"])


class BotFlowTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.tmp = tempfile.TemporaryDirectory()
        self.favorites = FavoriteStore(Path(self.tmp.name) / "favorites.sqlite")
        bot.set_store(self.favorites)

    def tearDown(self) -> None:
        bot.set_store(None)
        self.favorites.close()
        self.tmp.cleanup()

    def _update(self, text: str = "/start", user_id: int = 42) -> MagicMock:
        update = MagicMock()
        update.effective_user.id = user_id
        update.message = MagicMock()
        update.message.text = text
        update.message.reply_html = AsyncMock()
        update.message.reply_text = AsyncMock()
        update.effective_message = update.message
        return update

    async def test_start_offers_search_and_favorites(self) -> None:
        update = self._update()
        context = MagicMock()
        context.user_data = {}
        await bot.start(update, context)
        text, kwargs = update.message.reply_html.await_args.args[0], update.message.reply_html.await_args.kwargs
        self.assertIn("Выбери действие", text)
        labels = [button.text for row in kwargs["reply_markup"].keyboard for button in row]
        self.assertEqual(labels, ["Поиск рецептов", "Мои рецепты"])

    async def test_search_button_asks_for_query(self) -> None:
        update = self._update(bot.BTN_SEARCH)
        context = MagicMock()
        context.user_data = {}
        await bot.on_text(update, context)
        self.assertEqual(context.user_data["state"], bot.STATE_SEARCH)
        update.message.reply_text.assert_awaited()
        self.assertIn("название блюда", update.message.reply_text.await_args.args[0])

    async def test_empty_favorites_message(self) -> None:
        update = self._update(bot.BTN_FAVORITES)
        context = MagicMock()
        context.user_data = {}
        await bot.on_text(update, context)
        text = update.message.reply_html.await_args.args[0]
        self.assertIn("Пока нет избранных рецептов", text)

    async def test_saved_recipe_appears_in_my_recipes(self) -> None:
        meal = parse_meal(SAMPLE_MEAL)
        self.favorites.add(42, meal)
        update = self._update(bot.BTN_FAVORITES)
        context = MagicMock()
        context.user_data = {}
        await bot.on_text(update, context)
        text = update.message.reply_html.await_args.args[0]
        markup = update.message.reply_html.await_args.kwargs["reply_markup"]
        self.assertIn("Spicy Arrabiata Penne", text)
        labels = [button.text for row in markup.inline_keyboard for button in row]
        self.assertTrue(any("Spicy Arrabiata Penne" in label for label in labels))
        self.assertIn("без оценки", text)

    async def test_rate_callback_saves_stars(self) -> None:
        meal = parse_meal(SAMPLE_MEAL)
        update = MagicMock()
        update.effective_user.id = 42
        update.effective_message = MagicMock()
        update.callback_query = MagicMock()
        update.callback_query.data = f"rate:{meal.id}:5"
        update.callback_query.answer = AsyncMock()
        update.callback_query.edit_message_text = AsyncMock()
        update.callback_query.message = update.effective_message
        context = MagicMock()
        context.user_data = {}

        with unittest.mock.patch.object(bot, "mealdb") as mealdb_factory:
            client = MagicMock()
            client.lookup.return_value = meal
            mealdb_factory.return_value = client
            await bot.on_callback(update, context)

        self.assertTrue(self.favorites.is_favorite(42, meal.id))
        self.assertEqual(self.favorites.get_rating(42, meal.id), 5)
        update.callback_query.answer.assert_awaited()
        update.callback_query.edit_message_text.assert_awaited()
        self.assertIn("⭐⭐⭐⭐⭐", update.callback_query.edit_message_text.await_args.args[0])
