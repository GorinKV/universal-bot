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
    r'\bидеев\b': 'идею',
    r'\bгугу\b': 'Google',
    r'\bгугл\b': 'Google',
}

# 2. Целевые слова (правильные варианты, которые мы ищем fuzzy-поиском)
TARGET_WORDS = [
    "задачу", "задачи", "задача",
    "позвонить", "позвони",
    "сыроварение", "сыроварня", "сыр",
    "молоко", "купить", "сценарий",
    "написать", "сделать", "выполнить",
    "напомнить", "встреча", "проект",
    "бот", "код", "сервер", "приложение",
    "Google", "Диск", "reg.ru", "сервер",
]


def _fuzzy_fix_word(word: str) -> str:
    """Ищет похожее правильное слово и заменяет, если сходство > 80%."""
    if len(word) < 4:
        return word

    matches = difflib.get_close_matches(word.lower(), [w.lower() for w in TARGET_WORDS], n=1, cutoff=0.8)

    if matches:
        for target in TARGET_WORDS:
            if target.lower() == matches[0]:
                if word.lower() != target.lower():
                    logger.info("ASR fuzzy fix: '%s' -> '%s'", word, target)
                return target
    return word


def fix_text(text: str) -> str:
    """Исправляет типичные ошибки распознавания."""
    if not text:
        return text

    fixed = text
    for pattern, replacement in HARD_FIXES.items():
        fixed = re.sub(pattern, replacement, fixed, flags=re.IGNORECASE)

    words = re.findall(r'[\w-]+|[^\w\s]', fixed, flags=re.UNICODE)

    fixed_words = []
    for w in words:
        if w.isalpha():
            fixed_words.append(_fuzzy_fix_word(w))
        else:
            fixed_words.append(w)

    result = " ".join(fixed_words)
    result = re.sub(r'\s+([.,!?])', r'\1', result)

    return result
