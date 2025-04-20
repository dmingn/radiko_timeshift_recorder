import asyncio
from typing import Generic, TypeVar

T = TypeVar("T")


class JobAlreadyExistsError(Exception):
    pass


class JobQueue(Generic[T]):
    def __init__(self) -> None:
        self.queue: asyncio.PriorityQueue[T] = asyncio.PriorityQueue()
        self.pending: set[T] = set()
        self.in_progress: set[T] = set()

    async def put(self, job: T) -> None:
        if job in self.pending or job in self.in_progress:
            raise JobAlreadyExistsError(
                f"Job {job} already exists in queue or is in progress."
            )

        await self.queue.put(job)
        self.pending.add(job)

    async def get(self) -> T:
        job = await self.queue.get()
        self.pending.remove(job)
        self.in_progress.add(job)
        return job

    def mark_done(self, job: T) -> None:
        self.in_progress.remove(job)

    def qsize(self) -> int:
        return self.queue.qsize()
