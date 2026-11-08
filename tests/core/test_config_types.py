from dataclasses import replace
from pathlib import Path

import pandas as pd
import pytest

from tvtools.core.config import DEFAULT_CONFIG_PATH, RiskConfig, load_config
from tvtools.core.types import Direction, Signal


def test_default_config_and_signal_math() -> None:
    config = load_config()
    signal = Signal(
        symbol="EURUSD",
        direction=Direction.LONG,
        model_id="sweep_mss_fvg",
        variant_id="base",
        session="nyam_kz",
        created_at=pd.Timestamp("2026-11-02T12:00:00Z"),
        entry=1.1,
        stop_loss=1.099,
        take_profit=1.102,
        valid_until=pd.Timestamp("2026-11-02T16:00:00Z"),
        invalidation_price=1.099,
        reason={"sweep": "prior low"},
    )
    assert signal.risk_pips(config.symbols["EURUSD"]) == pytest.approx(10)
    assert signal.rr() == pytest.approx(2)
    assert signal.horizon == "intraday"


def test_invalid_risk_and_lot(tmp_path: Path) -> None:
    config = load_config()
    with pytest.raises(ValueError, match="max_sl_pips_fx must be positive"):
        replace(config.risk, max_sl_pips_fx=-1)
    with pytest.raises(ValueError, match="below EURUSD min_lot"):
        replace(config, risk=replace(config.risk, lot=0.001))

    source = DEFAULT_CONFIG_PATH.read_text()
    bad_config = tmp_path / "bad.toml"
    bad_config.write_text(
        source.replace("max_sl_pips_fx = 20.0", "max_sl_pips_fx = -1")
    )
    with pytest.raises(ValueError, match="max_sl_pips_fx must be positive"):
        load_config(bad_config)


def test_negative_lot_rejected() -> None:
    config = load_config()
    with pytest.raises(ValueError, match="lot must be positive"):
        RiskConfig(**{**vars(config.risk), "lot": -0.01})


def test_lot_must_match_lot_step() -> None:
    config = load_config()
    with pytest.raises(ValueError, match="not a multiple of EURUSD lot_step"):
        replace(config, risk=replace(config.risk, lot=0.015))
    assert replace(config, risk=replace(config.risk, lot=0.03)).risk.lot == 0.03
