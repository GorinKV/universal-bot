"""Базовые команды бота."""
from aiogram import F, Router
from app.services import gigachat
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
        "/health — проверка компонентов бота\n"
        "/reset — сбросить контекст диалога\n\n"
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


@router.message(Command("reset"))
async def cmd_reset(message: Message) -> None:
    if message.from_user:
        gigachat.reset_history(message.from_user.id)
    await message.answer("🧹 Контекст сброшен.")


@router.message(F.text & ~F.text.startswith("/"))
async def handle_free_text(message: Message) -> None:
    if not message.text or not message.from_user:
        return
    await message.bot.send_chat_action(message.chat.id, "typing")
    try:
        answer = await gigachat.ask(message.from_user.id, message.text)
        await message.answer(answer)
    except RuntimeError as e:
        await message.answer(f"⚠️ {e}")
    except Exception:
        await message.answer("⚠️ Внутренняя ошибка, попробуй позже.")

