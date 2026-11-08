"""Validated, atomic monthly M1 Parquet storage."""

from pathlib import Path

import pandas as pd

COLUMNS = [
    "ts",
    "bid_o",
    "bid_h",
    "bid_l",
    "bid_c",
    "ask_o",
    "ask_h",
    "ask_l",
    "ask_c",
    "volume",
]
PRICES = COLUMNS[1:-1]


def month_path(root: Path, symbol: str, month: str) -> Path:
    return root / "m1" / symbol.upper() / f"{month}.parquet"


def validate_frame(frame: pd.DataFrame, month: str | None = None) -> None:
    if list(frame.columns) != COLUMNS or frame.empty:
        raise ValueError("M1 data needs nonempty canonical bid/ask columns")
    ts = frame["ts"]
    if not isinstance(ts.dtype, pd.DatetimeTZDtype) or str(ts.dt.tz) != "UTC":
        raise ValueError("ts must be timezone-aware UTC")
    if ts.isna().any() or ts.duplicated().any() or not ts.is_monotonic_increasing:
        raise ValueError("timestamps must be unique, nonnull and increasing")
    if (ts.dt.second != 0).any() or (ts.dt.microsecond != 0).any():
        raise ValueError("M1 timestamps must begin on minute boundaries")
    if month is not None and not ts.dt.strftime("%Y-%m").eq(month).all():
        raise ValueError(f"timestamps outside {month}")
    if frame[PRICES + ["volume"]].isna().any().any():
        raise ValueError("prices and volume must be nonnull")
    if not frame[PRICES].gt(0).all().all() or not frame["volume"].ge(0).all():
        raise ValueError("prices must be positive and volume nonnegative")
    for side in ("bid", "ask"):
        if not (
            frame[f"{side}_l"].le(frame[[f"{side}_o", f"{side}_c"]].min(axis=1)).all()
            and frame[f"{side}_h"]
            .ge(frame[[f"{side}_o", f"{side}_c"]].max(axis=1))
            .all()
            and frame[f"{side}_h"].ge(frame[f"{side}_l"]).all()
        ):
            raise ValueError(f"invalid {side} OHLC")
    for part in ("o", "h", "l", "c"):
        if not frame[f"ask_{part}"].ge(frame[f"bid_{part}"]).all():
            raise ValueError(f"ask_{part} below bid_{part}")


def read_month(root: Path, symbol: str, month: str) -> pd.DataFrame:
    frame = pd.read_parquet(month_path(root, symbol, month))
    validate_frame(frame, month)
    return frame


def write_month(root: Path, symbol: str, month: str, frame: pd.DataFrame) -> Path:
    validate_frame(frame, month)
    path = month_path(root, symbol, month)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".parquet.tmp")
    try:
        frame.to_parquet(temporary, index=False, compression="zstd")
        temporary.replace(path)
    finally:
        temporary.unlink(missing_ok=True)
    return path
