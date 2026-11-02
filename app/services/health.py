"""Проверка работоспособности компонентов."""

import logging
import platform
import shutil
import socket
from datetime import datetime

import psutil

from app.services import db, gigachat, whisper

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


def _get_ip() -> str:
    """Пытается определить внешний IP (через подключение к DNS 8.8.8.8)."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "неизвестен"


async def collect_health() -> str:
    """Возвращает отчёт о состоянии компонентов в HTML для Telegram."""
    lines: list[str] = ["<b>🏥 Проверка компонентов</b>", ""]

    # 1. Процесс и хост
    proc = psutil.Process()
    mem_mb = proc.memory_info().rss / 1024 / 1024
    uptime = str(datetime.now() - datetime.fromtimestamp(proc.create_time())).split(".")[0]
    lines.append(f"✅ <b>Процесс</b>: жив · RAM {mem_mb:.0f} MB · uptime {uptime}")
    lines.append(f"🌐 <b>IP сервера</b>: <code>{_get_ip()}</code>")

    # 2. Ресурсы (RAM, Swap, Диск)
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

    # Место на корневом диске (/)
    total, used, free = shutil.disk_usage("/")
    free_gb = free / (1024**3)
    total_gb = total / (1024**3)
    used_percent = (used / total) * 100

    disk_icon = "⚠️" if used_percent > 90 else "💾"
    lines.append(
        f"{disk_icon} <b>Диск</b>: {free_gb:.1f} / {total_gb:.1f} GB свободно "
        f"({used_percent:.0f}% занято)"
    )

    # 3. Компоненты
    lines.append("")

    ok_ai, detail_ai = await gigachat.ping()
    if ok_ai:
        lines.append("✅ <b>GigaChat</b>: отвечает")
    else:
        lines.append(f"❌ <b>GigaChat</b>: {detail_ai}")

    if whisper.is_configured():
        lines.append("✅ <b>whisper</b>: настроен (CLI)")
    else:
        lines.append("❌ <b>whisper</b>: не найден (проверьте пути в .env)")

    ok_db, detail_db = await db.ping()
    if ok_db:
        lines.append("✅ <b>MariaDB</b>: подключена")
    else:
        lines.append(f"❌ <b>MariaDB</b>: {detail_db}")

    return "\n".join(lines)
