from __future__ import annotations

import datetime
from functools import total_ordering
from typing import Self
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, RootModel

from radiko_timeshift_recorder.radiko import (
    Program,
    Schedule,
    StationId,
    fetch_schedule,
)


@total_ordering
class Job(BaseModel):
    program: Program
    station_id: StationId
    model_config = ConfigDict(frozen=True)

    def __lt__(self, other: Job) -> bool:
        # Order defines the priority of the job

        # Program which ends earlier should be prioritized
        # If the end time is the same, the one which starts earlier should be prioritized
        return (self.program.to, self.program.ft) < (
            other.program.to,
            other.program.ft,
        )

    @property
    def is_ready_to_process(self) -> bool:
        # Check if the program has already finished
        return self.program.to < datetime.datetime.now(ZoneInfo("Asia/Tokyo"))

    @property
    def url(self) -> str:
        return f"https://radiko.jp/#!/ts/{self.station_id}/{self.program.ft.strftime('%Y%m%d%H%M%S')}"


class Jobs(RootModel[frozenset[Job]]):
    def __iter__(self):
        return self.root.__iter__()

    @classmethod
    def from_date(cls, date: datetime.date) -> Self:
        return cls.from_schedule(fetch_schedule(date))

    @classmethod
    def from_schedule(cls, schedule: Schedule) -> Self:
        return cls.model_validate(
            frozenset(
                {
                    Job(program=program, station_id=station.id)
                    for station in schedule.stations
                    for program in station.progs
                }
            )
        )
