import asyncio
import json
import tempfile
from pathlib import Path

from logzero import logger

from radiko_timeshift_recorder.job import Job
from radiko_timeshift_recorder.radiko import Program
from radiko_timeshift_recorder.trim_filestem import trim_filestem


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


def get_out_filepath(job: Job, out_dir: Path) -> Path:
    out_filepath = (
        out_dir / job.station_id / job.program.title / program_to_filename(job.program)
    ).resolve()

    return trim_filestem(out_filepath)


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


async def download_stream(url: str, out_filepath: Path) -> None:
    # TODO: avoid using subprocess and use streamlink API
    # TODO: avoid using pipe
    # TODO: avoid using ffmpeg if possible
    proc = await asyncio.create_subprocess_shell(
        cmd=" ".join(
            [
                "python",
                "-m",
                "streamlink",
                url,
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
                f'"{out_filepath}"',
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


async def download(job: Job, out_dir: Path) -> None:
    out_filepath = get_out_filepath(job, out_dir)

    if out_filepath.exists():
        logger.info(f"File {out_filepath} already exists. Skipping download.")
        return

    out_filepath.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile(
        mode="w+b",
        suffix=out_filepath.suffix,
        dir=out_filepath.parent,
        delete=True,
    ) as tmp_file:
        temp_filepath = Path(tmp_file.name)

        await download_stream(job.url, temp_filepath)

        recorded_dur = await get_duration(temp_filepath)

        if abs(recorded_dur - job.program.dur) > 1:
            raise AssertionError(
                f"Recorded duration {recorded_dur} differs from the program duration {job.program.dur}."
            )

        temp_filepath.replace(out_filepath)
