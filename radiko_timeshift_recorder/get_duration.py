import asyncio
import json
from pathlib import Path

from logzero import logger


class FFprobeError(RuntimeError):
    pass


def parse_ffprobe_duration(stdout: bytes) -> float:
    data = json.loads(stdout)
    streams = data.get("streams")
    if not streams:
        raise ValueError("No audio streams found in ffprobe output")

    duration_str = streams[0].get("duration")
    if duration_str is None:
        raise ValueError("Duration not found in the audio stream")

    return float(duration_str)


async def get_duration(filepath: Path) -> float:
    command = [
        "ffprobe",
        "-v",
        "error",
        "-select_streams",
        "a:0",
        "-show_entries",
        "stream=duration",
        "-print_format",
        "json",
        str(filepath.resolve()),
    ]

    logger.debug(f"Running ffprobe command: {' '.join(command)}")

    proc = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    stdout, stderr = await proc.communicate()

    if proc.returncode != 0:
        logger.debug(f"stdout: {stdout.decode().strip()}")
        logger.debug(f"stderr: {stderr.decode().strip()}")
        raise FFprobeError(
            f"Failed to run ffprobe on {filepath}: {stderr.decode().strip()}"
        )

    try:
        return parse_ffprobe_duration(stdout)
    except Exception as e:
        raise FFprobeError(f"Failed to parse ffprobe output: {e}") from e
