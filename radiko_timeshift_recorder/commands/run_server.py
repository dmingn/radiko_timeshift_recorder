from pathlib import Path
from typing import Annotated

import typer
import uvicorn
from logzero import logger

from radiko_timeshift_recorder.download import DEFAULT_OUTPUT_FILE_MODE, download
from radiko_timeshift_recorder.fs_unix import parse_unix_mode_string
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
    output_file_mode: Annotated[
        str,
        typer.Option(
            help=(
                "Octal permission bits for recorded .mp4 files after download "
                f"(e.g. 644 or 0644). Default: {DEFAULT_OUTPUT_FILE_MODE:o}."
            ),
        ),
    ] = "644",
):
    try:
        file_mode = parse_unix_mode_string(output_file_mode)
        fastapi_app.state.process_job = lambda job: download(
            job=job,
            out_dir=out_dir,
            output_file_mode=file_mode,
        )
        fastapi_app.state.num_workers = num_workers
        uvicorn.run(app=fastapi_app, host=host, port=port)
    except Exception:
        logger.exception("Failed to run server")
        raise typer.Exit(1)
