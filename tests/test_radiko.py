import datetime

import pytest

from radiko_timeshift_recorder.radiko import (
    DateAreaSchedule,
    OutOfAreaError,
    fetch_area_id,
)


@pytest.fixture
def is_radiko_available() -> bool:
    try:
        fetch_area_id()
    except OutOfAreaError:
        return False

    return True


@pytest.mark.skipif(condition="not is_radiko_available")
def test_fetch_area_id_can_fetch_some_area_id():
    fetch_area_id()


@pytest.mark.skipif(condition="is_radiko_available")
def test_fetch_area_id_raises_out_of_area_error():
    with pytest.raises(OutOfAreaError):
        fetch_area_id()


@pytest.mark.skipif(condition="not is_radiko_available")
def test_date_area_schedule_can_be_parsed():
    DateAreaSchedule.from_date_area(date=datetime.date.today(), area_id=None)
