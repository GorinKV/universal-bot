from unittest.mock import patch

import pytest

from app.services import gigachat


@pytest.mark.asyncio
@patch("app.services.gigachat.items.add")
async def test_execute_function_create_task(mock_add):
    mock_add.return_value = 99

    result = await gigachat._execute_function(
        user_id=1,
        name="create_task",
        arguments={"title": "Сварить сыр"}
    )

    assert result["status"] == "success"
    assert result["id"] == 99
    # Проверяем, что вызов был с due_at=None (так как дата не передана)
    mock_add.assert_called_once_with(1, "Сварить сыр", item_type="task", due_at=None)


@pytest.mark.asyncio
@patch("app.services.gigachat.items.find_by_position")
@patch("app.services.gigachat.items.mark_done")
async def test_execute_function_mark_done(mock_mark, mock_find):
    mock_find.return_value = {"id": 5, "title": "Позвонить маме"}

    result = await gigachat._execute_function(
        user_id=1,
        name="mark_task_done",
        arguments={"position": 1}
    )

    assert result["status"] == "success"
    assert result["title"] == "Позвонить маме"
    mock_find.assert_called_once_with(1, 1)
    mock_mark.assert_called_once_with(1, 5)


def test_is_configured():
    # В conftest мы задали фейковый GIGACHAT_CREDENTIALS
    assert gigachat.is_configured() is True
