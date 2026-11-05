"""Хелперы форматирования: учёт лимита Telegram (4096 символов)."""

# Жёсткий лимит Telegram: 4096 символов, но оставляем запас на разметку.
SAFE_LIMIT = 4000


def split_text(text: str, limit: int = SAFE_LIMIT) -> list[str]:
    """Делит длинный текст на части <= limit, разрезая по строкам.

    Инлайновая разметка (<b>...</b>) в списках не выходит за границы одной
    строки, поэтому разрез по '\\n' не ломает HTML-fetch Telegram.
    """
    text = text.rstrip()
    if len(text) <= limit:
        return [text] if text else []

    chunks: list[str] = []
    while text:
        if len(text) <= limit:
            chunks.append(text)
            break
        # Ищем ближайший перенос строки, иначе режем жёстко
        cut = text.rfind("\n", 0, limit)
        if cut < limit // 2:
            cut = limit
        chunks.append(text[:cut].rstrip("\n"))
        text = text[cut:].lstrip("\n")
    return chunks
