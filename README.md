# Telegram-бот рецептов (TheMealDB)

Бот получает рецепты и картинки блюд из бесплатного API [TheMealDB](https://www.themealdb.com/).
Для разработки используется тестовый ключ `1`.

## Что умеет

- поиск блюда по названию
- случайный рецепт с фото
- категории и кухни мира
- ингредиенты, шаги приготовления, ссылки на YouTube и источник

TheMealDB отдаёт готовый URL картинки в поле `strMealThumb`. Бот отправляет его как фото в Telegram.

## Запуск бота

1. Создай бота в [@BotFather](https://t.me/BotFather) и скопируй токен.
2. Установи зависимости и задай токен:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# впиши TELEGRAM_BOT_TOKEN в .env
python bot.py
```

Команды: `/start`, `/help`, `/random`, `/search pasta`, `/categories`, `/areas`.
Можно просто написать название блюда в чат.

## Превью без Telegram

Чтобы посмотреть те же рецепты и картинки в браузере:

```bash
python preview.py
```

Открой http://127.0.0.1:8765

## Тесты

```bash
python -m pytest tests/test_mealdb.py -v
```

Часть тестов ходит в живой TheMealDB и проверяет, что у рецептов есть изображения.
