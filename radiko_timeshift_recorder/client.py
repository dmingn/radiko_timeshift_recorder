import requests
from fastapi.encoders import jsonable_encoder

from radiko_timeshift_recorder.job import Job


class Client:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session = None

    def __enter__(self):
        self.session = requests.Session()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.session:
            self.session.close()

    def put_job(self, job: Job):
        if not self.session:
            raise RuntimeError("Session not initialized. Use 'with' statement.")

        response = self.session.post(
            url=f"{self.base_url}/job_queue",
            headers={"Content-Type": "application/json"},
            json=jsonable_encoder(job),
        )

        response.raise_for_status()
