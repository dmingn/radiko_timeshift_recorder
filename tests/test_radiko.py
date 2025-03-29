import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest

from radiko_timeshift_recorder.radiko import (
    OutOfAreaError,
    Program,
    Schedule,
    Station,
    fetch_area_id,
    fetch_schedule,
)


@pytest.fixture
def is_radiko_available() -> bool:
    try:
        fetch_area_id()
    except OutOfAreaError:
        return False

    return True


@pytest.fixture
def schedule_xml_bytes() -> bytes:
    xml_path = Path(__file__).parent / "data" / "schedule.xml"
    return xml_path.read_bytes()


@pytest.mark.skipif(condition="not is_radiko_available")
def test_fetch_area_id_can_fetch_some_area_id():
    fetch_area_id()


@pytest.mark.skipif(condition="is_radiko_available")
def test_fetch_area_id_raises_out_of_area_error():
    with pytest.raises(OutOfAreaError):
        fetch_area_id()


def test_schedule_from_xml(schedule_xml_bytes: bytes):
    expected = Schedule(
        stations=frozenset(
            {
                Station(
                    id="FOO",
                    name="Foo",
                    progs=frozenset(
                        {
                            Program(
                                id="1",
                                ft=datetime.datetime(
                                    2025, 1, 1, 5, 0, tzinfo=ZoneInfo("Asia/Tokyo")
                                ),
                                to=datetime.datetime(
                                    2025, 1, 1, 5, 15, tzinfo=ZoneInfo("Asia/Tokyo")
                                ),
                                dur=900,
                                title="Foo1",
                                pfm="pfm1",
                            ),
                            Program(
                                id="2",
                                ft=datetime.datetime(
                                    2025, 1, 1, 5, 15, tzinfo=ZoneInfo("Asia/Tokyo")
                                ),
                                to=datetime.datetime(
                                    2025, 1, 1, 5, 30, tzinfo=ZoneInfo("Asia/Tokyo")
                                ),
                                dur=900,
                                title="Foo2",
                                pfm="pfm2",
                            ),
                        }
                    ),
                ),
                Station(
                    id="BAR",
                    name="Bar",
                    progs=frozenset(
                        {
                            Program(
                                id="3",
                                ft=datetime.datetime(
                                    2025, 1, 1, 5, 0, tzinfo=ZoneInfo("Asia/Tokyo")
                                ),
                                to=datetime.datetime(
                                    2025, 1, 1, 5, 5, tzinfo=ZoneInfo("Asia/Tokyo")
                                ),
                                dur=300,
                                title="Bar1",
                                pfm=None,
                            ),
                            Program(
                                id="4",
                                ft=datetime.datetime(
                                    2025, 1, 1, 5, 5, tzinfo=ZoneInfo("Asia/Tokyo")
                                ),
                                to=datetime.datetime(
                                    2025, 1, 1, 5, 15, tzinfo=ZoneInfo("Asia/Tokyo")
                                ),
                                dur=600,
                                title="Bar2",
                                pfm=None,
                            ),
                        }
                    ),
                ),
            }
        )
    )

    assert Schedule.from_xml(schedule_xml_bytes) == expected


@pytest.mark.skipif(condition="not is_radiko_available")
def test_fetch_schedule_can_fetch_some_schedule():
    fetch_schedule(date=datetime.date.today())
