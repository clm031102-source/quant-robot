from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class ETFLiquidUniversePolicy:
    min_history_days: int = 756
    recent_window_days: int = 60
    min_recent_observations: int = 40
    min_recent_amount: float = 5_000_000.0
    max_stale_price_rate: float = 0.05
    max_extreme_return_rate: float = 0.005
    extreme_return_threshold: float = 0.20
    min_selected_assets: int = 20
    required_asset_ids: tuple[str, ...] = ()


def build_etf_liquid_universe(
    bars: pd.DataFrame,
    *,
    market: str = "CN_ETF",
    start_date: str | None = None,
    end_date: str | None = None,
    policy: ETFLiquidUniversePolicy | None = None,
) -> dict[str, Any]:
    policy = policy or ETFLiquidUniversePolicy()
    frame = _filter_bars(bars, market=market, start_date=start_date, end_date=end_date)
    market_dates = sorted(frame["date"].unique())
    recent_dates = set(market_dates[-policy.recent_window_days :])
    assets = [_asset_row(asset_id, group, recent_dates, policy) for asset_id, group in frame.groupby("asset_id", sort=True)]
    selected_asset_ids = [row["asset_id"] for row in assets if not row["rejection_reasons"]]
    blockers = _blockers(selected_asset_ids, assets, policy)
    packet = {
        "stage": "cn_etf_liquid_universe_filter",
        "generated_at": date.today().isoformat(),
        "status": "cleared" if not blockers else "blocked",
        "market": market.upper(),
        "summary": {
            "rows": int(len(frame)),
            "asset_count": int(frame["asset_id"].nunique()),
            "selected_asset_count": len(selected_asset_ids),
            "date_count": len(market_dates),
            "start_date": str(min(market_dates)) if market_dates else None,
            "end_date": str(max(market_dates)) if market_dates else None,
            "recent_window_days": policy.recent_window_days,
            "recent_start_date": str(min(recent_dates)) if recent_dates else None,
            "recent_end_date": str(max(recent_dates)) if recent_dates else None,
        },
        "policy": _policy_dict(policy),
        "selected_asset_ids": selected_asset_ids,
        "assets": assets,
        "decision": {
            "universe_cleared": not blockers,
            "blockers": blockers,
        },
        "safety": "Research-to-review only. No broker connection, no account reads, no order placement, no live trading.",
        "live_boundary_allowed": False,
    }
    packet["markdown"] = render_etf_liquid_universe_markdown(packet)
    return packet


def write_etf_liquid_universe(output_dir: str | Path, packet: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    json_packet = {key: value for key, value in packet.items() if key != "markdown"}
    (output_path / "etf_liquid_universe.json").write_text(
        json.dumps(json_packet, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "etf_liquid_universe.md").write_text(str(packet.get("markdown", "")), encoding="utf-8")
    selected_asset_ids = [str(asset_id) for asset_id in packet.get("selected_asset_ids", [])]
    (output_path / "selected_asset_ids.txt").write_text("\n".join(selected_asset_ids) + ("\n" if selected_asset_ids else ""), encoding="utf-8")
    pd.DataFrame(packet.get("assets", [])).to_csv(output_path / "asset_metrics.csv", index=False)


def render_etf_liquid_universe_markdown(packet: dict[str, Any]) -> str:
    summary = packet.get("summary", {}) if isinstance(packet.get("summary"), dict) else {}
    decision = packet.get("decision", {}) if isinstance(packet.get("decision"), dict) else {}
    blockers = decision.get("blockers", []) if isinstance(decision.get("blockers"), list) else []
    lines = [
        "# CN ETF Liquid Universe Filter",
        "",
        f"- Status: {packet.get('status', 'unknown')}",
        f"- Market: {packet.get('market', 'unknown')}",
        f"- Date range: {summary.get('start_date')} to {summary.get('end_date')}",
        f"- Asset count: {summary.get('asset_count')}",
        f"- Selected asset count: {summary.get('selected_asset_count')}",
        f"- Date count: {summary.get('date_count')}",
        f"- Live boundary allowed: {packet.get('live_boundary_allowed', False)}",
        "",
        "## Blockers",
        "",
    ]
    lines.extend(f"- {item}" for item in blockers) if blockers else lines.append("- none")
    lines.extend(["", f"Safety: {packet.get('safety', '')}", ""])
    return "\n".join(lines)


def _filter_bars(
    bars: pd.DataFrame,
    *,
    market: str,
    start_date: str | None,
    end_date: str | None,
) -> pd.DataFrame:
    _require_columns(bars, ["date", "asset_id", "market", "adj_close", "volume"])
    frame = bars.copy()
    frame["date"] = pd.to_datetime(frame["date"]).dt.date
    frame = frame[frame["market"].astype(str).str.upper() == market.upper()]
    if start_date:
        frame = frame[frame["date"] >= pd.to_datetime(start_date).date()]
    if end_date:
        frame = frame[frame["date"] <= pd.to_datetime(end_date).date()]
    if frame.empty:
        raise ValueError(f"No {market.upper()} bars available for ETF liquid universe filter")
    frame["adj_close"] = pd.to_numeric(frame["adj_close"], errors="coerce")
    frame["volume"] = pd.to_numeric(frame["volume"], errors="coerce")
    if "amount" in frame.columns:
        frame["amount"] = pd.to_numeric(frame["amount"], errors="coerce")
    else:
        frame["amount"] = frame["adj_close"] * frame["volume"]
    return frame.sort_values(["asset_id", "date"]).reset_index(drop=True)


def _asset_row(
    asset_id: str,
    group: pd.DataFrame,
    recent_dates: set[Any],
    policy: ETFLiquidUniversePolicy,
) -> dict[str, Any]:
    source = group.sort_values("date").copy()
    dates = source["date"].unique()
    recent = source[source["date"].isin(recent_dates)]
    prices = pd.to_numeric(source["adj_close"], errors="coerce")
    returns = prices.pct_change().replace([float("inf"), float("-inf")], pd.NA)
    history_days = int(len(dates))
    recent_observations = int(recent["date"].nunique())
    median_recent_amount = _safe_float(pd.to_numeric(recent["amount"], errors="coerce").median())
    transition_count = max(len(prices.dropna()) - 1, 0)
    stale_price_count = int((prices.diff().abs() <= 1e-12).sum()) if transition_count else 0
    extreme_return_count = int((returns.abs() > policy.extreme_return_threshold).sum()) if transition_count else 0
    stale_price_rate = float(stale_price_count) / float(transition_count) if transition_count else 0.0
    extreme_return_rate = float(extreme_return_count) / float(transition_count) if transition_count else 0.0
    rejection_reasons = _rejection_reasons(
        history_days=history_days,
        recent_observations=recent_observations,
        median_recent_amount=median_recent_amount,
        stale_price_rate=stale_price_rate,
        extreme_return_rate=extreme_return_rate,
        policy=policy,
    )
    return {
        "asset_id": str(asset_id),
        "symbol": str(source["symbol"].iloc[0]) if "symbol" in source.columns and len(source) else str(asset_id),
        "start_date": str(source["date"].min()) if len(source) else None,
        "end_date": str(source["date"].max()) if len(source) else None,
        "history_days": history_days,
        "recent_observations": recent_observations,
        "median_recent_amount": median_recent_amount,
        "stale_price_count": stale_price_count,
        "stale_price_rate": stale_price_rate,
        "extreme_return_count": extreme_return_count,
        "extreme_return_rate": extreme_return_rate,
        "rejection_reasons": rejection_reasons,
        "selected": not rejection_reasons,
    }


def _rejection_reasons(
    *,
    history_days: int,
    recent_observations: int,
    median_recent_amount: float,
    stale_price_rate: float,
    extreme_return_rate: float,
    policy: ETFLiquidUniversePolicy,
) -> list[str]:
    reasons: list[str] = []
    if history_days < policy.min_history_days:
        reasons.append("history_days_below_minimum")
    if recent_observations < policy.min_recent_observations:
        reasons.append("recent_observations_below_minimum")
    if median_recent_amount < policy.min_recent_amount:
        reasons.append("recent_amount_below_minimum")
    if stale_price_rate > policy.max_stale_price_rate:
        reasons.append("stale_price_rate_above_limit")
    if extreme_return_rate > policy.max_extreme_return_rate:
        reasons.append("extreme_return_rate_above_limit")
    return reasons


def _blockers(
    selected_asset_ids: list[str],
    assets: list[dict[str, Any]],
    policy: ETFLiquidUniversePolicy,
) -> list[str]:
    blockers: list[str] = []
    selected = set(selected_asset_ids)
    available = {str(row["asset_id"]): row for row in assets}
    if len(selected_asset_ids) < policy.min_selected_assets:
        blockers.append("selected_asset_count_below_minimum")
    for asset_id in policy.required_asset_ids:
        if asset_id not in available:
            blockers.append(f"required_asset_missing:{asset_id}")
        elif asset_id not in selected:
            blockers.append(f"required_asset_rejected:{asset_id}")
    return blockers


def _policy_dict(policy: ETFLiquidUniversePolicy) -> dict[str, Any]:
    data = asdict(policy)
    data["required_asset_ids"] = list(policy.required_asset_ids)
    return data


def _safe_float(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    return number if pd.notna(number) else 0.0


def _require_columns(frame: pd.DataFrame, columns: list[str]) -> None:
    missing = [column for column in columns if column not in frame.columns]
    if missing:
        raise ValueError(f"ETF liquid universe filter missing columns: {', '.join(missing)}")
