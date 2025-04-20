import asyncio
import errno
import json
from pathlib import Path

from logzero import logger

from radiko_timeshift_recorder.programs import Program


def program_to_filename(program: Program) -> str:
    return (
        " - ".join(
            [
                program.ft.strftime("%Y-%m-%d %H-%M-%S"),
                program.title.replace("/", "／"),
            ]
            + ([program.pfm.replace("/", "／")] if program.pfm else [])
        )
        + ".mp4"
    )


def program_to_out_filepath(program: Program, out_dir: Path) -> Path:
    out_filepath = (out_dir / program.title / program_to_filename(program)).resolve()

    while True:
        try:
            out_filepath.exists()
        except OSError as e:
            if e.errno == errno.ENAMETOOLONG:
                out_filepath = out_filepath.with_stem(out_filepath.stem[:-1])
            else:
                raise e
        else:
            break

    return out_filepath


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


async def download(program: Program, out_dir: Path) -> None:
    out_filepath = program_to_out_filepath(program, out_dir)

    if out_filepath.exists():
        logger.info(f"File {out_filepath} already exists. Skipping download.")
        return

    out_filepath.parent.mkdir(parents=True, exist_ok=True)

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
