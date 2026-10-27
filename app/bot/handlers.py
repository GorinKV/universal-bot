"""Обработчики команд и сообщений."""

from aiogram import Bot, F, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

from app.services import gigachat, whisper
from app.services.health import collect_health
from app.repositories import items

router = Router()

@router.message(Command("start"))
async def cmd_start(message: Message) -> None:
    name = message.from_user.first_name if message.from_user else "друг"
    await message.answer(
        f"Привет, {name}!\n\n"
        "Я универсальный помощник. Умею вести задачи, записывать идеи, "
        "распознавать голос и общаться с ИИ.\n\n"
        "📋 <b>Задачи:</b>\n"
        "/task &lt;текст&gt; — добавить задачу\n"
        "/tasks — активные задачи\n"
        "/ideas — список идей\n"
        "/help — полная справка"
    )

@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await message.answer(
        "<b>📋 Справка</b>\n\n"
        "<b>Задачи и идеи:</b>\n"
        "/task &lt;текст&gt; — создать задачу\n"
        "/idea &lt;текст&gt; — сохранить идею\n"
        "/ideas — список идей\n"
        "/tasks — активные\n"
        "/all — все\n"
        "/completed — выполненные\n"
        "/month — выполненные за месяц\n"
        "/year — выполненные за год\n"
        "/done &lt;ID&gt; — отметить выполненной\n"
        "/undo &lt;N&gt; — вернуть N-ю из выполненных\n"
        "/del &lt;ID&gt; — удалить\n"
        "/clear — удалить всё\n\n"
        "<b>Голос:</b> просто отправь голосовое.\n"
        "<b>ИИ:</b> любой текст не-команда уходит в GigaChat.\n"
        "/reset — сбросить контекст ИИ.\n"
        "/health — проверка систем."
    )

@router.message(Command("chatid"))
async def cmd_chatid(message: Message) -> None:
    uid = message.from_user.id if message.from_user else "?"
    await message.answer(f"chat_id: <code>{message.chat.id}</code>\nuser_id: <code>{uid}</code>")

@router.message(Command("health"))
async def cmd_health(message: Message) -> None:
    await message.answer(await collect_health())

@router.message(Command("reset"))
async def cmd_reset(message: Message) -> None:
    if message.from_user:
        gigachat.reset_history(message.from_user.id)
    await message.answer("🧹 Контекст ИИ сброшен.")

# --- ЗАДАЧИ И ИДЕИ ---

@router.message(Command("task", "idea"))
async def cmd_add_item(message: Message, command: CommandObject) -> None:
    if not command.args:
        await message.answer(f"Использование: /{command.command} <текст>")
        return
    item_type = 'idea' if command.command == 'idea' else 'task'
    item_id = await items.add(message.from_user.id, command.args, item_type)
    icon = '💡' if item_type == 'idea' else '✅'
    await message.answer(f"{icon} Добавлено (ID: <code>{item_id}</code>)")

@router.message(Command("ideas"))
async def cmd_ideas(message: Message) -> None:
    ideas = await items.get_ideas(message.from_user.id)
    if not ideas:
        await message.answer("💡 Идей пока нет. Добавь: /idea <текст>")
        return

    active = [i for i in ideas if i["status"] == "todo"]
    done = [i for i in ideas if i["status"] == "done"]

    text = "<b>💡 Идеи:</b>\n\n"
    if active:
        text += "\n".join(f"[{i['id']}] {i['title']}" for i in active) + "\n"
    if done:
        if active:
            text += "\n<b>Выполненные:</b>\n"
        text += "\n".join(
            f"~[{i['id']}] {i['title']}~ ({i['dt']})" for i in done
        )
    await message.answer(text)

@router.message(Command("tasks", "all"))
async def cmd_list(message: Message, command: CommandObject) -> None:
    if command.command == 'all':
        todo = await items.get_list(message.from_user.id, 'todo')
        done = await items.get_list(message.from_user.id, 'done')
        text = "<b>📋 Все задачи:</b>\n\n"
        if todo:
            text += "<b>Активные:</b>\n" + "\n".join(
                f"[{i['id']}] {i['title']}" for i in todo
            ) + "\n\n"
        if done:
            text += "<b>Выполненные:</b>\n" + "\n".join(
                f"~[{i['id']}] {i['title']}~ ({i['dt']})" for i in done
            )
        if not todo and not done:
            text = "📭 Пусто."
        await message.answer(text)
    else:
        todo = await items.get_list(message.from_user.id, 'todo')
        if not todo:
            await message.answer("🎉 Нет активных задач!")
            return
        text = "<b>📋 Активные задачи:</b>\n\n" + "\n".join(
            f"[{i['id']}] {i['title']}" + (" 💡" if i['type'] == 'idea' else "")
            for i in todo
        )
        await message.answer(text)

@router.message(Command("completed", "month", "year"))
async def cmd_done_list(message: Message, command: CommandObject) -> None:
    period = command.command
    data = await items.get_list(message.from_user.id, 'done') if period == 'completed' else await items.get_by_period(message.from_user.id, period)
    
    titles = {"completed": "Выполненные", "month": "За этот месяц", "year": "За этот год"}
    if not data:
        await message.answer(f"📭 {titles[period]}: пусто.")
        return
    
    text = f"<b>✅ {titles[period]}:</b>\n\n" + "\n".join(
        f"[{i['id']}] {i['title']} ({i['dt']})" for i in data
    )
    await message.answer(text)

@router.message(Command("done"))
async def cmd_done(message: Message, command: CommandObject) -> None:
    if not command.args or not command.args.isdigit():
        await message.answer("Использование: /done <ID>")
        return
    if await items.mark_done(message.from_user.id, int(command.args)):
        await message.answer("✅ Выполнено!")
    else:
        await message.answer("⚠️ Не найдено или уже выполнено.")

@router.message(Command("undo"))
async def cmd_undo(message: Message, command: CommandObject) -> None:
    if not command.args or not command.args.isdigit():
        await message.answer("Использование: /undo <номер в списке выполненных>")
        return
    if await items.undo_by_position(message.from_user.id, int(command.args)):
        await message.answer("🔄 Возвращено в активные.")
    else:
        await message.answer("⚠️ Не найдено.")

@router.message(Command("del"))
async def cmd_del(message: Message, command: CommandObject) -> None:
    if not command.args or not command.args.isdigit():
        await message.answer("Использование: /del <ID>")
        return
    if await items.delete(message.from_user.id, int(command.args)):
        await message.answer("🗑 Удалено.")
    else:
        await message.answer("⚠️ Не найдено.")

@router.message(Command("clear"))
async def cmd_clear(message: Message) -> None:
    count = await items.clear_all(message.from_user.id)
    await message.answer(f"🗑 Удалено задач: {count}")

# --- ГОЛОС И ИИ ---

@router.message(F.voice)
async def handle_voice(message: Message, bot: Bot) -> None:
    if not message.voice or not message.from_user:
        return
    status_msg = await message.answer("🎤 Слушаю...")
    await bot.send_chat_action(message.chat.id, "typing")
    try:
        text = await whisper.transcribe_voice(bot, message.voice)
        if not text:
            await status_msg.edit_text("🤷 Не удалось разобрать речь.")
            return
        await status_msg.edit_text(f"🗣 <i>«{text}»</i>\n\n⏳ Думаю...")
        answer = await gigachat.ask(message.from_user.id, text)
        await message.answer(answer)
    except RuntimeError as e:
        await status_msg.edit_text(f"⚠️ {e}")

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
