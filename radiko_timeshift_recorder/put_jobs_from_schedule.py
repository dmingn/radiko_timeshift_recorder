import datetime
import itertools
from pathlib import Path
from typing import Annotated

import typer
from logzero import logger

from radiko_timeshift_recorder.client import Client
from radiko_timeshift_recorder.programs import Programs
from radiko_timeshift_recorder.rules import Rules

typer_app = typer.Typer()


@typer_app.command()
def put_jobs_from_schedule(
    rules_path: Annotated[
        Path,
        typer.Option(
            "--rules", exists=True, help="Path to the rules YAML file or directory"
        ),
    ],
    server_url: Annotated[
        str,
        typer.Option(help="URL of the server"),
    ] = "http://localhost:8000",
):
    rules = Rules.from_yaml(rules_path)

    programs = itertools.chain.from_iterable(
        [
            Programs.from_date(datetime.date.today() - datetime.timedelta(days=i))
            for i in range(8)
        ]
    )

    with Client(server_url) as client:
        for program in [
            program
            for program in sorted(programs)
            if program.is_finished and rules.to_record(program=program)
        ]:
            try:
                client.put_job(program)
            except Exception as e:
                logger.exception(f"Failed to put job: {program}, error: {e}")
                continue
