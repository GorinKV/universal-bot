from app.bot.formatting import SAFE_LIMIT, split_text


def test_short_text_unchanged():
    assert split_text("привет") == ["привет"]


def test_empty_text():
    assert split_text("") == []


def test_no_split_needed_exactly_limit():
    text = "a" * SAFE_LIMIT
    assert split_text(text) == [text]


def test_splits_at_newline():
    # 5000 строк по 100 символов -> куски <= SAFE_LIMIT
    line = "x" * 99 + "\n"
    text = line * 50
    chunks = split_text(text)
    assert len(chunks) > 1
    assert all(len(c) <= SAFE_LIMIT for c in chunks)
    # Собранный текст не теряет содержимое
    assert "".join(c + "\n" for c in chunks).strip() == text.strip()


def test_hard_cut_without_newlines():
    # Длинная строка без переносов — режется жёстко
    text = "y" * (SAFE_LIMIT + 1000)
    chunks = split_text(text)
    assert "".join(chunks) == "y" * (SAFE_LIMIT + 1000)
    assert all(len(c) <= SAFE_LIMIT for c in chunks)
