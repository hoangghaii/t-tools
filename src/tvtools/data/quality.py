"""Data quality checks and reproducible Markdown summaries."""

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from tvtools.core.config import default_config
from tvtools.core.timeutil import NY, market_open
from tvtools.data.store import COLUMNS, PRICES


@dataclass(frozen=True)
class QualityResult:
    symbol: str
    rows: int
    duplicates: int
    out_of_order: int
    invalid_ohlc: int
    crossed_quotes: int
    gaps: pd.DataFrame
    spreads: pd.DataFrame


def inspect(frame: pd.DataFrame, symbol: str) -> QualityResult:
    if list(frame.columns) != COLUMNS or frame.empty:
        raise ValueError("quality check requires nonempty canonical M1 data")
    ts = frame["ts"]
    if not isinstance(ts.dtype, pd.DatetimeTZDtype) or str(ts.dt.tz) != "UTC":
        raise ValueError("ts must be timezone-aware UTC")
    if frame[PRICES + ["volume"]].isna().any().any():
        raise ValueError("prices and volume must be nonnull")
    duplicates = int(ts.duplicated().sum())
    out_of_order = int(ts.diff().lt(pd.Timedelta(0)).sum())
    invalid = pd.Series(False, index=frame.index)
    for side in ("bid", "ask"):
        invalid |= (
            frame[f"{side}_l"].gt(frame[[f"{side}_o", f"{side}_c"]].min(axis=1))
            | frame[f"{side}_h"].lt(frame[[f"{side}_o", f"{side}_c"]].max(axis=1))
            | frame[f"{side}_h"].lt(frame[f"{side}_l"])
        )
    crossed = pd.Series(False, index=frame.index)
    for part in ("o", "h", "l", "c"):
        crossed |= frame[f"ask_{part}"].lt(frame[f"bid_{part}"])
    ordered = ts.sort_values().drop_duplicates().reset_index(drop=True)
    gaps: list[dict[str, object]] = []
    differences = ordered.diff()
    long_gap_positions = differences[differences.gt(pd.Timedelta(minutes=6))].index
    for position in long_gap_positions:
        previous, current = ordered.iloc[position - 1], ordered.iloc[position]
        missing_minutes = pd.date_range(
            previous + pd.Timedelta(minutes=1),
            current - pd.Timedelta(minutes=1),
            freq="min",
        )
        open_minutes = int(market_open(missing_minutes).sum())
        if open_minutes <= 5:
            continue
        gaps.append(
            {"from_utc": previous, "to_utc": current, "missing_minutes": open_minutes}
        )
    gap_frame = pd.DataFrame(gaps, columns=["from_utc", "to_utc", "missing_minutes"])
    gap_frame = gap_frame.astype({"missing_minutes": "int64"})

    pip = default_config().symbols[symbol.upper()].pip_size
    local_hour = ts.dt.tz_convert(NY).dt.hour
    spread = (frame["ask_c"] - frame["bid_c"]) / pip
    spreads = pd.DataFrame({"hour_ny": local_hour, "spread_pips": spread})
    spreads = (
        spreads.groupby("hour_ny")["spread_pips"]
        .agg(count="count", median="median", p95=lambda values: values.quantile(0.95))
        .reset_index()
    )
    return QualityResult(
        symbol.upper(),
        len(frame),
        duplicates,
        out_of_order,
        int(invalid.sum()),
        int(crossed.sum()),
        gap_frame,
        spreads,
    )


def render_report(result: QualityResult, months_found: list[str]) -> str:
    lines = [
        f"# Data quality: {result.symbol}",
        "",
        f"Months present: {len(months_found)} ({', '.join(months_found)})",
        "",
        f"Rows: {result.rows}",
        f"Duplicate timestamps: {result.duplicates}",
        f"Out-of-order timestamps: {result.out_of_order}",
        f"Invalid OHLC: {result.invalid_ohlc}",
        f"Ask below bid: {result.crossed_quotes}",
        f"Gaps over 5 minutes: {len(result.gaps)}",
        "",
        "Gaps count only minutes inside the FX week (Sunday 17:00 to Friday 17:00"
        " New York), excluding US market holidays. dukascopy-node omits minutes"
        " without ticks, so short quiet gaps are normal; review the long ones.",
        "",
        "## Largest gaps",
        "",
        "| From UTC | To UTC | Missing minutes |",
        "|---|---|---:|",
    ]
    for gap in result.gaps.nlargest(20, "missing_minutes").itertuples(index=False):
        lines.append(f"| {gap.from_utc} | {gap.to_utc} | {gap.missing_minutes} |")
    lines.extend(
        [
            "",
            "## Spread by New York hour (close quote)",
            "",
            "| Hour NY | Bars | Median pips | P95 pips |",
            "|---:|---:|---:|---:|",
        ]
    )
    for hour in result.spreads.itertuples(index=False):
        row = (
            f"| {hour.hour_ny:02d}:00 | {hour.count} | "
            f"{hour.median:.3f} | {hour.p95:.3f} |"
        )
        lines.append(row)
    lines.append("")
    return "\n".join(lines)


def check_store(root: Path, symbol: str, reports: Path) -> Path:
    symbol = symbol.upper()
    files = sorted((root / "m1" / symbol).glob("????-??.parquet"))
    if not files:
        raise FileNotFoundError(f"no M1 Parquet files for {symbol}")
    frames = [pd.read_parquet(path) for path in files]
    result = inspect(pd.concat(frames, ignore_index=True), symbol)
    output = reports / f"data-quality-{symbol}.md"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(render_report(result, [path.stem for path in files]))
    return output
