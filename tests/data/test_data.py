import subprocess
from collections.abc import Callable
from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from tvtools import cli
from tvtools.data.dukascopy import fetch_month, fetch_range, node_env
from tvtools.data.quality import check_store, inspect, render_report
from tvtools.data.resample import resample_m1
from tvtools.data.store import month_path, read_month, write_month

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "m1_sample.csv"


@pytest.fixture
def sample() -> pd.DataFrame:
    return pd.read_csv(FIXTURE, parse_dates=["ts"])


def test_resample_five_manual_candles(sample: pd.DataFrame) -> None:
    bars = resample_m1(sample, "M5")
    assert len(bars) == 1
    bar = bars.iloc[0]
    assert bar["ts"] == pd.Timestamp("2024-01-02T12:00:00Z")
    assert bar["closed_at"] == pd.Timestamp("2024-01-02T12:05:00Z")
    assert bar["bid_o"] == pytest.approx(1.1000)
    assert bar["bid_h"] == pytest.approx(1.1006)
    assert bar["bid_l"] == pytest.approx(1.0999)
    assert bar["bid_c"] == pytest.approx(1.1005)
    assert bar["ask_o"] == pytest.approx(1.1001)
    assert bar["ask_c"] == pytest.approx(1.1006)
    assert bar["volume"] == 20


def test_resample_keeps_windows_with_tickless_minutes(sample: pd.DataFrame) -> None:
    # Dukascopy omits minutes without ticks; the bar must survive the gap.
    later = sample.copy()
    later["ts"] = later["ts"] + pd.Timedelta(hours=2)
    frame = pd.concat([sample.drop(index=2), later], ignore_index=True)

    m5 = resample_m1(frame, "M5")
    assert m5["ts"].tolist() == [
        pd.Timestamp("2024-01-02T12:00:00Z"),
        pd.Timestamp("2024-01-02T14:00:00Z"),
    ]
    first = m5.iloc[0]
    assert first["bid_o"] == pytest.approx(1.1000)
    assert first["bid_h"] == pytest.approx(1.1006)
    assert first["bid_l"] == pytest.approx(1.0999)
    assert first["bid_c"] == pytest.approx(1.1005)
    assert first["volume"] == 16

    h1 = resample_m1(frame, "H1")
    assert h1["ts"].tolist() == [
        pd.Timestamp("2024-01-02T12:00:00Z"),
        pd.Timestamp("2024-01-02T14:00:00Z"),
    ]
    assert h1["closed_at"].tolist() == [
        pd.Timestamp("2024-01-02T13:00:00Z"),
        pd.Timestamp("2024-01-02T15:00:00Z"),
    ]


def test_quality_and_store(sample: pd.DataFrame, tmp_path: Path) -> None:
    write_month(tmp_path, "EURUSD", "2024-01", sample)
    stored = read_month(tmp_path, "EURUSD", "2024-01")
    result = inspect(stored, "EURUSD")
    assert result.rows == 5
    assert result.duplicates == result.invalid_ohlc == result.crossed_quotes == 0
    assert len(result.gaps) == 0
    assert "Median pips" in render_report(result, ["2024-01"])


def test_quality_detects_defects(sample: pd.DataFrame) -> None:
    broken = sample.copy()
    broken.loc[1, "ask_c"] = 1.0
    broken.loc[2, "bid_h"] = 1.0
    broken.loc[3, "ts"] = broken.loc[0, "ts"]
    result = inspect(broken, "EURUSD")
    assert result.duplicates == 1
    assert result.out_of_order == 1
    assert result.invalid_ohlc >= 2
    assert result.crossed_quotes >= 1


def test_fetch_is_idempotent_with_valid_existing_month(
    sample: pd.DataFrame, tmp_path: Path
) -> None:
    write_month(tmp_path, "EURUSD", "2024-01", sample)

    def unexpected_run(*args: object, **kwargs: object) -> None:
        raise AssertionError("valid historical month must not download again")

    _, changed = fetch_month(tmp_path, "EURUSD", "2024-01", runner=unexpected_run)
    assert not changed


def fake_dukascopy(
    sample: pd.DataFrame, calls: list[list[str]] | None = None
) -> Callable[..., subprocess.CompletedProcess[str]]:
    """Stand in for dukascopy-node: write the sample side as its CSV output."""

    def run(command: list[str], **kwargs: object) -> subprocess.CompletedProcess[str]:
        env = kwargs["env"]
        assert isinstance(env, dict)
        assert "--use-system-ca" in env["NODE_OPTIONS"].split()
        if calls is not None:
            calls.append(command)
        side = command[command.index("-p") + 1]
        month = command[command.index("-from") + 1][:7]
        directory = Path(command[command.index("-dir") + 1])
        filename = command[command.index("-fn") + 1]
        source = sample[
            ["ts", f"{side}_o", f"{side}_h", f"{side}_l", f"{side}_c", "volume"]
        ].copy()
        source["ts"] = source["ts"].map(
            lambda stamp: stamp.replace(year=int(month[:4]), month=int(month[5:]))
        )
        source["ts"] = source["ts"].map(lambda stamp: int(stamp.timestamp() * 1000))
        source.columns = ["timestamp", "open", "high", "low", "close", "volume"]
        source.to_csv(directory / f"{filename}.csv", index=False)
        return subprocess.CompletedProcess(command, 0, "", "")

    return run


def test_fetch_merges_bid_and_ask_csv(sample: pd.DataFrame, tmp_path: Path) -> None:
    calls: list[list[str]] = []
    _, changed = fetch_month(
        tmp_path, "EURUSD", "2024-01", runner=fake_dukascopy(sample, calls)
    )
    assert changed
    assert len(calls) == 2
    assert [call[call.index("-p") + 1] for call in calls] == ["bid", "ask"]
    assert all("-fl" not in call for call in calls)
    assert all(
        call[call.index("-chpath") + 1] == str(tmp_path / "dukascopy-cache")
        for call in calls
    )
    assert len(read_month(tmp_path, "EURUSD", "2024-01")) == 5


def test_fetch_range_skips_months_on_second_run(
    sample: pd.DataFrame, tmp_path: Path
) -> None:
    calls: list[list[str]] = []
    runner = fake_dukascopy(sample, calls)
    assert fetch_range(tmp_path, "eurusd", "2024-01", "2024-03", runner=runner) == (
        3,
        0,
    )
    assert len(calls) == 6
    assert fetch_range(tmp_path, "EURUSD", "2024-01", "2024-03", runner=runner) == (
        0,
        3,
    )
    assert len(calls) == 6


def test_fetch_replaces_corrupt_month(sample: pd.DataFrame, tmp_path: Path) -> None:
    path = month_path(tmp_path, "EURUSD", "2024-01")
    path.parent.mkdir(parents=True)
    path.write_bytes(b"not parquet")
    _, changed = fetch_month(
        tmp_path, "EURUSD", "2024-01", runner=fake_dukascopy(sample)
    )
    assert changed
    assert len(read_month(tmp_path, "EURUSD", "2024-01")) == 5


def test_fetch_always_refreshes_current_month(
    sample: pd.DataFrame, tmp_path: Path
) -> None:
    runner = fake_dukascopy(sample)
    today = date(2024, 1, 20)
    fetch_month(tmp_path, "EURUSD", "2024-01", runner=runner, today=today)
    _, changed = fetch_month(tmp_path, "EURUSD", "2024-01", runner=runner, today=today)
    assert changed
    with pytest.raises(ValueError, match="future month"):
        fetch_month(tmp_path, "EURUSD", "2024-02", runner=runner, today=today)


def test_fetch_rejects_bad_requests(sample: pd.DataFrame, tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="unsupported symbol"):
        fetch_month(tmp_path, "BTCUSD", "2024-01", runner=fake_dukascopy(sample))
    with pytest.raises(ValueError, match="YYYY-MM"):
        fetch_range(tmp_path, "EURUSD", "2024-1", "2024-02")
    with pytest.raises(ValueError, match="must not exceed"):
        fetch_range(tmp_path, "EURUSD", "2024-03", "2024-01")


def test_fetch_reports_cli_failure(tmp_path: Path) -> None:
    def failing(command: list[str], **kwargs: object) -> None:
        raise subprocess.CalledProcessError(1, command, "", "fetch failed")

    with pytest.raises(RuntimeError, match="EURUSD 2024-01 bid: fetch failed"):
        fetch_month(tmp_path, "EURUSD", "2024-01", runner=failing)
    assert not month_path(tmp_path, "EURUSD", "2024-01").exists()


def test_fetch_rejects_one_sided_minutes(sample: pd.DataFrame, tmp_path: Path) -> None:
    def runner(
        command: list[str], **kwargs: object
    ) -> subprocess.CompletedProcess[str]:
        side = command[command.index("-p") + 1]
        frame = sample.drop(index=2) if side == "ask" else sample
        return fake_dukascopy(frame)(command, **kwargs)

    with pytest.raises(ValueError, match="bid/ask timestamps disagree"):
        fetch_month(tmp_path, "EURUSD", "2024-01", runner=runner)


def _minutes(start: str, count: int) -> pd.DataFrame:
    ts = pd.date_range(start, periods=count, freq="min", tz="UTC")
    bid = pd.Series(1.1, index=range(count))
    return pd.DataFrame(
        {
            "ts": ts,
            "bid_o": bid,
            "bid_h": bid + 0.0002,
            "bid_l": bid - 0.0001,
            "bid_c": bid + 0.0001,
            "ask_o": bid + 0.0001,
            "ask_h": bid + 0.0003,
            "ask_l": bid,
            "ask_c": bid + 0.0002,
            "volume": 1.0,
        }
    )


@pytest.mark.parametrize(
    ("before", "after", "expected"),
    [
        # Tuesday: 6 missing open minutes is a gap, 5 is not.
        ("2024-01-02T12:00Z", "2024-01-02T12:16Z", 1),
        ("2024-01-02T12:00Z", "2024-01-02T12:15Z", 0),
        # Weekend: Friday 17:00 NY to Sunday 17:00 NY.
        ("2024-01-05T21:50Z", "2024-01-07T22:00Z", 0),
        # Christmas 2024: FX day Dec 24 17:00 NY to Dec 25 17:00 NY.
        ("2024-12-24T21:50Z", "2024-12-25T22:00Z", 0),
        # Holiday closure ends at 17:00 NY; later missing minutes still count.
        ("2024-12-24T21:50Z", "2024-12-25T23:00Z", 1),
        # Thanksgiving 2024 during standard time (17:00 NY = 22:00 UTC).
        ("2024-11-27T21:50Z", "2024-11-28T22:00Z", 0),
        # Independence Day 2024 during daylight time (17:00 NY = 21:00 UTC).
        ("2024-07-03T20:50Z", "2024-07-04T21:00Z", 0),
    ],
)
def test_gaps_exclude_weekends_and_holidays(
    before: str, after: str, expected: int
) -> None:
    first = _minutes(before, 10)
    second = _minutes(after, 10)
    frame = pd.concat([first, second], ignore_index=True)
    assert len(inspect(frame, "EURUSD").gaps) == expected


def test_check_store_writes_report(sample: pd.DataFrame, tmp_path: Path) -> None:
    write_month(tmp_path / "data", "EURUSD", "2024-01", sample)
    report = check_store(tmp_path / "data", "eurusd", tmp_path / "reports")
    assert report == tmp_path / "reports" / "data-quality-EURUSD.md"
    text = report.read_text()
    assert "Months present: 1 (2024-01)" in text
    assert "Duplicate timestamps: 0" in text
    with pytest.raises(FileNotFoundError, match="GBPUSD"):
        check_store(tmp_path / "data", "GBPUSD", tmp_path / "reports")


def test_cli_fetch_and_check(
    sample: pd.DataFrame,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.chdir(tmp_path)
    runner = fake_dukascopy(sample)

    def offline_fetch_range(
        root: Path, symbol: str, start: str, end: str
    ) -> tuple[int, int]:
        return fetch_range(root, symbol, start, end, runner=runner)

    monkeypatch.setattr(cli, "fetch_range", offline_fetch_range)
    args = [
        "data",
        "fetch",
        "--symbol",
        "EURUSD",
        "--from",
        "2024-01",
        "--to",
        "2024-02",
    ]
    assert cli.main(args) == 0
    assert cli.main(args) == 0
    assert cli.main(["data", "check", "--symbol", "EURUSD"]) == 0
    out = capsys.readouterr().out.splitlines()
    assert out[:2] == [
        "EURUSD: downloaded 2, skipped 0 months",
        "EURUSD: downloaded 0, skipped 2 months",
    ]
    assert out[2] == str(Path("reports") / "data-quality-EURUSD.md")
    assert (tmp_path / "data" / "m1" / "EURUSD" / "2024-02.parquet").exists()
    with pytest.raises(SystemExit):
        cli.main(["data", "fetch", "--symbol", "BTCUSD", "--from", "2024-01"])


def test_node_env_trusts_system_ca_and_keeps_options(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("NODE_OPTIONS", raising=False)
    assert node_env()["NODE_OPTIONS"] == "--use-system-ca"
    monkeypatch.setenv("NODE_OPTIONS", "--max-old-space-size=4096")
    assert node_env()["NODE_OPTIONS"] == "--max-old-space-size=4096 --use-system-ca"
    monkeypatch.setenv("NODE_OPTIONS", "--use-system-ca")
    assert node_env()["NODE_OPTIONS"] == "--use-system-ca"
