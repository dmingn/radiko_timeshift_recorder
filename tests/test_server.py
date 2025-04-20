import asyncio
from typing import Any, Generator

import pytest
from fastapi import FastAPI
from fastapi.encoders import jsonable_encoder
from fastapi.testclient import TestClient

from radiko_timeshift_recorder.job_queue import JobQueue
from radiko_timeshift_recorder.programs import Program
from radiko_timeshift_recorder.server import fastapi_app, get_job_queue, lifespan


@pytest.fixture
def test_client_with_override() -> Generator[tuple[TestClient, JobQueue], Any, None]:
    test_queue: JobQueue[Program] = JobQueue()

    def override_get_job_queue() -> JobQueue[Program]:
        return test_queue

    fastapi_app.dependency_overrides[get_job_queue] = override_get_job_queue
    client = TestClient(fastapi_app)

    yield client, test_queue

    fastapi_app.dependency_overrides.clear()


def test_put_job_success(
    test_client_with_override: tuple[TestClient, JobQueue], sample_program: Program
):
    client, test_queue = test_client_with_override
    response = client.post("/job_queue", json=jsonable_encoder(sample_program))

    assert response.status_code == 201
    assert response.json() == jsonable_encoder(sample_program)
    assert test_queue.qsize() == 1
    assert asyncio.run(test_queue.get()) == sample_program


def test_put_job_conflict(
    test_client_with_override: tuple[TestClient, JobQueue], sample_program: Program
):
    client, test_queue = test_client_with_override
    asyncio.run(test_queue.put(sample_program))

    response = client.post("/job_queue", json=jsonable_encoder(sample_program))

    assert response.status_code == 409
    assert test_queue.qsize() == 1


def test_put_job_validation_error(
    test_client_with_override: tuple[TestClient, JobQueue],
):
    invalid_program = {"title": "title only"}

    client, _ = test_client_with_override
    response = client.post("/job_queue", json=invalid_program)

    assert response.status_code == 422


@pytest.mark.asyncio
async def test_lifespan_starts_and_cancels_workers():
    @pytest.mark.asyncio
    async def mock_process_job(program):
        await asyncio.sleep(0.1)

    app = FastAPI(lifespan=lifespan)
    app.state.num_workers = 3
    app.state.process_job = mock_process_job

    with TestClient(app):
        assert len(app.state.worker_tasks) == app.state.num_workers
        initial_tasks = list(app.state.worker_tasks)

    for task in initial_tasks:
        assert task.cancelled()

    await asyncio.gather(*initial_tasks, return_exceptions=True)
    for task in initial_tasks:
        assert task.done()
