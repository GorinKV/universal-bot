"""Проверка работоспособности компонентов."""

import logging
import platform
from datetime import datetime

import psutil

from app.services import gigachat, whisper

logger = logging.getLogger(__name__)


def log_startup_info() -> None:
    """Логирует окружение при старте — удобно смотреть через journalctl."""
    logger.info("=== Старт бота ===")
    logger.info("Python: %s", platform.python_version())
    logger.info("Хост: %s", platform.node())
    vm = psutil.virtual_memory()
    logger.info(
        "RAM VPS: %.0f / %.0f MB (%.0f%%)",
        vm.used / 1024 / 1024,
        vm.total / 1024 / 1024,
        vm.percent,
    )
    swap = psutil.swap_memory()
    if swap.total > 0:
        logger.info(
            "Swap: %.0f / %.0f MB",
            swap.used / 1024 / 1024,
            swap.total / 1024 / 1024,
        )


async def collect_health() -> str:
    """Возвращает отчёт о состоянии компонентов в HTML для Telegram."""
    lines: list[str] = ["<b>🏥 Проверка компонентов</b>", ""]

    proc = psutil.Process()
    mem_mb = proc.memory_info().rss / 1024 / 1024
    uptime = str(datetime.now() - datetime.fromtimestamp(proc.create_time())).split(".")[0]
    lines.append(f"✅ <b>Процесс</b>: жив · RAM {mem_mb:.0f} MB · uptime {uptime}")

    vm = psutil.virtual_memory()
    lines.append(
        f"   RAM VPS: {vm.used / 1024 / 1024:.0f} / "
        f"{vm.total / 1024 / 1024:.0f} MB ({vm.percent}%)"
    )
    swap = psutil.swap_memory()
    if swap.total > 0:
        lines.append(
            f"   Swap: {swap.used / 1024 / 1024:.0f} / "
            f"{swap.total / 1024 / 1024:.0f} MB"
        )

    lines.append("")
    
    ok, detail = await gigachat.ping()
    if ok:
        lines.append("✅ <b>GigaChat</b>: отвечает")
    else:
        lines.append(f"❌ <b>GigaChat</b>: {detail}")

    if whisper.is_configured():
        lines.append("✅ <b>whisper</b>: настроен (CLI)")
    else:
        lines.append("❌ <b>whisper</b>: не найден (проверьте пути в .env)")

    lines.append("⏸ <b>MariaDB</b>: не настроена (Ф3)")

    return "\n".join(lines)
