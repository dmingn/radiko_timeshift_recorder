import asyncio
import errno
import logging
import shlex
import tempfile
from pathlib import Path
from typing import Optional

import tenacity
from logzero import logger

from radiko_timeshift_recorder.get_duration import get_duration
from radiko_timeshift_recorder.job import Job
from radiko_timeshift_recorder.radiko import Program


def generate_filename_candidates(program: Program) -> tuple[str, ...]:
    name_parts = [
        program.ft.strftime("%Y-%m-%d %H-%M-%S"),
        program.title.replace("/", "／"),
    ] + ([program.pfm.replace("/", "／")] if program.pfm else [])

    return tuple(" - ".join(name_parts[:i]) for i in range(len(name_parts), 0, -1))


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
                "-hide_banner",
                "-i",
                "-",
                "-codec",
                "copy",
                "-format",
                "mp4",
                "-y",
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


def try_rename_with_candidates(
    temp_filepath: Path, out_filepath_candidates: list[Path]
) -> Path:
    if not out_filepath_candidates:
        raise ValueError("out_filepath_candidates list cannot be empty.")

    name_too_long_exception: Optional[OSError] = None
    for out_filepath_candidate in out_filepath_candidates:
        try:
            temp_filepath.replace(out_filepath_candidate)
            return out_filepath_candidate
        except OSError as e:
            if e.errno == errno.ENAMETOOLONG:
                name_too_long_exception = e
                continue
            else:
                raise e

    if name_too_long_exception:
        raise name_too_long_exception

    raise RuntimeError(
        "try_rename_with_candidates reached an unexpected state. This should not happen."
    )


@tenacity.retry(
    stop=tenacity.stop_after_attempt(max_attempt_number=3),
    wait=tenacity.wait_fixed(wait=60),
    before_sleep=tenacity.before_sleep_log(logger=logger, log_level=logging.INFO),
)
async def download(job: Job, out_dir: Path) -> None:
    program_dir = out_dir / job.station_id / job.program.title
    filename_candidates = generate_filename_candidates(job.program)
    suffix = ".mp4"

    out_filepath_candidates = [
        program_dir.joinpath(filename).with_suffix(suffix)
        for filename in filename_candidates
    ]

    for out_filepath in out_filepath_candidates:
        if out_filepath.exists():
            logger.info(f"File {out_filepath} already exists. Skipping download.")
            return

    program_dir.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile(
        mode="w+b",
        suffix=suffix,
        dir=program_dir,
        delete=True,
    ) as tmp_file:
        temp_filepath = Path(tmp_file.name)

        await download_stream(job.url, temp_filepath)

        recorded_dur = await get_duration(temp_filepath)

        if abs(recorded_dur - job.program.dur) > 1:
            raise AssertionError(
                f"Recorded duration {recorded_dur} differs from the program duration {job.program.dur}."
            )

        out_filepath = try_rename_with_candidates(
            temp_filepath, out_filepath_candidates
        )

    logger.info(f"Downloaded {job} to {out_filepath}")
