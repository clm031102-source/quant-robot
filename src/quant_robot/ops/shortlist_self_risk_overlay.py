from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

import numpy as np
import pandas as pd

from quant_robot.ops.shortlist_return_block_audit import (
    load_candidate_period_returns,
    summarize_return_blocks,
)


STAGE = "shortlist_self_risk_overlay"
SAFETY = "research-to-review only; no broker, account, order, or live-trading access"


@dataclass(frozen=True)
class SelfRiskPolicy:
    name: str
    description: str
    roll21_threshold: float | None = None
    roll42_threshold: float | None = None
    drawdown_threshold: float | None = None
    threshold_action: str = "half"
    secondary_drawdown_threshold: float | None = None
    secondary_action: str = "half"


DEFAULT_POLICIES: tuple[SelfRiskPolicy, ...] = (
    SelfRiskPolicy(name="baseline", description="No extra self-risk overlay"),
    SelfRiskPolicy(
        name="roll21_sum_neg_half",
        description="Half exposure when prior 21-event return sum is negative",
        roll21_threshold=0.0,
        threshold_action="half",
    ),
    SelfRiskPolicy(
        name="roll21_sum_m2_cash",
        description="Cash when prior 21-event return sum is below -2%",
        roll21_threshold=-0.02,
        threshold_action="cash",
    ),
    SelfRiskPolicy(
        name="roll42_sum_neg_half",
        description="Half exposure when prior 42-event return sum is negative",
        roll42_threshold=0.0,
        threshold_action="half",
    ),
    SelfRiskPolicy(
        name="roll42_sum_m3_half",
        description="Half exposure when prior 42-event return sum is below -3%",
        roll42_threshold=-0.03,
        threshold_action="half",
    ),
    SelfRiskPolicy(
        name="current_dd_10_half",
        description="Half exposure when prior strategy drawdown is below -10%",
        drawdown_threshold=-0.10,
        threshold_action="half",
    ),
    SelfRiskPolicy(
        name="current_dd_15_cash",
        description="Cash when prior strategy drawdown is below -15%",
        drawdown_threshold=-0.15,
        threshold_action="cash",
    ),
    SelfRiskPolicy(
        name="combo_roll21_neg_or_dd10_half",
        description="Half exposure when prior 21-event sum is negative or prior drawdown is below -10%",
        roll21_threshold=0.0,
        drawdown_threshold=-0.10,
        threshold_action="half",
    ),
    SelfRiskPolicy(
        name="combo_roll21_m2_cash_dd10_half",
        description="Cash when prior 21-event sum is below -2%; otherwise half exposure below -10% prior drawdown",
        roll21_threshold=-0.02,
        threshold_action="cash",
        secondary_drawdown_threshold=-0.10,
        secondary_action="half",
    ),
)


def build_shortlist_self_risk_overlay(
    return_sources: Mapping[str, str | Path | pd.DataFrame | Mapping[str, Any]],
    *,
    policy_names: Sequence[str] | None = None,
    return_column: str | None = None,
    date_column: str = "date",
    periods_per_year: float = 252.0 / 5.0,
    holding_period: int = 20,
) -> dict[str, Any]:
    policies = _resolve_policies(policy_names)
    rows: list[dict[str, Any]] = []
    events: dict[str, pd.DataFrame] = {}
    for base_name, source in return_sources.items():
        source_path, source_return_column, source_date_column = _normalise_source_spec(
            source,
            default_return_column=return_column,
            default_date_column=date_column,
        )
        period_returns, resolved_column = load_candidate_period_returns(
            source_path,
            return_column=source_return_column,
            date_column=source_date_column,
        )
        state = _build_prior_state(period_returns)
        for policy in policies:
            candidate_name = _candidate_name(str(base_name), policy.name)
            event_frame = _apply_policy(
                state,
                base_name=str(base_name),
                candidate_name=candidate_name,
                policy=policy,
                source_return_column=resolved_column,
            )
            metrics = summarize_return_blocks(
                event_frame[["date", "period_return"]],
                candidate_name=candidate_name,
                return_column="period_return",
                periods_per_year=periods_per_year,
                holding_period=holding_period,
            )
            row = {
                "base_name": str(base_name),
                "candidate_name": candidate_name,
                "policy": policy.name,
                "policy_description": policy.description,
                "source_return_column": resolved_column,
                "period_count": int(len(event_frame)),
                "average_self_risk_exposure": _number(event_frame["self_risk_exposure"].mean()),
                "guard_event_share": _number((event_frame["self_risk_exposure"] < 0.999999).mean()),
                "event_path": "",
            }
            row.update(
                {
                    key: metrics[key]
                    for key in (
                        "total_return",
                        "annualized_return",
                        "sharpe",
                        "overlap_autocorr_adjusted_sharpe",
                        "max_drawdown",
                        "win_rate",
                        "leave_one_year_min_annualized_return",
                        "leave_one_year_min_overlap_sharpe",
                        "best_month_log_share_of_total",
                        "blockers",
                    )
                }
            )
            rows.append(row)
            events[candidate_name] = event_frame
    rows = sorted(
        rows,
        key=lambda row: (
            bool(row["blockers"]),
            -float(row["annualized_return"]),
            -float(row["overlap_autocorr_adjusted_sharpe"]),
        ),
    )
    return {
        "stage": STAGE,
        "safety": SAFETY,
        "thresholds": {
            "return_column": return_column or "auto",
            "date_column": date_column,
            "periods_per_year": float(periods_per_year),
            "holding_period": int(holding_period),
            "policies": [policy.name for policy in policies],
        },
        "summary": {
            "base_count": int(len(return_sources)),
            "candidate_count": int(len(rows)),
            "best_candidate": rows[0]["candidate_name"] if rows else None,
        },
        "policy_definitions": [
            {
                "name": policy.name,
                "description": policy.description,
                "roll21_threshold": policy.roll21_threshold,
                "roll42_threshold": policy.roll42_threshold,
                "drawdown_threshold": policy.drawdown_threshold,
                "threshold_action": policy.threshold_action,
                "secondary_drawdown_threshold": policy.secondary_drawdown_threshold,
                "secondary_action": policy.secondary_action,
            }
            for policy in policies
        ],
        "rows": _sanitize(rows),
        "events": events,
        "promotion_policy": {
            "promotion_allowed": False,
            "reason": "Self-risk overlays are pre-simulation robustness checks; final holdout remains sealed.",
        },
    }


def write_shortlist_self_risk_overlay(output_dir: str | Path, audit: dict[str, Any]) -> None:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    rows = []
    for row in audit.get("rows", []):
        candidate_name = str(row["candidate_name"])
        event_path = output / f"{_safe_filename(candidate_name)}_events.csv"
        events = audit["events"][candidate_name]
        events.to_csv(event_path, index=False)
        row["event_path"] = str(event_path)
        row_with_path = dict(row)
        rows.append(row_with_path)
    sanitized = _sanitize({key: value for key, value in audit.items() if key != "events"})
    sanitized["rows"] = _sanitize(rows)
    (output / "shortlist_self_risk_overlay.json").write_text(
        json.dumps(sanitized, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    pd.DataFrame(sanitized["rows"]).to_csv(output / "shortlist_self_risk_overlay_summary.csv", index=False)
    pd.DataFrame(sanitized.get("policy_definitions", [])).to_csv(
        output / "shortlist_self_risk_overlay_policies.csv",
        index=False,
    )


def _build_prior_state(period_returns: pd.DataFrame) -> pd.DataFrame:
    frame = period_returns[["date", "period_return"]].copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce")
    frame["source_period_return"] = pd.to_numeric(frame["period_return"], errors="coerce").fillna(0.0)
    frame = frame.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)
    returns = frame["source_period_return"]
    prior_returns = returns.shift(1)
    frame["prior_roll21_sum"] = prior_returns.rolling(21, min_periods=1).sum().fillna(0.0)
    frame["prior_roll42_sum"] = prior_returns.rolling(42, min_periods=1).sum().fillna(0.0)
    base_equity = (1.0 + returns).cumprod()
    prior_equity = base_equity.shift(1).fillna(1.0)
    prior_peak = prior_equity.cummax().replace(0.0, np.nan)
    frame["prior_equity"] = prior_equity
    frame["prior_drawdown"] = (prior_equity / prior_peak - 1.0).fillna(0.0)
    return frame.drop(columns=["period_return"])


def _apply_policy(
    state: pd.DataFrame,
    *,
    base_name: str,
    candidate_name: str,
    policy: SelfRiskPolicy,
    source_return_column: str,
) -> pd.DataFrame:
    frame = state.copy()
    exposure = pd.Series(1.0, index=frame.index, dtype=float)
    primary_mask = _policy_mask(frame, policy)
    exposure.loc[primary_mask] = _action_exposure(policy.threshold_action)
    if policy.secondary_drawdown_threshold is not None:
        secondary_mask = frame["prior_drawdown"] < float(policy.secondary_drawdown_threshold)
        unresolved = exposure >= 0.999999
        exposure.loc[secondary_mask & unresolved] = _action_exposure(policy.secondary_action)
    frame["base_name"] = base_name
    frame["candidate_name"] = candidate_name
    frame["policy"] = policy.name
    frame["source_return_column"] = source_return_column
    frame["self_risk_exposure"] = exposure.clip(lower=0.0, upper=1.0)
    frame["period_return"] = frame["source_period_return"] * frame["self_risk_exposure"]
    frame["equity"] = (1.0 + frame["period_return"]).cumprod()
    peak = frame["equity"].cummax().replace(0.0, np.nan)
    frame["drawdown"] = (frame["equity"] / peak - 1.0).fillna(0.0)
    return frame[
        [
            "date",
            "base_name",
            "candidate_name",
            "policy",
            "source_return_column",
            "source_period_return",
            "prior_roll21_sum",
            "prior_roll42_sum",
            "prior_equity",
            "prior_drawdown",
            "self_risk_exposure",
            "period_return",
            "equity",
            "drawdown",
        ]
    ]


def _policy_mask(frame: pd.DataFrame, policy: SelfRiskPolicy) -> pd.Series:
    mask = pd.Series(False, index=frame.index)
    if policy.roll21_threshold is not None:
        mask = mask | (frame["prior_roll21_sum"] < float(policy.roll21_threshold))
    if policy.roll42_threshold is not None:
        mask = mask | (frame["prior_roll42_sum"] < float(policy.roll42_threshold))
    if policy.drawdown_threshold is not None:
        mask = mask | (frame["prior_drawdown"] < float(policy.drawdown_threshold))
    return mask


def _action_exposure(action: str) -> float:
    if action == "cash":
        return 0.0
    if action == "half":
        return 0.5
    raise ValueError(f"unsupported self-risk action: {action}")


def _resolve_policies(policy_names: Sequence[str] | None) -> tuple[SelfRiskPolicy, ...]:
    policies = {policy.name: policy for policy in DEFAULT_POLICIES}
    if not policy_names:
        return DEFAULT_POLICIES
    resolved = []
    for name in policy_names:
        if name not in policies:
            raise ValueError(f"unknown self-risk policy: {name}")
        resolved.append(policies[name])
    return tuple(resolved)


def _normalise_source_spec(
    source: str | Path | pd.DataFrame | Mapping[str, Any],
    *,
    default_return_column: str | None,
    default_date_column: str,
) -> tuple[str | Path | pd.DataFrame, str | None, str]:
    if isinstance(source, Mapping) and not isinstance(source, pd.DataFrame):
        path = source.get("path")
        if path is None:
            raise ValueError("source spec missing path")
        return (
            path,
            str(source.get("return_column")) if source.get("return_column") else default_return_column,
            str(source.get("date_column") or default_date_column),
        )
    return source, default_return_column, default_date_column


def _candidate_name(base_name: str, policy_name: str) -> str:
    if policy_name == "baseline":
        return base_name
    return f"{base_name}_self_{policy_name}"


def _safe_filename(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in value)


def _number(value: Any) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    return number if math.isfinite(number) else 0.0


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _sanitize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if isinstance(value, tuple):
        return [_sanitize(item) for item in value]
    if isinstance(value, pd.Timestamp):
        return value.date().isoformat()
    if isinstance(value, np.integer):
        return int(value)
    if isinstance(value, np.floating):
        return _number(value)
    if isinstance(value, float):
        return _number(value)
    return value
