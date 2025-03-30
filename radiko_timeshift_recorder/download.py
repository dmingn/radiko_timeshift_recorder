import asyncio
import json
from pathlib import Path

from radiko_timeshift_recorder.programs import Program


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
    stdout, _ = await proc.communicate()
    return float(json.loads(stdout)["streams"][0]["duration"])


async def download(program: Program, out_filepath: Path) -> None:
    part_filepath = out_filepath.with_stem(program.id).with_suffix(
        out_filepath.suffix + ".part"
    )

    # TODO: avoid using subprocess and use streamlink API
    # TODO: avoid using pipe
    # TODO: avoid using ffmpeg if possible
    proc = await asyncio.create_subprocess_shell(
        cmd=" ".join(
            [
                "python",
                "-m",
                "streamlink",
                program.url,
                "best",
                "-O",
                "|",
                "ffmpeg",
                "-i",
                "-",
                "-c",
                "copy",
                "-f",
                "mp4",
                "-y",
                f'"{part_filepath}"',
            ]
        ),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    stdout, stderr = await proc.communicate()

    if proc.returncode != 0:
        raise RuntimeError(
            f"Command failed with exit code {proc.returncode}\n{stderr.decode()}"
        )

    recorded_dur = await get_duration(part_filepath)

    if abs(recorded_dur - program.dur) > 1:
        raise AssertionError(
            f"Recorded duration {recorded_dur} differs from the program duration {program.dur}."
        )

    part_filepath.replace(out_filepath)
