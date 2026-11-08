from datetime import date, datetime, timedelta, timezone

import pandas as pd
import pytest

from tvtools.core.timeutil import (
    market_holidays,
    market_open,
    session_window,
    trading_day,
    utc_to_ny,
)


def test_nyam_winter_and_summer() -> None:
    assert session_window(date(2026, 11, 2), "nyam_kz") == (
        pd.Timestamp("2026-11-02T12:00:00Z"),
        pd.Timestamp("2026-11-02T16:00:00Z"),
    )
    assert session_window(date(2026, 7, 15), "nyam_kz") == (
        pd.Timestamp("2026-07-15T11:00:00Z"),
        pd.Timestamp("2026-07-15T15:00:00Z"),
    )
    start, end = session_window(date(2026, 11, 2), "nyam_kz")
    assert start.tz_convert("Asia/Ho_Chi_Minh").hour == 19
    assert end.tz_convert("Asia/Ho_Chi_Minh").hour == 23


@pytest.mark.parametrize(
    ("day", "expected_start"),
    [
        (date(2026, 3, 7), "2026-03-07T12:00:00Z"),
        (date(2026, 3, 8), "2026-03-08T11:00:00Z"),
        (date(2026, 11, 1), "2026-11-01T12:00:00Z"),
        (date(2026, 11, 2), "2026-11-02T12:00:00Z"),
    ],
)
def test_dst_boundaries(day: date, expected_start: str) -> None:
    start, end = session_window(day, "nyam_kz")
    assert start == pd.Timestamp(expected_start)
    assert end - start == pd.Timedelta(hours=4)


def test_asia_window_assigned_to_next_day_but_labeled_prior_date() -> None:
    start, end = session_window(date(2026, 11, 2), "asia")
    assert start == pd.Timestamp("2026-11-02T01:00:00Z")
    assert end == pd.Timestamp("2026-11-02T05:00:00Z")
    assert trading_day(start) == date(2026, 11, 1)
    assert trading_day(end) == date(2026, 11, 2)
    last_asia_minute = end - pd.Timedelta(minutes=1)
    assert start <= last_asia_minute < end
    assert trading_day(last_asia_minute) == date(2026, 11, 1)


def test_reject_naive_timestamp() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        utc_to_ny(pd.Timestamp("2026-01-01"))
    with pytest.raises(ValueError, match="UTC"):
        trading_day(datetime(2026, 1, 1, tzinfo=timezone(timedelta(hours=7))))


def test_market_holidays_follow_nyse_full_day_rules() -> None:
    assert sorted(market_holidays(date(2024, 1, 1), date(2024, 12, 31))) == [
        date(2024, 1, 1),
        date(2024, 1, 15),
        date(2024, 2, 19),
        date(2024, 3, 29),
        date(2024, 5, 27),
        date(2024, 6, 19),
        date(2024, 7, 4),
        date(2024, 9, 2),
        date(2024, 11, 28),
        date(2024, 12, 25),
    ]
    # Juneteenth starts in 2022; observed dates move off weekends.
    assert date(2021, 6, 18) not in market_holidays(
        date(2021, 1, 1), date(2021, 12, 31)
    )
    assert date(2022, 12, 26) in market_holidays(date(2022, 12, 1), date(2022, 12, 31))


def test_market_open_fx_week_and_holiday_boundaries() -> None:
    stamps = pd.DatetimeIndex(
        [
            "2024-01-05T21:59Z",  # Friday 16:59 NY
            "2024-01-05T22:00Z",  # Friday 17:00 NY, weekend starts
            "2024-01-07T21:59Z",  # Sunday 16:59 NY
            "2024-01-07T22:00Z",  # Sunday 17:00 NY, week opens
            "2024-12-24T22:00Z",  # Christmas FX day begins
            "2024-12-25T21:59Z",
            "2024-12-25T22:00Z",  # reopens 17:00 NY
            "2024-07-03T21:00Z",  # Independence Day, daylight time
            "2024-07-04T21:00Z",
        ]
    )
    assert market_open(stamps).tolist() == [
        True,
        False,
        False,
        True,
        False,
        False,
        True,
        False,
        True,
    ]
    assert market_open(pd.DatetimeIndex([], tz="UTC")).tolist() == []
    with pytest.raises(ValueError, match="UTC"):
        market_open(pd.DatetimeIndex(["2024-01-02 12:00"]))
