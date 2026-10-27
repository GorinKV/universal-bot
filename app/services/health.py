"""Проверка работоспособности компонентов."""

import logging
import platform
from datetime import datetime
import psutil

from app.services import gigachat, whisper, db

logger = logging.getLogger(__name__)

def log_startup_info() -> None:
    logger.info("=== Старт бота ===")
    logger.info("Python: %s", platform.python_version())
    vm = psutil.virtual_memory()
    logger.info("RAM VPS: %.0f / %.0f MB (%.0f%%)", vm.used / 1048576, vm.total / 1048576, vm.percent)

async def collect_health() -> str:
    lines: list[str] = ["<b>🏥 Проверка компонентов</b>", ""]

    proc = psutil.Process()
    mem_mb = proc.memory_info().rss / 1048576
    uptime = str(datetime.now() - datetime.fromtimestamp(proc.create_time())).split(".")[0]
    lines.append(f"✅ <b>Процесс</b>: жив · RAM {mem_mb:.0f} MB · uptime {uptime}")

    vm = psutil.virtual_memory()
    lines.append(f"   RAM VPS: {vm.used / 1048576:.0f} / {vm.total / 1048576:.0f} MB")

    lines.append("")
    
    ok_ai, detail_ai = await gigachat.ping()
    lines.append("✅ <b>GigaChat</b>: отвечает" if ok_ai else f"❌ <b>GigaChat</b>: {detail_ai}")

    lines.append("✅ <b>whisper</b>: CLI" if whisper.is_configured() else "❌ <b>whisper</b>: не найден")

    ok_db, detail_db = await db.ping()
    lines.append("✅ <b>MariaDB</b>: подключена" if ok_db else f"❌ <b>MariaDB</b>: {detail_db}")

    return "\n".join(lines)
