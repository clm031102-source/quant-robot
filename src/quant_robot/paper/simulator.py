from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from quant_robot.backtest.costs import capacity_limited, market_impact_cost_bps
from quant_robot.backtest.portfolio import select_top_n
from quant_robot.backtest.metrics import max_drawdown, summarize_returns
from quant_robot.data.quality import validate_market_data
from quant_robot.factors.technical import compute_basic_factors
from quant_robot.factors.tushare_inputs import compute_daily_basic_factors
from quant_robot.factors.tushare_moneyflow import compute_moneyflow_factors
from quant_robot.portfolio.constraints import PortfolioConstraints, apply_portfolio_constraints
from quant_robot.portfolio.rebalance import FORBIDDEN_REAL_ACCOUNT_COLUMNS, build_rebalance_plan
from quant_robot.storage.factor_inputs import load_factor_inputs
from quant_robot.storage.moneyflow_inputs import load_moneyflow_inputs


@dataclass(frozen=True)
class PaperSimulationConfig:
    market: str = "ALL"
    factor_source: str = "technical"
    factor_name: str = "momentum_2"
    factor_windows: tuple[int, ...] = (2, 3)
    factor_input_root: Path | None = None
    moneyflow_input_root: Path | None = None
    top_n: int = 2
    rebalance_interval: int = 1
    start_date: str | None = None
    end_date: str | None = None
    initial_cash: float = 100000.0
    commission_bps: float = 5.0
    slippage_bps: float = 5.0
    market_impact_bps: float = 0.0
    max_participation_rate: float | None = None
    min_trade_value: float = 1.0
    max_asset_weight: float = 1.0
    max_market_weight: float = 1.0
    max_gross_exposure: float = 1.0
    min_cash_weight: float = 0.0
    periods_per_year: float | None = None
    max_drawdown_guard: float | None = None
    guard_cooldown_periods: int = 0
    respect_execution_constraints: bool = True
    output_dir: Path | None = None


def run_paper_simulation(
    bars: pd.DataFrame,
    config: PaperSimulationConfig,
    initial_positions: pd.DataFrame | None = None,
) -> dict[str, Any]:
    if config.initial_cash <= 0.0:
        raise ValueError("initial_cash must be positive")
    if config.rebalance_interval < 1:
        raise ValueError("rebalance_interval must be at least 1")
    positions = _initial_positions(initial_positions)
    filtered = _filter_bars(bars, config)
    validate_market_data(filtered)
    factors = _compute_factors(filtered, config)
    dates = sorted(pd.to_datetime(filtered["date"]).dt.date.unique())
    factor_slices = _factor_slices_by_date(factors, config.factor_name, dates)
    valuation_prices_by_date = _latest_prices_by_date(filtered, dates)
    execution_prices_by_date = _current_prices_by_date(filtered, dates)
    cash = float(config.initial_cash)
    intents: list[dict[str, Any]] = []
    fills: list[dict[str, Any]] = []
    equity_rows: list[dict[str, Any]] = []
    snapshots: list[dict[str, Any]] = []
    guard_events: list[dict[str, Any]] = []
    execution_events: list[dict[str, Any]] = []

    rebalance_counter = 0
    baseline_recorded = False
    peak_equity = float(config.initial_cash)
    guard_remaining = 0
    for index, signal_date in enumerate(dates[:-1]):
        if config.start_date and signal_date < pd.to_datetime(config.start_date).date():
            continue
        if rebalance_counter % config.rebalance_interval != 0:
            rebalance_counter += 1
            continue
        rebalance_counter += 1
        execution_date = dates[index + 1]
        if config.end_date and execution_date > pd.to_datetime(config.end_date).date():
            continue
        selected = factor_slices.get(signal_date)
        if selected is None or selected.empty:
            continue

        signal_prices = valuation_prices_by_date[signal_date]
        execution_prices = execution_prices_by_date[execution_date]
        valuation_prices = valuation_prices_by_date[execution_date]
        if not baseline_recorded:
            baseline_row = _equity_row(signal_date, cash, positions, signal_prices)
            equity_rows.append(baseline_row)
            peak_equity = max(peak_equity, float(baseline_row["equity"]))
            baseline_recorded = True
        portfolio_value = _portfolio_value(cash, positions, signal_prices)
        targets, cash_weight = _targets_from_factor_slice(selected, signal_prices, config)
        plan = build_rebalance_plan(
            targets,
            _positions_frame(positions),
            signal_prices,
            portfolio_value=portfolio_value,
        )
        snapshots.append(
            {
                "signal_date": str(signal_date),
                "target_weight": float(targets["target_weight"].sum()) if not targets.empty else 0.0,
                "cash_weight": cash_weight,
                "target_count": int(len(targets)),
            }
        )
        day_intents = _build_intents(plan, signal_date, execution_date, config.min_trade_value)
        day_intents, guard_remaining, guard_event = _apply_drawdown_guard(day_intents, signal_date, guard_remaining)
        if guard_event is not None:
            guard_events.append(guard_event)
        day_fills, day_execution_events = _simulate_fills(
            day_intents,
            execution_prices,
            config.commission_bps,
            config.slippage_bps,
            config.market_impact_bps,
            config.max_participation_rate,
            cash,
            respect_execution_constraints=config.respect_execution_constraints,
        )
        cash = _apply_fills(positions, cash, day_fills)
        intents.extend(day_intents)
        fills.extend(day_fills)
        execution_events.extend(day_execution_events)
        equity_row = _equity_row(execution_date, cash, positions, valuation_prices)
        equity_rows.append(equity_row)
        peak_equity, guard_remaining, trigger_event = _update_drawdown_guard(equity_row, peak_equity, guard_remaining, config)
        if trigger_event is not None:
            guard_events.append(trigger_event)

    equity_curve = _equity_curve(equity_rows)
    metrics = _metrics(equity_curve, cash, positions, filtered, config, guard_events, execution_events, fills)
    result = _sanitize(
        {
            "data_mode": "fixture" if set(filtered["source"].astype(str)) == {"fixture"} else "research",
            "request": _config_dict(config),
            "metrics": metrics,
            "intents": intents,
            "fills": fills,
            "positions": _records(_positions_frame(positions)),
            "equity_curve": _records(equity_curve),
            "snapshots": snapshots,
            "guard_events": guard_events,
            "execution_events": execution_events,
        }
    )
    if config.output_dir is not None:
        write_paper_simulation_artifacts(result, config.output_dir)
    return result


def write_paper_simulation_artifacts(result: dict[str, Any], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(result["intents"]).to_csv(output_dir / "intents.csv", index=False)
    pd.DataFrame(result["fills"]).to_csv(output_dir / "fills.csv", index=False)
    pd.DataFrame(result["positions"]).to_csv(output_dir / "positions.csv", index=False)
    pd.DataFrame(result["equity_curve"]).to_csv(output_dir / "equity_curve.csv", index=False)
    pd.DataFrame(result["snapshots"]).to_csv(output_dir / "snapshots.csv", index=False)
    pd.DataFrame(result["guard_events"]).to_csv(output_dir / "guard_events.csv", index=False)
    pd.DataFrame(result.get("execution_events", [])).to_csv(output_dir / "execution_events.csv", index=False)
    manifest = {
        "data_mode": result["data_mode"],
        "request": result["request"],
        "metrics": result["metrics"],
        "safety": "Local paper simulation only. No broker connection, no order placement, no live trading.",
    }
    (output_dir / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True), encoding="utf-8")


def _filter_bars(bars: pd.DataFrame, config: PaperSimulationConfig) -> pd.DataFrame:
    frame = bars.copy()
    if config.market.upper() != "ALL":
        frame = frame[frame["market"] == config.market.upper()]
    if config.end_date:
        frame = frame[pd.to_datetime(frame["date"]).dt.date <= pd.to_datetime(config.end_date).date()]
    if frame.empty:
        raise ValueError("No bars available for paper simulation")
    return frame.sort_values(["asset_id", "date"]).reset_index(drop=True)


def _compute_factors(bars: pd.DataFrame, config: PaperSimulationConfig) -> pd.DataFrame:
    if config.factor_source == "technical":
        return compute_basic_factors(bars, windows=config.factor_windows)
    if config.factor_source == "tushare_moneyflow":
        if config.moneyflow_input_root is None:
            raise ValueError("moneyflow_input_root is required for Tushare moneyflow paper simulation")
        if config.market.upper() == "ALL":
            raise ValueError("Tushare moneyflow paper simulation requires a specific market")
        moneyflow_inputs = load_moneyflow_inputs(config.moneyflow_input_root, config.market.upper())
        moneyflow_inputs = _external_factor_inputs_for_window(moneyflow_inputs, bars, config)
        if moneyflow_inputs.empty:
            raise ValueError("No moneyflow inputs available for paper simulation")
        return compute_moneyflow_factors(moneyflow_inputs)
    if config.factor_source != "tushare_daily_basic":
        raise ValueError(f"Unsupported paper simulation factor_source: {config.factor_source}")
    if config.factor_input_root is None:
        raise ValueError("factor_input_root is required for Tushare daily-basic paper simulation")
    if config.market.upper() == "ALL":
        raise ValueError("Tushare daily-basic paper simulation requires a specific market")
    factor_inputs = load_factor_inputs(config.factor_input_root, config.market.upper())
    factor_inputs = _external_factor_inputs_for_window(factor_inputs, bars, config)
    if factor_inputs.empty:
        raise ValueError("No factor inputs available for paper simulation")
    return compute_daily_basic_factors(factor_inputs)


def _external_factor_inputs_for_window(
    inputs: pd.DataFrame,
    bars: pd.DataFrame,
    config: PaperSimulationConfig,
) -> pd.DataFrame:
    frame = inputs[inputs["asset_id"].isin(set(bars["asset_id"].astype(str)))].copy()
    if frame.empty:
        return frame.reset_index(drop=True)
    dates = pd.to_datetime(frame["date"]).dt.date
    if config.start_date:
        frame = frame[dates >= pd.to_datetime(config.start_date).date()]
        dates = dates.loc[frame.index]
    if config.end_date:
        frame = frame[dates <= pd.to_datetime(config.end_date).date()]
    return frame.reset_index(drop=True)


def _initial_positions(initial_positions: pd.DataFrame | None) -> dict[str, float]:
    if initial_positions is None:
        return {}
    forbidden = sorted(FORBIDDEN_REAL_ACCOUNT_COLUMNS & set(initial_positions.columns))
    if forbidden:
        raise ValueError("initial_positions contains real account or broker columns: " + ", ".join(forbidden))
    missing = [column for column in ("asset_id", "quantity") if column not in initial_positions.columns]
    if missing:
        raise ValueError("initial_positions is missing columns: " + ", ".join(missing))
    return {
        str(row.asset_id): float(row.quantity)
        for row in initial_positions.itertuples(index=False)
        if float(row.quantity) != 0.0
    }


def _latest_prices(bars: pd.DataFrame, as_of_date: Any) -> pd.DataFrame:
    available = bars[pd.to_datetime(bars["date"]).dt.date <= as_of_date].sort_values(["asset_id", "date"])
    return (
        available.groupby("asset_id", as_index=False, group_keys=False)
        .tail(1)[["asset_id", "market", "adj_close"]]
        .rename(columns={"adj_close": "latest_price"})
        .reset_index(drop=True)
    )


def _factor_slices_by_date(factors: pd.DataFrame, factor_name: str, dates: list[Any]) -> dict[Any, pd.DataFrame]:
    selected = factors[factors["factor_name"] == factor_name].dropna(subset=["factor_value"]).copy()
    if selected.empty:
        return {}
    selected["_date_key"] = pd.to_datetime(selected["date"]).dt.date
    groups = {date: group.drop(columns=["_date_key"]).reset_index(drop=True) for date, group in selected.groupby("_date_key")}
    slices: dict[Any, pd.DataFrame] = {}
    latest: pd.DataFrame | None = None
    for date in dates:
        latest = groups.get(date, latest)
        if latest is not None:
            slices[date] = latest
    return slices


def _latest_prices_by_date(bars: pd.DataFrame, dates: list[Any]) -> dict[Any, pd.DataFrame]:
    frame = bars.copy()
    frame["_date_key"] = pd.to_datetime(frame["date"]).dt.date
    groups = {date: group for date, group in frame.groupby("_date_key")}
    latest: dict[str, dict[str, Any]] = {}
    prices: dict[Any, pd.DataFrame] = {}
    for date in dates:
        for row in groups.get(date, pd.DataFrame()).itertuples(index=False):
            latest[str(row.asset_id)] = {
                "asset_id": str(row.asset_id),
                "market": str(row.market),
                "latest_price": float(row.adj_close),
            }
        prices[date] = pd.DataFrame(latest.values(), columns=["asset_id", "market", "latest_price"])
    return prices


def _current_prices_by_date(bars: pd.DataFrame, dates: list[Any]) -> dict[Any, pd.DataFrame]:
    frame = bars.copy()
    frame["_date_key"] = pd.to_datetime(frame["date"]).dt.date
    prices: dict[Any, pd.DataFrame] = {}
    optional = [column for column in ("amount", "suspended", "limit_up", "limit_down") if column in frame.columns]
    columns = ["asset_id", "market", "adj_close", "volume", *optional]
    empty = pd.DataFrame(columns=["asset_id", "market", "latest_price", "volume", *optional])
    for date, group in frame.groupby("_date_key"):
        prices[date] = group[columns].rename(columns={"adj_close": "latest_price"}).reset_index(drop=True)
    return {date: prices.get(date, empty) for date in dates}


def _targets_from_factor_slice(
    selected: pd.DataFrame,
    prices: pd.DataFrame,
    config: PaperSimulationConfig,
) -> tuple[pd.DataFrame, float]:
    ranked = select_top_n(selected, top_n=config.top_n, portfolio_scope=_portfolio_scope(config))
    if ranked.empty:
        return ranked.assign(latest_price=pd.Series(dtype=float)), 1.0
    targets = ranked.merge(prices[["asset_id", "latest_price"]], on="asset_id", how="left")
    targets = targets.dropna(subset=["latest_price"]).copy()
    if targets.empty:
        return targets, 1.0
    targets["signal_date"] = targets["date"]
    constrained, cash_weight, _warnings = apply_portfolio_constraints(
        targets,
        PortfolioConstraints(
            max_asset_weight=config.max_asset_weight,
            max_market_weight=config.max_market_weight,
            max_gross_exposure=config.max_gross_exposure,
            min_cash_weight=config.min_cash_weight,
        ),
    )
    return constrained, cash_weight


def _portfolio_scope(config: PaperSimulationConfig) -> str:
    return "global" if config.market.upper() == "ALL" else "market"


def _portfolio_value(cash: float, positions: dict[str, float], prices: pd.DataFrame) -> float:
    price_lookup = prices.set_index("asset_id")["latest_price"].to_dict()
    return cash + sum(quantity * float(price_lookup.get(asset_id, 0.0)) for asset_id, quantity in positions.items())


def _positions_frame(positions: dict[str, float]) -> pd.DataFrame:
    if not positions:
        return pd.DataFrame(columns=["asset_id", "quantity"])
    return pd.DataFrame(
        [{"asset_id": asset_id, "quantity": quantity} for asset_id, quantity in sorted(positions.items()) if abs(quantity) > 1e-12]
    )


def _build_intents(plan: pd.DataFrame, signal_date: Any, execution_date: Any, min_trade_value: float) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for row in plan.itertuples(index=False):
        delta_value = float(row.delta_value)
        if abs(delta_value) < min_trade_value:
            continue
        quantity = float(row.estimated_quantity_delta)
        side = "buy" if quantity > 0.0 else "sell"
        rows.append(
            {
                "intent_id": f"{signal_date}-{row.asset_id}-{side}",
                "signal_date": signal_date,
                "execution_date": execution_date,
                "asset_id": row.asset_id,
                "market": row.market,
                "side": side,
                "intended_quantity": abs(quantity),
                "signed_quantity": quantity,
                "reference_price": float(row.latest_price),
                "target_weight": float(row.target_weight),
                "executable": False,
                "broker_order_id": None,
                "intent_type": "paper_simulation_intent",
            }
        )
    return rows


def _simulate_fills(
    intents: list[dict[str, Any]],
    execution_prices: pd.DataFrame,
    commission_bps: float,
    slippage_bps: float,
    market_impact_bps: float,
    max_participation_rate: float | None,
    available_cash: float,
    respect_execution_constraints: bool = True,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    price_lookup = execution_prices.set_index("asset_id").to_dict(orient="index")
    fills: list[dict[str, Any]] = []
    execution_events: list[dict[str, Any]] = []
    cash = available_cash
    for intent in sorted(intents, key=lambda item: 0 if item["side"] == "sell" else 1):
        price_row = price_lookup.get(intent["asset_id"])
        if price_row is None:
            continue
        blocked_reason = _execution_blocking_reason(intent, price_row, respect_execution_constraints)
        if blocked_reason is not None:
            execution_events.append(
                {
                    "event_type": "execution_constraint_blocked_fill",
                    "reason": blocked_reason,
                    "intent_id": intent["intent_id"],
                    "signal_date": intent["signal_date"],
                    "execution_date": intent["execution_date"],
                    "asset_id": intent["asset_id"],
                    "market": str(price_row.get("market", intent["market"])),
                    "side": intent["side"],
                }
            )
            continue
        base_price = float(price_row["latest_price"])
        signed_quantity = float(intent["signed_quantity"])
        fill_price = _fill_price(base_price, signed_quantity, slippage_bps)
        lot_size = _lot_size_for_market(str(price_row.get("market", intent["market"])))
        signed_quantity = _round_signed_quantity_to_lot(signed_quantity, lot_size)
        quantity = abs(signed_quantity)
        notional = quantity * fill_price
        fee = notional * commission_bps / 10000.0
        if signed_quantity > 0.0 and notional + fee > cash and notional > 0.0:
            scale = max(cash, 0.0) / (notional + fee)
            signed_quantity = _round_signed_quantity_to_lot(quantity * scale, lot_size)
            quantity = abs(signed_quantity)
            notional = quantity * fill_price
            fee = notional * commission_bps / 10000.0
        if quantity <= 1e-12:
            continue
        participation_rate = _participation_rate(quantity, fill_price, price_row)
        impact_bps = market_impact_cost_bps(market_impact_bps, participation_rate, max_participation_rate)
        market_impact_fee = notional * impact_bps / 10000.0
        capacity_flag = capacity_limited(participation_rate, max_participation_rate)
        fee += market_impact_fee
        cash += notional - fee if signed_quantity < 0.0 else -(notional + fee)
        fills.append(
            {
                "intent_id": intent["intent_id"],
                "signal_date": intent["signal_date"],
                "execution_date": intent["execution_date"],
                "asset_id": intent["asset_id"],
                "market": str(price_row.get("market", intent["market"])),
                "side": intent["side"],
                "quantity": quantity,
                "signed_quantity": signed_quantity,
                "lot_size": lot_size,
                "fill_price": fill_price,
                "notional": notional,
                "fee": fee,
                "commission_fee": notional * commission_bps / 10000.0,
                "market_impact_fee": market_impact_fee,
                "participation_rate": participation_rate,
                "capacity_limited": capacity_flag,
                "fill_type": "simulated",
                "broker_order_id": None,
            }
        )
    return fills, execution_events


def _participation_rate(quantity: float, fill_price: float, price_row: dict[str, Any]) -> float:
    try:
        amount = float(price_row.get("amount", 0.0))
    except (TypeError, ValueError):
        return 0.0
    if amount <= 0.0:
        return 0.0
    return abs(float(quantity)) * float(fill_price) / amount


def _execution_blocking_reason(intent: dict[str, Any], price_row: dict[str, Any], enabled: bool) -> str | None:
    if not enabled:
        return None
    if _truthy(price_row.get("suspended")):
        return "suspended"
    volume = price_row.get("volume")
    if volume is not None and not pd.isna(volume) and float(volume) <= 0.0:
        return "zero_volume"
    side = str(intent.get("side", "")).lower()
    if side == "buy" and _truthy(price_row.get("limit_up")):
        return "limit_up_buy_blocked"
    if side == "sell" and _truthy(price_row.get("limit_down")):
        return "limit_down_sell_blocked"
    return None


def _truthy(value: Any) -> bool:
    if value is None or pd.isna(value):
        return False
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "y", "on"}
    return bool(value)


def _apply_drawdown_guard(
    intents: list[dict[str, Any]],
    signal_date: Any,
    guard_remaining: int,
) -> tuple[list[dict[str, Any]], int, dict[str, Any] | None]:
    if guard_remaining <= 0:
        return intents, guard_remaining, None
    allowed = [intent for intent in intents if intent["side"] != "buy"]
    blocked = len(intents) - len(allowed)
    event = None
    if blocked:
        event = {
            "event_type": "drawdown_guard_blocked_buys",
            "date": signal_date,
            "blocked_buy_intents": blocked,
            "cooldown_remaining": guard_remaining,
        }
    return allowed, max(guard_remaining - 1, 0), event


def _update_drawdown_guard(
    equity_row: dict[str, Any],
    peak_equity: float,
    guard_remaining: int,
    config: PaperSimulationConfig,
) -> tuple[float, int, dict[str, Any] | None]:
    equity = float(equity_row["equity"])
    peak = max(peak_equity, equity)
    if config.max_drawdown_guard is None or peak <= 0.0:
        return peak, guard_remaining, None
    drawdown = equity / peak - 1.0
    if drawdown >= -abs(config.max_drawdown_guard) or guard_remaining > 0:
        return peak, guard_remaining, None
    cooldown = max(1, int(config.guard_cooldown_periods))
    return peak, cooldown, {
        "event_type": "drawdown_guard_triggered",
        "date": equity_row["date"],
        "equity": equity,
        "peak_equity": peak,
        "drawdown": drawdown,
        "cooldown_remaining": cooldown,
        "blocked_buy_intents": 0,
    }


def _fill_price(base_price: float, signed_quantity: float, slippage_bps: float) -> float:
    direction = 1.0 if signed_quantity > 0.0 else -1.0
    return base_price * (1.0 + direction * slippage_bps / 10000.0)


def _lot_size_for_market(market: str) -> float:
    return 100.0 if market.upper() in {"CN", "CN_ETF"} else 1.0


def _round_signed_quantity_to_lot(signed_quantity: float, lot_size: float) -> float:
    if lot_size <= 1.0:
        return signed_quantity
    direction = 1.0 if signed_quantity > 0.0 else -1.0
    lots = math.floor(abs(signed_quantity) / lot_size)
    return direction * lots * lot_size


def _apply_fills(positions: dict[str, float], cash: float, fills: list[dict[str, Any]]) -> float:
    for fill in fills:
        signed_quantity = float(fill["signed_quantity"])
        asset_id = str(fill["asset_id"])
        positions[asset_id] = positions.get(asset_id, 0.0) + signed_quantity
        if abs(positions[asset_id]) < 1e-12:
            positions.pop(asset_id)
        cash += float(fill["notional"]) - float(fill["fee"]) if signed_quantity < 0.0 else -(float(fill["notional"]) + float(fill["fee"]))
    return cash


def _equity_row(date: Any, cash: float, positions: dict[str, float], prices: pd.DataFrame) -> dict[str, Any]:
    equity = _portfolio_value(cash, positions, prices)
    gross_exposure = 0.0 if equity <= 0.0 else (equity - cash) / equity
    return {
        "date": date,
        "cash": cash,
        "equity": equity,
        "gross_exposure": gross_exposure,
        "position_count": len(positions),
    }


def _equity_curve(rows: list[dict[str, Any]]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame(columns=["date", "cash", "equity", "gross_exposure", "position_count", "period_return"])
    frame = pd.DataFrame(rows).sort_values("date").reset_index(drop=True)
    frame["period_return"] = frame["equity"].pct_change().fillna(0.0)
    return frame


def _metrics(
    equity_curve: pd.DataFrame,
    cash: float,
    positions: dict[str, float],
    bars: pd.DataFrame,
    config: PaperSimulationConfig,
    guard_events: list[dict[str, Any]],
    execution_events: list[dict[str, Any]],
    fills: list[dict[str, Any]],
) -> dict[str, float]:
    periods = _resolve_periods_per_year(config)
    summary = summarize_returns(equity_curve["period_return"] if not equity_curve.empty else pd.Series(dtype=float), periods_per_year=periods)
    starting_equity = float(equity_curve.iloc[0]["equity"]) if not equity_curve.empty else float(config.initial_cash)
    ending_equity = float(equity_curve.iloc[-1]["equity"]) if not equity_curve.empty else float(config.initial_cash)
    total_return = 0.0 if starting_equity <= 0.0 else ending_equity / starting_equity - 1.0
    summary.update(
        {
            "starting_cash": float(config.initial_cash),
            "starting_equity": starting_equity,
            "ending_cash": float(cash),
            "ending_equity": ending_equity,
            "total_return": total_return,
            "cash_return": total_return,
            "open_positions": float(len(positions)),
            "max_equity_drawdown": max_drawdown(equity_curve["equity"]) if not equity_curve.empty else 0.0,
            "guard_event_count": float(len(guard_events)),
            "execution_block_event_count": float(len(execution_events)),
            "capacity_limited_fills": float(sum(1 for fill in fills if fill.get("capacity_limited"))),
            "max_participation_rate": max((float(fill.get("participation_rate", 0.0)) for fill in fills), default=0.0),
            "market_impact_fee": sum(float(fill.get("market_impact_fee", 0.0)) for fill in fills),
        }
    )
    return summary


def _config_dict(config: PaperSimulationConfig) -> dict[str, Any]:
    data = asdict(config)
    data["factor_windows"] = list(config.factor_windows)
    data["periods_per_year"] = _resolve_periods_per_year(config)
    data["output_dir"] = str(config.output_dir) if config.output_dir is not None else None
    return data


def _resolve_periods_per_year(config: PaperSimulationConfig) -> float:
    if config.periods_per_year is not None:
        return config.periods_per_year
    base_periods = 365 if config.market.upper() == "CRYPTO" else 252
    return base_periods / float(max(config.rebalance_interval, 1))


def _records(frame: pd.DataFrame) -> list[dict[str, Any]]:
    if frame.empty:
        return []
    return frame.to_dict(orient="records")


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _sanitize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if isinstance(value, tuple):
        return [_sanitize(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if hasattr(value, "isoformat") and value.__class__.__module__ == "datetime":
        return value.isoformat()
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    return value
