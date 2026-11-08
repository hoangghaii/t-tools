"""Checks on real Dukascopy M1 data.

``eurusd_m1_2024-01-09_10.csv`` is cut from ``data/m1/EURUSD/2024-01.parquet``
(dukascopy-node 1.51.1, ``-v``, no ``-fl``): 2024-01-08 22:00 UTC up to
2024-01-10 22:00 UTC, i.e. 17:00 NY to 17:00 NY two days later. It covers the
Asia, London and NY AM sessions of Jan 9 and 10 and the 17:00 NY rollover.
"""

from pathlib import Path

import pandas as pd
import pytest

from tvtools.core.timeutil import NY
from tvtools.data.quality import inspect
from tvtools.data.resample import resample_m1
from tvtools.data.store import validate_frame

REAL = Path(__file__).resolve().parents[1] / "fixtures" / "eurusd_m1_2024-01-09_10.csv"


@pytest.fixture(scope="module")
def real() -> pd.DataFrame:
    return pd.read_csv(REAL, parse_dates=["ts"])


def test_real_fixture_is_canonical_m1(real: pd.DataFrame) -> None:
    validate_frame(real)
    assert real["ts"].iloc[0] == pd.Timestamp("2024-01-08T22:00:00Z")
    assert real["ts"].iloc[-1] == pd.Timestamp("2024-01-10T21:59:00Z")
    # Tickless minutes are absent, not filled: 2872 of 2880 minutes exist.
    assert len(real) == 2872


def test_real_quality_is_clean_and_shows_rollover_spread(real: pd.DataFrame) -> None:
    result = inspect(real, "EURUSD")
    assert (result.duplicates, result.out_of_order) == (0, 0)
    assert (result.invalid_ohlc, result.crossed_quotes) == (0, 0)
    assert result.gaps.empty
    median = result.spreads.set_index("hour_ny")["median"]
    killzone = median.loc[7:10]
    assert killzone.between(0.1, 0.5).all()
    assert median.loc[17] > 3 * killzone.max()


@pytest.mark.parametrize("timeframe", ["M5", "M15", "H1"])
def test_real_resample_matches_m1_windows(real: pd.DataFrame, timeframe: str) -> None:
    bars = resample_m1(real, timeframe)
    width = bars["closed_at"].iloc[0] - bars["ts"].iloc[0]
    assert (bars["closed_at"] - bars["ts"]).eq(width).all()
    assert bars["ts"].dt.floor(width).eq(bars["ts"]).all()
    window = real["ts"].dt.floor(width)
    grouped = real.groupby(window)
    expected = pd.DataFrame(
        {
            "bid_o": grouped["bid_o"].first(),
            "bid_h": grouped["bid_h"].max(),
            "bid_l": grouped["bid_l"].min(),
            "bid_c": grouped["bid_c"].last(),
            "ask_o": grouped["ask_o"].first(),
            "ask_c": grouped["ask_c"].last(),
            "volume": grouped["volume"].sum(),
        }
    )
    actual = bars.set_index("ts")[expected.columns]
    pd.testing.assert_frame_equal(actual, expected, check_names=False)
    assert bars["volume"].sum() == pytest.approx(real["volume"].sum())


def test_real_h1_from_m1_equals_h1_from_m5(real: pd.DataFrame) -> None:
    m5 = resample_m1(real, "M5").drop(columns="closed_at")
    direct = resample_m1(real, "H1")
    via_m5 = resample_m1(m5, "H1")
    pd.testing.assert_frame_equal(direct, via_m5)


def test_real_fixture_spans_two_ny_sessions(real: pd.DataFrame) -> None:
    ny = real["ts"].dt.tz_convert(NY)
    london = ny[(ny.dt.hour >= 2) & (ny.dt.hour < 5)]
    nyam = ny[(ny.dt.hour >= 7) & (ny.dt.hour < 11)]
    days = [pd.Timestamp("2024-01-09").date(), pd.Timestamp("2024-01-10").date()]
    assert sorted(set(london.dt.date)) == days
    assert sorted(set(nyam.dt.date)) == days
