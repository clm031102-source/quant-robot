from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd


@dataclass(frozen=True)
class PromotionGateConfig:
    walk_forward_leaderboard: Path | None = None
    experiment_leaderboard: Path | None = None
    paper_manifest: Path | None = None
    paper_manifests: tuple[Path, ...] = ()
    paper_manifest_dir: Path | None = None
    provider_status: Path | None = None
    quality_report: Path | None = None
    market_regime_coverage: Path | None = None
    output_dir: Path | None = None
    min_oos_trades: int = 20
    min_oos_sharpe: float = 0.50
    min_stability_score: float = 0.30
    min_oos_relative_return: float = 0.0
    max_oos_drawdown: float = 0.25
    min_paper_sharpe: float = 0.50
    max_paper_drawdown: float = 0.25
    require_non_fixture_data: bool = True
    allow_manual_live_review: bool = False
    dedupe_similar_candidates: bool = True
    duplicate_similarity_threshold: float = 0.98
    duplicate_min_events: int = 3
    min_walk_forward_folds: int = 1
    min_accepted_folds: int = 1
    max_ic_p_value: float | None = None
    min_positive_ic_rate: float | None = None
    required_factor_source: str | None = None
    max_adjusted_ic_p_value: float | None = None
    require_provider_ready_for_promotion: bool = False
    max_provider_status_age_days: int | None = None
    require_market_regime_coverage: bool = False


def load_promotion_gate_config(path: str | Path) -> PromotionGateConfig:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    return PromotionGateConfig(
        walk_forward_leaderboard=_optional_path(data.get("walk_forward_leaderboard")),
        experiment_leaderboard=_optional_path(data.get("experiment_leaderboard")),
        paper_manifest=_optional_path(data.get("paper_manifest")),
        paper_manifests=tuple(_optional_path(value) for value in data.get("paper_manifests", ()) if _optional_path(value) is not None),
        paper_manifest_dir=_optional_path(data.get("paper_manifest_dir")),
        provider_status=_optional_path(data.get("provider_status")),
        quality_report=_optional_path(data.get("quality_report")),
        market_regime_coverage=_optional_path(data.get("market_regime_coverage")),
        output_dir=_optional_path(data.get("output_dir")),
        min_oos_trades=int(data.get("min_oos_trades", PromotionGateConfig.min_oos_trades)),
        min_oos_sharpe=float(data.get("min_oos_sharpe", PromotionGateConfig.min_oos_sharpe)),
        min_stability_score=float(data.get("min_stability_score", PromotionGateConfig.min_stability_score)),
        min_oos_relative_return=float(data.get("min_oos_relative_return", PromotionGateConfig.min_oos_relative_return)),
        max_oos_drawdown=float(data.get("max_oos_drawdown", PromotionGateConfig.max_oos_drawdown)),
        min_paper_sharpe=float(data.get("min_paper_sharpe", PromotionGateConfig.min_paper_sharpe)),
        max_paper_drawdown=float(data.get("max_paper_drawdown", PromotionGateConfig.max_paper_drawdown)),
        require_non_fixture_data=bool(data.get("require_non_fixture_data", PromotionGateConfig.require_non_fixture_data)),
        allow_manual_live_review=bool(data.get("allow_manual_live_review", PromotionGateConfig.allow_manual_live_review)),
        dedupe_similar_candidates=bool(data.get("dedupe_similar_candidates", PromotionGateConfig.dedupe_similar_candidates)),
        duplicate_similarity_threshold=float(data.get("duplicate_similarity_threshold", PromotionGateConfig.duplicate_similarity_threshold)),
        duplicate_min_events=int(data.get("duplicate_min_events", PromotionGateConfig.duplicate_min_events)),
        min_walk_forward_folds=int(data.get("min_walk_forward_folds", PromotionGateConfig.min_walk_forward_folds)),
        min_accepted_folds=int(data.get("min_accepted_folds", PromotionGateConfig.min_accepted_folds)),
        max_ic_p_value=float(data["max_ic_p_value"]) if data.get("max_ic_p_value") is not None else None,
        min_positive_ic_rate=float(data["min_positive_ic_rate"]) if data.get("min_positive_ic_rate") is not None else None,
        required_factor_source=str(data["required_factor_source"]) if data.get("required_factor_source") else None,
        max_adjusted_ic_p_value=(
            float(data["max_adjusted_ic_p_value"]) if data.get("max_adjusted_ic_p_value") is not None else None
        ),
        require_provider_ready_for_promotion=bool(
            data.get("require_provider_ready_for_promotion", PromotionGateConfig.require_provider_ready_for_promotion)
        ),
        max_provider_status_age_days=(
            int(data["max_provider_status_age_days"]) if data.get("max_provider_status_age_days") is not None else None
        ),
        require_market_regime_coverage=bool(
            data.get("require_market_regime_coverage", PromotionGateConfig.require_market_regime_coverage)
        ),
    )


def run_promotion_gate(config: PromotionGateConfig) -> dict[str, Any]:
    if config.walk_forward_leaderboard is None:
        raise ValueError("walk_forward_leaderboard is required")
    walk_forward_rows = _read_csv_records(config.walk_forward_leaderboard)
    experiment_rows = _read_csv_records(config.experiment_leaderboard) if config.experiment_leaderboard else None
    paper_manifests = _load_paper_manifests(config)
    provider_status = _read_json(config.provider_status) if config.provider_status else None
    quality_report = _read_json(config.quality_report) if config.quality_report else None
    market_regime_coverage = _read_json(config.market_regime_coverage) if config.market_regime_coverage else None
    report = build_promotion_report(
        walk_forward_rows,
        experiment_rows=experiment_rows,
        paper_manifests=paper_manifests,
        provider_status=provider_status,
        quality_report=quality_report,
        market_regime_coverage=market_regime_coverage,
        config=config,
    )
    if config.output_dir is not None:
        write_promotion_report(config.output_dir, report)
    return report


def build_promotion_report(
    walk_forward_rows: list[dict[str, Any]],
    experiment_rows: list[dict[str, Any]] | None = None,
    paper_manifest: dict[str, Any] | None = None,
    paper_manifests: list[dict[str, Any]] | None = None,
    provider_status: dict[str, Any] | None = None,
    quality_report: dict[str, Any] | None = None,
    market_regime_coverage: dict[str, Any] | None = None,
    config: PromotionGateConfig = PromotionGateConfig(),
) -> dict[str, Any]:
    experiment_by_case = {str(row.get("case_id")): row for row in experiment_rows or []}
    paper_evidence = list(paper_manifests or [])
    if paper_manifest is not None:
        paper_evidence.append(paper_manifest)
    candidates = [
        _candidate_report(
            row,
            experiment_by_case.get(str(row.get("case_id"))),
            paper_evidence,
            provider_status,
            quality_report,
            market_regime_coverage,
            config,
        )
        for row in walk_forward_rows
    ]
    if config.dedupe_similar_candidates:
        _mark_duplicate_candidates(candidates, config)
    for candidate in candidates:
        candidate.pop("_signal_signature", None)
    candidates = sorted(candidates, key=lambda row: (_status_order(row["promotion_status"]), -_metric(row, "score"), str(row["case_id"])))
    ranked = [{**row, "promotion_rank": index + 1} for index, row in enumerate(candidates)]
    return {
        "config": _config_dict(config),
        "summary": _summary(ranked),
        "candidates": ranked,
    }


def write_promotion_report(output_dir: str | Path, report: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    candidates = report["candidates"]
    pd.DataFrame(candidates).to_csv(output_path / "promotion_report.csv", index=False)
    (output_path / "promotion_report.json").write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")


def _candidate_report(
    row: dict[str, Any],
    experiment_row: dict[str, Any] | None,
    paper_manifests: list[dict[str, Any]],
    provider_status: dict[str, Any] | None,
    quality_report: dict[str, Any] | None,
    market_regime_coverage: dict[str, Any] | None,
    config: PromotionGateConfig,
) -> dict[str, Any]:
    blocking: list[str] = []
    warnings: list[str] = []
    case_id = str(row.get("case_id", "unknown"))
    data_mode = str(row.get("data_mode", "unknown"))
    validation_status = str(row.get("validation_status", "unknown"))
    test_trades = int(_metric(row, "test_trades"))
    test_sharpe = _metric(row, "test_sharpe")
    test_relative_return = _metric(row, "test_relative_return")
    test_max_drawdown = _metric(row, "test_max_drawdown")
    stability_score = _metric(row, "stability_score")
    folds = _maybe_int(row.get("folds"))
    accepted_folds = _maybe_int(row.get("accepted_folds"))
    test_ic_p_value = _maybe_float(row.get("test_ic_p_value"))
    test_positive_ic_rate = _maybe_float(row.get("test_positive_ic_rate"))
    factor_source = _optional_text(row.get("factor_source"))
    adjusted_ic_p_value = _maybe_float(row.get("adjusted_ic_p_value"))
    passes_adjusted_ic_p_value = _maybe_bool(row.get("passes_adjusted_ic_p_value"))
    hypothesis_count = _maybe_int(row.get("hypothesis_count"))

    blocking.extend(_missing_walk_forward_metrics(row, config))
    blocking.extend(_walk_forward_evidence_reasons(folds, accepted_folds, test_ic_p_value, test_positive_ic_rate, config))
    blocking.extend(_factor_source_reasons(factor_source, config))
    blocking.extend(_adjusted_ic_evidence_reasons(adjusted_ic_p_value, passes_adjusted_ic_p_value, config))
    if validation_status != "accepted":
        blocking.append("walk_forward_not_accepted")
    if config.require_non_fixture_data and data_mode == "fixture":
        blocking.append("fixture_data_not_promotable")
    if test_trades < config.min_oos_trades:
        blocking.append("insufficient_oos_trades")
    if test_relative_return < config.min_oos_relative_return:
        blocking.append("relative_return_below_threshold")
    if test_max_drawdown < -abs(config.max_oos_drawdown):
        blocking.append("oos_drawdown_above_limit")

    quality_reasons = _quality_reasons(quality_report)
    blocking.extend(quality_reasons["blocking"])
    warnings.extend(quality_reasons["warnings"])

    blocking.extend(_market_regime_reasons(market_regime_coverage, config))

    paper_summary = _paper_summary(row, paper_manifests, config)
    blocking.extend(paper_summary["blocking"])
    warnings.extend(paper_summary["warnings"])

    providers_ready = _providers_ready(provider_status)
    provider_reasons = _provider_reasons(provider_status, providers_ready, config)
    blocking.extend(provider_reasons["blocking"])
    warnings.extend(provider_reasons["warnings"])

    research_warnings = []
    if test_sharpe < config.min_oos_sharpe:
        research_warnings.append("oos_sharpe_below_paper_threshold")
    if stability_score < config.min_stability_score:
        research_warnings.append("stability_score_below_paper_threshold")
    if paper_summary["paper_present"] and paper_summary["paper_sharpe"] < config.min_paper_sharpe:
        research_warnings.append("paper_sharpe_below_threshold")
    warnings.extend(research_warnings)

    if blocking:
        promotion_status = "blocked"
    elif research_warnings or not paper_summary["paper_present"]:
        promotion_status = "research_only"
    elif config.allow_manual_live_review and providers_ready:
        promotion_status = "manual_live_review"
    else:
        promotion_status = "paper_ready"

    return _sanitize(
        {
            "case_id": case_id,
            "market": row.get("market"),
            "factor_source": factor_source,
            "factor_name": row.get("factor_name"),
            "top_n": _maybe_int(row.get("top_n")),
            "cost_bps": _maybe_float(row.get("cost_bps")),
            "data_mode": data_mode,
            "promotion_status": promotion_status,
            "score": _score(row, paper_summary, blocking, config),
            "blocking_reasons": blocking,
            "warnings": _dedupe(warnings),
            "walk_forward": {
                "validation_status": validation_status,
                "test_trades": test_trades,
                "test_sharpe": test_sharpe,
                "test_relative_return": test_relative_return,
                "test_max_drawdown": test_max_drawdown,
                "stability_score": stability_score,
                "folds": folds,
                "accepted_folds": accepted_folds,
                "test_ic_p_value": test_ic_p_value,
                "test_positive_ic_rate": test_positive_ic_rate,
                "factor_source": factor_source,
                "hypothesis_count": hypothesis_count,
                "adjusted_ic_p_value": adjusted_ic_p_value,
                "passes_adjusted_ic_p_value": passes_adjusted_ic_p_value,
            },
            "experiment": _experiment_summary(experiment_row),
            "paper": {
                "present": paper_summary["paper_present"],
                "matched": paper_summary["paper_matched"],
                "manifest_path": paper_summary["paper_manifest_path"],
                "risk_profile_id": paper_summary["paper_risk_profile_id"],
                "sharpe": paper_summary["paper_sharpe"],
                "total_return": paper_summary["paper_total_return"],
                "max_drawdown": paper_summary["paper_max_drawdown"],
            },
            "market_regime_coverage": _market_regime_summary(market_regime_coverage),
            "duplicate_of": None,
            "duplicate_similarity": 0.0,
            "_signal_signature": sorted(paper_summary["signal_signature"]),
        }
    )


def _paper_summary(row: dict[str, Any], paper_manifests: list[dict[str, Any]], config: PromotionGateConfig) -> dict[str, Any]:
    summary: dict[str, Any] = {
        "paper_present": bool(paper_manifests),
        "paper_matched": False,
        "paper_manifest_path": None,
        "paper_risk_profile_id": None,
        "paper_sharpe": 0.0,
        "paper_total_return": 0.0,
        "paper_max_drawdown": 0.0,
        "signal_signature": set(),
        "blocking": [],
        "warnings": [],
    }
    if not paper_manifests:
        summary["warnings"].append("paper_simulation_missing")
        return summary
    paper_manifest = _matching_paper_manifest(row, paper_manifests)
    if paper_manifest is None:
        summary["warnings"].append("paper_simulation_does_not_match_candidate")
        return summary
    if not _paper_matches(row, paper_manifest):
        summary["warnings"].append("paper_simulation_does_not_match_candidate")
        return summary
    metrics = paper_manifest.get("metrics", {})
    if not isinstance(metrics, dict):
        metrics = {}
    summary["paper_matched"] = True
    summary["paper_manifest_path"] = paper_manifest.get("manifest_path")
    request = paper_manifest.get("request", {})
    summary["paper_risk_profile_id"] = request.get("risk_profile_id") if isinstance(request, dict) else None
    summary["signal_signature"] = _paper_signal_signature(summary["paper_manifest_path"])
    summary["paper_sharpe"] = _metric(metrics, "sharpe")
    summary["paper_total_return"] = _metric(metrics, "total_return")
    summary["paper_max_drawdown"] = _paper_drawdown(metrics)
    if str(paper_manifest.get("data_mode", "unknown")) == "fixture" and config.require_non_fixture_data:
        summary["blocking"].append("paper_fixture_data_not_promotable")
    if summary["paper_max_drawdown"] < -abs(config.max_paper_drawdown):
        summary["blocking"].append("paper_drawdown_above_limit")
    if summary["paper_total_return"] <= 0.0:
        summary["warnings"].append("paper_total_return_not_positive")
    return summary


def _mark_duplicate_candidates(candidates: list[dict[str, Any]], config: PromotionGateConfig) -> None:
    representatives: list[dict[str, Any]] = []
    ranked = sorted(enumerate(candidates), key=lambda item: (_status_order(item[1]["promotion_status"]), -_metric(item[1], "score"), item[0], str(item[1]["case_id"])))
    for _, candidate in ranked:
        if candidate["promotion_status"] == "blocked":
            continue
        signature = set(candidate.get("_signal_signature") or [])
        if len(signature) < config.duplicate_min_events:
            representatives.append(candidate)
            continue
        duplicate_of = None
        duplicate_similarity = 0.0
        for representative in representatives:
            representative_signature = set(representative.get("_signal_signature") or [])
            if len(representative_signature) < config.duplicate_min_events:
                continue
            similarity = _jaccard_similarity(signature, representative_signature)
            if similarity > duplicate_similarity:
                duplicate_similarity = similarity
                duplicate_of = representative
        if duplicate_of is not None and duplicate_similarity >= config.duplicate_similarity_threshold:
            candidate["promotion_status"] = "blocked"
            candidate["score"] = 0.0
            candidate["duplicate_of"] = duplicate_of["case_id"]
            candidate["duplicate_similarity"] = round(duplicate_similarity, 4)
            candidate["blocking_reasons"] = _dedupe([*candidate["blocking_reasons"], "duplicate_signal_candidate"])
            candidate["warnings"] = _dedupe([*candidate["warnings"], f"duplicate_of:{duplicate_of['case_id']}"])
            continue
        representatives.append(candidate)


def _paper_signal_signature(manifest_path: Any) -> set[str]:
    if not manifest_path:
        return set()
    path = Path(str(manifest_path))
    intents_path = path.with_name("intents.csv")
    if not intents_path.exists():
        return set()
    try:
        rows = pd.read_csv(intents_path)
    except (OSError, pd.errors.EmptyDataError, pd.errors.ParserError):
        return set()
    signature_columns = ["signal_date", "execution_date", "asset_id", "side"]
    if not set(signature_columns).issubset(rows.columns):
        return set()
    signature = set()
    for row in rows[signature_columns].itertuples(index=False):
        values = [str(value) for value in row]
        if all(value and value.lower() != "nan" for value in values):
            signature.add("|".join(values))
    return signature


def _jaccard_similarity(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def _matching_paper_manifest(row: dict[str, Any], paper_manifests: list[dict[str, Any]]) -> dict[str, Any] | None:
    matches = [manifest for manifest in paper_manifests if _paper_matches(row, manifest)]
    if not matches:
        return None
    exact_case = [manifest for manifest in matches if _case_id_from_manifest(manifest) == str(row.get("case_id", ""))]
    if exact_case:
        return exact_case[0]
    return matches[0]


def _paper_matches(row: dict[str, Any], paper_manifest: dict[str, Any]) -> bool:
    request = paper_manifest.get("request", {})
    if not isinstance(request, dict):
        return False
    row_rebalance = _case_rebalance_interval(str(row.get("case_id", "")))
    checks = (
        str(row.get("market", "")).upper() == str(request.get("market", "")).upper(),
        str(row.get("factor_name", "")) == str(request.get("factor_name", "")),
        _maybe_int(row.get("top_n")) == _maybe_int(request.get("top_n")),
    )
    if not all(checks):
        return False
    request_rebalance = _maybe_int(request.get("rebalance_interval"))
    if row_rebalance is not None and request_rebalance is not None and row_rebalance != request_rebalance:
        return False
    return True


def _case_id_from_manifest(paper_manifest: dict[str, Any]) -> str | None:
    request = paper_manifest.get("request", {})
    if not isinstance(request, dict):
        return None
    case_id = request.get("case_id")
    return str(case_id) if case_id else None


def _case_rebalance_interval(case_id: str) -> int | None:
    marker = "_reb"
    if marker not in case_id:
        return None
    try:
        return int(case_id.rsplit(marker, 1)[1])
    except ValueError:
        return None


def _paper_drawdown(metrics: dict[str, Any]) -> float:
    if "max_equity_drawdown" in metrics:
        return _metric(metrics, "max_equity_drawdown")
    return _metric(metrics, "max_drawdown")


def _quality_reasons(quality_report: dict[str, Any] | None) -> dict[str, list[str]]:
    if quality_report is None:
        return {"blocking": [], "warnings": ["quality_report_missing"]}
    blocking = []
    warnings = []
    if _metric(quality_report, "duplicate_bars") > 0:
        blocking.append("duplicate_bars_present")
    if _metric(quality_report, "extreme_return_rows") > 0:
        blocking.append("extreme_returns_present")
    if _metric(quality_report, "adj_close_jump_rows") > 0:
        blocking.append("adj_close_jumps_present")
    if _metric(quality_report, "missing_date_rows") > 0:
        warnings.append("missing_dates_present")
    if _metric(quality_report, "zero_volume_rows") > 0:
        warnings.append("zero_volume_rows_present")
    if _metric(quality_report, "stale_price_rows") > 0:
        warnings.append("stale_price_rows_present")
    return {"blocking": blocking, "warnings": warnings}


def _market_regime_reasons(market_regime_coverage: dict[str, Any] | None, config: PromotionGateConfig) -> list[str]:
    if not config.require_market_regime_coverage:
        return []
    if market_regime_coverage is None:
        return ["market_regime_coverage_missing"]
    summary = market_regime_coverage.get("summary", {})
    decision = market_regime_coverage.get("decision", {})
    if not isinstance(summary, dict):
        summary = {}
    if not isinstance(decision, dict):
        decision = {}
    cleared = bool(decision.get("market_regime_coverage_cleared")) or str(market_regime_coverage.get("status")) == "sufficient"
    reasons = [str(reason) for reason in decision.get("blockers", []) or []]
    if not cleared:
        reasons.insert(0, "market_regime_coverage_not_sufficient")
    if _maybe_int(summary.get("covered_regimes")) is None:
        reasons.append("market_regime_coverage_summary_missing")
    return _dedupe(reasons)


def _market_regime_summary(market_regime_coverage: dict[str, Any] | None) -> dict[str, Any]:
    if market_regime_coverage is None:
        return {"present": False}
    summary = market_regime_coverage.get("summary", {})
    decision = market_regime_coverage.get("decision", {})
    if not isinstance(summary, dict):
        summary = {}
    if not isinstance(decision, dict):
        decision = {}
    return {
        "present": True,
        "status": market_regime_coverage.get("status"),
        "covered_regimes": _maybe_int(summary.get("covered_regimes")),
        "regimes": summary.get("regimes", []),
        "cleared": bool(decision.get("market_regime_coverage_cleared")) or str(market_regime_coverage.get("status")) == "sufficient",
        "blockers": decision.get("blockers", []) if isinstance(decision.get("blockers", []), list) else [],
    }


def _missing_walk_forward_metrics(row: dict[str, Any], config: PromotionGateConfig) -> list[str]:
    required = {
        "test_trades": "oos_trades_missing",
        "test_sharpe": "oos_sharpe_missing",
        "test_max_drawdown": "oos_drawdown_missing",
        "stability_score": "stability_score_missing",
    }
    if config.min_oos_relative_return is not None:
        required["test_relative_return"] = "oos_relative_return_missing"
    return [reason for metric, reason in required.items() if not _metric_present(row, metric)]


def _walk_forward_evidence_reasons(
    folds: int | None,
    accepted_folds: int | None,
    test_ic_p_value: float | None,
    test_positive_ic_rate: float | None,
    config: PromotionGateConfig,
) -> list[str]:
    reasons = []
    if config.min_walk_forward_folds > 1 and (folds is None or folds < config.min_walk_forward_folds):
        reasons.append("insufficient_walk_forward_folds")
    if config.min_accepted_folds > 1 and (accepted_folds is None or accepted_folds < config.min_accepted_folds):
        reasons.append("insufficient_accepted_folds")
    if config.max_ic_p_value is not None and (test_ic_p_value is None or test_ic_p_value > config.max_ic_p_value):
        reasons.append("ic_significance_below_threshold")
    if config.min_positive_ic_rate is not None and (
        test_positive_ic_rate is None or test_positive_ic_rate < config.min_positive_ic_rate
    ):
        reasons.append("positive_ic_rate_below_threshold")
    return reasons


def _factor_source_reasons(factor_source: str | None, config: PromotionGateConfig) -> list[str]:
    if config.required_factor_source is None:
        return []
    if factor_source != config.required_factor_source:
        return ["factor_source_mismatch"]
    return []


def _adjusted_ic_evidence_reasons(
    adjusted_ic_p_value: float | None,
    passes_adjusted_ic_p_value: bool | None,
    config: PromotionGateConfig,
) -> list[str]:
    if config.max_adjusted_ic_p_value is None:
        return []
    reasons = []
    if adjusted_ic_p_value is None:
        reasons.append("adjusted_ic_p_value_missing")
    elif adjusted_ic_p_value > config.max_adjusted_ic_p_value:
        reasons.append("adjusted_ic_p_value_above_threshold")
    if passes_adjusted_ic_p_value is not True:
        reasons.append("adjusted_ic_significance_not_passed")
    return reasons


def _experiment_summary(row: dict[str, Any] | None) -> dict[str, Any]:
    if row is None:
        return {"present": False}
    return {
        "present": True,
        "status": row.get("status"),
        "sharpe": _metric(row, "sharpe"),
        "total_return": _metric(row, "total_return"),
        "max_drawdown": _metric(row, "max_drawdown"),
        "turnover": _metric(row, "turnover"),
        "rank": int(_metric(row, "rank")),
    }


def _score(row: dict[str, Any], paper_summary: dict[str, Any], blocking: list[str], config: PromotionGateConfig) -> float:
    test_sharpe = max(_metric(row, "test_sharpe"), 0.0)
    stability = max(_metric(row, "stability_score"), 0.0)
    relative = max(_metric(row, "test_relative_return"), 0.0)
    oos_drawdown = abs(min(_metric(row, "test_max_drawdown"), 0.0))
    paper_sharpe = max(float(paper_summary["paper_sharpe"]), 0.0)
    paper_return = max(float(paper_summary["paper_total_return"]), 0.0)
    paper_drawdown = abs(min(float(paper_summary["paper_max_drawdown"]), 0.0))
    raw = (
        min(test_sharpe, 3.0) * 25.0
        + min(stability, 3.0) * 15.0
        + min(relative, 0.5) * 100.0
        + min(paper_sharpe, 3.0) * 15.0
        + min(paper_return, 0.5) * 20.0
        - max(oos_drawdown - 0.10, 0.0) * 50.0
        - max(config.min_paper_sharpe - paper_sharpe, 0.0) * 20.0
        - max(paper_drawdown - 0.10, 0.0) * 50.0
        - len(blocking) * 25.0
    )
    return round(max(raw, 0.0), 4)


def _providers_ready(provider_status: dict[str, Any] | None) -> bool:
    if provider_status is None:
        return False
    providers = provider_status.get("providers", {})
    if not isinstance(providers, dict):
        return False
    ready_values = [provider.get("ready") for provider in providers.values() if isinstance(provider, dict)]
    return bool(ready_values) and all(bool(value) for value in ready_values)


def _provider_reasons(
    provider_status: dict[str, Any] | None,
    providers_ready: bool,
    config: PromotionGateConfig,
) -> dict[str, list[str]]:
    blocking = []
    warnings = []
    if provider_status is None:
        warnings.append("provider_status_missing")
        if config.require_provider_ready_for_promotion:
            blocking.append("providers_not_ready_for_promotion")
        if config.max_provider_status_age_days is not None:
            blocking.append("provider_status_timestamp_missing")
        return {"blocking": blocking, "warnings": warnings}
    if not providers_ready:
        warnings.append("providers_not_ready_for_live_review")
        if config.require_provider_ready_for_promotion:
            blocking.append("providers_not_ready_for_promotion")
    if config.max_provider_status_age_days is not None:
        generated_at = _parse_date(provider_status.get("generated_at"))
        if generated_at is None:
            blocking.append("provider_status_timestamp_missing")
        elif (date.today() - generated_at).days > config.max_provider_status_age_days:
            blocking.append("provider_status_stale")
    return {"blocking": blocking, "warnings": warnings}


def _parse_date(value: Any) -> date | None:
    try:
        return date.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None


def _summary(candidates: list[dict[str, Any]]) -> dict[str, int]:
    return {
        "candidates": len(candidates),
        "blocked": sum(1 for row in candidates if row["promotion_status"] == "blocked"),
        "research_only": sum(1 for row in candidates if row["promotion_status"] == "research_only"),
        "paper_ready": sum(1 for row in candidates if row["promotion_status"] == "paper_ready"),
        "manual_live_review": sum(1 for row in candidates if row["promotion_status"] == "manual_live_review"),
        "duplicates": sum(1 for row in candidates if row.get("duplicate_of")),
    }


def _status_order(status: str) -> int:
    return {"manual_live_review": 0, "paper_ready": 1, "research_only": 2, "blocked": 3}.get(status, 4)


def _read_csv_records(path: str | Path) -> list[dict[str, Any]]:
    return pd.read_csv(Path(path)).to_dict(orient="records")


def _read_json(path: str | Path) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return data


def _load_paper_manifests(config: PromotionGateConfig) -> list[dict[str, Any]]:
    paths: list[Path] = []
    if config.paper_manifest is not None:
        paths.append(config.paper_manifest)
    paths.extend(config.paper_manifests)
    if config.paper_manifest_dir is not None and config.paper_manifest_dir.exists():
        paths.extend(sorted(config.paper_manifest_dir.rglob("manifest.json")))
    manifests = []
    seen = set()
    for path in paths:
        resolved = str(path)
        if resolved in seen:
            continue
        seen.add(resolved)
        manifest = _read_json(path)
        manifest.setdefault("manifest_path", str(path))
        manifests.append(manifest)
    return manifests


def _config_dict(config: PromotionGateConfig) -> dict[str, Any]:
    data = asdict(config)
    for key in (
        "walk_forward_leaderboard",
        "experiment_leaderboard",
        "paper_manifest",
        "paper_manifest_dir",
        "provider_status",
        "quality_report",
        "market_regime_coverage",
        "output_dir",
    ):
        data[key] = str(data[key]) if data[key] is not None else None
    data["paper_manifests"] = [str(path) for path in config.paper_manifests]
    return data


def _optional_path(value: Any) -> Path | None:
    if value is None or value == "":
        return None
    return Path(str(value))


def _metric(row: dict[str, Any] | None, key: str) -> float:
    if row is None:
        return 0.0
    try:
        value = float(row.get(key, 0.0))
    except (TypeError, ValueError):
        return 0.0
    return value if math.isfinite(value) else 0.0


def _metric_present(row: dict[str, Any] | None, key: str) -> bool:
    if row is None or key not in row:
        return False
    try:
        value = float(row.get(key))
    except (TypeError, ValueError):
        return False
    return math.isfinite(value)


def _maybe_int(value: Any) -> int | None:
    try:
        number = int(float(value))
    except (TypeError, ValueError):
        return None
    return number


def _maybe_float(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _maybe_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if value is None:
        return None
    text = str(value).strip().lower()
    if text in {"true", "1", "yes", "y"}:
        return True
    if text in {"false", "0", "no", "n"}:
        return False
    return None


def _optional_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _dedupe(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _sanitize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    return value
