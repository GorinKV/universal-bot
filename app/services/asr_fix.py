"""Постобработка текста после распознавания речи (whisper)."""

import difflib
import logging
import re

logger = logging.getLogger(__name__)

# 1. Жесткие замены (если whisper выдал конкретный бред)
HARD_FIXES = {
    r'\bнада\b': 'надо',
    r'\bсварится\b': 'сварить',
    r'\bсвариться\b': 'сварить',
    r'\bсадач\w*': 'задач',
    r'\bпозван\w*': 'позвони',
    r'\bмалако\b': 'молоко',
}

# 2. Целевые слова (правильные варианты, которые мы ищем fuzzy-поиском)
# Сюда вносим термины, имена и частые слова, которые whisper коверкает.
TARGET_WORDS = [
    "задачу", "задачи", "задача",
    "позвонить", "позвони",
    "сыроварение", "сыроварня", "сыр",
    "молоко", "купить", "сценарий",
    "написать", "сделать", "выполнить",
    "напомнить", "встреча", "проект",
    "бот", "код", "сервер", "приложение"
]


def _fuzzy_fix_word(word: str) -> str:
    """Ищет похожее правильное слово и заменяет, если сходство > 80%."""
    # Игнорируем короткие слова (предлоги, союзы)
    if len(word) < 4:
        return word

    # Ищем наиболее похожее слово из TARGET_WORDS
    matches = difflib.get_close_matches(word.lower(), TARGET_WORDS, n=1, cutoff=0.8)

    if matches:
        fixed = matches[0]
        logger.info("ASR fuzzy fix: '%s' -> '%s'", word, fixed)
        return fixed
    return word


def fix_text(text: str) -> str:
    """Исправляет типичные ошибки распознавания."""
    if not text:
        return text

    # 1. Сначала применяем жесткие регулярки
    fixed = text
    for pattern, replacement in HARD_FIXES.items():
        fixed = re.sub(pattern, replacement, fixed, flags=re.IGNORECASE)

    # 2. Затем проходим по каждому слову и делаем fuzzy-поиск
    # Используем регулярку для разделения слов и знаков препинания
    words = re.findall(r'[\w-]+|[^\w\s]', fixed, flags=re.UNICODE)

    fixed_words = []
    for w in words:
        if w.isalpha():
            fixed_words.append(_fuzzy_fix_word(w))
        else:
            fixed_words.append(w)

    # Собираем обратно (с пробелами, но без двойных пробелов)
    result = " ".join(fixed_words)

    # Убираем пробел перед знаками препинания (например, "молоко ," -> "молоко,")
    result = re.sub(r'\s+([.,!?])', r'\1', result)

    return result
