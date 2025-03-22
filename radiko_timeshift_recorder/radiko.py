from __future__ import annotations

import datetime
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Optional, cast
from zoneinfo import ZoneInfo

import requests

AreaId = str
ProgramId = str
StationId = str


def fetch_area_id() -> AreaId:
    response = requests.get("https://radiko.jp/area")
    response.encoding = response.apparent_encoding

    match = re.search(r'class="([A-Z]+[0-9]+)"', response.text)

    if match:
        return match.groups()[0]
    else:
        raise RuntimeError(
            f"Failed to get area from api.: {response.text}, {response.status_code} {response.reason}"
        )


@dataclass(frozen=True, order=True)
class Program:
    to: datetime.datetime
    ft: datetime.datetime
    id: ProgramId
    dur: int
    title: str
    pfm: str
    station_id: StationId

    @classmethod
    def from_element(cls, element: ET.Element, station_id: StationId) -> Program:
        return cls(
            id=cast(ProgramId, element.get("id")),
            ft=datetime.datetime.strptime(
                cast(str, element.get("ft")), "%Y%m%d%H%M%S"
            ).replace(tzinfo=ZoneInfo("Asia/Tokyo")),
            to=datetime.datetime.strptime(
                cast(str, element.get("to")), "%Y%m%d%H%M%S"
            ).replace(tzinfo=ZoneInfo("Asia/Tokyo")),
            dur=int(cast(str, element.get("dur"))),
            title=cast(str, element.findtext("title")),
            pfm=element.findtext("pfm", default=""),
            station_id=station_id,
        )

    @property
    def url(self) -> str:
        return f"https://radiko.jp/#!/ts/{self.station_id}/{self.ft.strftime('%Y%m%d%H%M%S')}"

    @property
    def is_finished(self) -> bool:
        return self.to < datetime.datetime.now(ZoneInfo("Asia/Tokyo"))


@dataclass(frozen=True)
class StationSchedule:
    id: StationId
    name: str
    progs: frozenset[Program]

    @classmethod
    def from_element(cls, element: ET.Element) -> StationSchedule:
        return cls(
            id=element.get("id", default=""),
            name=element.findtext("name", default=""),
            progs=frozenset(
                Program.from_element(
                    element=prog, station_id=element.get("id", default="")
                )
                for prog in element.iter("prog")
            ),
        )


@dataclass(frozen=True)
class DateAreaSchedule:
    date: datetime.date
    area_id: AreaId
    stations: frozenset[StationSchedule]

    @classmethod
    def from_date_area(
        cls, date: datetime.date, area_id: Optional[AreaId] = None
    ) -> DateAreaSchedule:
        if not area_id:
            area_id = fetch_area_id()

        response = requests.get(
            f"https://radiko.jp/v3/program/date/{date.strftime('%Y%m%d')}/{area_id}.xml"
        )
        response.encoding = response.apparent_encoding

        element = ET.fromstring(response.text)

        return cls(
            date=date,
            area_id=area_id,
            stations=frozenset(
                StationSchedule.from_element(station)
                for station in element.iter("station")
            ),
        )
