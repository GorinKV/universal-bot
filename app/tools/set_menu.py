"""Подпрограмма для обновления меню команд в Telegram."""

import json
import urllib.request
from app.config import settings

def main() -> None:
    url = f"https://api.telegram.org/bot{settings.bot_token}/setMyCommands"
    
    payload = {
        "commands": [
            {"command": "start", "description": "Начать работу"},
            {"command": "tasks", "description": "Активные задачи"},
            {"command": "ideas", "description": "Список идей"},
            {"command": "help", "description": "Справка"},
            {"command": "health", "description": "Проверка компонентов"}
        ]
    }
    
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, 
        data=data, 
        headers={"Content-Type": "application/json"}
    )

    print("📤 Отправка POST-запроса...")
    try:
        with urllib.request.urlopen(req) as response:
            res = json.loads(response.read().decode())
            if res.get("ok"):
                print("✅ Меню успешно обновлено!")
            else:
                print(f"❌ Ошибка Telegram: {res}")
    except Exception as e:
        print(f"⚠️ Сетевая ошибка: {e}")

if __name__ == "__main__":
    main()
