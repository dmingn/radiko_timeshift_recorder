import datetime
from zoneinfo import ZoneInfo

import pytest

from radiko_timeshift_recorder.job import Job
from radiko_timeshift_recorder.radiko import Program


@pytest.fixture()
def sample_job() -> Job:
    return Job(
        program=Program(
            id="1",
            ft=datetime.datetime(2025, 1, 1, 5, 0, tzinfo=ZoneInfo("Asia/Tokyo")),
            to=datetime.datetime(2025, 1, 1, 5, 15, tzinfo=ZoneInfo("Asia/Tokyo")),
            dur=900,
            title="test program",
            pfm="test performer",
        ),
        station_id="TEST",
    )
