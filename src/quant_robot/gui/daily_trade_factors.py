from __future__ import annotations

import json
from typing import Any


def candidate_factor_names(candidates: list[dict[str, Any]]) -> tuple[str, ...]:
    names = (str(candidate.get("factor_name") or "").strip() for candidate in candidates)
    return tuple(dict.fromkeys(name for name in names if name))


def daily_trade_factor_windows(candidates: list[dict[str, Any]]) -> tuple[int, ...]:
    windows: set[int] = set()
    for candidate in candidates:
        factor_name = str(candidate.get("factor_name") or "")
        windows.update(resolve_factor_windows(factor_name, candidate_factor_windows(candidate)))
    return tuple(sorted(windows)) or (2, 3)


def candidate_factor_windows(candidate: dict[str, Any]) -> tuple[int, ...] | None:
    params = candidate.get("params") if isinstance(candidate.get("params"), dict) else {}
    value = params.get("factor_windows") or candidate.get("factor_windows")
    if isinstance(value, list):
        return tuple(int(item) for item in value if str(item).strip())
    if isinstance(value, str) and value.strip():
        text = value.strip()
        if text.startswith("[") and text.endswith("]"):
            try:
                parsed = json.loads(text)
            except json.JSONDecodeError:
                parsed = None
            if isinstance(parsed, list):
                return tuple(int(item) for item in parsed if str(item).strip())
        cleaned = text.replace("[", "").replace("]", "")
        return tuple(int(part.strip()) for part in cleaned.split(",") if part.strip().isdigit())
    suffix = str(candidate.get("factor_name") or "").rsplit("_", 1)[-1]
    return (int(suffix),) if suffix.isdigit() else None


def resolve_factor_windows(factor_name: str, explicit: tuple[int, ...] | None) -> tuple[int, ...]:
    if explicit:
        return explicit
    suffix = factor_name.rsplit("_", 1)[-1]
    return (int(suffix),) if suffix.isdigit() else (2, 3)


def runtime_daily_trade_candidates(factor_names: list[str], market: str, limit: int) -> list[dict[str, Any]]:
    preferred = ["momentum_2", "reversal_2", "volatility_2", "liquidity_2", "volume_change_2"]
    ordered = [name for name in preferred if name in set(factor_names)]
    ordered.extend(name for name in factor_names if name not in ordered)
    rows = []
    for index, factor_name in enumerate(ordered[: max(1, int(limit))], start=1):
        rows.append(
            {
                "rank": index,
                "case_id": f"runtime_baseline_{factor_name}",
                "factor_name": factor_name,
                "market": market,
                "family": "runtime_baseline",
                "promotion_label": "可运行基线信号",
                "plain_conclusion": "排行榜里暂时没有可运行前三候选时，用内置可运行因子生成手工建议；这不是可推广盈利承诺。",
                "params": {"top_n": 2},
                "signalable": True,
                "advisory_eligible": False,
                "fallback_baseline": True,
                "manual_trade_allowed": False,
                "manual_trade_block_reason": "fallback_baseline_not_tradeable",
            }
        )
    return rows
