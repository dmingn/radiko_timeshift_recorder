from __future__ import annotations

import datetime
import functools
import re
from typing import Annotated, Any, Optional
from zoneinfo import ZoneInfo

import requests
from logzero import logger
from pydantic import AwareDatetime, BeforeValidator, ConfigDict
from pydantic_xml import BaseXmlModel, attr, element, wrapped

AreaId = str
ProgramId = str
StationId = str


class OutOfAreaError(Exception):
    pass


@functools.cache
def fetch_area_id() -> AreaId:
    response = requests.get("https://radiko.jp/area", timeout=10)

    response.encoding = response.apparent_encoding
    match = re.search(r'class="(.+)"', response.text)
    if not match:
        raise ValueError("Failed to parse area ID: {response.text}")

    area_id = match.groups()[0]
    logger.debug(f"Retrieved area ID: {area_id}")

    if area_id == "OUT":
        raise OutOfAreaError("Out of area.")

    return AreaId(area_id)


def validate_program_datetime(value: Any) -> datetime.datetime:
    if isinstance(value, str):
        try:
            return datetime.datetime.strptime(value, "%Y%m%d%H%M%S").replace(
                tzinfo=ZoneInfo("Asia/Tokyo")
            )
        except ValueError:
            pass

    # pass through value to the next validator
    return value


ProgramDateTime = Annotated[
    AwareDatetime,
    BeforeValidator(validate_program_datetime),
]


class Program(BaseXmlModel, search_mode="unordered"):
    id: ProgramId = attr()
    ft: ProgramDateTime = attr()
    to: ProgramDateTime = attr()
    dur: int = attr()
    title: str = element()
    pfm: Optional[str] = element(default=None)
    model_config = ConfigDict(frozen=True)


class Station(BaseXmlModel, search_mode="unordered"):
    id: StationId = attr()
    name: str = element()
    progs: frozenset[Program] = wrapped(path="progs", entity=element(tag="prog"))
    model_config = ConfigDict(frozen=True)


class Schedule(BaseXmlModel, tag="radiko", search_mode="unordered"):
    stations: frozenset[Station] = wrapped(
        path="stations", entity=element(tag="station")
    )
    model_config = ConfigDict(frozen=True)


def fetch_schedule(date: datetime.date) -> Schedule:
    area_id = fetch_area_id()

    response = requests.get(
        f"https://radiko.jp/v3/program/date/{date.strftime('%Y%m%d')}/{area_id}.xml"
    )

    return Schedule.from_xml(response.content)
