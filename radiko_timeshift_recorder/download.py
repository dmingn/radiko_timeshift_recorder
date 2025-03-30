import json
import subprocess
from pathlib import Path

from radiko_timeshift_recorder.programs import Program


def get_duration(filepath: Path) -> float:
    proc = subprocess.run(
        [
            "ffprobe",
            "-hide_banner",
            "-show_streams",
            "-print_format",
            "json",
            str(filepath.resolve()),
        ],
        capture_output=True,
        text=True,
    )
    return float(json.loads(proc.stdout)["streams"][0]["duration"])


def download(program: Program, out_filepath: Path) -> None:
    part_filepath = out_filepath.with_stem(program.id).with_suffix(
        out_filepath.suffix + ".part"
    )

    # TODO: avoid using subprocess and use streamlink API
    # TODO: avoid using pipe
    # TODO: avoid using ffmpeg if possible
    subprocess.run(
        args=" ".join(
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
        shell=True,
    )

    recorded_dur = get_duration(part_filepath)

    if abs(recorded_dur - program.dur) > 1:
        raise AssertionError(
            f"Recorded duration {recorded_dur} differs from the program duration {program.dur}."
        )

    part_filepath.replace(out_filepath)
