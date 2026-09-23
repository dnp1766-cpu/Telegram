#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

if ! command -v python3 >/dev/null 2>&1; then
  echo "Сначала установи Python 3."
  exit 1
fi

if [ ! -d .venv ]; then
  python3 -m venv .venv
fi

# shellcheck disable=SC1091
source .venv/bin/activate
python -m pip install -q -r requirements.txt

if [ ! -f .env ]; then
  cp .env.example .env
  echo "Создан файл .env. Открой его, вставь TELEGRAM_BOT_TOKEN и запусти скрипт снова."
  exit 1
fi

echo "Бот запущен. Не закрывай терминал, пока бот должен отвечать в Telegram."
echo "Чтобы остановить бота, нажми Ctrl+C."
python bot.py
