import datetime

import pytest

from radiko_timeshift_recorder.radiko import DateAreaSchedule, fetch_area_id


def test_fetch_area_id_works():
    fetch_area_id()


@pytest.mark.skip()
def test_date_area_schedule_can_be_parsed():
    DateAreaSchedule.from_date_area(date=datetime.date.today(), area_id=None)
