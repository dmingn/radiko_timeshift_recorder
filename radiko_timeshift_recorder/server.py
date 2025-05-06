import asyncio
import functools
from contextlib import asynccontextmanager
from typing import Awaitable, Callable

from fastapi import Depends, FastAPI, HTTPException, status
from logzero import logger

from radiko_timeshift_recorder.job import Job
from radiko_timeshift_recorder.job_queue import JobAlreadyExistsError, JobQueue


@functools.cache
def get_job_queue() -> JobQueue[Job]:
    return JobQueue()


async def worker(
    id: int,
    job_queue: JobQueue[Job],
    process_job: Callable[[Job], Awaitable[None]],
) -> None:
    logger.info(f"Worker-{id} started")

    while True:
        job = await job_queue.get()
        logger.debug(f"Worker-{id} received job: {job}")

        try:
            await process_job(job)
        except Exception as e:
            logger.exception(f"Worker-{id} failed to process job: {job}, error: {e}")

        job_queue.mark_done(job)
        logger.debug(f"Worker-{id} finished job: {job}")


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


app = FastAPI(lifespan=lifespan)


@app.post(
    "/job_queue",
    response_model=Job,
    status_code=status.HTTP_201_CREATED,
    responses={status.HTTP_409_CONFLICT: {"description": "Job already exists"}},
)
async def put_job(job: Job, job_queue: JobQueue[Job] = Depends(get_job_queue)) -> Job:
    try:
        await job_queue.put(job)
        logger.info(f"Put job to queue: {job}")
    except JobAlreadyExistsError:
        logger.info(f"Job already exists in queue: {job}")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Job already exists in queue",
        )

    return job
