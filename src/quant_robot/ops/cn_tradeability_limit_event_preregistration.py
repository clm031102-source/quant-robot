from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Any, Iterable

from quant_robot.ops.public_reference_multi_family_preregistration import DEFAULT_CAPACITY_FILTERS


STAGE = "cn_tradeability_limit_event_preregistration"
SOURCE_AUDIT = "docs/research/cn_stock_price_volume_shock_reversal_neutral_prescreen_round158_2026-06-23.md"
NEGATIVE_EVIDENCE_AUDIT = SOURCE_AUDIT
NEXT_REQUIRED_GATE = "round160_cn_tradeability_limit_event_proxy_prescreen"
SOURCE_EVIDENCE_STATUS = "tradeability_limit_event_hypothesis_after_round158_rotation"
SAFETY = "Research-to-review only. No broker connection, no account reads, no order placement, no live trading."
PUBLIC_REFERENCE_PROJECTS = (
    "tushare_limit_list",
    "cn_stock_tradeability_gate",
    "limit_up_down_microstructure",
    "alphalens",
    "vectorbt",
)
DEFAULT_REQUIRED_CONTROLS = (
    "true_limit_status_audit",
    "cn_stock_tradeability_gate",
    "st_suspension_new_listing_delist_board_filter",
    "board_aware_limit_thresholds",
    "execution_lag_1",
)


@dataclass(frozen=True)
class CNTradeabilityLimitEventCandidateSpec:
    factor_name: str
    family: str
    formula_template: str
    direction: str
    windows: tuple[int, ...]
    required_fields: tuple[str, ...]
    economic_rationale: str
    public_reference_tags: tuple[str, ...]
    expected_failure_modes: tuple[str, ...]
    required_controls: tuple[str, ...] = DEFAULT_REQUIRED_CONTROLS
    true_limit_status_audit_required: bool = True
    tradeability_controls_required: bool = True
    source_evidence_status: str = SOURCE_EVIDENCE_STATUS
    portfolio_backtest_allowed: bool = False
    promotion_allowed: bool = False


def default_cn_tradeability_limit_event_specs() -> list[CNTradeabilityLimitEventCandidateSpec]:
    return [
        CNTradeabilityLimitEventCandidateSpec(
            factor_name="limit_down_relief_reversal_liquid_1_5",
            family="limit_down_recovery",
            formula_template="0.40*cs_z(limit_down_like_lag1*(1-limit_down_like_0))+0.30*cs_z(-ret_5)+0.30*cs_z(log_adv20_amount)",
            direction="higher_is_better",
            windows=(1, 5, 20),
            required_fields=("open", "high", "low", "close", "amount", "volume"),
            economic_rationale="Tests whether names that escape a recent limit-down-like state recover after forced-selling pressure relaxes, while keeping liquidity positive.",
            public_reference_tags=("limit_down", "tradeability_gate", "alphalens"),
            expected_failure_modes=("true_limit_proxy_error", "bad_news_continuation", "sell_block_execution_gap"),
        ),
        CNTradeabilityLimitEventCandidateSpec(
            factor_name="near_limit_down_rebound_quality_3_10",
            family="limit_down_recovery",
            formula_template="0.35*cs_z(near_limit_down_count_3)+0.30*cs_z(non_st_tradeable_quality_10)+0.20*cs_z(log_adv20_amount)+0.15*cs_z(-realized_vol_20)",
            direction="higher_is_better",
            windows=(3, 10, 20),
            required_fields=("open", "high", "low", "close", "amount", "volume"),
            economic_rationale="Separates liquid, non-ST rebound candidates from untradeable distress after repeated near-limit-down sessions.",
            public_reference_tags=("limit_down", "rebound_quality", "tradeability_gate"),
            expected_failure_modes=("distress_trap", "st_metadata_lag", "limit_status_proxy_noise"),
        ),
        CNTradeabilityLimitEventCandidateSpec(
            factor_name="limit_up_exhaustion_avoidance_1_5",
            family="limit_up_exhaustion",
            formula_template="0.45*cs_z(limit_up_like_1)+0.25*cs_z(close_unseal_proxy_1)+0.20*cs_z(turnover_spike_5)+0.10*cs_z(-log_adv20_amount)",
            direction="lower_is_better",
            windows=(1, 5, 20),
            required_fields=("open", "high", "low", "close", "amount", "volume"),
            economic_rationale="Flags one-day limit-up-like exhaustion as a short-horizon avoidance signal rather than chasing unbuyable strength.",
            public_reference_tags=("limit_up", "failed_seal", "vectorbt"),
            expected_failure_modes=("continuation_after_policy_news", "buy_block_proxy_error", "microcap_tail"),
        ),
        CNTradeabilityLimitEventCandidateSpec(
            factor_name="failed_limit_up_reversal_1_5",
            family="limit_up_failure",
            formula_template="0.40*cs_z(intraday_limit_up_failure_proxy_1)+0.30*cs_z(weak_close_location_1)+0.20*cs_z(turnover_spike_5)+0.10*cs_z(log_adv20_amount)",
            direction="higher_is_worse",
            windows=(1, 5, 20),
            required_fields=("open", "high", "low", "close", "amount", "volume"),
            economic_rationale="Failed sealing near the upper limit can reveal distribution pressure; this is treated as an avoidance/exclusion candidate first.",
            public_reference_tags=("failed_limit_up", "close_location", "alphalens"),
            expected_failure_modes=("intraday_proxy_insufficient", "same_day_alignment_error", "event_contamination"),
        ),
        CNTradeabilityLimitEventCandidateSpec(
            factor_name="limit_event_cooling_momentum_5_20",
            family="post_limit_cooling",
            formula_template="0.35*cs_z(post_limit_cooling_days_5)+0.30*cs_z(ret_20_skip_5)+0.20*cs_z(log_adv20_amount)+0.15*cs_z(-realized_vol_20)",
            direction="higher_is_better",
            windows=(5, 20),
            required_fields=("open", "high", "low", "close", "amount", "volume"),
            economic_rationale="Tests whether cooling-off after a limit event preserves medium-horizon information while avoiding immediate non-tradability.",
            public_reference_tags=("limit_event", "cooling_period", "vectorbt"),
            expected_failure_modes=("momentum_reference_redundancy", "short_sample_regime_dependency", "tradeability_decay"),
        ),
        CNTradeabilityLimitEventCandidateSpec(
            factor_name="post_limit_down_nonst_recovery_5_20",
            family="nonst_limit_down_recovery",
            formula_template="0.35*cs_z(post_limit_down_recovery_5)+0.30*cs_z(non_st_flag)+0.20*cs_z(log_adv20_amount)+0.15*cs_z(-downside_vol_20)",
            direction="higher_is_better",
            windows=(5, 20),
            required_fields=("open", "high", "low", "close", "amount", "volume"),
            economic_rationale="Focuses on non-ST recovery after limit-down-like pressure, explicitly blocking the old mistake of buying delisting-risk distress.",
            public_reference_tags=("limit_down", "non_st", "tradeability_gate"),
            expected_failure_modes=("snapshot_metadata_bias", "delist_history_missing", "bad_news_continuation"),
        ),
        CNTradeabilityLimitEventCandidateSpec(
            factor_name="limit_pressure_asymmetry_reversal_5_20",
            family="limit_pressure_asymmetry",
            formula_template="0.45*cs_z(limit_down_pressure_5-limit_up_pressure_5)+0.30*cs_z(-ret_5)+0.25*cs_z(log_adv20_amount)",
            direction="higher_is_better",
            windows=(5, 20),
            required_fields=("open", "high", "low", "close", "amount", "volume"),
            economic_rationale="Measures asymmetric downside limit pressure as a forced-selling proxy, then requires liquidity and true-limit audit before any portfolio use.",
            public_reference_tags=("limit_pressure", "asymmetry", "alphalens"),
            expected_failure_modes=("one_sided_bear_regime", "limit_proxy_bias", "industry_crash_exposure"),
        ),
        CNTradeabilityLimitEventCandidateSpec(
            factor_name="new_high_near_limit_failure_reversal_20",
            family="new_high_limit_failure",
            formula_template="0.35*cs_z(new_high_20)+0.35*cs_z(near_limit_up_failure_proxy_1)+0.20*cs_z(turnover_spike_5)+0.10*cs_z(log_adv20_amount)",
            direction="higher_is_worse",
            windows=(1, 5, 20),
            required_fields=("open", "high", "low", "close", "amount", "volume"),
            economic_rationale="Tests whether failed upper-limit behavior at a 20-day high is distribution rather than breakout strength.",
            public_reference_tags=("new_high_failure", "limit_up_failure", "vectorbt"),
            expected_failure_modes=("strong_trend_false_negative", "intraday_proxy_noise", "event_news_contamination"),
        ),
    ]


def build_cn_tradeability_limit_event_preregistration(
    *,
    min_candidates: int = 8,
    min_families: int = 5,
    candidate_specs: Iterable[CNTradeabilityLimitEventCandidateSpec] | None = None,
) -> dict[str, Any]:
    specs = list(candidate_specs or default_cn_tradeability_limit_event_specs())
    candidates = [_candidate_payload(spec) for spec in specs]
    blockers = _blockers(candidates, min_candidates=min_candidates, min_families=min_families)
    result: dict[str, Any] = {
        "stage": STAGE,
        "generated_at": date.today().isoformat(),
        "summary": {
            "passes": not blockers,
            "blockers": blockers,
            "candidate_count": len(candidates),
            "min_candidates": int(min_candidates),
            "family_count": len({candidate["family"] for candidate in candidates}),
            "min_families": int(min_families),
            "unique_candidate_names": len({candidate["factor_name"] for candidate in candidates}),
            "rsrs_candidate_count": _mention_count(candidates, "rsrs"),
            "moneyflow_candidate_count": _mention_count(candidates, "moneyflow"),
            "price_volume_shock_candidate_count": _mention_count(candidates, "price_volume_shock"),
            "true_limit_status_audit_required_candidates": sum(
                1 for candidate in candidates if candidate["true_limit_status_audit_required"]
            ),
            "tradeability_controls_required_candidates": sum(
                1 for candidate in candidates if candidate["tradeability_controls_required"]
            ),
            "portfolio_backtest_allowed_candidates": sum(
                1 for candidate in candidates if candidate["portfolio_backtest_allowed"]
            ),
            "promotion_allowed_candidates": sum(1 for candidate in candidates if candidate["promotion_allowed"]),
            "next_required_gate": NEXT_REQUIRED_GATE,
            "next_direction": NEXT_REQUIRED_GATE,
        },
        "rotation_context": {
            "source_audit": SOURCE_AUDIT,
            "negative_evidence_audit": NEGATIVE_EVIDENCE_AUDIT,
            "source_round": "round158_price_volume_shock_reversal_neutral_prescreen",
            "rotation_reason": "Round158 produced zero residual research leads; Round159 rotates to a structurally different A-share tradeability and limit-event mechanism.",
            "hibernated_families": [
                "price_volume_shock_reversal_parameter_tuning",
                "moneyflow_only_selection",
                "public_rsrs_failure_reversal",
            ],
            "next_direction": NEXT_REQUIRED_GATE,
        },
        "public_reference_review": {
            "projects_reviewed": list(PUBLIC_REFERENCE_PROJECTS),
            "method": "Use public limit-up/down and tradeability microstructure ideas only as hypotheses. Official limit/suspend status must be audited before any portfolio grid.",
        },
        "capacity_policy": {
            "filters": DEFAULT_CAPACITY_FILTERS,
            "liquidity_kept_positive": True,
            "reason": "Limit-event signals can drift into non-tradable tails, so liquidity and execution feasibility are mandatory gates.",
        },
        "evaluation_gate": {
            "next_required_gate": NEXT_REQUIRED_GATE,
            "required_metrics": [
                "true_limit_status_coverage",
                "suspension_st_new_listing_delist_board_filter_coverage",
                "mean_spearman_ic",
                "icir",
                "ic_t_stat",
                "industry_neutral_ic",
                "style_residual_ic",
                "yearly_residual_stability",
                "reference_correlation_dedup",
                "factor_turnover",
                "fdr_multiple_testing",
                "tradeability_blocked_signal_rate",
                "cost_capacity_walk_forward_later_gate",
            ],
            "portfolio_backtest_allowed_after": "true_limit_proxy_prescreen_and_tradeability_audit_only",
            "multiple_testing_accounting_required": True,
            "final_holdout_available_for_tuning": False,
        },
        "promotion_policy": {
            "promotion_allowed": False,
            "portfolio_backtest_allowed_before_proxy_prescreen": False,
            "requires_true_limit_status_audit": True,
            "requires_cn_stock_tradeability_gate": True,
            "requires_long_cycle_replay": True,
            "requires_walk_forward": True,
            "requires_cost_capacity_gate": True,
            "requires_regime_coverage": True,
            "requires_multiple_testing_accounting": True,
            "requires_reference_dedup": True,
            "requires_event_contamination_audit": True,
        },
        "candidates": candidates,
        "live_boundary_allowed": False,
        "safety": SAFETY,
    }
    result["markdown"] = render_cn_tradeability_limit_event_preregistration_markdown(result)
    return result


def write_cn_tradeability_limit_event_preregistration(output_dir: str | Path, result: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "cn_tradeability_limit_event_preregistration.json").write_text(
        json.dumps(_sanitize(result), indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "cn_tradeability_limit_event_preregistration.md").write_text(
        render_cn_tradeability_limit_event_preregistration_markdown(result),
        encoding="utf-8",
    )
    _write_csv(output_path / "cn_tradeability_limit_event_candidates.csv", _candidate_csv_rows(result))


def render_cn_tradeability_limit_event_preregistration_markdown(result: dict[str, Any]) -> str:
    summary = result.get("summary", {})
    rotation = result.get("rotation_context", {})
    lines = [
        "# CN Tradeability Limit Event Preregistration Round159",
        "",
        f"- Stage: {result.get('stage', STAGE)}",
        f"- Passes: {summary.get('passes', False)}",
        f"- Candidates: {summary.get('candidate_count', 0)}",
        f"- Families: {summary.get('family_count', 0)}",
        f"- RSRS candidates: {summary.get('rsrs_candidate_count', 0)}",
        f"- Moneyflow candidates: {summary.get('moneyflow_candidate_count', 0)}",
        f"- Price-volume-shock candidates: {summary.get('price_volume_shock_candidate_count', 0)}",
        f"- True limit audit required candidates: {summary.get('true_limit_status_audit_required_candidates', 0)}",
        f"- Tradeability controls required candidates: {summary.get('tradeability_controls_required_candidates', 0)}",
        f"- Blockers: {', '.join(summary.get('blockers', []) or []) or 'none'}",
        f"- Source audit: {rotation.get('source_audit', SOURCE_AUDIT)}",
        f"- Negative evidence audit: {rotation.get('negative_evidence_audit', NEGATIVE_EVIDENCE_AUDIT)}",
        f"- Next required gate: {summary.get('next_required_gate', NEXT_REQUIRED_GATE)}",
        f"- Promotion allowed: {result.get('promotion_policy', {}).get('promotion_allowed', False)}",
        f"- Portfolio before proxy prescreen: {result.get('promotion_policy', {}).get('portfolio_backtest_allowed_before_proxy_prescreen', False)}",
        f"- Live boundary allowed: {result.get('live_boundary_allowed', False)}",
        f"- Safety: {result.get('safety', SAFETY)}",
        "",
        "## Rotation Context",
        "",
        f"- Reason: {rotation.get('rotation_reason', '')}",
        f"- Hibernated families: {', '.join(rotation.get('hibernated_families', []) or [])}",
        "",
        "## Candidates",
        "",
    ]
    for candidate in result.get("candidates", []):
        lines.extend(
            [
                f"### {candidate.get('factor_name')}",
                "",
                f"- Family: {candidate.get('family')}",
                f"- Direction: {candidate.get('direction')}",
                f"- Windows: {', '.join(str(item) for item in candidate.get('windows', []))}",
                f"- Formula template: `{candidate.get('formula_template')}`",
                f"- Required fields: {', '.join(candidate.get('required_fields', []))}",
                f"- Required controls: {', '.join(candidate.get('required_controls', []))}",
                f"- Rationale: {candidate.get('economic_rationale')}",
                f"- Public references: {', '.join(candidate.get('public_reference_tags', []))}",
                f"- Expected failure modes: {', '.join(candidate.get('expected_failure_modes', []))}",
                "",
            ]
        )
    return "\n".join(lines)


def _candidate_payload(spec: CNTradeabilityLimitEventCandidateSpec) -> dict[str, Any]:
    payload = asdict(spec)
    payload.update(
        {
            "market": "CN",
            "asset_type": "stock",
            "source_audit": SOURCE_AUDIT,
            "next_required_gate": NEXT_REQUIRED_GATE,
        }
    )
    return payload


def _blockers(candidates: list[dict[str, Any]], *, min_candidates: int, min_families: int) -> list[str]:
    blockers: list[str] = []
    if len(candidates) < min_candidates:
        blockers.append("candidate_count_below_minimum")
    if len({candidate["family"] for candidate in candidates}) < min_families:
        blockers.append("family_breadth_below_minimum")
    if len({candidate["factor_name"] for candidate in candidates}) != len(candidates):
        blockers.append("duplicate_candidate_names")
    if _mention_count(candidates, "rsrs"):
        blockers.append("rsrs_family_reentry_blocked")
    if _mention_count(candidates, "moneyflow"):
        blockers.append("moneyflow_family_reentry_blocked")
    if _mention_count(candidates, "price_volume_shock"):
        blockers.append("price_volume_shock_reentry_blocked")
    if any(not candidate.get("true_limit_status_audit_required") for candidate in candidates):
        blockers.append("true_limit_status_audit_not_required_for_all_candidates")
    if any(not candidate.get("tradeability_controls_required") for candidate in candidates):
        blockers.append("tradeability_controls_not_required_for_all_candidates")
    if any(candidate.get("portfolio_backtest_allowed") for candidate in candidates):
        blockers.append("portfolio_backtest_allowed_before_proxy_prescreen")
    if any(candidate.get("promotion_allowed") for candidate in candidates):
        blockers.append("promotion_allowed_before_validation")
    return blockers


def _mention_count(candidates: list[dict[str, Any]], needle: str) -> int:
    return sum(1 for candidate in candidates if _candidate_mentions(candidate, needle))


def _candidate_mentions(candidate: dict[str, Any], needle: str) -> bool:
    searchable = {
        "factor_name": candidate.get("factor_name", ""),
        "family": candidate.get("family", ""),
        "formula_template": candidate.get("formula_template", ""),
        "public_reference_tags": candidate.get("public_reference_tags", []),
    }
    haystack = json.dumps(searchable, ensure_ascii=True).lower()
    return needle.lower() in haystack


def _candidate_csv_rows(result: dict[str, Any]) -> list[dict[str, Any]]:
    rows = []
    for candidate in result.get("candidates", []):
        rows.append(
            {
                "factor_name": candidate.get("factor_name"),
                "family": candidate.get("family"),
                "direction": candidate.get("direction"),
                "windows": "|".join(str(item) for item in candidate.get("windows", [])),
                "required_fields": "|".join(candidate.get("required_fields", [])),
                "required_controls": "|".join(candidate.get("required_controls", [])),
                "true_limit_status_audit_required": candidate.get("true_limit_status_audit_required"),
                "tradeability_controls_required": candidate.get("tradeability_controls_required"),
                "portfolio_backtest_allowed": candidate.get("portfolio_backtest_allowed"),
                "promotion_allowed": candidate.get("promotion_allowed"),
                "source_evidence_status": candidate.get("source_evidence_status"),
                "formula_template": candidate.get("formula_template"),
            }
        )
    return rows


def _write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _sanitize(item) for key, item in value.items() if key != "markdown"}
    if isinstance(value, tuple):
        return [_sanitize(item) for item in value]
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    return value
