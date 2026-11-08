"""Shared market and signal records. Monetary risk uses price distance, not pips."""

from dataclasses import dataclass, field
from enum import StrEnum

import pandas as pd

from tvtools.core.config import SymbolSpec
from tvtools.core.timeutil import as_utc


class Direction(StrEnum):
    LONG = "long"
    SHORT = "short"


class Horizon(StrEnum):
    INTRADAY = "intraday"
    SWING = "swing"


class TradeResult(StrEnum):
    WIN = "win"
    LOSS = "loss"
    BREAKEVEN = "breakeven"


@dataclass(frozen=True)
class Bar:
    symbol: str
    timestamp: pd.Timestamp
    bid_open: float
    bid_high: float
    bid_low: float
    bid_close: float
    ask_open: float
    ask_high: float
    ask_low: float
    ask_close: float
    volume: float | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "timestamp", as_utc(self.timestamp))
        if not self.symbol:
            raise ValueError("symbol is required")
        for side in ("bid", "ask"):
            high = getattr(self, f"{side}_high")
            low = getattr(self, f"{side}_low")
            opened = getattr(self, f"{side}_open")
            closed = getattr(self, f"{side}_close")
            if low > min(opened, closed) or high < max(opened, closed):
                raise ValueError(f"invalid {side} OHLC")
        if self.bid_high > self.ask_high or self.bid_low > self.ask_low:
            raise ValueError("ask prices must not be below bid prices")


@dataclass(frozen=True)
class Signal:
    symbol: str
    direction: Direction
    model_id: str
    variant_id: str
    session: str
    created_at: pd.Timestamp
    entry: float
    stop_loss: float
    take_profit: float
    valid_until: pd.Timestamp
    invalidation_price: float
    reason: dict[str, str]
    horizon: Horizon = Horizon.INTRADAY

    def __post_init__(self) -> None:
        object.__setattr__(self, "created_at", as_utc(self.created_at))
        object.__setattr__(self, "valid_until", as_utc(self.valid_until))
        if self.valid_until <= self.created_at:
            raise ValueError("valid_until must follow created_at")
        if self.direction == Direction.LONG:
            valid_prices = self.stop_loss < self.entry < self.take_profit
        else:
            valid_prices = self.take_profit < self.entry < self.stop_loss
        if not valid_prices:
            raise ValueError("entry, stop_loss and take_profit conflict with direction")

    def risk_pips(self, spec: SymbolSpec) -> float:
        return abs(self.entry - self.stop_loss) / spec.pip_size

    def rr(self) -> float:
        return abs(self.take_profit - self.entry) / abs(self.entry - self.stop_loss)


@dataclass(frozen=True)
class Trade:
    signal: Signal
    lot: float
    opened_at: pd.Timestamp
    entry_fill: float
    closed_at: pd.Timestamp | None = None
    exit_fill: float | None = None
    result: TradeResult | None = None
    fees_usd: float = 0.0
    metadata: dict[str, str] = field(default_factory=dict)

    def __post_init__(self) -> None:
        object.__setattr__(self, "opened_at", as_utc(self.opened_at))
        if self.closed_at is not None:
            object.__setattr__(self, "closed_at", as_utc(self.closed_at))
        if self.lot <= 0:
            raise ValueError("lot must be positive")
        if self.fees_usd < 0:
            raise ValueError("fees_usd must not be negative")
        if (self.closed_at is None) != (self.exit_fill is None):
            raise ValueError("closed_at and exit_fill must be supplied together")
        if (self.closed_at is None) != (self.result is None):
            raise ValueError("result must be supplied exactly when the trade is closed")
        if self.closed_at is not None and self.closed_at < self.opened_at:
            raise ValueError("closed_at must not precede opened_at")
