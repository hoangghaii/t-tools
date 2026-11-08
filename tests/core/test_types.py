from typing import Any

import pandas as pd
import pytest

from tvtools.core.types import Bar, Direction, Signal, Trade, TradeResult

T = pd.Timestamp


def make_signal(direction: Direction, **overrides: Any) -> Signal:
    prices = (
        {"entry": 1.1, "stop_loss": 1.099, "take_profit": 1.102}
        if direction == Direction.LONG
        else {"entry": 1.1, "stop_loss": 1.101, "take_profit": 1.098}
    )
    fields: dict[str, Any] = {
        "symbol": "EURUSD",
        "direction": direction,
        "model_id": "sweep_mss_fvg",
        "variant_id": "base",
        "session": "nyam_kz",
        "created_at": T("2026-11-02T12:00:00Z"),
        "valid_until": T("2026-11-02T16:00:00Z"),
        "invalidation_price": prices["stop_loss"],
        "reason": {},
        **prices,
        **overrides,
    }
    return Signal(**fields)


def make_bar(**overrides: Any) -> Bar:
    fields: dict[str, Any] = {
        "symbol": "EURUSD",
        "timestamp": T("2026-11-02T12:00:00Z"),
        "bid_open": 1.1000,
        "bid_high": 1.1010,
        "bid_low": 1.0990,
        "bid_close": 1.1005,
        "ask_open": 1.1001,
        "ask_high": 1.1011,
        "ask_low": 1.0991,
        "ask_close": 1.1006,
        **overrides,
    }
    return Bar(**fields)


def test_short_signal_math() -> None:
    signal = make_signal(Direction.SHORT)
    assert signal.rr() == pytest.approx(2)
    assert signal.horizon == "intraday"


@pytest.mark.parametrize("direction", list(Direction))
def test_signal_rejects_prices_on_wrong_side(direction: Direction) -> None:
    with pytest.raises(ValueError, match="conflict with direction"):
        make_signal(direction, stop_loss=1.1)


def test_signal_rejects_bad_timestamps() -> None:
    with pytest.raises(ValueError, match="valid_until must follow"):
        make_signal(Direction.LONG, valid_until=T("2026-11-02T12:00:00Z"))
    with pytest.raises(ValueError, match="timezone-aware"):
        make_signal(Direction.LONG, created_at=T("2026-11-02 12:00"))


def test_bar_accepts_valid_and_normalizes_utc() -> None:
    bar = make_bar()
    assert bar.timestamp.tzinfo is not None
    assert bar.timestamp == T("2026-11-02T12:00:00Z")


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"bid_high": 1.0995}, "invalid bid OHLC"),
        ({"ask_low": 1.1002}, "invalid ask OHLC"),
        ({"ask_high": 1.1009}, "ask prices must not be below bid"),
        ({"symbol": ""}, "symbol is required"),
        ({"timestamp": T("2026-11-02 12:00")}, "timezone-aware"),
    ],
)
def test_bar_rejects_invalid(overrides: dict[str, Any], message: str) -> None:
    with pytest.raises(ValueError, match=message):
        make_bar(**overrides)


def test_trade_open_and_closed() -> None:
    signal = make_signal(Direction.LONG)
    opened = Trade(signal, 0.01, T("2026-11-02T12:05:00Z"), 1.1)
    assert opened.closed_at is None and opened.result is None
    closed = Trade(
        signal,
        0.01,
        T("2026-11-02T12:05:00Z"),
        1.1,
        closed_at=T("2026-11-02T13:00:00Z"),
        exit_fill=1.102,
        result=TradeResult.WIN,
    )
    assert closed.result == TradeResult.WIN


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"lot": 0}, "lot must be positive"),
        ({"fees_usd": -1.0}, "fees_usd must not be negative"),
        ({"closed_at": T("2026-11-02T13:00:00Z")}, "supplied together"),
        ({"result": TradeResult.WIN}, "result must be supplied exactly"),
        (
            {"closed_at": T("2026-11-02T13:00:00Z"), "exit_fill": 1.102},
            "result must be supplied exactly",
        ),
        (
            {
                "closed_at": T("2026-11-02T12:00:00Z"),
                "exit_fill": 1.1,
                "result": TradeResult.BREAKEVEN,
            },
            "must not precede opened_at",
        ),
    ],
)
def test_trade_rejects_invalid(overrides: dict[str, Any], message: str) -> None:
    fields: dict[str, Any] = {
        "signal": make_signal(Direction.LONG),
        "lot": 0.01,
        "opened_at": T("2026-11-02T12:05:00Z"),
        "entry_fill": 1.1,
        **overrides,
    }
    with pytest.raises(ValueError, match=message):
        Trade(**fields)
