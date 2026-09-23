# Telegram-бот рецептов (TheMealDB)

Бот в Telegram: [@nina_recipes_bot](https://t.me/nina_recipes_bot)

После `/start` у пользователя две кнопки:

- **Поиск рецептов** — ищет блюда и картинки в [TheMealDB](https://www.themealdb.com/)
- **Мои рецепты** — показывает избранное из локальной базы SQLite

В карточке рецепта есть кнопка **В избранное**. Сохранённый рецепт можно открыть из «Мои рецепты».

## Запуск

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# впиши TELEGRAM_BOT_TOKEN из @BotFather
python bot.py
```

Избранное пишется в `data/favorites.sqlite`.

## Тесты

```bash
python -m pytest tests -v
```
