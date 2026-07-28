from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Mapping

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from quant_robot.data.cn_trading_calendar import validate_cn_trading_calendar_artifact  # noqa: E402
from quant_robot.data.etf_point_in_time_universe import (  # noqa: E402
    EtfEligibilityPolicy,
    build_point_in_time_etf_eligibility,
    load_official_etf_lifecycle,
)
from quant_robot.factors.etf_residual_margin_financing_growth import (  # noqa: E402
    DIRECT_EXPOSURE_NAMES,
    FACTOR_NAME,
    compute_etf_residual_margin_financing_growth,
)
from quant_robot.ops.cn_etf_margin_positioning_prescreen import (  # noqa: E402
    CLOSED_FAMILY_REFERENCE_NAMES,
    STAGE,
    compute_closed_family_reference_union,
    summarize_cn_etf_margin_positioning_prescreen,
    write_cn_etf_margin_positioning_prescreen,
)
from quant_robot.research.labels import (  # noqa: E402
    filter_market_calendar_aligned_forward_returns,
    make_forward_returns,
)
from quant_robot.storage.atomic import atomic_write_json  # noqa: E402
from quant_robot.storage.fingerprints import sha256_file  # noqa: E402
from quant_robot.storage.processed_bars import load_processed_bars  # noqa: E402
from quant_robot.validation.single_prescreen_authorization import (  # noqa: E402
    claim_single_prescreen_authorization,
    validate_single_prescreen_authorization,
)
from scripts.run_cn_etf_margin_positioning_preregistration import (  # noqa: E402
    SOURCE_KEYS,
    _load_and_validate_config as _load_preregistration_config,
)
from scripts.run_quant_pm_startup_gate import run_quant_pm_startup_gate  # noqa: E402


DEFAULT_CONFIG = Path("configs/cn_etf_margin_positioning_preregistration_20260728.json")
DEFAULT_PREREGISTRATION_RESULT = Path(
    "data/reports/cn_etf_margin_positioning_preregistration_20260728/"
    "cn_etf_margin_positioning_preregistration.json"
)
DEFAULT_AUTHORIZATION = Path(
    "data/reports/cn_etf_margin_positioning_preregistration_20260728/"
    "single_prescreen_authorization.json"
)
DEFAULT_SCHEDULER = Path("configs/research_family_scheduler_cn_etf.json")
DEFAULT_LEDGER = Path("data/reports/cn_etf_margin_positioning_prescreen_execution_ledger.json")
DEFAULT_OUTPUT_DIR = Path("data/reports/cn_etf_margin_positioning_prescreen_20260728")
EXPECTED_BRANCH = "codex/factor-batch-cn-etf-margin-positioning-20260728"
PREFLIGHT_STAGE = "cn_etf_margin_positioning_prescreen_preflight"
FROZEN_HASHES = {
    "config": "c6d11639c7e1f5c454f7ad4434e682139c074d031bd391d89034aafc76b26855",
    "preregistration_result": "bcc8f5030d24530f9f9afa81f2c411375fba9009ce82f70589ff6a4b7973e45d",
    "authorization": "2dbc3f08f1c16a9a174b2bae3ddf1ba94188ae1fcf764c775fe6691709053fc2",
    "source_config": "0b0760536cd779e90bc9b4af607ef6ce0441f9f948369006dedcbbbb47c30c22",
    "source_result": "8c61c7b147046bfd6c4a33f832e8c77bcd732d51b52c98b0aa9be5a6e0a3f2d5",
    "manifest": "382ccf8b48bb3e64f2bf8e3b3cbe5b176791d450094e6be004b291d2938542db",
    "date_coverage": "819dd2b0f2b52cee8844acf46e919d9e0b733930347615ce939d950311147fe1",
    "canonical_2020": "14e65c8bacbfd9cec30a0fc38dd5c5be7cf659b2bed3000d174ba296b763b124",
    "canonical_2021": "d831a01c0e103a1c6677dca895d3b133edbd739441e3d7c3490ec61d42aaa3df",
    "canonical_2022": "05441569b2a688d69daa351a9d038a3590404efc3b45e33c9f1a79c33dac07cf",
    "canonical_2023": "54dc11c92fb54c930c45157ec38c4d9e81b80d57b170193e8d6dc9117fe11105",
    "canonical_2024": "707c7cd99f4956fc3d961a1b4c3d0f354e73aca60321e47b591e7aababe637fe",
    "canonical_data": "f1152513e73bc69576d04a61585f3971cad007dc04482dbdc0e38d049d3565ec",
}
FALSE_DECISION_BOUNDARIES = (
    "portfolio_grid_allowed",
    "walk_forward_allowed",
    "final_holdout_allowed",
    "promotion_allowed",
    "paper_signal_allowed",
    "broker_connection_allowed",
    "account_read_allowed",
    "order_placement_allowed",
    "live_boundary_allowed",
)


@dataclass(frozen=True)
class PrescreenRuntime:
    config_path: Path = DEFAULT_CONFIG
    preregistration_result_path: Path = DEFAULT_PREREGISTRATION_RESULT
    authorization_path: Path = DEFAULT_AUTHORIZATION
    scheduler_path: Path = DEFAULT_SCHEDULER
    ledger_path: Path = DEFAULT_LEDGER
    output_dir: Path = DEFAULT_OUTPUT_DIR


@dataclass(frozen=True)
class PreparedInputs:
    bars: pd.DataFrame
    factors: pd.DataFrame
    references: pd.DataFrame
    direct_exposures: pd.DataFrame
    adv20: pd.DataFrame
    official_sessions: pd.DatetimeIndex
    metadata: dict[str, Any]


def run_cn_etf_margin_positioning_prescreen_cli(
    *,
    mode: str,
    runtime: PrescreenRuntime = PrescreenRuntime(),
) -> dict[str, Any]:
    if mode not in {"preflight", "execute"}:
        raise ValueError("mode must be preflight or execute")
    preflight = preflight_cn_etf_margin_positioning_prescreen(runtime=runtime)
    return preflight if mode == "preflight" else _execute(preflight, runtime=runtime)


def preflight_cn_etf_margin_positioning_prescreen(
    *,
    runtime: PrescreenRuntime = PrescreenRuntime(),
) -> dict[str, Any]:
    _validate_runtime(runtime)
    _require_hash(runtime.config_path, FROZEN_HASHES["config"], "config")
    config = _load_preregistration_config(runtime.config_path)
    if tuple(config["reference_policy"]["direct_exposure_names"]) != DIRECT_EXPOSURE_NAMES:
        raise ValueError("config direct exposures do not match the frozen factor")
    source_paths = {
        key: Path(config["source_evidence"]["paths"][key])
        for key in SOURCE_KEYS
    }
    for key, path in source_paths.items():
        _require_hash(path, FROZEN_HASHES[key], f"source {key}")
    manifest = _load_json(source_paths["manifest"], "source manifest")
    if manifest.get("content_sha256") != FROZEN_HASHES["canonical_data"]:
        raise ValueError("canonical margin-positioning data identity mismatch")
    _require_hash(
        runtime.preregistration_result_path,
        FROZEN_HASHES["preregistration_result"],
        "preregistration result",
    )
    authorization = validate_single_prescreen_authorization(
        packet_path=runtime.authorization_path,
        expected_candidate_name=FACTOR_NAME,
        expected_config_sha256=FROZEN_HASHES["config"],
        expected_packet_sha256=FROZEN_HASHES["authorization"],
        expected_allowed_stage=STAGE,
        expected_source_hash_keys=SOURCE_KEYS,
        context="CN ETF margin-positioning prescreen preflight",
    )
    packet = authorization["packet"]
    source_hashes = {key: FROZEN_HASHES[key] for key in SOURCE_KEYS}
    if packet.get("preregistration_result_sha256") != FROZEN_HASHES["preregistration_result"]:
        raise ValueError("authorization preregistration result hash mismatch")
    if packet.get("source_hashes") != source_hashes:
        raise ValueError("authorization source hashes mismatch")
    if Path(str(packet.get("execution_ledger_path"))).resolve() != runtime.ledger_path.resolve():
        raise ValueError("authorization ledger path mismatch")
    scheduler = _load_json(runtime.scheduler_path, "research-family scheduler")
    _validate_scheduler(
        scheduler,
        authorization_id=authorization["authorization_id"],
        authorization_path=runtime.authorization_path,
    )
    gate = run_quant_pm_startup_gate(
        machine="office_desktop",
        task="factor_batch",
        branch=EXPECTED_BRANCH,
    )
    _validate_gate(gate)
    _require_unconsumed(runtime.ledger_path, authorization["authorization_id"])
    reference_names = _load_reference_names(config)
    return {
        "stage": PREFLIGHT_STAGE,
        "status": "ready_unconsumed",
        "config": config,
        "config_sha256": FROZEN_HASHES["config"],
        "preregistration_result_sha256": FROZEN_HASHES["preregistration_result"],
        "authorization_sha256": FROZEN_HASHES["authorization"],
        "authorization_id": authorization["authorization_id"],
        "source_hashes": source_hashes,
        "canonical_data_sha256": FROZEN_HASHES["canonical_data"],
        "reference_names": list(reference_names),
        "runtime": runtime,
        "quant_pm_gate": {
            "status": gate["status"],
            "mode": gate["mode"],
            "factor_batch_scope": gate["safety"]["factor_batch_scope"],
        },
        "forward_labels_read": False,
        "execution_claim_recorded": False,
    }


def _execute(preflight: Mapping[str, Any], *, runtime: PrescreenRuntime) -> dict[str, Any]:
    receipt: dict[str, Any] | None = None
    prepared = _prepare_unlabeled(preflight)
    try:
        receipt = claim_single_prescreen_authorization(
            packet_path=runtime.authorization_path,
            ledger_path=runtime.ledger_path,
            expected_candidate_name=FACTOR_NAME,
            expected_config_sha256=str(preflight["config_sha256"]),
            expected_packet_sha256=str(preflight["authorization_sha256"]),
            expected_allowed_stage=STAGE,
            expected_source_hash_keys=SOURCE_KEYS,
            context="CN ETF margin-positioning prescreen",
        )
        config = dict(preflight["config"])
        evaluation = config["evaluation"]
        labels = make_forward_returns(
            prepared.bars[["date", "asset_id", "market", "adj_close"]],
            horizons=tuple(int(value) for value in evaluation["horizons"]),
            execution_lag=int(evaluation["execution_lag"]),
        )
        raw_rows = int(len(labels))
        labels = filter_market_calendar_aligned_forward_returns(labels, prepared.bars)
        labels = _exclude_gap_crossing_labels(
            labels,
            official_sessions=prepared.official_sessions,
            gap_dates=config["data_boundary"]["bar_authority_gap_dates"],
            execution_lag=int(evaluation["execution_lag"]),
        )
        start = pd.Timestamp(config["data_boundary"]["analysis_start_date"])
        end = pd.Timestamp(config["data_boundary"]["analysis_end_date"])
        labels = labels[pd.to_datetime(labels["date"]).between(start, end)].reset_index(drop=True)
        result = _summarize(preflight, prepared, labels)
        result["configuration"] = {
            "path": str(runtime.config_path),
            "sha256": str(preflight["config_sha256"]),
            "preregistration_result_sha256": str(preflight["preregistration_result_sha256"]),
            "authorization_sha256": str(preflight["authorization_sha256"]),
        }
        result["source_hashes"] = dict(preflight["source_hashes"])
        result["canonical_data_sha256"] = str(preflight["canonical_data_sha256"])
        result["data_window"] = {
            **prepared.metadata,
            "raw_forward_label_rows": raw_rows,
            "gap_filtered_calendar_aligned_forward_label_rows": int(len(labels)),
            "bar_gap_crossing_windows_excluded": True,
            "final_holdout_included": False,
        }
        result["authorization"] = {
            "authorization_id": str(preflight["authorization_id"]),
            "execution_claim_recorded": True,
            "max_executions": 1,
        }
        paths = write_cn_etf_margin_positioning_prescreen(runtime.output_dir, result)
        manifest_path, hashes = _write_hash_manifest(runtime, preflight, paths)
        outcome = atomic_write_json(
            runtime.output_dir / "execution_outcome.json",
            {
                "stage": STAGE,
                "status": "completed",
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "authorization_id": str(preflight["authorization_id"]),
                "authorization_claim": receipt,
                "result_status": result["status"],
                "artifact_hashes": hashes,
                "manifest_path": str(manifest_path),
            },
        )
        result["artifacts"] = {
            **{name: str(path) for name, path in paths.items()},
            "hash_manifest": str(manifest_path),
            "execution_outcome": str(outcome),
        }
        result["artifact_hashes"] = hashes
        return result
    except Exception as exc:
        if receipt is not None:
            atomic_write_json(
                runtime.output_dir / "execution_outcome.json",
                {
                    "stage": STAGE,
                    "status": "terminal_failure_after_claim",
                    "failed_at": datetime.now(timezone.utc).isoformat(),
                    "authorization_id": str(preflight["authorization_id"]),
                    "authorization_claim": receipt,
                    "error_type": type(exc).__name__,
                    "error": str(exc),
                    "retry_allowed": False,
                },
            )
        raise


def _prepare_unlabeled(preflight: Mapping[str, Any]) -> PreparedInputs:
    config = dict(preflight["config"])
    boundary = config["data_boundary"]
    candidate = config["candidate"]
    eligibility_config = config["eligibility"]
    start = pd.Timestamp(boundary["analysis_start_date"])
    end = pd.Timestamp(boundary["analysis_end_date"])
    holdout = pd.Timestamp(boundary["final_holdout_start"])
    bars = load_processed_bars(boundary["bar_root"], "CN_ETF", end_date=end).copy()
    bars["date"] = pd.to_datetime(bars["date"])
    if bars.empty or bars["date"].max() > end or bars["date"].ge(holdout).any():
        raise ValueError("bounded CN ETF bar read violated the analysis boundary")
    source_paths = config["source_evidence"]["paths"]
    margin = pd.concat(
        [pd.read_parquet(source_paths[f"canonical_{year}"]) for year in range(2020, 2025)],
        ignore_index=True,
    )
    margin["date"] = pd.to_datetime(margin["date"])
    margin["available_date"] = pd.to_datetime(margin["available_date"])
    margin = margin[
        margin["date"].le(end) & margin["available_date"].lt(holdout)
    ].reset_index(drop=True)
    if margin.empty or margin["available_date"].le(margin["date"]).any():
        raise ValueError("margin-positioning availability boundary was violated")
    official_sessions = _load_official_sessions(boundary)
    invalid_factor_dates = _factor_gap_dates(
        official_sessions,
        boundary["bar_authority_gap_dates"],
        window=int(candidate["long_return_window"]),
    )
    lifecycle = load_official_etf_lifecycle(
        Path(boundary["bar_root"]) / "metadata" / "tushare_fund_basic"
    )
    policy = EtfEligibilityPolicy(
        min_prior_observations=int(eligibility_config["min_prior_observations"]),
        liquidity_window=int(eligibility_config["liquidity_window"]),
        min_trailing_median_amount=float(eligibility_config["min_trailing_median_amount_cny"]),
        max_stale_rate=float(eligibility_config["max_stale_price_rate"]),
        max_abs_return=float(eligibility_config["max_abs_daily_adjusted_return"]),
    )
    eligibility = build_point_in_time_etf_eligibility(bars, lifecycle, policy=policy)
    eligible_keys = eligibility[
        eligibility["eligible"] & pd.to_datetime(eligibility["date"]).le(end)
    ][["date", "asset_id", "market"]].drop_duplicates()
    factor_result = compute_etf_residual_margin_financing_growth(
        bars,
        margin,
        eligible_keys=eligible_keys,
        margin_lookback=int(candidate["margin_lookback"]),
        short_return_window=int(candidate["short_return_window"]),
        long_return_window=int(candidate["long_return_window"]),
        volatility_window=int(candidate["volatility_window"]),
        adv_window=int(candidate["adv_window"]),
        min_cross_section=int(candidate["minimum_daily_cross_section"]),
        winsor_lower=float(candidate["winsor_lower"]),
        winsor_upper=float(candidate["winsor_upper"]),
        scale_epsilon=float(candidate["scale_epsilon"]),
        invalid_signal_dates=invalid_factor_dates,
    )
    factors = _slice(factor_result.factors, start, end)
    direct = _slice(factor_result.direct_exposures, start, end)
    adv20 = _slice(factor_result.adv20, start, end)
    finite = pd.to_numeric(factors["factor_value"], errors="coerce").replace(
        [np.inf, -np.inf],
        np.nan,
    )
    evaluation_keys = factors.loc[finite.notna(), ["date", "asset_id", "market"]].drop_duplicates()
    if evaluation_keys.empty:
        raise ValueError("margin-positioning factor produced no finite values")
    references = compute_closed_family_reference_union(
        bars,
        eligible_keys=eligible_keys,
        evaluation_keys=evaluation_keys,
        expected_names=tuple(preflight["reference_names"]),
    )
    direct = direct.merge(
        evaluation_keys,
        on=["date", "asset_id", "market"],
        how="inner",
        validate="many_to_one",
    )
    adv20 = adv20.merge(
        evaluation_keys,
        on=["date", "asset_id", "market"],
        how="inner",
        validate="one_to_one",
    )
    return PreparedInputs(
        bars=bars,
        factors=factors,
        references=references,
        direct_exposures=direct,
        adv20=adv20,
        official_sessions=official_sessions,
        metadata={
            "analysis_start_date": start.date().isoformat(),
            "analysis_end_date": end.date().isoformat(),
            "history_rows": int(len(bars)),
            "history_assets": int(bars["asset_id"].nunique()),
            "history_dates": int(bars["date"].nunique()),
            "margin_positioning_rows": int(len(margin)),
            "margin_positioning_assets": int(margin["asset_id"].nunique()),
            "eligible_rows": int(len(eligible_keys)),
            "candidate_rows": int(len(factors)),
            "finite_candidate_rows": int(finite.notna().sum()),
            "candidate_assets": int(evaluation_keys["asset_id"].nunique()),
            "candidate_dates": int(pd.to_datetime(evaluation_keys["date"]).nunique()),
            "invalid_factor_dates_for_bar_gaps": int(len(invalid_factor_dates)),
            "later_partitions_skipped_before_read": True,
        },
    )


def _summarize(
    preflight: Mapping[str, Any],
    prepared: PreparedInputs,
    labels: pd.DataFrame,
) -> dict[str, Any]:
    config = dict(preflight["config"])
    evaluation = config["evaluation"]
    reference = config["reference_policy"]
    capacity = config["capacity"]
    costs = config["costs"]
    return summarize_cn_etf_margin_positioning_prescreen(
        prepared.factors,
        labels,
        prepared.references,
        prepared.direct_exposures,
        prepared.adv20,
        expected_reference_names=tuple(preflight["reference_names"]),
        direct_exposure_names=tuple(reference["direct_exposure_names"]),
        horizons=tuple(evaluation["horizons"]),
        primary_horizon=int(evaluation["primary_horizon"]),
        diagnostic_horizon=int(evaluation["diagnostic_horizon"]),
        min_cross_section=int(evaluation["minimum_daily_cross_section"]),
        min_ic_observations=int(evaluation["minimum_ic_observations"]),
        min_year_ic_observations=int(evaluation["minimum_yearly_ic_observations"]),
        min_usable_years=int(evaluation["minimum_usable_years"]),
        alpha=float(evaluation["fdr_alpha"]),
        min_mean_rank_ic=float(evaluation["minimum_mean_rank_ic"]),
        min_icir=float(evaluation["minimum_icir"]),
        min_positive_ic_rate=float(evaluation["minimum_positive_ic_rate"]),
        min_quantile_monotonicity=float(evaluation["minimum_quintile_monotonicity"]),
        max_top_quantile_turnover=float(evaluation["maximum_top_quintile_turnover"]),
        min_positive_year_rate=float(evaluation["minimum_positive_year_rate"]),
        max_abs_reference_correlation=float(
            evaluation["maximum_abs_mean_daily_reference_correlation"]
        ),
        direct_min_daily_observations=int(evaluation["minimum_ic_observations"]),
        max_abs_direct_exposure_correlation=float(
            reference["max_abs_direct_exposure_correlation"]
        ),
        position_value_cny=float(capacity["diagnostic_position_value_cny"]),
        max_one_way_participation_rate=float(capacity["max_one_way_participation_rate"]),
        one_way_costs_bps=tuple(costs["one_way_bps"]),
        required_positive_net_spread_bps=float(costs["required_positive_net_spread_bps"]),
        diagnostic_min_mean_rank_ic=float(evaluation["diagnostic_minimum_mean_rank_ic"]),
        diagnostic_min_quantile_spread=float(
            evaluation["diagnostic_minimum_top_minus_bottom_spread"]
        ),
    )


def _load_official_sessions(boundary: Mapping[str, Any]) -> pd.DatetimeIndex:
    path = Path(boundary["trading_calendar_path"])
    manifest = Path(boundary["trading_calendar_manifest_path"])
    validate_cn_trading_calendar_artifact(path, manifest)
    dates = pd.to_datetime(pd.read_csv(path)["date"], errors="raise")
    start = pd.Timestamp(boundary["analysis_start_date"])
    end = pd.Timestamp(boundary["analysis_end_date"])
    return pd.DatetimeIndex(dates[dates.between(start, end)]).drop_duplicates().sort_values()


def _factor_gap_dates(
    sessions: pd.DatetimeIndex,
    gaps: list[str],
    *,
    window: int,
) -> set[pd.Timestamp]:
    result: set[pd.Timestamp] = set()
    positions = {date: index for index, date in enumerate(sessions)}
    for value in gaps:
        gap = pd.Timestamp(value)
        if gap not in positions:
            raise ValueError(f"frozen bar gap is not an official session: {value}")
        index = positions[gap]
        result.update(pd.Timestamp(date) for date in sessions[index : index + window + 1])
    return result


def _exclude_gap_crossing_labels(
    labels: pd.DataFrame,
    *,
    official_sessions: pd.DatetimeIndex,
    gap_dates: list[str],
    execution_lag: int,
) -> pd.DataFrame:
    invalid: dict[int, set[pd.Timestamp]] = {}
    positions = {date: index for index, date in enumerate(official_sessions)}
    for horizon in sorted(int(value) for value in labels["horizon"].unique()):
        dates: set[pd.Timestamp] = set()
        for value in gap_dates:
            gap = pd.Timestamp(value)
            index = positions[gap]
            start = max(0, index - horizon - execution_lag)
            dates.update(pd.Timestamp(date) for date in official_sessions[start : index + 1])
        invalid[horizon] = dates
    label_dates = pd.to_datetime(labels["date"]).dt.normalize()
    keep = [
        date not in invalid[int(horizon)]
        for date, horizon in zip(label_dates, labels["horizon"], strict=True)
    ]
    return labels.loc[keep].reset_index(drop=True)


def _load_reference_names(config: Mapping[str, Any]) -> tuple[str, ...]:
    names: list[str] = []
    for item in config["reference_policy"]["reference_configs"]:
        path = Path(item["path"])
        _require_hash(path, str(item["sha256"]), f"reference config {path}")
        payload = _load_json(path, f"reference config {path}")
        names.extend(str(value) for value in payload["candidate_names"])
        names.extend(str(value) for value in payload["reference_names"])
    observed = tuple(names)
    if observed != CLOSED_FAMILY_REFERENCE_NAMES or len(set(observed)) != len(observed):
        raise ValueError("reference configs do not produce the exact frozen union")
    return observed


def _validate_scheduler(
    scheduler: Mapping[str, Any],
    *,
    authorization_id: str,
    authorization_path: Path,
) -> None:
    decision = scheduler.get("last_decision", {})
    expected = {
        "decision": "prescreen_preregistered_single_batch_only",
        "factor_name": FACTOR_NAME,
        "preregistration_config_sha256": FROZEN_HASHES["config"],
        "preregistration_result_sha256": FROZEN_HASHES["preregistration_result"],
        "authorization_sha256": FROZEN_HASHES["authorization"],
        "authorization_id": authorization_id,
        "source_config_sha256": FROZEN_HASHES["source_config"],
        "source_result_sha256": FROZEN_HASHES["source_result"],
        "canonical_data_sha256": FROZEN_HASHES["canonical_data"],
        "primary_horizon": 5,
        "diagnostic_horizon": 20,
        "single_prescreen_run_limit": 1,
        "execution_count": 0,
        "execution_ledger_required": True,
        "allowed_stage": STAGE,
        "factor_batch_allowed": True,
        "single_prescreen_allowed": True,
    }
    for key, value in expected.items():
        if decision.get(key) != value:
            raise ValueError(f"scheduler single-prescreen decision mismatch: {key}")
    if Path(str(decision.get("authorization_path"))).resolve() != authorization_path.resolve():
        raise ValueError("scheduler authorization path mismatch")
    if Path(str(decision.get("execution_ledger_path"))).resolve() != DEFAULT_LEDGER.resolve():
        raise ValueError("scheduler execution ledger path mismatch")
    for key in FALSE_DECISION_BOUNDARIES:
        if decision.get(key) is not False:
            raise ValueError(f"scheduler boundary must remain false: {key}")


def _validate_gate(gate: Mapping[str, Any]) -> None:
    if gate.get("status") != "ready" or gate.get("mode") != "single_prescreen_only":
        raise ValueError("Quant PM gate did not authorize single_prescreen_only")
    selected = gate.get("selected", {})
    if selected.get("current_branch") != EXPECTED_BRANCH or selected.get("task") != "factor_batch":
        raise ValueError("Quant PM selected context mismatch")
    scope = gate.get("safety", {}).get("factor_batch_scope", {})
    expected = {
        "allowed_stage": STAGE,
        "authorization_sha256": FROZEN_HASHES["authorization"],
        "canonical_data_sha256": FROZEN_HASHES["canonical_data"],
        "config_sha256": FROZEN_HASHES["config"],
        "execution_count": 0,
        "execution_ledger_path": str(DEFAULT_LEDGER).replace("\\", "/"),
        "factor_name": FACTOR_NAME,
        "max_executions": 1,
        "preregistration_result_sha256": FROZEN_HASHES["preregistration_result"],
        "source_config_sha256": FROZEN_HASHES["source_config"],
        "source_result_sha256": FROZEN_HASHES["source_result"],
    }
    if scope != expected:
        raise ValueError("Quant PM factor-batch scope mismatch")


def _validate_runtime(runtime: PrescreenRuntime) -> None:
    expected = PrescreenRuntime()
    for field in PrescreenRuntime.__dataclass_fields__:
        if Path(getattr(runtime, field)).resolve() != Path(getattr(expected, field)).resolve():
            raise ValueError(f"runtime {field} must remain on the frozen path")
    if Path("data/reports").resolve() not in runtime.output_dir.resolve().parents:
        raise ValueError("prescreen output must remain under data/reports")


def _require_unconsumed(path: Path, authorization_id: str) -> None:
    if not path.exists():
        return
    claims = _load_json(path, "execution ledger").get("claims")
    if not isinstance(claims, Mapping) or authorization_id in claims:
        raise ValueError(f"single prescreen authorization already consumed: {authorization_id}")


def _write_hash_manifest(
    runtime: PrescreenRuntime,
    preflight: Mapping[str, Any],
    paths: Mapping[str, Path],
) -> tuple[Path, dict[str, str]]:
    hashes = {name: sha256_file(path) for name, path in sorted(paths.items())}
    path = atomic_write_json(
        runtime.output_dir / "hash_manifest.json",
        {
            "stage": STAGE,
            "config_sha256": str(preflight["config_sha256"]),
            "preregistration_result_sha256": str(preflight["preregistration_result_sha256"]),
            "authorization_sha256": str(preflight["authorization_sha256"]),
            "authorization_id": str(preflight["authorization_id"]),
            "source_hashes": dict(preflight["source_hashes"]),
            "canonical_data_sha256": str(preflight["canonical_data_sha256"]),
            "artifact_hashes": hashes,
        },
    )
    return path, hashes


def _slice(frame: pd.DataFrame, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    return frame[pd.to_datetime(frame["date"]).between(start, end)].reset_index(drop=True)


def _require_hash(path: Path, expected: str, label: str) -> None:
    if not path.is_file():
        raise FileNotFoundError(f"{label} is missing: {path}")
    actual = sha256_file(path)
    if actual != expected:
        raise ValueError(f"{label} hash mismatch: expected {expected}, observed {actual}")


def _load_json(path: Path, label: str) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"{label} is missing: {path}")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"{label} is invalid JSON: {path}") from exc
    if not isinstance(value, dict):
        raise ValueError(f"{label} must be a JSON object: {path}")
    return value


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the one authorized CN ETF margin-positioning prescreen."
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preflight-only", action="store_true")
    mode.add_argument("--execute", action="store_true")
    args = parser.parse_args()
    result = run_cn_etf_margin_positioning_prescreen_cli(
        mode="execute" if args.execute else "preflight"
    )
    print(
        json.dumps(
            {
                "stage": result.get("stage"),
                "status": result.get("status"),
                "authorization_id": result.get("authorization_id")
                or result.get("authorization", {}).get("authorization_id"),
                "forward_labels_read": result.get("forward_labels_read"),
                "execution_claim_recorded": result.get("execution_claim_recorded")
                or result.get("authorization", {}).get("execution_claim_recorded"),
                "decision": result.get("decision"),
                "data_window": result.get("data_window"),
                "artifacts": result.get("artifacts"),
            },
            indent=2,
            sort_keys=True,
            default=str,
        )
    )


if __name__ == "__main__":
    main()
