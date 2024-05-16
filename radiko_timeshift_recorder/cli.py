import datetime
import errno
import json
import os
import subprocess
import time
from pathlib import Path
from queue import PriorityQueue

import click
from slack_sdk import WebhookClient

from radiko_timeshift_recorder.radiko import DateAreaSchedule, Program
from radiko_timeshift_recorder.rules import Rules


def program_to_filename(program: Program) -> str:
    return (
        " - ".join(
            [
                program.ft.strftime("%Y-%m-%d %H-%M-%S"),
                program.title.replace("/", "／"),
                program.pfm.replace("/", "／"),
            ]
        )
        + ".mp4"
    )


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

    while True:
        try:
            part_filepath.replace(out_filepath)
        except OSError as e:
            if e.errno == errno.ENAMETOOLONG:
                out_filepath = out_filepath.with_stem(out_filepath.stem[:-1])
            else:
                raise e
        else:
            break


@click.command()
@click.option("--rules", type=click.Path(exists=True, path_type=Path), required=True)
@click.option(
    "--out",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    required=True,
)
def main(rules: Path, out: Path):
    try:
        client = WebhookClient(os.environ["SLACK_WEBHOOK_URL"])
    except KeyError:
        client = None

    def job():
        rules_ = Rules.from_yaml(rules)

        pq: PriorityQueue[Program] = PriorityQueue()

        for date in [
            datetime.date.today() - datetime.timedelta(days=i) for i in range(8)
        ]:
            date_area_schedule = DateAreaSchedule.from_date_area(date=date)

            # TODO: loop over stations that appears in the rules
            for station_schedule in date_area_schedule.stations:
                for program in station_schedule.progs:
                    if program.is_finished and rules_.to_record(program=program):
                        pq.put_nowait(program)

        while not pq.empty():
            program = pq.get_nowait()

            out_filepath = (
                out / program.title / program_to_filename(program)
            ).resolve()

            out_filepath.parent.mkdir(parents=True, exist_ok=True)

            if not out_filepath.exists():
                try:
                    download(program=program, out_filepath=out_filepath)
                except BaseException as e:
                    message = f"Failed to download {out_filepath}: {e}"
                else:
                    message = f"Successfully downloaded {out_filepath}"

                print(message)
                if client:
                    client.send(text=message)

            pq.task_done()

    while True:
        job()

        time.sleep(3 * 60 * 60)
