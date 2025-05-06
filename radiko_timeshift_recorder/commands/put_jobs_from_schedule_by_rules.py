from pathlib import Path
from typing import Annotated

import typer
from logzero import logger
from requests import HTTPError

from radiko_timeshift_recorder.client import Client
from radiko_timeshift_recorder.job import Job, fetch_all_jobs
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

        jobs_succeed: list[Job] = []
        jobs_already_exist: list[Job] = []
        jobs_failed: list[Job] = []
        with Client(server_url) as client:
            for job in jobs_to_record:
                try:
                    client.put_job(job)
                except HTTPError as e:
                    if e.response.status_code == 409:
                        logger.debug(f"Job already exists: {job}")
                        jobs_already_exist.append(job)
                    else:
                        logger.exception(f"Failed to put job: {job}")
                        jobs_failed.append(job)

                    continue
                except Exception:
                    logger.exception(f"Failed to put job: {job}")
                    jobs_failed.append(job)
                    continue
                else:
                    jobs_succeed.append(job)

        if jobs_succeed:
            logger.info(f"Successfully put {len(jobs_succeed)} jobs.")

        if jobs_already_exist:
            logger.info(
                f"Skipped {len(jobs_already_exist)} jobs because they already exist."
            )

        if jobs_failed:
            logger.error(f"Failed to put {len(jobs_failed)} jobs.")
            raise typer.Exit(1)
    except typer.Exit:
        raise
    except Exception:
        logger.exception(
            f"Failed to put jobs from schedule by rules: {rules_yaml_paths}"
        )
        raise typer.Exit(1)
