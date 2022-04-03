from __future__ import annotations

import datetime
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Optional

import requests

AreaId = str
ProgramId = str
StationId = str


@dataclass(frozen=True)
class Area:
    id: AreaId

    @classmethod
    def from_api(cls) -> Area:
        response = requests.get("https://radiko.jp/area")
        response.encoding = response.apparent_encoding

        match = re.search(r'class="([A-Z]+[0-9]+)"', response.text)

        if match:
            return Area(id=match.groups()[0])
        else:
            raise RuntimeError("Failed to get area from api.")


@dataclass(frozen=True)
class Program:
    id: ProgramId
    ft: str
    to: str
    ftl: str
    tol: str
    dur: str
    title: str
    pfm: str
    station_id: StationId

    @classmethod
    def from_element(cls, element: ET.Element, station_id: StationId) -> Program:
        return cls(
            id=element.get("id", default=""),
            ft=element.get("ft", default=""),
            to=element.get("to", default=""),
            ftl=element.get("ftl", default=""),
            tol=element.get("tol", default=""),
            dur=element.get("dur", default=""),
            title=element.findtext("title", default=""),
            pfm=element.findtext("pfm", default=""),
            station_id=station_id,
        )

    @property
    def url(self) -> str:
        return f"https://radiko.jp/#!/ts/{self.station_id}/{self.ft}"


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
    area: Area
    stations: frozenset[StationSchedule]

    @classmethod
    def from_date_area(
        cls, date: datetime.date, area: Optional[Area] = None
    ) -> DateAreaSchedule:
        if not area:
            area = Area.from_api()

        response = requests.get(
            f"https://radiko.jp/v3/program/date/{date.strftime('%Y%m%d')}/{area.id}.xml"
        )
        response.encoding = response.apparent_encoding

        element = ET.fromstring(response.text)

        return cls(
            date=date,
            area=area,
            stations=frozenset(
                StationSchedule.from_element(station)
                for station in element.iter("station")
            ),
        )
