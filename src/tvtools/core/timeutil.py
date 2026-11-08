"""UTC timestamps and ICT trading sessions in New York wall time."""

from datetime import UTC, date, datetime, timedelta
from zoneinfo import ZoneInfo

import numpy as np
import numpy.typing as npt
import pandas as pd
from pandas.tseries.holiday import (
    AbstractHolidayCalendar,
    GoodFriday,
    Holiday,
    USLaborDay,
    USMartinLutherKingJr,
    USMemorialDay,
    USPresidentsDay,
    USThanksgivingDay,
    nearest_workday,
    sunday_to_monday,
)

from tvtools.core.config import AppConfig, default_config

NY = ZoneInfo("America/New_York")


class _MarketHolidayCalendar(AbstractHolidayCalendar):
    """Full-day NYSE holiday rules. No trading is planned on these days."""

    rules = [
        Holiday("New Year's Day", month=1, day=1, observance=sunday_to_monday),
        USMartinLutherKingJr,
        USPresidentsDay,
        GoodFriday,
        USMemorialDay,
        Holiday(
            "Juneteenth",
            month=6,
            day=19,
            start_date="2022-06-19",
            observance=nearest_workday,
        ),
        Holiday("Independence Day", month=7, day=4, observance=nearest_workday),
        USLaborDay,
        USThanksgivingDay,
        Holiday("Christmas Day", month=12, day=25, observance=nearest_workday),
    ]


def market_holidays(start: date, end: date) -> set[date]:
    """US market holidays between *start* and *end*, inclusive."""
    days = _MarketHolidayCalendar().holidays(start=start, end=end)
    return {stamp.date() for stamp in days}


def market_open(timestamps: pd.DatetimeIndex) -> npt.NDArray[np.bool_]:
    """Whether each UTC instant falls in the FX week, excluding holidays.

    An FX day runs 17:00-17:00 New York and is named by the date it ends on,
    so the week opens Sunday 17:00 NY and closes Friday 17:00 NY. A holiday
    closes the FX day that ends at 17:00 NY on that date.
    """
    if str(timestamps.tz) != "UTC":
        raise ValueError("timestamps must be timezone-aware UTC")
    if timestamps.empty:
        return np.zeros(0, dtype=bool)
    wall = timestamps.tz_convert(NY).tz_localize(None)
    fx_day = (wall + pd.Timedelta(hours=7)).normalize()
    holidays = market_holidays(fx_day.min().date(), fx_day.max().date())
    closed = fx_day.isin(pd.DatetimeIndex(sorted(holidays)))
    return np.asarray((fx_day.day_of_week < 5) & ~closed, dtype=bool)


def as_utc(value: pd.Timestamp | datetime) -> pd.Timestamp:
    timestamp = pd.Timestamp(value)
    if timestamp.tzinfo is None:
        raise ValueError("timestamp must be timezone-aware UTC")
    if timestamp.utcoffset() != timedelta(0):
        raise ValueError("timestamp must be UTC")
    return timestamp.tz_convert(UTC)


def utc_to_ny(value: pd.Timestamp | datetime) -> pd.Timestamp:
    return as_utc(value).tz_convert(NY)


def trading_day(value: pd.Timestamp | datetime) -> date:
    """Calendar date of *value* in New York; the ICT day starts at 00:00 NY.

    This is a label for daily limits and reports, not a way to group bars into
    reference ranges. Asia bars (20:00-00:00 NY) carry the prior date here but
    belong to the next day's Asia range; select ranges with ``session_window``.
    """
    return utc_to_ny(value).date()


def session_window(
    day: date, name: str, config: AppConfig | None = None
) -> tuple[pd.Timestamp, pd.Timestamp]:
    """Return UTC half-open bounds for a session assigned to *day*.

    Asia begins the previous NY evening and ends at midnight on *day*.
    A zero-length session such as flat_by denotes a cutoff instant.
    """
    active_config = config if config is not None else default_config()
    try:
        spec = active_config.sessions[name]
    except KeyError as exc:
        raise ValueError(f"unknown session: {name}") from exc
    start_day = day + timedelta(days=spec.start_day_offset)
    start = pd.Timestamp(datetime.combine(start_day, spec.start, tzinfo=NY))
    end = pd.Timestamp(datetime.combine(day, spec.end, tzinfo=NY))
    return start.tz_convert(UTC), end.tz_convert(UTC)
