"""Обработчики команд и сообщений."""
from aiogram import Bot, F, Router
from aiogram.filters import Command, CommandObject
from aiogram.types import Message

from app.config import settings
from app.repositories import git_projects, items
from app.services import gigachat, git_manager, whisper
from app.services.backup import create_and_send_backup
from app.services.health import collect_health

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


@router.message(Command("backup"))
async def cmd_backup(message: Message, bot: Bot) -> None:
    if message.from_user.id != settings.admin_id:
        await message.answer("⛔️ У вас нет прав на это действие.")
        return
    await message.answer("⏳ Создаю бэкап базы и кода...")
    await create_and_send_backup(bot)


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
                f"[{i['id']}] {i['title']}" + (f" (до {i['due']})" if i.get('due') else "")
                for i in todo
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
            f"[{i['id']}] {i['title']}" + (f" (до {i['due']})" if i.get('due') else "") + (" 💡" if i['type'] == 'idea' else "")
            for i in todo
        )
        await message.answer(text)


@router.message(Command("completed", "month", "year"))
async def cmd_done_list(message: Message, command: CommandObject) -> None:
    period = command.command
    if period == 'completed':
        data = await items.get_list(message.from_user.id, 'done')
    else:
        data = await items.get_by_period(message.from_user.id, period)

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


# --- GIT УПРАВЛЕНИЕ ---

@router.message(Command("git"))
async def cmd_git(message: Message, command: CommandObject) -> None:
    if message.from_user.id != settings.admin_id:
        await message.answer("⛔️ Управление Git доступно только админу.")
        return

    args = command.args.split() if command.args else []
    if not args:
        await message.answer(
            "<b>Git команды:</b>\n"
            "/git add &lt;путь&gt; — добавить проект\n"
            "/git list — список\n"
            "/git status — статус изменений\n"
            "/git commit — коммит с ИИ-сообщением\n"
            "/git auto — принудительный коммит всех\n"
            "/git remove &lt;ID&gt; — удалить из списка"
        )
        return

    action = args[0]

    if action == "add":
        if len(args) < 2:
            await message.answer("Укажи путь: /git add /home/kvg/myproject")
            return
        path = args[1].strip()
        # Проверяем, что это git-репо
        if not await git_manager.is_git_repo(path):
            await message.answer("❌ Это не git-репозиторий или путь не существует.")
            return
        proj_id = await git_projects.add_project(message.from_user.id, path)
        await message.answer(f"✅ Проект добавлен (ID: {proj_id})")

    elif action == "list":
        projects = await git_projects.get_projects(message.from_user.id)
        if not projects:
            await message.answer("📭 Список пуст. Добавь: /git add <путь>")
            return
        text = "<b>📂 Отслеживаемые проекты:</b>\n\n"
        for p in projects:
            text += f"[{p['id']}] <code>{p['path']}</code>\n"
        await message.answer(text)

    elif action == "status":
        projects = await git_projects.get_projects(message.from_user.id)
        if not projects:
            await message.answer("📭 Список пуст.")
            return
        text = "<b>📊 Статус проектов:</b>\n\n"
        for p in projects:
            status = await git_manager.get_status(p['path'])
            if status.startswith("✅"):
                text += f"<b>[{p['id']}]</b> {status}\n\n"
            else:
                text += f"<b>[{p['id']}]</b> {p['path']}\n<pre>{status}</pre>\n\n"
        await message.answer(text)

    elif action == "commit":
        projects = await git_projects.get_projects(message.from_user.id)
        if not projects:
            await message.answer("📭 Список пуст.")
            return
        await message.answer("⏳ Генерирую коммиты...")
        for p in projects:
            status = await git_manager.get_status(p['path'])
            if "Изменений нет" in status:
                continue
            msg = await git_manager.generate_commit_message(p['path'])
            success = await git_manager.commit(p['path'], msg)
            if success:
                await message.answer(f"✅ <b>{p['path']}</b>\n<code>{msg}</code>")
            else:
                await message.answer(f"⚠️ Ошибка коммита в {p['path']}")

    elif action == "auto":
        # Аналогично commit, но для крона (без вывода в чат)
        projects = await git_projects.get_projects(message.from_user.id)
        for p in projects:
            status = await git_manager.get_status(p['path'])
            if "Изменений нет" in status:
                continue
            msg = await git_manager.generate_commit_message(p['path'])
            await git_manager.commit(p['path'], msg)

    elif action == "remove":
        if len(args) < 2 or not args[1].isdigit():
            await message.answer("Укажи ID: /git remove 1")
            return
        if await git_projects.remove_project(message.from_user.id, int(args[1])):
            await message.answer("🗑 Удалено из списка.")
        else:
            await message.answer("⚠️ Не найдено.")
    else:
        await message.answer("Неизвестная команда. Напиши /git для справки.")
