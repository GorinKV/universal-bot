import os

import pytest

# Устанавливаем фейковые переменные окружения ДО импорта app.config
os.environ["BOT_TOKEN"] = "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
os.environ["ADMIN_ID"] = "123456789"
os.environ["GIGACHAT_CREDENTIALS"] = "fake_credentials"
os.environ["DB_HOST"] = "localhost"
os.environ["DB_USER"] = "test_user"
os.environ["DB_PASSWORD"] = "test_password"
os.environ["DB_NAME"] = "test_db"

@pytest.fixture
def mock_user_id():
    return 123456789

@pytest.fixture
def mock_item():
    return {"id": 1, "title": "Тестовая задача", "status": "todo", "type": "task"}
