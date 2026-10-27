"""Распознавание речи через whisper.cpp (CLI)."""

import asyncio
import logging
import os
import subprocess
import tempfile

from aiogram import Bot
from aiogram.types import Voice

from app.config import settings

logger = logging.getLogger(__name__)

# Защита от одновременных запусков (1ГБ ОЗУ)
_semaphore = asyncio.Semaphore(1)


def is_configured() -> bool:
    return bool(
        os.path.exists(settings.whisper_cli)
        and os.path.exists(settings.whisper_model)
    )


async def transcribe_voice(bot: Bot, voice: Voice) -> str:
    """Скачивает .oga, конвертирует в wav и распознаёт."""
    if not is_configured():
        raise RuntimeError("whisper не настроен (проверьте пути в .env)")

    async with _semaphore:
        # 1. Скачиваем голосовое во временную папку
        with tempfile.TemporaryDirectory() as tmpdir:
            oga_path = os.path.join(tmpdir, "voice.oga")
            wav_path = os.path.join(tmpdir, "voice.wav")

            file = await bot.get_file(voice.file_id)
            await bot.download_file(file.file_path, oga_path)

            # 2. Конвертируем в 16kHz mono wav (требование whisper)
            ffmpeg_cmd = [
                "ffmpeg", "-y", "-i", oga_path,
                "-ar", "16000", "-ac", "1", "-c:a", "pcm_s16le",
                wav_path,
            ]
            proc = await asyncio.create_subprocess_exec(
                *ffmpeg_cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            await proc.wait()
            if proc.returncode != 0:
                raise RuntimeError("Ошибка ffmpeg при конвертации")

            # 3. Распознаём через whisper-cli
            # -nt : без таймкодов, -l ru : язык русский, -np : без вывода прогресса
            whisper_cmd = [
                settings.whisper_cli,
                "-m", settings.whisper_model,
                "-f", wav_path,
                "-l", "ru",
                "-nt",
                "-np",
            ]
            logger.info("Запуск whisper-cli...")
            proc = await asyncio.create_subprocess_exec(
                *whisper_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()

            if proc.returncode != 0:
                logger.error("whisper-cli stderr: %s", stderr.decode())
                raise RuntimeError("Ошибка whisper-cli")

            # Чистим вывод от лишних пробелов
            text = stdout.decode("utf-8").strip()
            logger.info("Распознано: %s", text)
            return text
