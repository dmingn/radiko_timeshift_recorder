import asyncio
import json
from pathlib import Path

from logzero import logger


async def get_duration(filepath: Path) -> float:
    proc = await asyncio.create_subprocess_exec(
        "ffprobe",
        "-hide_banner",
        "-show_streams",
        "-print_format",
        "json",
        str(filepath.resolve()),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    stdout, stderr = await proc.communicate()

    if proc.returncode != 0:
        logger.debug(f"stdout: {stdout.decode().strip()}")
        logger.debug(f"stderr: {stderr.decode().strip()}")
        raise RuntimeError(
            f"Failed to get duration of {filepath}: {stderr.decode().strip()}"
        )

    return float(json.loads(stdout)["streams"][0]["duration"])
