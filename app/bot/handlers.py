"""Базовые команды бота."""

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from app.services.health import collect_health

router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    name = message.from_user.first_name if message.from_user else "друг"
    await message.answer(
        f"Привет, {name}!\n\n"
        "Я универсальный помощник.\n"
        "Пока умею немного — но это только начало.\n\n"
        "📋 <b>Команды:</b>\n"
        "/help — справка\n"
        "/chatid — узнать свой chat_id\n"
        "/health — проверка компонентов"
    )


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(
        "<b>📋 Справка</b>\n\n"
        "<b>Основное:</b>\n"
        "/start — приветствие\n"
        "/help — эта справка\n"
        "/chatid — узнать свой chat_id\n"
        "/health — проверка компонентов бота\n\n"
        "<b>Скоро:</b>\n"
        "• диалог с ИИ (Ф1b)\n"
        "• голосовой ввод (Ф2)\n"
        "• задачи и идеи (Ф3–Ф4)\n"
        "• автоматические отчёты (Ф5)\n"
        "• git-автокоммиты (Ф6)"
    )


@router.message(Command("chatid"))
async def cmd_chatid(message: Message) -> None:
    uid = message.from_user.id if message.from_user else "?"
    await message.answer(
        f"Твой chat_id: <code>{message.chat.id}</code>\n"
        f"user_id: <code>{uid}</code>"
    )


@router.message(Command("health"))
async def cmd_health(message: Message) -> None:
    report = await collect_health()
    await message.answer(report)

