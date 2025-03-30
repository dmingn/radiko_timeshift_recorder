import datetime
import errno
import os
import time
from pathlib import Path
from queue import PriorityQueue
from typing import Annotated

import typer
from slack_sdk import WebhookClient

from radiko_timeshift_recorder.download import download
from radiko_timeshift_recorder.programs import Program, Programs
from radiko_timeshift_recorder.rules import Rules


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


def program_to_out_filepath(program: Program, out: Path) -> Path:
    out_filepath = (out / program.title / program_to_filename(program)).resolve()

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


def main(
    rules: Annotated[
        Path,
        typer.Option(exists=True),
    ],
    out: Annotated[
        Path,
        typer.Option(
            exists=True,
            file_okay=False,
            dir_okay=True,
            writable=True,
        ),
    ],
):
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
            programs = Programs.from_date(date)

            for program in programs:
                if program.is_finished and rules_.to_record(program=program):
                    pq.put_nowait(program)

        while not pq.empty():
            program = pq.get_nowait()

            out_filepath = program_to_out_filepath(program=program, out=out)
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
