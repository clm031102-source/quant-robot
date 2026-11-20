"""Clean Pydantic configuration models for Quant Robot v2."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field


class CostConfig(BaseModel):
    commission_bps: float = Field(default=1.0, ge=0.0)
    minimum_commission: float = Field(default=5.0, ge=0.0)
    slippage_bps: float = Field(default=5.0, ge=0.0)
    stamp_duty_sell_bps: float = Field(default=0.0, ge=0.0)


class RiskConfig(BaseModel):
    max_drawdown_halt: float | None = Field(default=0.30, gt=0.0, lt=1.0)
    daily_loss_halt: float | None = Field(default=None, gt=0.0, lt=1.0)
    cooldown_sessions: int = Field(default=5, ge=0)
    max_single_weight: float = Field(default=1.0, gt=0.0, le=1.0)
    min_cash_weight: float = Field(default=0.0, ge=0.0, lt=1.0)


class StrategySpec(BaseModel):
    kind: Literal["fixed_allocation", "passive_drift", "dual_momentum", "risk_parity_trend"]
    target_weights: dict[str, float] = Field(default_factory=dict)
    rebalance_frequency: Literal["daily", "weekly", "monthly", "quarterly", "never"] = "monthly"
    rebalance_band: float = Field(default=0.05, ge=0.0, le=1.0)
    lookback_days: int = Field(default=60, ge=5)
    trend_ma_days: int = Field(default=120, ge=0)
    vol_lookback_days: int = Field(default=60, ge=5)
    top_n: int = Field(default=2, ge=1)
    defensive_symbol: str | None = None


class PortfolioSpec(BaseModel):
    portfolio_id: str
    name: str
    description: str = ""
    enabled: bool = True
    market: Literal["CN_ETF", "US_ETF", "CN", "HK", "CRYPTO"]
    currency: str = "CNY"
    symbols: list[str]
    lot_size: int = Field(default=100, ge=1)
    initial_cash: float = Field(default=10000.0, gt=0.0)
    start_date: str = "2026-11-01"
    execution_price: Literal["open", "close"] = "open"
    cost: CostConfig = Field(default_factory=CostConfig)
    risk: RiskConfig = Field(default_factory=RiskConfig)
    strategy: StrategySpec


class PortfoliosConfig(BaseModel):
    research_to_paper_only: bool = True
    portfolios: list[PortfolioSpec] = Field(default_factory=list)


class BacktestPreset(BaseModel):
    preset_id: str
    name: str
    market: Literal["CN_ETF", "US_ETF", "CN", "HK", "CRYPTO"]
    currency: str = "CNY"
    symbols: list[str]
    lot_size: int = Field(default=100, ge=1)
    initial_cash: float = Field(default=10000.0, gt=0.0)
    start_date: str = "2021-01-01"
    end_date: str | None = None
    execution_price: Literal["open", "close"] = "open"
    cost: CostConfig = Field(default_factory=CostConfig)
    risk: RiskConfig = Field(default_factory=RiskConfig)
    strategy: StrategySpec


class BacktestPresetsConfig(BaseModel):
    presets: list[BacktestPreset] = Field(default_factory=list)


def load_portfolios_config(path: str | Path = "configs/portfolios.json") -> PortfoliosConfig:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    return PortfoliosConfig.model_validate(raw)


def load_backtest_presets(path: str | Path = "configs/backtest_presets.json") -> BacktestPresetsConfig:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    return BacktestPresetsConfig.model_validate(raw)


def find_repo_root(start: str | Path | None = None) -> Path:
    current = Path(start or Path.cwd()).resolve()
    for candidate in (current, *current.parents):
        if (candidate / "pyproject.toml").is_file():
            return candidate
    return current


def resolve_data_root(repo_root: str | Path | None = None) -> Path:
    root = find_repo_root(repo_root)
    local_data = root / "data"
    if (local_data / "processed").exists() or (local_data / "market_cache").exists():
        return local_data
    # When running from a git worktree, also share the main checkout's local data directory if present.
    git_file = root / ".git"
    if git_file.is_file():
        text = git_file.read_text(encoding="utf-8", errors="ignore").strip()
        if text.startswith("gitdir:"):
            gitdir = Path(text.split(":", 1)[1].strip())
            if not gitdir.is_absolute():
                gitdir = (root / gitdir).resolve()
            # .git/worktrees/<name> -> repo/.git -> repo
            common_repo = gitdir.parent.parent.parent
            if (common_repo / "data").exists():
                return common_repo / "data"
    local_data.mkdir(parents=True, exist_ok=True)
    return local_data


def to_jsonable(obj: Any) -> Any:
    if isinstance(obj, BaseModel):
        return obj.model_dump()
    if isinstance(obj, Path):
        return str(obj)
    return obj
