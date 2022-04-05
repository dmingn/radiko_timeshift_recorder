import datetime
import os
import subprocess
import time
from pathlib import Path
from typing import Optional

import click
import schedule
from slack_sdk import WebhookClient

from radiko_timeshift_recorder.radiko import DateAreaSchedule, Program
from radiko_timeshift_recorder.rules import Rules


def program_to_filename(program: Program) -> str:
    return (
        " - ".join(
            [
                datetime.datetime.strptime(program.ft, "%Y%m%d%H%M%S").strftime(
                    "%Y-%m-%d %H-%M-%S"
                ),
                program.title,
                program.pfm,
            ]
        )
        + ".mp4"
    )


@click.command()
@click.option("--rules", type=click.Path(exists=True, path_type=Path), required=True)
@click.option(
    "--out",
    type=click.Path(exists=True, file_okay=False, path_type=Path),
    required=True,
)
@click.option("--at", type=str, default=None)
def main(rules: Path, out: Path, at: Optional[str]):
    try:
        client = WebhookClient(os.environ["SLACK_WEBHOOK_URL"])
    except KeyError:
        client = None

    def job():
        rules_ = Rules.from_yaml(rules)

        dates = sorted(
            [datetime.date.today() - datetime.timedelta(days=i) for i in range(8)]
        )

        for date in dates:
            date_area_schedule = DateAreaSchedule.from_date_area(date=date)

            # TODO: loop over stations that appears in the rules
            for station_schedule in date_area_schedule.stations:
                for program in station_schedule.progs:
                    if program.is_finished and rules_.to_record(program=program):
                        out_filepath = (
                            out / program.title / program_to_filename(program)
                        ).resolve()

                        out_filepath.parent.mkdir(parents=True, exist_ok=True)

                        if not out_filepath.exists():
                            try:
                                # TODO: stop using subprocess and use streamlink API
                                # TODO: stop using pipe
                                # TODO: stop using ffmpeg if possible
                                subprocess.run(
                                    " ".join(
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
                                            f'"{out_filepath}"',
                                        ]
                                    ),
                                    shell=True,
                                )
                                # TODO: duration check
                            except BaseException as e:
                                message = f"Failed to download {out_filepath}: {e}"
                            else:
                                message = f"Successfully downloaded {out_filepath}"

                            print(message)
                            if client:
                                client.send(text=message)

    if at:
        schedule.every().day.at(at).do(job)

        while True:
            schedule.run_pending()
            time.sleep(1)
    else:
        job()
