"""Базовые команды бота и обработка сообщений."""

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.types import Message

from app.services import gigachat, whisper
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
        "/health — проверка компонентов\n"
        "/reset — сбросить контекст диалога"
    )


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(
        "<b>📋 Справка</b>\n\n"
        "<b>Основное:</b>\n"
        "/start — приветствие\n"
        "/help — эта справка\n"
        "/chatid — узнать свой chat_id\n"
        "/health — проверка компонентов\n"
        "/reset — сбросить контекст\n\n"
        "<b>Голос:</b> просто отправь голосовое сообщение.\n\n"
        "<b>Скоро:</b>\n"
        "• задачи и идеи (Ф3–Ф4)\n"
        "• автоматические отчёты (Ф5)"
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


@router.message(F.voice)
async def handle_voice(message: Message, bot: Bot) -> None:
    if not message.voice or not message.from_user:
        return

    status_msg = await message.answer("🎤 Слушаю и распознаю...")
    await bot.send_chat_action(message.chat.id, "typing")

    try:
        # 1. Распознаем
        text = await whisper.transcribe_voice(bot, message.voice)
        
        if not text:
            await status_msg.edit_text("🤷 Не удалось разобрать речь.")
            return

        await status_msg.edit_text(f"🗣 <i>«{text}»</i>\n\n⏳ Думаю...")

        # 2. Отправляем в ИИ
        answer = await gigachat.ask(message.from_user.id, text)
        await message.answer(answer)

    except RuntimeError as e:
        await status_msg.edit_text(f"⚠️ {e}")
    except Exception:
        await status_msg.edit_text("⚠️ Внутренняя ошибка при обработке голоса.")


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
