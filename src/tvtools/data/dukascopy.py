"""Download Dukascopy M1 candles with the verified dukascopy-node CLI.

Verified with ``npx --yes dukascopy-node --help`` on 2026-11-06: ``-i``,
``-from`` (inclusive), ``-to`` (exclusive), ``-t m1``, ``-p bid|ask``,
``-f csv``, ``-v``, ``-dir``, ``-fn``, ``-r``, ``-rp`` and ``-ch``.
Instrument ids are ``eurusd``, ``gbpusd`` and ``xauusd``. CSV timestamps are
Unix epoch milliseconds UTC. Volume is bid-side candle volume in millions.

``-fl`` (include flats) is deliberately not passed. The Dukascopy API returns
only minutes that had ticks; with ``-fl`` dukascopy-node 1.51.1 fills every
gap with a synthetic candle at the previous close and zero volume
(``normaliseCandles``). Those rows carry no market information, so tickless
minutes stay absent and the resampler builds bars from the minutes present.
"""

import os
import re
import subprocess
import tempfile
from collections.abc import Callable, Iterator
from datetime import date
from pathlib import Path

import pandas as pd

from tvtools.data.store import month_path, read_month, write_month

SYMBOLS = frozenset(("EURUSD", "GBPUSD", "XAUUSD"))
Runner = Callable[..., subprocess.CompletedProcess[str]]


def months(start: str, end: str) -> Iterator[str]:
    if not re.fullmatch(r"\d{4}-(0[1-9]|1[0-2])", start) or not re.fullmatch(
        r"\d{4}-(0[1-9]|1[0-2])", end
    ):
        raise ValueError("months must use YYYY-MM")
    first = pd.Period(start, freq="M")
    last = pd.Period(end, freq="M")
    if first > last:
        raise ValueError("from month must not exceed to month")
    for period in pd.period_range(first, last, freq="M"):
        yield str(period)


def node_env() -> dict[str, str]:
    """Environment for npx that trusts the OS certificate store.

    Networks that inspect HTTPS re-sign traffic with a private CA that macOS
    trusts but Node does not, which makes every request fail with
    ``fetch failed`` (UNABLE_TO_VERIFY_LEAF_SIGNATURE). Existing NODE_OPTIONS
    are kept.
    """
    env = dict(os.environ)
    options = env.get("NODE_OPTIONS", "").split()
    if "--use-system-ca" not in options:
        options.append("--use-system-ca")
    env["NODE_OPTIONS"] = " ".join(options)
    return env


def _download_side(
    symbol: str,
    month: str,
    side: str,
    directory: Path,
    cache: Path,
    runner: Runner,
) -> pd.DataFrame:
    start = pd.Period(month, freq="M").start_time.date()
    end = (pd.Period(month, freq="M") + 1).start_time.date()
    filename = f"{symbol.lower()}-{month}-{side}"
    command = [
        "npx",
        "--yes",
        "dukascopy-node",
        "-i",
        symbol.lower(),
        "-from",
        start.isoformat(),
        "-to",
        end.isoformat(),
        "-t",
        "m1",
        "-p",
        side,
        "-f",
        "csv",
        "-v",
        "-dir",
        str(directory),
        "-fn",
        filename,
        "-r",
        "3",
        "-rp",
        "2000",
        "-ch",
        "-chpath",
        str(cache),
    ]
    try:
        runner(command, check=True, capture_output=True, text=True, env=node_env())
    except subprocess.CalledProcessError as exc:
        detail = "\n".join(part for part in (exc.stdout, exc.stderr) if part).strip()
        raise RuntimeError(
            f"dukascopy-node failed for {symbol} {month} {side}: "
            f"{detail or 'unknown error'}"
        ) from exc
    csv_path = directory / f"{filename}.csv"
    if not csv_path.exists():
        raise RuntimeError(f"dukascopy-node did not write {csv_path}")
    frame = pd.read_csv(csv_path)
    expected = ["timestamp", "open", "high", "low", "close", "volume"]
    if list(frame.columns) != expected or frame.empty:
        raise ValueError(f"unexpected or empty {side} CSV for {symbol} {month}")
    frame["ts"] = pd.to_datetime(frame.pop("timestamp"), unit="ms", utc=True)
    return frame.rename(
        columns={
            "open": f"{side}_o",
            "high": f"{side}_h",
            "low": f"{side}_l",
            "close": f"{side}_c",
            "volume": f"{side}_volume",
        }
    )


def fetch_month(
    root: Path,
    symbol: str,
    month: str,
    *,
    runner: Runner = subprocess.run,
    today: date | None = None,
) -> tuple[Path, bool]:
    symbol = symbol.upper()
    if symbol not in SYMBOLS:
        raise ValueError(f"unsupported symbol: {symbol}")
    current = (today or date.today()).strftime("%Y-%m")
    if month > current:
        raise ValueError("cannot fetch a future month")
    path = month_path(root, symbol, month)
    if path.exists() and month != current:
        try:
            read_month(root, symbol, month)
            return path, False
        except (ValueError, OSError):
            pass
    with tempfile.TemporaryDirectory(prefix="tvtools-dukascopy-") as temporary:
        directory = Path(temporary)
        cache = root / "dukascopy-cache"
        bid = _download_side(symbol, month, "bid", directory, cache, runner)
        ask = _download_side(symbol, month, "ask", directory, cache, runner)
    if bid["ts"].duplicated().any() or ask["ts"].duplicated().any():
        raise ValueError(f"duplicate source timestamps for {symbol} {month}")
    frame = bid.merge(ask, on="ts", how="outer", validate="one_to_one", indicator=True)
    if not frame["_merge"].eq("both").all():
        counts = frame["_merge"].value_counts().to_dict()
        raise ValueError(f"bid/ask timestamps disagree for {symbol} {month}: {counts}")
    frame = frame.drop(columns=["_merge", "ask_volume"])
    frame = frame.rename(columns={"bid_volume": "volume"})
    frame = frame[
        [
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
    ]
    return write_month(root, symbol, month, frame), True


def fetch_range(
    root: Path,
    symbol: str,
    start: str,
    end: str,
    *,
    runner: Runner = subprocess.run,
) -> tuple[int, int]:
    downloaded = skipped = 0
    for month in months(start, end):
        _, changed = fetch_month(root, symbol, month, runner=runner)
        downloaded += changed
        skipped += not changed
    return downloaded, skipped
