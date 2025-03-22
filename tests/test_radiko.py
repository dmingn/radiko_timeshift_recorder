import datetime

from radiko_timeshift_recorder.radiko import DateAreaSchedule


def test_date_area_schedule_can_be_parsed():
    DateAreaSchedule.from_date_area(date=datetime.date.today(), area=None)
