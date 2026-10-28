"""Генерация ежедневных отчетов и дайджестов."""

from datetime import datetime

from app.repositories import items


async def morning_digest(user_id: int) -> str:
    tasks = await items.get_list(user_id, 'todo')

    text = "<b>☀️ Доброе утро!</b>\n\n"
    if tasks:
        text += "<b>Твои задачи:</b>\n"
        for t in tasks:
            due = f" (до {t['due']})" if t.get('due') else ""
            text += f"• {t['title']}{due}\n"
    else:
        text += "На сегодня задач нет. Отдыхай или придумай новую! 😎\n"

    ideas = await items.get_ideas(user_id)
    if ideas:
        text += f"\n💡 <b>Идея для вдохновения:</b>\n{ideas[0]['title']}"

    return text

async def midday_report(user_id: int) -> str:
    tasks = await items.get_list(user_id, 'todo')
    today = datetime.now().strftime("%d.%m")

    text = "<b>🕔 Промежуточный отчёт (17:00)</b>\n\n"
    urgent = [t for t in tasks if t.get('due') == today]
    other = [t for t in tasks if t.get('due') != today]

    if urgent:
        text += "<b>🔥 Задачи на сегодня:</b>\n"
        for t in urgent:
            text += f"• {t['title']}\n"
        text += "\n"

    if other:
        text += "<b>Остальные задачи:</b>\n"
        for t in other:
            due = f" (до {t['due']})" if t.get('due') else ""
            text += f"• {t['title']}{due}\n"
        text += "\n"

    if not tasks:
        text += "Все задачи закрыты! Отличная работа, можно немного отдохнуть. ☕️"
    else:
        text += "Осталось время, чтобы что-то закрыть! 💪"

    return text

async def evening_report(user_id: int) -> str:
    done_today = await items.get_by_period(user_id, 'day')

    if not done_today:
        return "🌙 <b>Вечерний отчёт</b>\n\nСегодня ничего не выполнено. Завтра будет новый день, всё получится! 💪"

    text = "<b>🌙 Вечерний отчёт</b>\n\nТы сегодня молодец! Сделано:\n"
    for t in done_today:
        text += f"✅ {t['title']}\n"

    text += "\nТак держать! 🥂"
    return text
