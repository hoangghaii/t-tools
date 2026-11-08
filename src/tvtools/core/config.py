"""Validated, immutable project configuration. Secrets stay in environment variables."""

import tomllib
from dataclasses import dataclass
from datetime import time
from functools import cache
from pathlib import Path


@dataclass(frozen=True)
class SymbolSpec:
    pip_size: float
    contract_size: float
    min_lot: float
    lot_step: float
    enabled: bool

    def __post_init__(self) -> None:
        for name in ("pip_size", "contract_size", "min_lot", "lot_step"):
            if getattr(self, name) <= 0:
                raise ValueError(f"{name} must be positive")


@dataclass(frozen=True)
class SessionSpec:
    start: time
    end: time
    start_day_offset: int = 0

    def __post_init__(self) -> None:
        if self.start_day_offset not in (-1, 0):
            raise ValueError("start_day_offset must be -1 or 0")
        if self.start_day_offset == -1 and self.start <= self.end:
            raise ValueError("prior-day session start must be after end")
        if self.start_day_offset == 0 and self.start > self.end:
            raise ValueError("same-day session start must not be after end")


@dataclass(frozen=True)
class RiskConfig:
    account_usd: float
    lot: float
    max_sl_pips_fx: float
    max_open_trades: int
    max_daily_losses: int
    max_weekly_drawdown_fraction: float
    min_rr: float

    def __post_init__(self) -> None:
        for name in ("account_usd", "lot", "max_sl_pips_fx", "min_rr"):
            if getattr(self, name) <= 0:
                raise ValueError(f"{name} must be positive")
        if self.max_open_trades < 1 or self.max_daily_losses < 1:
            raise ValueError("trade and loss limits must be at least 1")
        if not 0 < self.max_weekly_drawdown_fraction < 1:
            raise ValueError("max_weekly_drawdown_fraction must be between 0 and 1")


@dataclass(frozen=True)
class IctConfig:
    model_id: str
    variant_id: str


@dataclass(frozen=True)
class AppConfig:
    symbols: dict[str, SymbolSpec]
    sessions: dict[str, SessionSpec]
    risk: RiskConfig
    ict: IctConfig

    def __post_init__(self) -> None:
        if not self.symbols or not any(spec.enabled for spec in self.symbols.values()):
            raise ValueError("at least one symbol must be enabled")
        if not self.sessions:
            raise ValueError("at least one session is required")
        for name, spec in self.symbols.items():
            if spec.enabled and self.risk.lot < spec.min_lot:
                raise ValueError(
                    f"lot {self.risk.lot} is below {name} min_lot {spec.min_lot}"
                )
            steps = self.risk.lot / spec.lot_step
            if spec.enabled and abs(steps - round(steps)) > 1e-9:
                raise ValueError(
                    f"lot {self.risk.lot} is not a multiple of {name} "
                    f"lot_step {spec.lot_step}"
                )


_SOURCE_DEFAULT = Path(__file__).resolve().parents[3] / "config" / "default.toml"
DEFAULT_CONFIG_PATH = (
    _SOURCE_DEFAULT
    if _SOURCE_DEFAULT.exists()
    else Path(__file__).resolve().parents[1] / "default.toml"
)


def load_config(path: Path = DEFAULT_CONFIG_PATH) -> AppConfig:
    with path.open("rb") as stream:
        raw = tomllib.load(stream)
    try:
        symbols = {
            name: SymbolSpec(**values) for name, values in raw["symbols"].items()
        }
        sessions = {
            name: SessionSpec(
                start=time.fromisoformat(values["start"]),
                end=time.fromisoformat(values["end"]),
                start_day_offset=values.get("start_day_offset", 0),
            )
            for name, values in raw["sessions"].items()
        }
        return AppConfig(
            symbols=symbols,
            sessions=sessions,
            risk=RiskConfig(**raw["risk"]),
            ict=IctConfig(**raw["ict"]),
        )
    except (KeyError, TypeError) as exc:
        raise ValueError(f"Invalid config {path}: {exc}") from exc


@cache
def default_config() -> AppConfig:
    """Default config loaded once per process; pass an explicit config to override."""
    return load_config()
