@echo off
chcp 65001 >nul
cd /d "%~dp0"

where python >nul 2>&1
if errorlevel 1 (
  echo Сначала установи Python: https://www.python.org/downloads/
  echo На установке поставь галочку "Add python.exe to PATH".
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  python -m venv .venv
)

call .venv\Scripts\activate.bat
python -m pip install -q -r requirements.txt

if not exist ".env" (
  copy /Y .env.example .env >nul
  echo Создан файл .env. Вставь туда свой TELEGRAM_BOT_TOKEN и сохрани.
  notepad .env
)

echo.
echo Бот запущен. Не закрывай это окно, пока бот должен отвечать в Telegram.
echo Чтобы остановить бота, нажми Ctrl+C.
echo.
python bot.py
pause
