import asyncio
import functools
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Annotated, Awaitable, Callable

import typer
import uvicorn
from fastapi import Depends, FastAPI, HTTPException, status
from logzero import logger

from radiko_timeshift_recorder.download import download
from radiko_timeshift_recorder.job_queue import JobAlreadyExistsError, JobQueue
from radiko_timeshift_recorder.programs import Program


@functools.cache
def get_job_queue() -> JobQueue[Program]:
    return JobQueue()


async def worker(
    id: int,
    job_queue: JobQueue[Program],
    process_job: Callable[[Program], Awaitable[None]],
) -> None:
    logger.info(f"Worker-{id} started")

    while True:
        program = await job_queue.get()
        logger.info(f"Worker-{id} received job: {program}")

        try:
            await process_job(program)
        except Exception as e:
            logger.exception(
                f"Worker-{id} failed to process job: {program}, error: {e}"
            )

        job_queue.mark_done(program)
        logger.info(f"Worker-{id} finished job: {program}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.worker_tasks = []

    for i in range(app.state.num_workers):
        logger.info(f"Starting worker-{i}")
        app.state.worker_tasks.append(
            asyncio.create_task(
                worker(
                    id=i, job_queue=get_job_queue(), process_job=app.state.process_job
                )
            )
        )

    yield

    for task in app.state.worker_tasks:
        logger.info(f"Cancelling worker-{task.get_name()}")
        task.cancel()

    await asyncio.gather(*app.state.worker_tasks, return_exceptions=True)


fastapi_app = FastAPI(lifespan=lifespan)


@fastapi_app.post(
    "/job_queue",
    response_model=Program,
    status_code=status.HTTP_201_CREATED,
    responses={status.HTTP_409_CONFLICT: {"description": "Job already exists"}},
)
async def put_job(
    program: Program, job_queue: JobQueue[Program] = Depends(get_job_queue)
) -> Program:
    try:
        await job_queue.put(program)
        logger.info(f"Put job to queue: {program}")
    except JobAlreadyExistsError:
        logger.info(f"Job already exists in queue: {program}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Job already exists in queue",
        )

    return program


typer_app = typer.Typer()


@typer_app.command()
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
    fastapi_app.state.process_job = lambda program: download(
        program=program, out_dir=out_dir
    )
    fastapi_app.state.num_workers = num_workers
    uvicorn.run(app=fastapi_app, host=host, port=port)
