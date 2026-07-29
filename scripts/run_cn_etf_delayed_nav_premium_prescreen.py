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

from quant_robot.data.etf_point_in_time_universe import (  # noqa: E402
    EtfEligibilityPolicy,
    build_point_in_time_etf_eligibility,
    load_official_etf_lifecycle,
)
from quant_robot.factors.etf_delayed_nav_premium_innovation import (  # noqa: E402
    DIRECT_EXPOSURE_NAMES,
    FACTOR_NAME,
    compute_etf_delayed_nav_premium_innovation,
)
from quant_robot.ops.cn_etf_delayed_nav_premium_prescreen import (  # noqa: E402
    CLOSED_FAMILY_REFERENCE_NAMES,
    STAGE,
    compute_closed_family_reference_union,
    summarize_cn_etf_delayed_nav_premium_prescreen,
    write_cn_etf_delayed_nav_premium_prescreen,
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
from scripts.run_cn_etf_delayed_nav_premium_preregistration import (  # noqa: E402
    SOURCE_KEYS,
    _load_and_validate_config as _load_preregistration_config,
)
from scripts.run_quant_pm_startup_gate import run_quant_pm_startup_gate  # noqa: E402


DEFAULT_CONFIG = Path(
    "configs/cn_etf_delayed_nav_premium_innovation_reversal_60_20260729.json"
)
DEFAULT_PREREGISTRATION_RESULT = Path(
    "data/reports/cn_etf_delayed_nav_premium_preregistration_20260729/"
    "cn_etf_delayed_nav_premium_preregistration.json"
)
DEFAULT_AUTHORIZATION = Path(
    "data/reports/cn_etf_delayed_nav_premium_preregistration_20260729/"
    "single_prescreen_authorization.json"
)
DEFAULT_SCHEDULER = Path("configs/research_family_scheduler_cn_etf.json")
DEFAULT_LEDGER = Path(
    "data/reports/cn_etf_delayed_nav_premium_prescreen_execution_ledger.json"
)
DEFAULT_OUTPUT_DIR = Path(
    "data/reports/cn_etf_delayed_nav_premium_prescreen_20260729"
)
EXPECTED_BRANCH = "codex/factor-review-cn-etf-current-access-20260728"
PREFLIGHT_STAGE = "cn_etf_delayed_nav_premium_prescreen_preflight"
FROZEN_HASHES = {
    "config": "2b2af772c377257531cd9692550790def6c6112862f37d1208abd65f4c8f11f9",
    "preregistration_result": (
        "98c15eef32ade8180d74a402e65aadaba6e903a1310838ff5c653cedb73dcaa3"
    ),
    "authorization": (
        "2866603a951b63c11f05422d9fa6890ab2f7231a5d3313f118e3c3c8e830c7f4"
    ),
    "source_config": (
        "0cc8f1d5ea88e1c262b32d3b698275e0552df1da7f65df5a3cbc9c50de032814"
    ),
    "source_result": (
        "151a30944fd4ca62fd765af2a48fa33b5dc3997e469af7bf923b126179b53f8b"
    ),
    "request_manifest": (
        "35a2c5331b2ca3efae870010c2604099be4ab6d6ec6b1046208d3038a1f2e920"
    ),
    "canonical_nav": (
        "8cbc3a63561dbfcb0a42dcef56b053da484c149f32f1554ff271c1875cb6338a"
    ),
    "session_coverage": (
        "9b1483919cafeaf497ecea2581eeb7193408f2995c9f5edc22bd02fe48704f1e"
    ),
    "nav_agreement": (
        "62d4b65694a1fa5d3d204e9fa76702d71b2946ee92956a5aa80562102f64a7c4"
    ),
    "small_capital_inputs": (
        "06ab14e15b6ba6bff0cd586ffa86ceef5d8873c4cb767790056dff5f97afaf41"
    ),
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
    metadata: dict[str, Any]


def run_cn_etf_delayed_nav_premium_prescreen_cli(
    *,
    mode: str,
    runtime: PrescreenRuntime = PrescreenRuntime(),
) -> dict[str, Any]:
    if mode not in {"preflight", "execute"}:
        raise ValueError("mode must be preflight or execute")
    preflight = preflight_cn_etf_delayed_nav_premium_prescreen(runtime=runtime)
    return preflight if mode == "preflight" else _execute(preflight, runtime=runtime)


def preflight_cn_etf_delayed_nav_premium_prescreen(
    *,
    runtime: PrescreenRuntime = PrescreenRuntime(),
) -> dict[str, Any]:
    _validate_runtime(runtime)
    config = _load_config(runtime.config_path, expected_sha256=FROZEN_HASHES["config"])
    source_paths = {
        key: Path(config["source_evidence"]["paths"][key])
        for key in SOURCE_KEYS
    }
    source_hashes = {}
    for key, path in source_paths.items():
        _require_hash(path, FROZEN_HASHES[key], f"source {key}")
        source_hashes[key] = FROZEN_HASHES[key]
    _require_hash(
        runtime.preregistration_result_path,
        FROZEN_HASHES["preregistration_result"],
        "preregistration result",
    )
    preregistration = _load_json(
        runtime.preregistration_result_path,
        "delayed-NAV premium preregistration result",
    )
    if preregistration.get("status") != "preregistered_single_prescreen":
        raise ValueError("preregistration result is not ready")
    authorization = validate_single_prescreen_authorization(
        packet_path=runtime.authorization_path,
        expected_candidate_name=FACTOR_NAME,
        expected_config_sha256=FROZEN_HASHES["config"],
        expected_packet_sha256=FROZEN_HASHES["authorization"],
        expected_allowed_stage=STAGE,
        expected_source_hash_keys=SOURCE_KEYS,
        expected_primary_horizon=1,
        expected_diagnostic_horizon=5,
        context="CN ETF delayed-NAV premium prescreen preflight",
    )
    packet = authorization["packet"]
    if packet.get("preregistration_result_sha256") != FROZEN_HASHES["preregistration_result"]:
        raise ValueError("authorization preregistration result hash mismatch")
    if packet.get("source_hashes") != source_hashes:
        raise ValueError("authorization source hashes mismatch")
    if Path(str(packet.get("execution_ledger_path"))).resolve() != runtime.ledger_path.resolve():
        raise ValueError("authorization ledger path mismatch")
    scheduler = _load_json(runtime.scheduler_path, "research-family scheduler")
    _validate_scheduler(
        scheduler,
        authorization_id=str(authorization["authorization_id"]),
        authorization_path=runtime.authorization_path,
    )
    gate = run_quant_pm_startup_gate(
        machine="office_desktop",
        task="factor_batch",
        branch=EXPECTED_BRANCH,
    )
    _validate_gate(gate)
    _require_unconsumed(runtime.ledger_path, str(authorization["authorization_id"]))
    return {
        "stage": PREFLIGHT_STAGE,
        "status": "ready_unconsumed",
        "config": config,
        "config_sha256": FROZEN_HASHES["config"],
        "preregistration_result_sha256": FROZEN_HASHES["preregistration_result"],
        "authorization_sha256": FROZEN_HASHES["authorization"],
        "authorization_id": authorization["authorization_id"],
        "source_hashes": source_hashes,
        "canonical_data_sha256": FROZEN_HASHES["canonical_nav"],
        "reference_names": list(CLOSED_FAMILY_REFERENCE_NAMES),
        "forward_labels_read": False,
        "execution_claim_recorded": False,
        "quant_pm_gate": {
            "status": gate["status"],
            "mode": gate["mode"],
            "factor_batch_scope": gate["safety"]["factor_batch_scope"],
        },
    }


def _execute(
    preflight: Mapping[str, Any],
    *,
    runtime: PrescreenRuntime,
) -> dict[str, Any]:
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
            expected_primary_horizon=1,
            expected_diagnostic_horizon=5,
            context="CN ETF delayed-NAV premium prescreen",
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
        start = pd.Timestamp(config["data_boundary"]["analysis_start_date"])
        end = pd.Timestamp(config["data_boundary"]["analysis_end_date"])
        labels = labels[
            pd.to_datetime(labels["date"]).between(start, end)
        ].reset_index(drop=True)
        result = _summarize(preflight, prepared, labels)
        result["configuration"] = {
            "path": str(runtime.config_path),
            "sha256": str(preflight["config_sha256"]),
            "preregistration_result_sha256": str(
                preflight["preregistration_result_sha256"]
            ),
            "authorization_sha256": str(preflight["authorization_sha256"]),
        }
        result["source_hashes"] = dict(preflight["source_hashes"])
        result["canonical_data_sha256"] = str(
            preflight.get("canonical_data_sha256", "")
        )
        result["data_window"] = {
            **prepared.metadata,
            "raw_forward_label_rows": raw_rows,
            "calendar_aligned_forward_label_rows": int(len(labels)),
            "market_calendar_alignment_required": True,
            "final_holdout_included": False,
        }
        result["authorization"] = {
            "authorization_id": str(preflight["authorization_id"]),
            "execution_claim_recorded": True,
            "max_executions": 1,
        }
        paths = write_cn_etf_delayed_nav_premium_prescreen(
            runtime.output_dir,
            result,
        )
        manifest_path, hashes = _write_hash_manifest(runtime, preflight, paths)
        outcome_path = atomic_write_json(
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
            "execution_outcome": str(outcome_path),
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
    eligibility_config = config["eligibility"]
    candidate = config["candidate"]
    start = pd.Timestamp(boundary["analysis_start_date"])
    end = pd.Timestamp(boundary["analysis_end_date"])
    holdout = pd.Timestamp(boundary["final_holdout_start"])
    bar_root = Path(boundary["bar_root"])
    bars = load_processed_bars(bar_root, "CN_ETF", end_date=end).copy()
    bars["date"] = pd.to_datetime(bars["date"], errors="raise").dt.normalize()
    if bars.empty or bars["date"].max() > end or bars["date"].ge(holdout).any():
        raise ValueError("bounded CN ETF bar read violated the frozen analysis boundary")
    nav = pd.read_parquet(Path(boundary["canonical_nav_path"])).copy()
    nav["nav_date"] = pd.to_datetime(nav["nav_date"], errors="coerce").dt.normalize()
    nav["known_from"] = pd.to_datetime(nav["known_from"], errors="coerce").dt.normalize()
    if nav.empty or nav["known_from"].ge(holdout).any():
        raise ValueError("bounded NAV read violated the frozen holdout boundary")
    official_sessions = _load_official_sessions(boundary)
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
        max_abs_return=float(
            eligibility_config["max_abs_daily_adjusted_return"]
        ),
    )
    eligibility = build_point_in_time_etf_eligibility(bars, lifecycle, policy=policy)
    nav_assets = set(nav["asset_id"].astype(str))
    eligible_keys = eligibility[
        eligibility["eligible"]
        & eligibility["asset_id"].astype(str).isin(nav_assets)
        & pd.to_datetime(eligibility["date"]).le(end)
    ][["date", "asset_id", "market"]].drop_duplicates()
    if eligible_keys.empty:
        raise ValueError("NAV-backed point-in-time ETF eligibility is empty")
    factor_result = compute_etf_delayed_nav_premium_innovation(
        bars,
        nav,
        eligible_keys=eligible_keys,
        official_sessions=official_sessions,
        premium_lookback=int(candidate["premium_lookback"]),
    )
    factors = _slice(factor_result.factors, start=start, end=end)
    direct = _slice(factor_result.direct_exposures, start=start, end=end)
    adv20 = _slice(factor_result.adv20, start=start, end=end)
    finite = pd.to_numeric(factors["factor_value"], errors="coerce").replace(
        [np.inf, -np.inf],
        np.nan,
    )
    evaluation_keys = factors.loc[
        finite.notna(), ["date", "asset_id", "market"]
    ].drop_duplicates()
    if evaluation_keys.empty:
        raise ValueError("delayed-NAV premium factor produced no finite values")
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
        metadata={
            "analysis_start_date": start.date().isoformat(),
            "analysis_end_date": end.date().isoformat(),
            "history_rows": int(len(bars)),
            "history_assets": int(bars["asset_id"].nunique()),
            "history_dates": int(bars["date"].nunique()),
            "nav_rows": int(len(nav)),
            "nav_assets": int(nav["asset_id"].nunique()),
            "eligible_rows": int(len(eligible_keys)),
            "candidate_rows": int(len(factors)),
            "finite_candidate_rows": int(finite.notna().sum()),
            "candidate_assets": int(evaluation_keys["asset_id"].nunique()),
            "candidate_dates": int(
                pd.to_datetime(evaluation_keys["date"]).nunique()
            ),
            "reference_rows": int(len(references)),
            "later_partitions_skipped_before_read": True,
            "current_name_input_used": False,
            "current_theme_input_used": False,
            "final_holdout_included": False,
        },
    )


def _summarize(
    preflight: Mapping[str, Any],
    prepared: PreparedInputs,
    labels: pd.DataFrame,
) -> dict[str, Any]:
    thresholds = dict(preflight["config"]["thresholds"])
    return summarize_cn_etf_delayed_nav_premium_prescreen(
        prepared.factors,
        labels,
        prepared.references,
        prepared.direct_exposures,
        prepared.adv20,
        min_cross_section=int(thresholds["minimum_daily_cross_section"]),
        min_ic_observations=int(thresholds["minimum_ic_observations"]),
        min_year_ic_observations=int(
            thresholds["minimum_yearly_ic_observations"]
        ),
        min_usable_years=int(thresholds["minimum_usable_years"]),
        alpha=float(thresholds["newey_west_alpha"]),
        min_mean_rank_ic=float(thresholds["minimum_mean_rank_ic"]),
        min_icir=float(thresholds["minimum_icir"]),
        min_positive_ic_rate=float(thresholds["minimum_positive_ic_rate"]),
        min_quantile_monotonicity=float(
            thresholds["minimum_quintile_monotonicity"]
        ),
        max_top_quantile_turnover=float(
            thresholds["maximum_top_quintile_turnover"]
        ),
        min_positive_year_rate=float(thresholds["minimum_positive_year_rate"]),
        max_abs_reference_correlation=float(
            thresholds["maximum_abs_mean_daily_reference_correlation"]
        ),
        direct_min_daily_observations=int(
            thresholds["direct_minimum_daily_observations"]
        ),
        max_abs_direct_exposure_correlation=float(
            thresholds["maximum_abs_direct_exposure_correlation"]
        ),
        diagnostic_min_mean_rank_ic=float(
            thresholds["diagnostic_minimum_mean_rank_ic"]
        ),
        diagnostic_min_quantile_spread=float(
            thresholds["diagnostic_minimum_top_minus_bottom_spread"]
        ),
    )


def _load_official_sessions(boundary: Mapping[str, Any]) -> pd.DatetimeIndex:
    calendar = pd.read_csv(Path(boundary["trading_calendar_path"]))
    required = {"market", "date", "is_open"}
    if not required.issubset(calendar.columns):
        raise ValueError("official trading calendar schema is invalid")
    calendar["date"] = pd.to_datetime(calendar["date"], errors="raise").dt.normalize()
    sessions = calendar[
        calendar["market"].astype(str).str.upper().eq("CN")
        & pd.to_numeric(calendar["is_open"], errors="coerce").eq(1)
    ]["date"]
    result = pd.DatetimeIndex(sessions).drop_duplicates().sort_values()
    if result.empty:
        raise ValueError("official trading calendar has no CN sessions")
    return result


def _load_config(path: Path, *, expected_sha256: str) -> dict[str, Any]:
    _require_hash(path, expected_sha256, "config")
    config = _load_preregistration_config(path)
    if config["candidate"]["factor_name"] != FACTOR_NAME:
        raise ValueError("config candidate does not match the frozen factor")
    if tuple(config["evaluation"]["horizons"]) != (1, 5):
        raise ValueError("config horizons do not match the frozen prescreen")
    if tuple(config["reference_policy"]["direct_exposure_names"]) != DIRECT_EXPOSURE_NAMES:
        raise ValueError("config direct exposures do not match the frozen factor")
    return config


def _validate_scheduler(
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
        "canonical_data_sha256": FROZEN_HASHES["canonical_nav"],
        "hypothesis_count": 1,
        "primary_horizon": 1,
        "diagnostic_horizon": 5,
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
    expected_scope = {
        "allowed_stage": STAGE,
        "authorization_sha256": FROZEN_HASHES["authorization"],
        "canonical_data_sha256": FROZEN_HASHES["canonical_nav"],
        "config_sha256": FROZEN_HASHES["config"],
        "execution_count": 0,
        "execution_ledger_path": str(DEFAULT_LEDGER).replace("\\", "/"),
        "factor_name": FACTOR_NAME,
        "max_executions": 1,
        "preregistration_result_sha256": FROZEN_HASHES["preregistration_result"],
        "source_config_sha256": FROZEN_HASHES["source_config"],
        "source_result_sha256": FROZEN_HASHES["source_result"],
    }
    safety = gate.get("safety", {})
    if safety.get("factor_batch_allowed") is not True:
        raise ValueError("Quant PM factor batch is not allowed")
    if safety.get("factor_batch_scope") != expected_scope:
        raise ValueError("Quant PM factor-batch scope mismatch")


def _validate_runtime(runtime: PrescreenRuntime) -> None:
    expected = PrescreenRuntime()
    for field in (
        "config_path",
        "preregistration_result_path",
        "authorization_path",
        "scheduler_path",
        "ledger_path",
        "output_dir",
    ):
        if Path(getattr(runtime, field)).resolve() != Path(
            getattr(expected, field)
        ).resolve():
            raise ValueError(f"runtime {field} must remain on the frozen path")
    if Path("data/reports").resolve() not in runtime.output_dir.resolve().parents:
        raise ValueError("prescreen output must remain under data/reports")


def _require_unconsumed(path: Path, authorization_id: str) -> None:
    if not path.exists():
        return
    ledger = _load_json(path, "single-prescreen execution ledger")
    claims = ledger.get("claims")
    if not isinstance(claims, Mapping):
        raise ValueError("single-prescreen execution ledger claims are invalid")
    if authorization_id in claims:
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
            "preregistration_result_sha256": str(
                preflight["preregistration_result_sha256"]
            ),
            "authorization_sha256": str(preflight["authorization_sha256"]),
            "authorization_id": str(preflight["authorization_id"]),
            "source_hashes": dict(preflight["source_hashes"]),
            "canonical_data_sha256": str(
                preflight.get("canonical_data_sha256", "")
            ),
            "artifact_hashes": hashes,
        },
    )
    return path, hashes


def _slice(
    frame: pd.DataFrame,
    *,
    start: pd.Timestamp,
    end: pd.Timestamp,
) -> pd.DataFrame:
    dates = pd.to_datetime(frame["date"], errors="raise")
    return frame[dates.between(start, end)].reset_index(drop=True)


def _require_hash(path: Path, expected: str, label: str) -> None:
    if not path.is_file():
        raise FileNotFoundError(f"{label} is missing: {path}")
    observed = sha256_file(path)
    if observed != expected:
        raise ValueError(
            f"{label} hash mismatch: expected {expected}, observed {observed}"
        )


def _load_json(path: Path, label: str) -> dict[str, Any]:
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
        description="Run the single-use delayed-NAV premium prescreen."
    )
    parser.add_argument(
        "--mode",
        choices=("preflight", "execute"),
        default="preflight",
    )
    args = parser.parse_args()
    result = run_cn_etf_delayed_nav_premium_prescreen_cli(mode=args.mode)
    print(
        json.dumps(
            {
                "stage": result.get("stage"),
                "status": result.get("status"),
                "execution_claim_recorded": result.get(
                    "execution_claim_recorded"
                )
                if "execution_claim_recorded" in result
                else result.get("authorization", {}).get(
                    "execution_claim_recorded"
                ),
                "decision": result.get("decision"),
                "artifacts": result.get("artifacts", {}),
                "artifact_hashes": result.get("artifact_hashes", {}),
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
