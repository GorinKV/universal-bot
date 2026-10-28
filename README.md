Universal Bot 🤖

https://img.shields.io/badge/python-3.12-blue.svg
https://img.shields.io/badge/aiogram-3.x-2ca5e0.svg
https://img.shields.io/badge/MariaDB-10.11-003545.svg
https://github.com/GorinKV/universal-bot/actions/workflows/ci-cd.yml/badge.svg

Универсальный Telegram-помощник: умный диалог, управление задачами и идеями, локальное распознавание речи и автоматические отчёты. Спроектирован для стабильной работы на слабом VPS (1 ГБ ОЗУ) с использованием локального ASR.

✨ Возможности

· 💬 Умный диалог — общение с GigaChat (с сохранением контекста).
· 🎤 Голосовой ввод — локальное распознавание речи (whisper.cpp) без внешних API. Есть умная постобработка ошибок (fuzzy matching).
· ✅ Задачи и идеи — создание, выполнение, удаление, дедлайны («завтра», «до пятницы»).
· 🧠 NL-парсинг — понимание естественного языка через Function Calling (GigaChat).
· ⏰ Автоматика — утренний дайджест (07:00), напоминания (17:00), вечерний отчёт (20:40).
· 📦 Бэкапы — ежедневная выгрузка БД и кода в Telegram (04:00).
· 🐙 Git-менеджер — управление репозиториями и автокоммиты с LLM-сообщениями каждые 4 часа.
· 🛡 CI/CD — строгая проверка (ruff, mypy, pytest) и автодеплой на сервер.

🖥️ Стек

Слой Технология
Bot aiogram 3
ИИ GigaChat API
ASR whisper.cpp (model: base) + difflib
БД MariaDB + asyncmy
Планировщик APScheduler
CI/CD GitHub Actions, ruff, mypy, pytest
Деплой systemd + venv

🚀 Быстрый старт

1. Клонируйте репозиторий:
   git clone https://github.com/GorinKV/universal-bot.git
   cd universal-bot
2. Создайте окружение и установите зависимости:
   python3.12 -m venv .venv
   source .venv/bin/activate
   pip install -e ".[dev]"
3. Настройте конфигурацию:
   cp .env.example .env
   chmod 600 .env
   nano .env  # Заполните BOT_TOKEN, ADMIN_ID, GIGACHAT_CREDENTIALS, DB_*
4. Запуск:
   python -m app.main

📋 Команды

Задачи и идеи

· /task <текст> — создать задачу (с парсингом дат)
· /idea <текст> — сохранить идею
· /tasks — активные задачи
· /ideas — список идей
· /all — все задачи
· /completed — выполненные
· /month, /year — выполненные за месяц / год
· /done <ID> — отметить выполненной
· /undo <N> — вернуть N-ю из выполненных
· /del <ID> — удалить
· /clear — удалить все

Git (только для админа)

· /git add <путь> — добавить проект в отслеживаемые
· /git list — список проектов
· /git status — статус репозиториев
· /git commit — коммит с LLM-сообщением
· /git auto — принудительный коммит прямо сейчас
· /git remove <ID> — убрать проект

ИИ и Система

· /start, /help — справка
· /reset — сбросить контекст диалога с ИИ
· /health — проверка всех компонентов (БД, ИИ, whisper)
· /backup — создать бэкап БД и кода (только админ)

Голос: просто отправьте голосовое сообщение.
Свободный текст: любые сообщения без команд уходят в GigaChat.

🗺️ Roadmap

☑ Ф1: Каркас и GigaChat
☑ Ф2: Голос (whisper.cpp)
☑ Ф3: База данных (MariaDB)
☑ Ф4: NL-парсинг (Function Calling)
☑ Ф5: Планировщик и бэкапы
☑ Ф6: Git-автокоммиты
☑ Ф7: Постобработка ошибок ASR
☑ Ф8: Парсинг дат и напоминания
☑ CI/CD: GitHub Actions, mypy, pytest

🔒 Безопасность

· Секреты хранятся только в .env (файл в .gitignore, права 600).
· Бэкапы кода в Telegram отправляются в архиве без .env.
· MariaDB слушает только 127.0.0.1.
· Деплой защищен: код не попадет на сервер, если не пройдут тесты, линтер или mypy.

📄 Лицензия

MIT — см. LICENSE.

👤 Автор

Константин Горин — @GorinKV
