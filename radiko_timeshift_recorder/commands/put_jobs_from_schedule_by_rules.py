from pathlib import Path
from typing import Annotated

import typer
from logzero import logger

from radiko_timeshift_recorder.client import Client
from radiko_timeshift_recorder.job import fetch_all_jobs
from radiko_timeshift_recorder.rules import Rules

app = typer.Typer()


@app.command()
def put_jobs_from_schedule_by_rules(
    rules_yaml_paths: Annotated[
        list[Path],
        typer.Argument(
            file_okay=True,
            dir_okay=False,
            exists=True,
            readable=True,
            help="Path to the rules YAML file",
        ),
    ],
    server_url: Annotated[
        str,
        typer.Option(help="URL of the server"),
    ] = "http://localhost:8000",
):
    try:
        try:
            rules = Rules.from_yaml_paths(rules_yaml_paths)
        except Exception:
            logger.exception(f"Failed to load rules from YAML: {rules_yaml_paths}")
            raise typer.Exit(1)

        try:
            jobs = fetch_all_jobs()
        except Exception:
            logger.exception(f"Failed to fetch jobs from schedule: {rules_yaml_paths}")
            raise typer.Exit(1)

        try:
            jobs_to_record = [
                job
                for job in sorted(jobs)
                if job.is_ready_to_process
                and rules.to_record(station_id=job.station_id, program=job.program)
            ]
        except Exception:
            logger.exception(f"Failed to filter jobs by rules: {rules_yaml_paths}")
            raise typer.Exit(1)

        with Client(server_url) as client:
            for job in jobs_to_record:
                try:
                    client.put_job(job)
                except Exception as e:
                    logger.exception(f"Failed to put job: {job}, error: {e}")
                    continue
    except typer.Exit:
        raise
    except Exception:
        logger.exception(
            f"Failed to put jobs from schedule by rules: {rules_yaml_paths}"
        )
        raise typer.Exit(1)
