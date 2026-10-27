# Universal Bot

[![Python](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/)
[![aiogram](https://img.shields.io/badge/aiogram-3.x-2ca5e0.svg)](https://aiogram.dev/)
[![CI](https://github.com/GorinKV/universal-bot/actions/workflows/ci.yml/badge.svg)](https://github.com/GorinKV/universal-bot/actions)

Универсальный Telegram-помощник: умный диалог, управление задачами и идеями, голосовой ввод и автоматические отчёты. Работает на VPS (1 ГБ ОЗУ).

## Возможности

- Умный диалог с GigaChat (с контекстом)
- Локальное распознавание речи (whisper.cpp)
- Задачи и идеи (создание, выполнение, списки)
- NL-парсинг (понимание фраз вроде "сделай до пятницы")
- Автоматика (дайджест 07:00, отчеты 17:00 и 20:40, бэкапы в 04:00)
- Автотесты и линтер в GitHub Actions

## Стек

- Bot: aiogram 3
- ИИ: GigaChat API
- ASR: whisper.cpp (base)
- БД: MariaDB + asyncmy
- Планировщик: APScheduler
- Тесты: pytest, ruff

## Быстрый старт

    git clone https://github.com/GorinKV/universal-bot.git
    cd universal-bot
    python3.12 -m venv .venv
    source .venv/bin/activate
    pip install -e .[dev]
    cp .env.example .env
    chmod 600 .env
    python -m app.main

## Команды

Задачи и идеи:
/task - создать задачу
/idea - сохранить идею
/tasks - активные задачи
/ideas - список идей
/all - все задачи
/completed - выполненные
/done ID - выполнить
/del ID - удалить
/clear - удалить всё

ИИ и Система:
/start, /help - справка
/reset - сбросить контекст ИИ
/health - проверка компонентов
/backup - бэкап (только админ)

## Roadmap

- [x] Ф1: Каркас и GigaChat
- [x] Ф2: Голос (whisper)
- [x] Ф3: База данных
- [x] Ф4: NL-парсинг
- [x] Ф5: Планировщик и бэкапы
- [x] CI: GitHub Actions
- [ ] Ф6: Git-автокоммиты
- [ ] Ф7: Постобработка ASR
- [ ] Ф8: Парсинг дат

## Безопасность

- Секреты только в .env (chmod 600)
- Бэкапы кода в Telegram без .env
- MariaDB слушает только localhost

## Лицензия
MIT

## Автор
Константин Горин (github.com/GorinKV)
