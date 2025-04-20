import pytest

from radiko_timeshift_recorder.job_queue import JobAlreadyExistsError, JobQueue


@pytest.mark.asyncio
async def test_job_queue_respects_priority():
    job_queue = JobQueue[int]()

    await job_queue.put(2)
    await job_queue.put(1)
    await job_queue.put(3)

    job = await job_queue.get()
    assert job == 1

    job = await job_queue.get()
    assert job == 2

    job = await job_queue.get()
    assert job == 3


@pytest.mark.asyncio
async def test_job_queue_duplicated_pending_job_cant_be_put():
    job_queue = JobQueue[int]()

    await job_queue.put(1)

    with pytest.raises(JobAlreadyExistsError):
        await job_queue.put(1)


@pytest.mark.asyncio
async def test_job_queue_duplicated_in_progress_job_cant_be_put():
    job_queue = JobQueue[int]()

    await job_queue.put(1)

    job = await job_queue.get()
    assert job == 1

    with pytest.raises(JobAlreadyExistsError):
        await job_queue.put(1)


@pytest.mark.asyncio
async def test_job_queue_done_job_can_be_reput():
    job_queue = JobQueue[int]()

    await job_queue.put(1)
    job = await job_queue.get()
    assert job == 1

    job_queue.mark_done(job)

    await job_queue.put(1)
    job = await job_queue.get()
    assert job == 1
