"""UTC-anchored intraday bars built from whichever M1 candles exist.

Dukascopy omits minutes without ticks, so a window with missing minutes is
still a real bar, as on MT/TradingView. Windows with no M1 candle produce no
bar. Look-ahead is prevented by ``closed_at``: callers may use a bar only once
``closed_at`` is at or before the current time.
"""

import pandas as pd

from tvtools.data.store import COLUMNS, validate_frame

FREQUENCIES = {"M5": "5min", "M15": "15min", "H1": "1h"}


def resample_m1(frame: pd.DataFrame, timeframe: str) -> pd.DataFrame:
    try:
        frequency = FREQUENCIES[timeframe.upper()]
    except KeyError as exc:
        raise ValueError(f"unsupported timeframe: {timeframe}") from exc
    validate_frame(frame)
    indexed = frame.set_index("ts")
    aggregation = {
        f"{side}_{part}": operation
        for side in ("bid", "ask")
        for part, operation in (
            ("o", "first"),
            ("h", "max"),
            ("l", "min"),
            ("c", "last"),
        )
    }
    aggregation["volume"] = "sum"
    grouped = indexed.resample(frequency, origin="epoch", label="left", closed="left")
    bars = grouped.agg(aggregation)
    bars["count"] = grouped.size()
    bars = bars.loc[bars["count"].gt(0)].drop(columns="count")
    bars = bars.reset_index()[COLUMNS]
    bars["closed_at"] = bars["ts"] + pd.Timedelta(frequency)
    return bars
