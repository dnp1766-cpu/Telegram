# Telegram-бот рецептов (TheMealDB)

Бот в Telegram: [@nina_recipes_bot](https://t.me/nina_recipes_bot)

После `/start` две кнопки:

- **Поиск рецептов** — блюда и картинки из [TheMealDB](https://www.themealdb.com/)
- **Мои рецепты** — избранное на этом компьютере

После рецепта, если есть ссылка, показывается **видеорецепт**. Можно поставить оценку **1–5 звёзд**. В «Мои рецепты» сначала идут блюда с высокой оценкой.

Бот отвечает, только пока на компьютере запущена программа. Выключила ноутбук или закрыла окно — бот молчит. Снова запустила — снова отвечает.

## Запуск на своём компьютере

Нужен [Python 3](https://www.python.org/downloads/). На Windows при установке поставь галочку **Add python.exe to PATH**.

### 1. Скачай код

Вариант без Git — скачай архив ветки с кодом бота:

[Скачать ZIP](https://github.com/dnp1766-cpu/Telegram/archive/refs/heads/cursor/themealdb-telegram-bot-a431.zip)

Распакуй папку. Внутри должны быть файлы `bot.py`, `requirements.txt`, `.env.example`.

Или через Git:

```bash
git clone https://github.com/dnp1766-cpu/Telegram.git
cd Telegram
git checkout cursor/themealdb-telegram-bot-a431
```

Важно: ветка `main` почти пустая. Нужна ветка `cursor/themealdb-telegram-bot-a431`.

### 2. Добавь токен

Скопируй `.env.example` в `.env` и впиши токен от [@BotFather](https://t.me/BotFather):

```env
TELEGRAM_BOT_TOKEN=вставь_свой_токен
MEALDB_API_KEY=1
DATABASE_PATH=data/favorites.sqlite
```

Файл `.env` никуда не отправляй и не клади в Git.

### 3. Запусти бота

**Windows:** дважды нажми `start.bat`. Не закрывай чёрное окно.

**Mac или Linux:**

```bash
chmod +x start.sh
./start.sh
```

В окне должно появиться: `Запускаю бота рецептов TheMealDB`. Потом открой [@nina_recipes_bot](https://t.me/nina_recipes_bot) и напиши `/start`.

Остановить бота: в том же окне `Ctrl+C`.

### Запуск вручную

```bash
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Mac / Linux:
source .venv/bin/activate

pip install -r requirements.txt
python bot.py
```

Избранное хранится в `data/favorites.sqlite` на этом компьютере.

## Тесты

```bash
python -m pytest tests -v
```
