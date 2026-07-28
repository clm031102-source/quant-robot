from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
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

from quant_robot.data.etf_point_in_time_universe import (  # noqa: E402
    EtfEligibilityPolicy,
    build_point_in_time_etf_eligibility,
    load_official_etf_lifecycle,
)
from quant_robot.factors.etf_residual_share_creation_crowding import (  # noqa: E402
    DIRECT_EXPOSURE_NAMES,
    FACTOR_NAME,
    compute_etf_residual_share_creation_crowding,
)
from quant_robot.ops.cn_etf_fund_structure_crowding_prescreen import (  # noqa: E402
    CLOSED_FAMILY_REFERENCE_NAMES,
    STAGE,
    compute_closed_family_reference_union,
    summarize_cn_etf_fund_structure_crowding_prescreen,
    write_cn_etf_fund_structure_crowding_prescreen,
)
from quant_robot.research.labels import (  # noqa: E402
    filter_market_calendar_aligned_forward_returns,
    make_forward_returns,
)
from quant_robot.storage.atomic import atomic_write_json  # noqa: E402
from quant_robot.storage.etf_share_size import load_etf_share_size_inputs  # noqa: E402
from quant_robot.storage.fingerprints import sha256_file  # noqa: E402
from quant_robot.storage.processed_bars import load_processed_bars  # noqa: E402
from quant_robot.validation.single_prescreen_authorization import (  # noqa: E402
    claim_single_prescreen_authorization,
    validate_single_prescreen_authorization,
)
from scripts.run_cn_etf_fund_structure_crowding_preregistration import (  # noqa: E402
    SOURCE_KEYS,
    _load_and_validate_config as _load_preregistration_config,
)
from scripts.run_quant_pm_startup_gate import run_quant_pm_startup_gate  # noqa: E402


DEFAULT_CONFIG = Path(
    "configs/cn_etf_fund_structure_crowding_preregistration_20260728.json"
)
DEFAULT_PREREGISTRATION_RESULT = Path(
    "data/reports/cn_etf_fund_structure_crowding_preregistration_20260728/"
    "cn_etf_fund_structure_crowding_preregistration.json"
)
DEFAULT_AUTHORIZATION = Path(
    "data/reports/cn_etf_fund_structure_crowding_preregistration_20260728/"
    "single_prescreen_authorization.json"
)
DEFAULT_SCHEDULER = Path("configs/research_family_scheduler_cn_etf.json")
DEFAULT_LEDGER = Path(
    "data/reports/cn_etf_fund_structure_crowding_prescreen_execution_ledger.json"
)
DEFAULT_OUTPUT_DIR = Path(
    "data/reports/cn_etf_fund_structure_crowding_prescreen_20260728"
)
EXPECTED_BRANCH = "codex/factor-batch-cn-etf-fund-structure-20260728"
PREFLIGHT_STAGE = "cn_etf_fund_structure_crowding_prescreen_preflight"
FROZEN_HASHES = {
    "config": "a6a7a7f3d694e0a8484d907302f4f35c423a8432e1fb24b687c9896e7bc8ce8e",
    "preregistration_result": "6d76024f892e82a849bbe3de8d2d1c8c13635924993fa9f6f4eb2bd232f82e13",
    "authorization": "383a87953a5263faacb46ab6fc893ad58cc1300b364dc463869a72e8776e0b3d",
    "source_config": "04cb2acc675762f04c109798949d2b174fb1c9c72a9d91497423837f366a0ba3",
    "source_result": "3ccb5ba4d04ff24b7b5ef81c2984f1571a0a23cd41f077c7b20ae688879f3a13",
    "canonical_2020": "a46680257d3765ad8e3f945d48c68733ae23a98aab1d80a7d607675027cb6e2d",
    "canonical_2021": "70dcdfd169a227207809160a63f75106a136e2a5eef9c67c4fd325855cb5c192",
    "canonical_2022": "65357c506b86bc1ce46eed164cd126bbc61e3c71d43debea5e1aa418f6321bff",
    "canonical_2023": "4d35a34aa3932a8dfe8d1d0efa53d1d075ddb55c5ecf0666766ac5dfac30c3ba",
    "canonical_2024": "98d58a9a9ad508d9f8ec6182e219632319659db560f836b2b9386cf4b27705ca",
    "canonical_data": "34fddae9b46c97acdd1c6d953f3c0e68b48c9712bc93c5fe8e735297007f2bde",
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
class PreparedPrescreenInputs:
    bars: pd.DataFrame
    factors: pd.DataFrame
    references: pd.DataFrame
    direct_exposures: pd.DataFrame
    adv20: pd.DataFrame
    metadata: dict[str, Any]


def run_cn_etf_fund_structure_crowding_prescreen_cli(
    *,
    mode: str,
    runtime: PrescreenRuntime = PrescreenRuntime(),
) -> dict[str, Any]:
    if mode not in {"preflight", "execute"}:
        raise ValueError("mode must be preflight or execute")
    preflight = preflight_cn_etf_fund_structure_crowding_prescreen(runtime=runtime)
    if mode == "preflight":
        return preflight
    return _execute_authorized(preflight, runtime=runtime)


def preflight_cn_etf_fund_structure_crowding_prescreen(
    *,
    runtime: PrescreenRuntime = PrescreenRuntime(),
) -> dict[str, Any]:
    _validate_default_runtime(runtime)
    config = _load_and_validate_config(
        runtime.config_path,
        expected_sha256=FROZEN_HASHES["config"],
    )
    source_paths = {
        key: Path(config["source_evidence"]["paths"][key])
        for key in SOURCE_KEYS
    }
    source_hashes = {}
    for key, path in source_paths.items():
        _require_hash(path, FROZEN_HASHES[key], f"source {key}")
        source_hashes[key] = FROZEN_HASHES[key]
    if _canonical_data_hash(source_hashes) != FROZEN_HASHES["canonical_data"]:
        raise ValueError("canonical fund-structure data identity mismatch")
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
        context="CN ETF fund-structure crowding prescreen preflight",
    )
    packet = authorization["packet"]
    if packet.get("preregistration_result_sha256") != FROZEN_HASHES["preregistration_result"]:
        raise ValueError("authorization preregistration result hash mismatch")
    if packet.get("source_hashes") != source_hashes:
        raise ValueError("authorization source hashes mismatch")
    if Path(str(packet.get("execution_ledger_path"))).resolve() != runtime.ledger_path.resolve():
        raise ValueError("authorization ledger path mismatch")
    scheduler = _load_json_object(runtime.scheduler_path, "research-family scheduler")
    _validate_scheduler_decision(
        scheduler,
        authorization_id=authorization["authorization_id"],
        authorization_path=runtime.authorization_path,
    )
    gate = run_quant_pm_startup_gate(
        machine="office_desktop",
        task="factor_batch",
        branch=EXPECTED_BRANCH,
    )
    _validate_quant_pm_gate(gate)
    _require_unconsumed_authorization(
        runtime.ledger_path,
        authorization_id=authorization["authorization_id"],
    )
    reference_names = _load_frozen_reference_names(config)
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


def _execute_authorized(
    preflight: Mapping[str, Any],
    *,
    runtime: PrescreenRuntime,
) -> dict[str, Any]:
    receipt: dict[str, Any] | None = None
    prepared = _prepare_unlabeled_inputs(preflight)
    try:
        receipt = claim_single_prescreen_authorization(
            packet_path=runtime.authorization_path,
            ledger_path=runtime.ledger_path,
            expected_candidate_name=FACTOR_NAME,
            expected_config_sha256=str(preflight["config_sha256"]),
            expected_packet_sha256=str(preflight["authorization_sha256"]),
            expected_allowed_stage=STAGE,
            expected_source_hash_keys=SOURCE_KEYS,
            context="CN ETF fund-structure crowding prescreen",
        )
        config = dict(preflight["config"])
        evaluation = config["evaluation"]
        labels = make_forward_returns(
            prepared.bars[["date", "asset_id", "market", "adj_close"]],
            horizons=tuple(int(value) for value in evaluation["horizons"]),
            execution_lag=int(evaluation["execution_lag"]),
        )
        raw_label_rows = int(len(labels))
        labels = filter_market_calendar_aligned_forward_returns(labels, prepared.bars)
        start = pd.Timestamp(config["data_boundary"]["analysis_start_date"])
        end = pd.Timestamp(config["data_boundary"]["analysis_end_date"])
        dates = pd.to_datetime(labels["date"])
        labels = labels[dates.between(start, end)].reset_index(drop=True)
        result = _summarize_prepared(preflight, prepared, labels)
        result["configuration"] = {
            "path": str(runtime.config_path),
            "sha256": str(preflight["config_sha256"]),
            "preregistration_result_sha256": str(
                preflight["preregistration_result_sha256"]
            ),
            "authorization_sha256": str(preflight["authorization_sha256"]),
        }
        result["source_hashes"] = dict(preflight["source_hashes"])
        result["canonical_data_sha256"] = str(preflight.get("canonical_data_sha256", ""))
        result["data_window"] = {
            **prepared.metadata,
            "raw_forward_label_rows": raw_label_rows,
            "calendar_aligned_forward_label_rows": int(len(labels)),
            "market_calendar_alignment_required": True,
        }
        result["authorization"] = {
            "authorization_id": str(preflight["authorization_id"]),
            "execution_claim_recorded": True,
            "max_executions": 1,
        }
        paths = write_cn_etf_fund_structure_crowding_prescreen(runtime.output_dir, result)
        manifest_path, artifact_hashes = _write_hash_manifest(
            runtime,
            preflight=preflight,
            paths=paths,
        )
        outcome_path = _write_execution_outcome(
            runtime.output_dir,
            {
                "stage": STAGE,
                "status": "completed",
                "completed_at": datetime.now(timezone.utc).isoformat(),
                "authorization_id": str(preflight["authorization_id"]),
                "authorization_claim": receipt,
                "result_status": result["status"],
                "artifact_hashes": artifact_hashes,
                "manifest_path": str(manifest_path),
            },
        )
        result["artifacts"] = {
            **{name: str(path) for name, path in paths.items()},
            "hash_manifest": str(manifest_path),
            "execution_outcome": str(outcome_path),
        }
        result["artifact_hashes"] = artifact_hashes
        return result
    except Exception as exc:
        if receipt is not None:
            _write_execution_outcome(
                runtime.output_dir,
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


def _prepare_unlabeled_inputs(
    preflight: Mapping[str, Any],
) -> PreparedPrescreenInputs:
    config = dict(preflight["config"])
    boundary = config["data_boundary"]
    eligibility_config = config["eligibility"]
    candidate = config["candidate"]
    bar_root = Path(boundary["bar_root"])
    start = pd.Timestamp(boundary["analysis_start_date"])
    end = pd.Timestamp(boundary["analysis_end_date"])
    holdout = pd.Timestamp(boundary["final_holdout_start"])
    bars = load_processed_bars(bar_root, "CN_ETF", end_date=end).copy()
    bars["date"] = pd.to_datetime(bars["date"])
    if bars.empty or bars["date"].max() > end or bars["date"].ge(holdout).any():
        raise ValueError("bounded CN ETF bar read violated the frozen analysis boundary")
    fund_structure = load_etf_share_size_inputs(
        Path(boundary["fund_structure_root"]),
        "CN_ETF",
    ).copy()
    fund_structure["date"] = pd.to_datetime(fund_structure["date"])
    fund_structure["known_from"] = pd.to_datetime(fund_structure["known_from"])
    fund_structure = fund_structure[
        fund_structure["date"].le(end)
        & fund_structure["known_from"].lt(holdout)
    ].reset_index(drop=True)
    if fund_structure.empty:
        raise ValueError("bounded fund-structure read returned no rows")
    if fund_structure["known_from"].le(fund_structure["date"]).any():
        raise ValueError("fund-structure known_from boundary was violated")

    lifecycle = load_official_etf_lifecycle(
        bar_root / "metadata" / "tushare_fund_basic"
    )
    policy = EtfEligibilityPolicy(
        min_prior_observations=int(eligibility_config["min_prior_observations"]),
        liquidity_window=int(eligibility_config["liquidity_window"]),
        min_trailing_median_amount=float(
            eligibility_config["min_trailing_median_amount_cny"]
        ),
        max_stale_rate=float(eligibility_config["max_stale_price_rate"]),
        max_abs_return=float(eligibility_config["max_abs_daily_adjusted_return"]),
    )
    eligibility = build_point_in_time_etf_eligibility(bars, lifecycle, policy=policy)
    eligible_keys = eligibility[
        eligibility["eligible"] & pd.to_datetime(eligibility["date"]).le(end)
    ][["date", "asset_id", "market"]].drop_duplicates()
    factor_result = compute_etf_residual_share_creation_crowding(
        bars,
        fund_structure,
        eligible_keys=eligible_keys,
        share_lookback=int(candidate["share_lookback"]),
        short_return_window=int(candidate["short_return_window"]),
        long_return_window=int(candidate["long_return_window"]),
        volatility_window=int(candidate["volatility_window"]),
        adv_window=int(candidate["adv_window"]),
        min_cross_section=int(candidate["minimum_daily_cross_section"]),
        winsor_lower=float(candidate["winsor_lower"]),
        winsor_upper=float(candidate["winsor_upper"]),
        scale_epsilon=float(candidate["scale_epsilon"]),
    )
    factors = _analysis_slice(factor_result.factors, start=start, end=end)
    direct = _analysis_slice(factor_result.direct_exposures, start=start, end=end)
    adv20 = _analysis_slice(factor_result.adv20, start=start, end=end)
    finite = pd.to_numeric(factors["factor_value"], errors="coerce").replace(
        [np.inf, -np.inf], np.nan
    )
    evaluation_keys = factors.loc[
        finite.notna(), ["date", "asset_id", "market"]
    ].drop_duplicates()
    if evaluation_keys.empty:
        raise ValueError("fund-structure crowding factor produced no finite values")
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
    return PreparedPrescreenInputs(
        bars=bars,
        factors=factors,
        references=references,
        direct_exposures=direct,
        adv20=adv20,
        metadata={
            "analysis_start_date": start.date().isoformat(),
            "analysis_end_date": end.date().isoformat(),
            "history_rows": int(len(bars)),
            "history_assets": int(bars["asset_id"].nunique()),
            "history_dates": int(bars["date"].nunique()),
            "fund_structure_rows": int(len(fund_structure)),
            "fund_structure_assets": int(fund_structure["asset_id"].nunique()),
            "eligible_rows": int(len(eligible_keys)),
            "candidate_rows": int(len(factors)),
            "finite_candidate_rows": int(finite.notna().sum()),
            "candidate_assets": int(evaluation_keys["asset_id"].nunique()),
            "candidate_dates": int(pd.to_datetime(evaluation_keys["date"]).nunique()),
            "reference_rows": int(len(references)),
            "later_partitions_skipped_before_read": True,
            "final_holdout_included": False,
        },
    )


def _summarize_prepared(
    preflight: Mapping[str, Any],
    prepared: PreparedPrescreenInputs,
    labels: pd.DataFrame,
) -> dict[str, Any]:
    config = dict(preflight["config"])
    evaluation = config["evaluation"]
    reference = config["reference_policy"]
    capacity = config["capacity"]
    costs = config["costs"]
    return summarize_cn_etf_fund_structure_crowding_prescreen(
        prepared.factors,
        labels,
        prepared.references,
        prepared.direct_exposures,
        prepared.adv20,
        expected_reference_names=tuple(preflight["reference_names"]),
        direct_exposure_names=tuple(reference["direct_exposure_names"]),
        horizons=tuple(int(value) for value in evaluation["horizons"]),
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
        one_way_costs_bps=tuple(float(value) for value in costs["one_way_bps"]),
        required_positive_net_spread_bps=float(costs["required_positive_net_spread_bps"]),
        diagnostic_min_mean_rank_ic=float(evaluation["diagnostic_minimum_mean_rank_ic"]),
        diagnostic_min_quantile_spread=float(
            evaluation["diagnostic_minimum_top_minus_bottom_spread"]
        ),
    )


def _load_and_validate_config(path: Path, *, expected_sha256: str) -> dict[str, Any]:
    _require_hash(path, expected_sha256, "config")
    payload = _load_preregistration_config(path)
    if payload["candidate"]["factor_name"] != FACTOR_NAME:
        raise ValueError("config candidate does not match the frozen factor")
    if tuple(payload["evaluation"]["horizons"]) != (5, 20):
        raise ValueError("config horizons do not match the frozen prescreen")
    if tuple(payload["reference_policy"]["direct_exposure_names"]) != DIRECT_EXPOSURE_NAMES:
        raise ValueError("config direct exposures do not match the frozen prescreen")
    return payload


def _load_frozen_reference_names(config: Mapping[str, Any]) -> tuple[str, ...]:
    names = []
    for item in config["reference_policy"]["reference_configs"]:
        path = Path(item["path"])
        _require_hash(path, str(item["sha256"]), f"reference config {path}")
        payload = _load_json_object(path, f"reference config {path}")
        if not isinstance(payload.get("candidate_names"), list) or not isinstance(
            payload.get("reference_names"), list
        ):
            raise ValueError(f"reference config names are invalid: {path}")
        names.extend(str(value) for value in payload["candidate_names"])
        names.extend(str(value) for value in payload["reference_names"])
    observed = tuple(names)
    if observed != CLOSED_FAMILY_REFERENCE_NAMES or len(set(observed)) != len(observed):
        raise ValueError("reference configs do not produce the exact frozen 39-name union")
    return observed


def _validate_scheduler_decision(
    scheduler: Mapping[str, Any],
    *,
    authorization_id: str,
    authorization_path: Path,
) -> None:
    decision = scheduler.get("last_decision")
    if not isinstance(decision, Mapping):
        raise ValueError("scheduler last_decision is missing")
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


def _validate_quant_pm_gate(gate: Mapping[str, Any]) -> None:
    if gate.get("status") != "ready" or gate.get("mode") != "single_prescreen_only":
        raise ValueError("Quant PM gate did not authorize single_prescreen_only")
    if gate.get("blockers") != []:
        raise ValueError("Quant PM gate contains blockers")
    selected = gate.get("selected", {})
    if (
        selected.get("machine") != "office_desktop"
        or selected.get("task") != "factor_batch"
        or selected.get("branch") != EXPECTED_BRANCH
        or selected.get("current_branch") != EXPECTED_BRANCH
    ):
        raise ValueError("Quant PM selected context mismatch")
    safety = gate.get("safety", {})
    if safety.get("factor_batch_allowed") is not True:
        raise ValueError("Quant PM factor batch is not allowed")
    expected_scope = {
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
    if safety.get("factor_batch_scope") != expected_scope:
        raise ValueError("Quant PM factor-batch scope mismatch")


def _validate_default_runtime(runtime: PrescreenRuntime) -> None:
    expected = PrescreenRuntime()
    for field in (
        "config_path",
        "preregistration_result_path",
        "authorization_path",
        "scheduler_path",
        "ledger_path",
        "output_dir",
    ):
        if Path(getattr(runtime, field)).resolve() != Path(getattr(expected, field)).resolve():
            raise ValueError(f"runtime {field} must remain on the frozen path")
    if Path("data/reports").resolve() not in runtime.output_dir.resolve().parents:
        raise ValueError("prescreen output must remain under data/reports")


def _require_unconsumed_authorization(path: Path, *, authorization_id: str) -> None:
    if not path.exists():
        return
    payload = _load_json_object(path, "single-prescreen execution ledger")
    claims = payload.get("claims")
    if not isinstance(claims, Mapping):
        raise ValueError("single-prescreen execution ledger claims are invalid")
    if authorization_id in claims:
        raise ValueError(f"single prescreen authorization already consumed: {authorization_id}")


def _write_hash_manifest(
    runtime: PrescreenRuntime,
    *,
    preflight: Mapping[str, Any],
    paths: Mapping[str, Path],
) -> tuple[Path, dict[str, str]]:
    artifact_hashes = {name: sha256_file(path) for name, path in sorted(paths.items())}
    path = atomic_write_json(
        runtime.output_dir / "hash_manifest.json",
        {
            "stage": STAGE,
            "config_sha256": str(preflight["config_sha256"]),
            "preregistration_result_sha256": str(
                preflight["preregistration_result_sha256"]
            ),
            "authorization_sha256": str(preflight["authorization_sha256"]),
            "authorization_id": str(preflight["authorization_id"]),
            "source_hashes": dict(preflight["source_hashes"]),
            "canonical_data_sha256": str(preflight.get("canonical_data_sha256", "")),
            "artifact_hashes": artifact_hashes,
        },
    )
    return path, artifact_hashes


def _write_execution_outcome(output_dir: Path, payload: Mapping[str, Any]) -> Path:
    return atomic_write_json(output_dir / "execution_outcome.json", dict(payload))


def _analysis_slice(
    frame: pd.DataFrame,
    *,
    start: pd.Timestamp,
    end: pd.Timestamp,
) -> pd.DataFrame:
    dates = pd.to_datetime(frame["date"])
    return frame[dates.between(start, end)].reset_index(drop=True)


def _canonical_data_hash(source_hashes: Mapping[str, str]) -> str:
    canonical = {
        key: source_hashes[key]
        for key in SOURCE_KEYS
        if key.startswith("canonical_")
    }
    encoded = json.dumps(canonical, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


def _require_hash(path: Path, expected: str, label: str) -> None:
    if not path.is_file():
        raise FileNotFoundError(f"{label} is missing: {path}")
    observed = sha256_file(path)
    if observed != expected:
        raise ValueError(f"{label} hash mismatch: expected {expected}, observed {observed}")


def _load_json_object(path: Path, label: str) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"{label} is missing: {path}")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"{label} is invalid JSON: {path}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must be a JSON object: {path}")
    return payload


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Run the one authorized CN ETF fund-structure crowding prescreen."
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preflight-only", action="store_true")
    mode.add_argument("--execute-authorized", action="store_true")
    args = parser.parse_args()
    result = run_cn_etf_fund_structure_crowding_prescreen_cli(
        mode="execute" if args.execute_authorized else "preflight"
    )
    print(
        json.dumps(
            {
                "stage": result.get("stage"),
                "status": result.get("status"),
                "authorization_id": result.get("authorization_id")
                or result.get("authorization", {}).get("authorization_id"),
                "execution_claim_recorded": result.get("execution_claim_recorded")
                if "execution_claim_recorded" in result
                else result.get("authorization", {}).get("execution_claim_recorded"),
                "decision": result.get("decision"),
                "artifacts": result.get("artifacts"),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
