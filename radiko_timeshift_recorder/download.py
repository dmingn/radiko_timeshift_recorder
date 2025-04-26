import asyncio
import json
import logging
import shlex
import tempfile
from pathlib import Path

import tenacity
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
        shlex.quote(str(filepath.resolve())),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, _ = await proc.communicate()
    return float(json.loads(stdout)["streams"][0]["duration"])


async def download_stream(url: str, out_filepath: Path) -> None:
    # Pipe streamlink's output directly to ffmpeg.
    # This helps prevent issues where the end of the stream might be cut off
    # if saved directly by streamlink alone.
    proc = await asyncio.create_subprocess_shell(
        cmd=" ".join(
            [
                "python",
                "-m",
                "streamlink",
                shlex.quote(url),
                "best",
                "--stdout",
                "|",
                "ffmpeg",
                "-i",
                "-",
                "-codec",
                "copy",
                "-format",
                "mp4",
                "-overwrite",
                shlex.quote(str(out_filepath.resolve())),
            ]
        ),
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    stdout, stderr = await proc.communicate()

    if proc.returncode != 0:
        logger.debug(f"stdout: {stdout.decode().strip()}")
        logger.debug(f"stderr: {stderr.decode().strip()}")
        raise RuntimeError(
            f"Failed to download stream {url}: {stderr.decode().strip()}"
        )


@tenacity.retry(
    stop=tenacity.stop_after_attempt(max_attempt_number=3),
    wait=tenacity.wait_fixed(wait=60),
    before_sleep=tenacity.before_sleep_log(logger=logger, log_level=logging.INFO),
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
