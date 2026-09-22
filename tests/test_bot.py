from __future__ import annotations

import unittest

from telegram.ext import CallbackQueryHandler, CommandHandler, MessageHandler

import bot


class BotWiringTests(unittest.TestCase):
    def test_application_registers_handlers(self) -> None:
        application = bot.build_application("123456:TEST_TOKEN")
        handler_types = {type(handler) for handler in application.handlers[0]}
        self.assertIn(CommandHandler, handler_types)
        self.assertIn(CallbackQueryHandler, handler_types)
        self.assertIn(MessageHandler, handler_types)

    def test_meal_buttons_include_random(self) -> None:
        from mealdb import parse_meal
        from tests.test_mealdb import SAMPLE_MEAL

        meal = parse_meal(SAMPLE_MEAL)
        markup = bot.meal_buttons(meal)
        labels = [button.text for row in markup.inline_keyboard for button in row]
        self.assertIn("YouTube", labels)
        self.assertIn("Источник", labels)
        self.assertIn("Ещё случайный", labels)
