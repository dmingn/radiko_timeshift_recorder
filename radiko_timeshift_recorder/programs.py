from __future__ import annotations

import datetime
from functools import total_ordering
from typing import Self
from zoneinfo import ZoneInfo

from pydantic import ConfigDict, RootModel

from radiko_timeshift_recorder.radiko import Program as RadikoProgram
from radiko_timeshift_recorder.radiko import Schedule, StationId, fetch_schedule


@total_ordering
class Program(RadikoProgram):
    station_id: StationId
    model_config = ConfigDict(frozen=True)

    def __lt__(self, other: Program) -> bool:
        return self.to < other.to

    @property
    def is_finished(self) -> bool:
        return self.to < datetime.datetime.now(ZoneInfo("Asia/Tokyo"))

    @property
    def url(self) -> str:
        return f"https://radiko.jp/#!/ts/{self.station_id}/{self.ft.strftime('%Y%m%d%H%M%S')}"

    @classmethod
    def from_radiko_program(cls, program: RadikoProgram, station_id: StationId) -> Self:
        return cls(
            id=program.id,
            ft=program.ft,
            to=program.to,
            dur=program.dur,
            title=program.title,
            pfm=program.pfm,
            station_id=station_id,
        )


class Programs(RootModel[frozenset[Program]]):
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
                    Program.from_radiko_program(program=program, station_id=station.id)
                    for station in schedule.stations
                    for program in station.progs
                }
            )
        )
