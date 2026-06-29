from __future__ import annotations

import json
import math
from collections import defaultdict
from datetime import date
from pathlib import Path
from typing import Any, Iterable

import pandas as pd


STAGE = "phase_6_0_daily_trade_advisory"
SAFETY_NOTICE = "仅研究到模拟盘：不连接券商、不读取账户、不生成实盘委托、不自动下单。"


def select_daily_top_factor_candidates(
    leaderboard: dict[str, Any],
    runnable_factor_names: Iterable[str] | None = None,
    limit: int = 3,
    primary_market: str = "CN_ETF",
) -> list[dict[str, Any]]:
    runnable = {str(name) for name in (runnable_factor_names or []) if str(name).strip()}
    source_rows = _leaderboard_rows(leaderboard)
    selected: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in source_rows:
        if not isinstance(row, dict):
            continue
        market = str(row.get("market") or "").upper()
        factor_name = str(row.get("factor_name") or row.get("factor") or "").strip()
        if market != primary_market or not factor_name:
            continue
        if runnable and factor_name not in runnable:
            continue
        key = factor_name
        if key in seen:
            continue
        seen.add(key)
        selected.append(
            {
                "rank": _int(row.get("rank"), len(selected) + 1),
                "case_id": str(row.get("case_id") or factor_name),
                "factor_name": factor_name,
                "market": market,
                "family": row.get("family"),
                "sharpe": _float_or_none(row.get("sharpe")),
                "annualized_return": _float_or_none(row.get("annualized_return")),
                "total_return": _float_or_none(row.get("total_return")),
                "max_drawdown": _float_or_none(row.get("max_drawdown")),
                "win_rate": _float_or_none(row.get("win_rate")),
                "rank_ic": _float_or_none(row.get("rank_ic")),
                "trade_count": _float_or_none(row.get("trade_count")),
                "score_metric": row.get("score_metric"),
                "promotion_label": row.get("promotion_label"),
                "plain_conclusion": row.get("plain_conclusion"),
                "params": row.get("params") if isinstance(row.get("params"), dict) else {},
                "signalable": True,
            }
        )
        if len(selected) >= max(1, int(limit)):
            break
    return selected


def build_daily_trade_advisory_pack(
    candidates: list[dict[str, Any]],
    signal_snapshots: list[dict[str, Any]],
    run_date: str | None = None,
    portfolio_value: float = 100000.0,
    max_gross_exposure: float = 1.0,
) -> dict[str, Any]:
    signal_cards = [_signal_card(candidate, _matching_signal(candidate, signal_snapshots)) for candidate in candidates]
    combined_targets = _combined_targets(signal_cards, portfolio_value=portfolio_value, max_gross_exposure=max_gross_exposure)
    manual_plan = _manual_trade_plan(combined_targets)
    pack = {
        "stage": STAGE,
        "run_date": run_date or date.today().isoformat(),
        "safety": SAFETY_NOTICE,
        "summary": {
            "selected_factor_count": len(candidates),
            "signal_count": sum(1 for card in signal_cards if card["status"] == "signal_ready"),
            "combined_target_count": len(combined_targets),
            "manual_ticket_count": len(manual_plan),
            "manual_execution_required": True,
            "paper_simulation_recommended": True,
            "live_trading_allowed": False,
            "broker_connection_allowed": False,
            "account_read_allowed": False,
            "order_placement_allowed": False,
            "next_action": "先复核今日前三因子和目标仓位，再查看模拟盘表现；若要实盘，只能由人手工在券商端决定是否交易。",
        },
        "factors": candidates,
        "signal_cards": signal_cards,
        "combined_target_count": len(combined_targets),
        "combined_targets": combined_targets,
        "manual_trade_plan": manual_plan,
        "operator_checklist": _operator_checklist(),
        "markdown": "",
    }
    pack["markdown"] = render_daily_trade_advisory_markdown(pack)
    return _sanitize(pack)


def write_daily_trade_advisory_pack(output_dir: str | Path, pack: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "daily_trade_advisory_pack.json").write_text(
        json.dumps(pack, indent=2, sort_keys=True, ensure_ascii=False),
        encoding="utf-8",
    )
    (output_path / "daily_trade_advisory_pack.md").write_text(str(pack.get("markdown", "")), encoding="utf-8")
    pd.DataFrame(pack.get("combined_targets", [])).to_csv(output_path / "daily_trade_advisory_targets.csv", index=False)
    pd.DataFrame(pack.get("manual_trade_plan", [])).to_csv(output_path / "daily_trade_advisory_manual_plan.csv", index=False)


def render_daily_trade_advisory_markdown(pack: dict[str, Any]) -> str:
    summary = pack.get("summary", {}) if isinstance(pack.get("summary"), dict) else {}
    lines = [
        "# 今日前三因子手工交易建议",
        "",
        f"- 阶段: {pack.get('stage', STAGE)}",
        f"- 运行日期: {pack.get('run_date', '')}",
        f"- 入选因子: {summary.get('selected_factor_count', 0)}",
        f"- 可用信号: {summary.get('signal_count', 0)}",
        f"- 允许实盘自动化: {summary.get('live_trading_allowed', False)}",
        f"- 允许自动下单: {summary.get('order_placement_allowed', False)}",
        f"- 安全边界: {pack.get('safety', SAFETY_NOTICE)}",
        "",
        "## 入选因子",
        "",
    ]
    for row in pack.get("factors", []):
        if not isinstance(row, dict):
            continue
        lines.append(
            f"- #{row.get('rank', '')} {row.get('factor_name', '')} / {row.get('case_id', '')} "
            f"Sharpe={row.get('sharpe', '')} MaxDD={row.get('max_drawdown', '')}"
        )
    lines.extend(["", "## 手工计划", ""])
    plan = pack.get("manual_trade_plan", [])
    if plan:
        for row in plan:
            if isinstance(row, dict):
                lines.append(f"- {row.get('side', 'hold')} {row.get('asset_id', '')}: target_weight={row.get('target_weight', 0)}")
    else:
        lines.append("- 无手工工单")
    return "\n".join(lines) + "\n"


def _leaderboard_rows(leaderboard: dict[str, Any]) -> list[dict[str, Any]]:
    boards = leaderboard.get("leaderboards") if isinstance(leaderboard.get("leaderboards"), dict) else {}
    primary = boards.get("primary_cn_etf") if isinstance(boards.get("primary_cn_etf"), dict) else {}
    rows = primary.get("rows") if isinstance(primary.get("rows"), list) else None
    if rows is not None:
        return [row for row in rows if isinstance(row, dict)]
    top20 = leaderboard.get("top20") if isinstance(leaderboard.get("top20"), list) else []
    return [row for row in top20 if isinstance(row, dict)]


def _matching_signal(candidate: dict[str, Any], signal_snapshots: list[dict[str, Any]]) -> dict[str, Any] | None:
    factor_name = str(candidate.get("factor_name") or "")
    case_id = str(candidate.get("case_id") or "")
    for signal in signal_snapshots:
        if not isinstance(signal, dict):
            continue
        request = signal.get("request") if isinstance(signal.get("request"), dict) else {}
        signal_factor = str(signal.get("factor_name") or request.get("factor_name") or request.get("factor") or "")
        signal_case = str(signal.get("case_id") or "")
        if signal_case and signal_case == case_id:
            return signal
        if signal_factor and signal_factor == factor_name:
            return signal
    return None


def _signal_card(candidate: dict[str, Any], signal: dict[str, Any] | None) -> dict[str, Any]:
    if not signal:
        return {
            "case_id": candidate.get("case_id"),
            "factor_name": candidate.get("factor_name"),
            "status": "signal_missing",
            "signal_date": None,
            "target_count": 0,
            "targets": [],
            "rebalance_plan": [],
            "executable": False,
            "manual_note": "这个因子暂时没有生成信号快照。",
        }
    if signal.get("error"):
        return {
            "case_id": candidate.get("case_id"),
            "factor_name": candidate.get("factor_name"),
            "status": "signal_error",
            "signal_date": signal.get("signal_date"),
            "target_count": 0,
            "targets": [],
            "rebalance_plan": [],
            "executable": False,
            "error": signal.get("error"),
            "manual_note": "这个因子入选了，但信号引擎没有生成同日信号。",
        }
    targets = [row for row in signal.get("targets", []) if isinstance(row, dict)]
    rebalance = [row for row in signal.get("rebalance_plan", []) if isinstance(row, dict)]
    return {
        "case_id": candidate.get("case_id"),
        "factor_name": candidate.get("factor_name"),
        "status": "signal_ready",
        "as_of_date": signal.get("as_of_date"),
        "signal_date": signal.get("signal_date"),
        "target_count": len(targets),
        "target_gross_exposure": signal.get("target_gross_exposure"),
        "cash_weight": signal.get("cash_weight"),
        "targets": targets,
        "rebalance_plan": _force_non_executable(rebalance),
        "executable": False,
        "manual_note": "仅作为建议输入；任何手工交易前必须复核模拟盘和风险闸门。",
    }


def _force_non_executable(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    result = []
    for row in rows:
        item = dict(row)
        item["executable"] = False
        item.setdefault("safety_note", SAFETY_NOTICE)
        result.append(item)
    return result


def _combined_targets(
    signal_cards: list[dict[str, Any]],
    portfolio_value: float,
    max_gross_exposure: float,
) -> list[dict[str, Any]]:
    accum: dict[str, dict[str, Any]] = defaultdict(dict)
    ready_cards = [card for card in signal_cards if card.get("status") == "signal_ready"]
    if not ready_cards:
        return []
    divisor = float(len(ready_cards))
    for card in ready_cards:
        for target in card.get("targets", []):
            if not isinstance(target, dict):
                continue
            asset_id = str(target.get("asset_id") or "")
            if not asset_id:
                continue
            bucket = accum[asset_id]
            bucket.setdefault("asset_id", asset_id)
            bucket.setdefault("market", target.get("market") or "CN_ETF")
            bucket.setdefault("latest_price", _float_or_none(target.get("latest_price")))
            bucket.setdefault("source_factors", [])
            bucket["target_weight"] = float(bucket.get("target_weight") or 0.0) + _float(target.get("target_weight"), 0.0) / divisor
            bucket["source_factors"].append(card.get("factor_name"))
    total_weight = sum(float(row.get("target_weight") or 0.0) for row in accum.values())
    cap = max(0.0, min(float(max_gross_exposure), 1.0))
    scale = cap / total_weight if total_weight > cap and total_weight > 0.0 else 1.0
    rows = []
    for row in accum.values():
        weight = float(row.get("target_weight") or 0.0) * scale
        rows.append(
            {
                "asset_id": row["asset_id"],
                "market": row.get("market") or "CN_ETF",
                "target_weight": weight,
                "target_value": weight * float(portfolio_value),
                "latest_price": row.get("latest_price"),
                "source_factors": sorted({str(item) for item in row.get("source_factors", []) if item}),
                "executable": False,
            }
        )
    return sorted(rows, key=lambda item: (-float(item["target_weight"]), str(item["asset_id"])))


def _manual_trade_plan(combined_targets: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows = []
    for index, target in enumerate(combined_targets, start=1):
        rows.append(
            {
                "ticket_id": f"daily-top3-{index:03d}",
                "asset_id": target.get("asset_id"),
                "market": target.get("market"),
                "side": "buy_or_adjust",
                "target_weight": target.get("target_weight"),
                "target_value": target.get("target_value"),
                "source_factors": ", ".join(target.get("source_factors", [])),
                "executable": False,
                "live_order_allowed": False,
                "manual_instruction": "如需手工实盘，请先核对 ETF 代码、价格、流动性、账户现金和风险闸门，再由你本人在券商端操作；系统不会下单。",
            }
        )
    return rows


def _operator_checklist() -> list[dict[str, Any]]:
    return [
        {
            "check_id": "manual_review_required",
            "status": "required",
            "text": "人工复核今日前三因子、信号日期、目标仓位和风险闸门。",
        },
        {
            "check_id": "paper_simulation_first",
            "status": "required",
            "text": "先跑或查看本地模拟盘，不把单日信号直接等同于可实盘收益。",
        },
        {
            "check_id": "broker_side_only_by_human",
            "status": "blocked_for_automation",
            "text": "系统不连接券商、不读取账户、不自动下单；如实盘，只能由人手工在券商端操作。",
        },
    ]


def _float(value: Any, default: float = 0.0) -> float:
    number = _float_or_none(value)
    return default if number is None else number


def _float_or_none(value: Any) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _int(value: Any, default: int) -> int:
    try:
        return int(float(str(value).replace(",", "")))
    except (TypeError, ValueError):
        return default


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _sanitize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if isinstance(value, tuple):
        return [_sanitize(item) for item in value]
    if hasattr(value, "isoformat") and value.__class__.__module__ == "datetime":
        return value.isoformat()
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    return value
