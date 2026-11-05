from app.services.asr_fix import fix_text


def test_empty_string():
    assert fix_text("") == ""


def test_hard_replacements():
    assert "надо" in fix_text("нада позванить") or fix_text("нада") == "надо"
    assert "молоко" in fix_text("купить малако")
    assert "Google" in fix_text("загугли гугу")


def test_fuzzy_keeps_correct_words():
    assert fix_text("задачу") == "задачу"


def test_fuzzy_fixes_similar_word():
    # 'задачю' — типичная ошибка ASR, должно подтянуться к 'задачу'
    assert "задачу" in fix_text("создамен задачю")


def test_punctuation_spacing():
    assert fix_text("привет ! как дела ?") == "привет! как дела?"
