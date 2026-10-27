"""Генерация ежедневных отчетов и дайджестов."""

from app.repositories import items

async def morning_digest(user_id: int) -> str:
    """Утренний дайджест: задачи на сегодня + идея."""
    tasks = await items.get_list(user_id, 'todo')
    
    text = "<b>☀️ Доброе утро!</b>\n\n"
    if tasks:
        text += "<b>Твои задачи:</b>\n"
        for t in tasks:
            text += f"• {t['title']}\n"
    else:
        text += "На сегодня задач нет. Отдыхай или придумай новую! 😎\n"

    ideas = await items.get_ideas(user_id)
    if ideas:
        text += f"\n💡 <b>Идея для вдохновения:</b>\n{ideas[0]['title']}"
    
    return text

async def midday_report(user_id: int) -> str:
    """Промежуточный отчет в 17:00: напоминание о текущих задачах."""
    tasks = await items.get_list(user_id, 'todo')
    
    text = "<b>🕔 Промежуточный отчёт (17:00)</b>\n\n"
    if tasks:
        text += "Напоминаю о твоих активных задачах:\n"
        for t in tasks:
            text += f"• {t['title']}\n"
        text += "\nОсталось время, чтобы что-то закрыть! 💪"
    else:
        text += "Все задачи закрыты! Отличная работа, можно немного отдохнуть. ☕️"
    
    return text

async def evening_report(user_id: int) -> str:
    """Вечерний отчет: что сделано за сегодня."""
    done_today = await items.get_by_period(user_id, 'day')
    
    if not done_today:
        return "🌙 <b>Вечерний отчёт</b>\n\nСегодня ничего не выполнено. Завтра будет новый день, всё получится! 💪"
    
    text = "<b>🌙 Вечерний отчёт</b>\n\nТы сегодня молодец! Сделано:\n"
    for t in done_today:
        text += f"✅ {t['title']}\n"
    
    text += "\nТак держать! 🥂"
    return text
