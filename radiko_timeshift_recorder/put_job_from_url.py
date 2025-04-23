import datetime
from typing import Annotated

import typer
from logzero import logger

from radiko_timeshift_recorder.client import Client
from radiko_timeshift_recorder.job import Jobs


def find_job_by_url(url: str) -> Jobs | None:
    for i in range(8):
        for job in Jobs.from_date(datetime.date.today() - datetime.timedelta(days=i)):
            if job.url == url:
                return job

    return None


typer_app = typer.Typer()


@typer_app.command()
def put_job_from_url(
    url: Annotated[str, typer.Argument(help="URL of the program to put job from")],
    server_url: Annotated[
        str,
        typer.Option(help="URL of the server"),
    ] = "http://localhost:8000",
):
    job = find_job_by_url(url)

    if job is None:
        logger.error(f"Job not found for URL: {url}")
        raise typer.Exit(1)

    with Client(server_url) as client:
        try:
            client.put_job(job)
        except Exception as e:
            logger.exception(f"Failed to put job: {job}, error: {e}")
            raise typer.Exit(1)
