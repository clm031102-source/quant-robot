from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any, Mapping

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402

from quant_robot.data.etf_point_in_time_universe import (  # noqa: E402
    EtfEligibilityPolicy,
    build_point_in_time_etf_eligibility,
    load_official_etf_lifecycle,
)
from quant_robot.factors.etf_dynamic_peer_dislocation import (  # noqa: E402
    DIRECT_EXPOSURE_NAMES,
    FACTOR_NAME,
    compute_etf_dynamic_peer_dislocation,
)
from quant_robot.ops.cn_etf_dynamic_peer_dislocation_prescreen import (  # noqa: E402
    CLOSED_FAMILY_REFERENCE_NAMES,
    STAGE,
    compute_closed_family_reference_union,
    summarize_cn_etf_dynamic_peer_dislocation_prescreen,
    write_cn_etf_dynamic_peer_dislocation_prescreen,
)
from quant_robot.research.dynamic_comovement_peer_source import (  # noqa: E402
    MAPPING_METHOD,
    validate_dynamic_peer_mapping,
)
from quant_robot.research.labels import make_forward_returns  # noqa: E402
from quant_robot.storage.atomic import atomic_write_json  # noqa: E402
from quant_robot.storage.fingerprints import sha256_file  # noqa: E402
from quant_robot.storage.processed_bars import load_processed_bars  # noqa: E402
from quant_robot.validation.single_prescreen_authorization import (  # noqa: E402
    claim_single_prescreen_authorization,
    validate_single_prescreen_authorization,
)
from scripts.run_cn_etf_dynamic_peer_dislocation_preregistration import (  # noqa: E402
    _load_and_validate_config as _load_preregistration_config,
)
from scripts.run_quant_pm_startup_gate import run_quant_pm_startup_gate  # noqa: E402


DEFAULT_CONFIG = Path("configs/cn_etf_dynamic_peer_dislocation_preregistration_20260716.json")
DEFAULT_PREREGISTRATION_RESULT = Path(
    "data/reports/cn_etf_dynamic_peer_dislocation_preregistration_20260716/"
    "cn_etf_dynamic_peer_dislocation_preregistration.json"
)
DEFAULT_AUTHORIZATION = Path(
    "data/reports/cn_etf_dynamic_peer_dislocation_preregistration_20260716/"
    "single_prescreen_authorization.json"
)
DEFAULT_SCHEDULER = Path("configs/research_family_scheduler_cn_etf.json")
DEFAULT_LEDGER = Path("data/reports/cn_etf_dynamic_peer_dislocation_prescreen_execution_ledger.json")
DEFAULT_OUTPUT_DIR = Path("data/reports/cn_etf_dynamic_peer_dislocation_prescreen_20260716")
EXPECTED_BRANCH = "codex/factor-batch-cn-etf-dynamic-peer-dislocation-20260716"
PREFLIGHT_STAGE = "cn_etf_dynamic_peer_dislocation_prescreen_preflight"
FROZEN_HASHES = {
    "config": "4811e1497bbfe9688e006dcb7764381c7ea977ddfde79790248f0223996233c6",
    "preregistration_result": "2038a32fa9b250a33a76bdca08c204a349a1cdec959fc3c10dbe4b6a4f6440f5",
    "authorization": "c645de436c462365c443dd0574b750feb68b3955263b39a316b184862e99f5c9",
    "mapping": "52d7c0c80b32b164583bea52cc09e0fba7436051d236df6e1ab9343387f5fe63",
    "source_config": "a3eeda49ade9624c1e335d9adfc7a6cdd0803def723feda9ef28a99d1e9c6016",
    "source_result": "4177895b7799c5074ab0b7a0102f9a1f3917d789817e5b2380497c08346fac44",
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


def run_cn_etf_dynamic_peer_dislocation_prescreen_cli(
    *,
    mode: str,
    runtime: PrescreenRuntime = PrescreenRuntime(),
) -> dict[str, Any]:
    if mode not in {"preflight", "execute"}:
        raise ValueError("mode must be preflight or execute")
    preflight = preflight_cn_etf_dynamic_peer_dislocation_prescreen(runtime=runtime)
    if mode == "preflight":
        return preflight
    return _execute_authorized(preflight, runtime=runtime)


def preflight_cn_etf_dynamic_peer_dislocation_prescreen(
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
        for key in ("mapping", "source_config", "source_result")
    }
    for key, path in source_paths.items():
        _require_hash(path, FROZEN_HASHES[key], f"source {key}")
    _require_hash(
        runtime.preregistration_result_path,
        FROZEN_HASHES["preregistration_result"],
        "preregistration result",
    )
    reference_names = _load_frozen_reference_names(config)
    mapping = pd.read_csv(source_paths["mapping"])
    validate_dynamic_peer_mapping(mapping)
    if set(mapping["mapping_method"].dropna().astype(str)) != {MAPPING_METHOD}:
        raise ValueError("frozen mapping method mismatch")

    authorization = validate_single_prescreen_authorization(
        packet_path=runtime.authorization_path,
        expected_candidate_name=FACTOR_NAME,
        expected_config_sha256=FROZEN_HASHES["config"],
        expected_packet_sha256=FROZEN_HASHES["authorization"],
        context="CN ETF dynamic-peer prescreen preflight",
    )
    packet = authorization["packet"]
    if packet.get("preregistration_result_sha256") != FROZEN_HASHES["preregistration_result"]:
        raise ValueError("authorization preregistration result hash mismatch")
    if packet.get("source_hashes") != {
        "mapping": FROZEN_HASHES["mapping"],
        "source_config": FROZEN_HASHES["source_config"],
        "source_result": FROZEN_HASHES["source_result"],
    }:
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
    return {
        "stage": PREFLIGHT_STAGE,
        "status": "ready_unconsumed",
        "config": config,
        "config_sha256": FROZEN_HASHES["config"],
        "preregistration_result_sha256": FROZEN_HASHES["preregistration_result"],
        "authorization_sha256": FROZEN_HASHES["authorization"],
        "authorization_id": authorization["authorization_id"],
        "source_hashes": {
            "mapping": FROZEN_HASHES["mapping"],
            "source_config": FROZEN_HASHES["source_config"],
            "source_result": FROZEN_HASHES["source_result"],
        },
        "reference_names": list(reference_names),
        "mapping_rows": int(len(mapping)),
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
            context="CN ETF dynamic-peer dislocation prescreen",
        )
        config = dict(preflight["config"])
        evaluation = config["evaluation"]
        labels = make_forward_returns(
            prepared.bars[["date", "asset_id", "market", "adj_close"]],
            horizons=tuple(int(value) for value in evaluation["horizons"]),
            execution_lag=int(evaluation["execution_lag"]),
        )
        start = pd.Timestamp(config["data_boundary"]["analysis_start_date"])
        end = pd.Timestamp(config["data_boundary"]["analysis_end_date"])
        label_dates = pd.to_datetime(labels["date"])
        labels = labels[label_dates.between(start, end)].reset_index(drop=True)
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
        result["data_window"] = dict(prepared.metadata)
        result["authorization"] = {
            "authorization_id": str(preflight["authorization_id"]),
            "execution_claim_recorded": True,
            "max_executions": 1,
        }
        paths = write_cn_etf_dynamic_peer_dislocation_prescreen(runtime.output_dir, result)
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


def _prepare_unlabeled_inputs(preflight: Mapping[str, Any]) -> PreparedPrescreenInputs:
    config = dict(preflight["config"])
    boundary = config["data_boundary"]
    eligibility_config = config["eligibility"]
    candidate = config["candidate"]
    root = Path(boundary["data_root"])
    start = pd.Timestamp(boundary["analysis_start_date"])
    end = pd.Timestamp(boundary["analysis_end_date"])
    holdout = pd.Timestamp(boundary["final_holdout_start"])
    bars = load_processed_bars(root, "CN_ETF", end_date=end).copy()
    bars["date"] = pd.to_datetime(bars["date"])
    if bars.empty or bars["date"].max() > end or bars["date"].ge(holdout).any():
        raise ValueError("bounded CN ETF bar read violated the frozen analysis boundary")
    metadata_root = root / "metadata" / "tushare_fund_basic"
    lifecycle = load_official_etf_lifecycle(metadata_root)
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
    mapping_path = Path(config["source_evidence"]["paths"]["mapping"])
    mapping = pd.read_csv(mapping_path)
    factor_result = compute_etf_dynamic_peer_dislocation(
        bars,
        mapping,
        eligible_keys=eligible_keys,
        market_min_cross_section=int(candidate["market_min_cross_section"]),
        beta_window=int(candidate["beta_window"]),
        beta_min_observations=int(candidate["beta_min_observations"]),
        beta_lag=int(candidate["beta_lag"]),
        residual_sum_window=int(candidate["residual_sum_window"]),
        minimum_daily_peers=int(candidate["minimum_daily_peers"]),
        robust_scale_window=int(candidate["robust_scale_window"]),
        robust_scale_min_observations=int(candidate["robust_scale_min_observations"]),
        robust_scale_epsilon=float(candidate["robust_scale_epsilon"]),
        residual_volatility_window=60,
        residual_volatility_min_observations=40,
        momentum_window=60,
        short_return_window=5,
        adv_window=20,
    )
    factors = _analysis_slice(factor_result.factors, start=start, end=end)
    direct = _analysis_slice(factor_result.direct_exposures, start=start, end=end)
    adv20 = _analysis_slice(factor_result.adv20, start=start, end=end)
    finite_factor = pd.to_numeric(factors["factor_value"], errors="coerce").replace(
        [np.inf, -np.inf], np.nan
    )
    evaluation_keys = factors.loc[
        finite_factor.notna(), ["date", "asset_id", "market"]
    ].drop_duplicates()
    if evaluation_keys.empty:
        raise ValueError("dynamic-peer factor produced no finite analysis-window values")
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
    metadata = {
        "analysis_start_date": start.date().isoformat(),
        "analysis_end_date": end.date().isoformat(),
        "history_rows": int(len(bars)),
        "history_assets": int(bars["asset_id"].nunique()),
        "history_dates": int(bars["date"].nunique()),
        "eligible_rows": int(len(eligible_keys)),
        "eligible_assets": int(eligible_keys["asset_id"].nunique()),
        "candidate_rows": int(len(factors)),
        "finite_candidate_rows": int(finite_factor.notna().sum()),
        "candidate_assets": int(evaluation_keys["asset_id"].nunique()),
        "candidate_dates": int(pd.to_datetime(evaluation_keys["date"]).nunique()),
        "reference_rows": int(len(references)),
        "mapping_rows": int(len(mapping)),
        "later_partitions_skipped_before_read": True,
        "final_holdout_included": False,
    }
    return PreparedPrescreenInputs(
        bars=bars,
        factors=factors,
        references=references,
        direct_exposures=direct,
        adv20=adv20,
        metadata=metadata,
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
    return summarize_cn_etf_dynamic_peer_dislocation_prescreen(
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
    names: list[str] = []
    for item in config["reference_policy"]["reference_configs"]:
        path = Path(item["path"])
        _require_hash(path, str(item["sha256"]), f"reference config {path}")
        payload = _load_json_object(path, f"reference config {path}")
        candidate_names = payload.get("candidate_names")
        reference_names = payload.get("reference_names")
        if not isinstance(candidate_names, list) or not isinstance(reference_names, list):
            raise ValueError(f"reference config names are invalid: {path}")
        names.extend(str(value) for value in candidate_names)
        names.extend(str(value) for value in reference_names)
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
        "mapping_sha256": FROZEN_HASHES["mapping"],
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
    if selected.get("machine") != "office_desktop" or selected.get("task") != "factor_batch":
        raise ValueError("Quant PM selected context mismatch")
    if selected.get("branch") != EXPECTED_BRANCH or selected.get("current_branch") != EXPECTED_BRANCH:
        raise ValueError("Quant PM branch mismatch")
    safety = gate.get("safety", {})
    if safety.get("factor_batch_allowed") is not True:
        raise ValueError("Quant PM factor batch is not allowed")
    if safety.get("single_prescreen_authorization_required") is not True:
        raise ValueError("Quant PM single-prescreen authorization requirement is missing")
    for key in ("portfolio_grid_allowed", "walk_forward_allowed", "final_holdout_allowed", "live_boundary_allowed"):
        if safety.get(key) is not False:
            raise ValueError(f"Quant PM boundary must remain false: {key}")
    expected_scope = {
        "allowed_stage": STAGE,
        "authorization_sha256": FROZEN_HASHES["authorization"],
        "config_sha256": FROZEN_HASHES["config"],
        "execution_count": 0,
        "execution_ledger_path": str(DEFAULT_LEDGER).replace("\\", "/"),
        "factor_name": FACTOR_NAME,
        "mapping_sha256": FROZEN_HASHES["mapping"],
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
    output = runtime.output_dir.resolve()
    reports = Path("data/reports").resolve()
    if reports not in output.parents:
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
    manifest = {
        "stage": STAGE,
        "config_sha256": str(preflight["config_sha256"]),
        "preregistration_result_sha256": str(preflight["preregistration_result_sha256"]),
        "authorization_sha256": str(preflight["authorization_sha256"]),
        "authorization_id": str(preflight["authorization_id"]),
        "source_hashes": dict(preflight["source_hashes"]),
        "artifact_hashes": artifact_hashes,
    }
    path = atomic_write_json(runtime.output_dir / "hash_manifest.json", manifest)
    return path, artifact_hashes


def _write_execution_outcome(output_dir: Path, payload: Mapping[str, Any]) -> Path:
    return atomic_write_json(output_dir / "execution_outcome.json", dict(payload))


def _analysis_slice(frame: pd.DataFrame, *, start: pd.Timestamp, end: pd.Timestamp) -> pd.DataFrame:
    dates = pd.to_datetime(frame["date"])
    return frame[dates.between(start, end)].reset_index(drop=True)


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
        description="Run the one authorized CN ETF dynamic-peer dislocation prescreen."
    )
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--preflight-only", action="store_true")
    mode.add_argument("--execute-authorized", action="store_true")
    args = parser.parse_args()
    result = run_cn_etf_dynamic_peer_dislocation_prescreen_cli(
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
