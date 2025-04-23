from typing import Annotated

import typer
from logzero import logger

from radiko_timeshift_recorder.client import Client
from radiko_timeshift_recorder.job import fetch_job_by_url

typer_app = typer.Typer()


@typer_app.command()
def put_job_from_url(
    url: Annotated[str, typer.Argument(help="URL of the program to put job from")],
    server_url: Annotated[
        str,
        typer.Option(help="URL of the server"),
    ] = "http://localhost:8000",
):
    try:
        job = fetch_job_by_url(url)
    except ValueError as e:
        logger.exception(f"Failed to fetch job from URL: {url}, error: {e}")
        raise typer.Exit(1)

    with Client(server_url) as client:
        try:
            client.put_job(job)
        except Exception as e:
            logger.exception(f"Failed to put job: {job}, error: {e}")
            raise typer.Exit(1)
