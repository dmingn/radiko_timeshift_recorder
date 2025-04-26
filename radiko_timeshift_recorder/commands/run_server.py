from pathlib import Path
from typing import Annotated

import typer
import uvicorn
from logzero import logger

from radiko_timeshift_recorder.download import download
from radiko_timeshift_recorder.server import app as fastapi_app

app = typer.Typer()


@app.command()
def run_server(
    out_dir: Annotated[
        Path,
        typer.Option(
            exists=True,
            file_okay=False,
            dir_okay=True,
            writable=True,
            help="Directory to save downloaded files",
        ),
    ],
    host: Annotated[str, typer.Option(help="Host to run the server on")] = "127.0.0.1",
    port: Annotated[int, typer.Option(help="Port to run the server on")] = 8000,
    num_workers: Annotated[
        int, typer.Option(min=1, help="Number of workers to run")
    ] = 3,
):
    try:
        fastapi_app.state.process_job = lambda job: download(job=job, out_dir=out_dir)
        fastapi_app.state.num_workers = num_workers
        uvicorn.run(app=fastapi_app, host=host, port=port)
    except Exception:
        logger.exception("Failed to run server")
        raise typer.Exit(1)
