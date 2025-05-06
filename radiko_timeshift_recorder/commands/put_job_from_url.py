from typing import Annotated

import typer
from logzero import logger
from requests import HTTPError

from radiko_timeshift_recorder.client import Client
from radiko_timeshift_recorder.job import fetch_job_by_url

app = typer.Typer()


@app.command()
def put_job_from_url(
    url: Annotated[str, typer.Argument(help="URL of the program to put job from")],
    server_url: Annotated[
        str,
        typer.Option(help="URL of the server"),
    ] = "http://localhost:8000",
):
    try:
        try:
            job = fetch_job_by_url(url)
        except Exception:
            logger.exception(f"Failed to fetch job from URL: {url}")
            raise typer.Exit(1)

        with Client(server_url) as client:
            try:
                client.put_job(job)
            except HTTPError as e:
                if e.response.status_code == 409:
                    logger.info(f"Job already exists: {job}")
                else:
                    logger.exception(f"Failed to put job: {job}")
                    raise typer.Exit(1)
            except Exception:
                logger.exception(f"Failed to put job: {job}")
                raise typer.Exit(1)
    except typer.Exit:
        raise
    except Exception:
        logger.exception(f"Failed to put job from URL: {url}")
        raise typer.Exit(1)
