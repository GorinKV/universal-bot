# Universal Bot 🤖

[![Python](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/)
[![aiogram](https://img.shields.io/badge/aiogram-3.x-2ca5e0.svg)](https://aiogram.dev/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

Универсальный Telegram-помощник: диалог с ИИ, задачи и идеи, голосовой ввод, автоматические отчёты.

## ✨ Возможности

- 💬 **Диалог с GigaChat** — текст и голос
- 🎤 **Голосовой ввод** — локальный whisper.cpp (RU)
- ✅ **Задачи и идеи** — свой список у каждого пользователя
- ⏰ **Автоматика** — утренний дайджест, вечерний отчёт, бэкапы
- 🔧 **Git-автокоммиты** — с LLM-сообщениями

## 🖥️ Стек

| Слой | Технология |
|------|------------|
| Bot | aiogram 3 |
| ИИ | GigaChat API |
| ASR | whisper.cpp (`base`) |
| БД | MariaDB |
| Деплой | systemd + venv |

## 🚀 Быстрый старт

```bash
git clone git@github.com:GorinKV/universal-bot.git
cd universal-bot
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env
chmod 600 .env
# вписать BOT_TOKEN и ADMIN_ID


📋 Команды бота

Команда Описание
/start Приветствие
/help Справка
/chatid Узнать свой chat_id
/health Проверка компонентов
/reset Сбросить контекст диалога 
🗺️ Roadmap

☑ Ф1a — каркас, базовые команды, healthcheck
☐ Ф1b — интеграция GigaChat, диалог
☐ Ф2 — голос: whisper.cpp
☐ Ф3 — БД, задачи и идеи
☐ Ф4 — NL-парсинг (гибрид)
☐ Ф5 — планировщик: дайджест, отчёты, бэкапы
☐ Ф6 — git-автокоммиты
☐ Ф7 — постобработка ASR

📄 Лицензия

MIT — см. LICENSE.

👤 Автор

Константин Горин — @GorinKV

