# Universal Bot 🤖

[![Python](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/)
[![aiogram](https://img.shields.io/badge/aiogram-3.x-2ca5e0.svg)](https://aiogram.dev/)
[![MariaDB](https://img.shields.io/badge/MariaDB-10.11-003545.svg)](https://mariadb.org/)
[![CI/CD](https://github.com/GorinKV/universal-bot/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/GorinKV/universal-bot/actions)

Универсальный Telegram-помощник: умный диалог, управление задачами и идеями, локальное распознавание речи и автоматические отчёты. Спроектирован для стабильной работы на слабом VPS (1 ГБ ОЗУ) с использованием локального ASR.

## ✨ Возможности

- 💬 **Умный диалог** — общение с GigaChat (с сохранением контекста).
- 👥 **Мультипользовательский режим** — у каждого свои задачи, идеи, контекст ИИ и настройка отчётов; данные не пересекаются.
- 🎤 **Голосовой ввод** — локальное распознавание речи (whisper.cpp). Есть умная постобработка ошибок (fuzzy matching).
- ✅ **Задачи и идеи** — создание, выполнение, удаление, дедлайны («завтра», «до пятницы»).
- 🧠 **NL-парсинг** — понимание естественного языка через Function Calling (GigaChat).
- ⏰ **Автоматика** — утренний дайджест (07:00), напоминания (17:00), вечерний отчёт (20:40) — каждому пользователю отдельно, с возможностью отключить.
- 📦 **Бэкапы** — ежедневная выгрузка БД и кода в Telegram (04:00).
- 🐙 **Git-менеджер** — управление репозиториями и автокоммиты с LLM-сообщениями каждые 4 часа.
- 🛡 **CI/CD** — строгая проверка (ruff, mypy, pytest); сервер сам раскатывает коммит после зелёного CI.

## 🖥️ Стек

| Слой | Технология |
|------|------------|
| Bot | aiogram 3 |
| ИИ | GigaChat API |
| ASR | whisper.cpp (model: base) + difflib |
| БД | MariaDB + asyncmy |
| Планировщик | APScheduler |
| CI/CD | GitHub Actions, ruff, mypy, pytest |
| Деплой | systemd + venv, pull-таймер (без SSH-секретов) |

## 🚀 Быстрый старт

```bash
git clone https://github.com/GorinKV/universal-bot.git
cd universal-bot
python3.12 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"

cp .env.example .env
chmod 600 .env
# Заполните BOT_TOKEN, ADMIN_ID, GIGACHAT_CREDENTIALS, DB_*

python -m app.main

## 📋 Команды

### Задачи и идеи
- `/task <текст>` — создать задачу (с парсингом дат)
- `/idea <текст>` — сохранить идею
- `/tasks` — активные задачи
- `/ideas` — список идей
- `/all` — все задачи
- `/completed` — выполненные
- `/month`, `/year` — выполненные за месяц / год
- `/done <ID>` — отметить выполненной
- `/undo <N>` — вернуть N-ю из выполненных
- `/del <ID>` — удалить
- `/clear` — удалить все

### Git (только для админа)
- `/git add <путь>` — добавить проект в отслеживаемые
- `/git list` — список проектов
- `/git status` — статус репозиториев
- `/git commit` — коммит с LLM-сообщением
- `/git auto` — принудительный коммит прямо сейчас
- `/git remove <ID>` — убрать проект

### ИИ и Система
- `/start`, `/help` — справка
- `/reset` — сбросить контекст диалога с ИИ
- `/reports on|off` — включить/выключить ежедневные отчёты
- `/health` — проверка всех компонентов (БД, ИИ, whisper)
- `/backup` — создать бэкап БД и кода (только админ)

> **Голос:** просто отправьте голосовое сообщение.
> **Свободный текст:** любые сообщения без команд уходят в GigaChat.

## 👥 Многопользовательский режим

- Таблица `users` — профиль, `last_seen_at`, флаг `reports_enabled`. Регистрация идёт на каждом апдейте через middleware.
- Задачи, идеи и git-проекты привязаны к `user_id`; все запросы фильтруются по владельцу.
- Контекст GigaChat хранится отдельно для каждого `user_id`.
- Отчёты 07:00 / 17:00 / 20:40 уходят каждому пользователю с включёнными отчётами; блокировка бота автоматически выключает рассылку.
- `/reports on|off` — управление подпиской. Git-команды и `/backup` остаются только для админа.

## 🗺️ Roadmap

- [x] Ф1: Каркас и GigaChat
- [x] Ф2: Голос (whisper.cpp)
- [x] Ф3: База данных (MariaDB)
- [x] Ф4: NL-парсинг (Function Calling)
- [x] Ф5: Планировщик и бэкапы
- [x] Ф6: Git-автокоммиты
- [x] Ф7: Постобработка ошибок ASR
- [x] Ф8: Парсинг дат и напоминания
- [x] CI/CD: GitHub Actions, mypy, pytest

## 🔒 Безопасность

- Секреты хранятся только в `.env` (файл в `.gitignore`, права `600`).
- Бэкапы кода в Telegram отправляются в архиве **без** `.env`.
- MariaDB слушает только `127.0.0.1`.
- Деплой защищен: код не попадет на сервер, если не пройдут тесты, линтер или mypy.

## 🚀 Деплой (pull-схема)

GitHub Actions только проверяет код. Раскатывает его сам сервер:

1. `universal-bot-deploy.timer` раз в 2 минуты запускает `deploy/pull-deploy.sh`.
2. Скрипт делает `git fetch` и сравнивает `origin/main` с последним раскатанным
   коммитом (маркер `~/.cache/universal-bot-deploy.state`). Локальный `HEAD` не
   годится: репозиторий и сервис на одной машине, поэтому после пуша он уже совпадает.
3. Для нового коммита спрашивает у GitHub API статус CI **именно для него**.
   Пока идёт проверка или она упала, деплой не выполняется.
4. После зелёного CI: `git merge --ff-only`, `pip install -e .` (только при изменении
   `pyproject.toml`), `systemctl restart universal-bot`, ожидание `is-active`.
5. Если сервис не поднялся — автоматический откат на прежний коммит.

Почему так: внешний SSH-деплой из GitHub зависел от секретов (`SSH_HOST`,
`SSH_PRIVATE_KEY`) и доступности порта 22 с раннеров. Pull-схема работает без
секретов и не ломается при смене IP сервера.

Установка на сервере (один раз):

```bash
sudo install -m 0644 deploy/universal-bot-deploy.service /etc/systemd/system/
sudo install -m 0644 deploy/universal-bot-deploy.timer   /etc/systemd/system/
sudo install -m 0755 deploy/universal-bot-deploy /usr/local/bin/   # обёртка
sudo systemctl daemon-reload && sudo systemctl enable --now universal-bot-deploy.timer
```

Лог деплоя — `~/deploy.log`, журнал — `journalctl -u universal-bot-deploy`.

## 📄 Лицензия

MIT — см. [LICENSE](LICENSE).

## 👤 Автор

**Константин Горин** — [@GorinKV](https://github.com/GorinKV)

