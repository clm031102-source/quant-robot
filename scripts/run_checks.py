from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PROJECT_ROOT / "src"


@dataclass(frozen=True)
class CheckStep:
    name: str
    command: list[str]
    uses_network: bool = False


LAPTOP_CHECK_NAMES = (
    "unit_and_integration_tests",
    "compile_python",
    "project_audit",
    "readiness_check",
    "provider_status",
    "provider_evidence",
    "provider_remediation",
    "provider_remediation_rehearsal",
    "data_catalog",
    "fixture_research",
    "research_pipeline",
    "signal_snapshot",
    "paper_simulation",
    "recent_data_refresh",
    "tushare_activation_gate",
    "paper_ops_guardrail",
)

DESKTOP_VALIDATION_CHECK_NAMES = (
    "unit_and_integration_tests",
    "compile_python",
    "project_audit",
    "readiness_check",
    "provider_status",
    "data_catalog",
    "data_quality_audit",
)

DAILY_BASIC_VALIDATION_CONFIG = "configs/walk_forward_cn_stock_daily_basic_value_low_turnover_bucket_20260620.json"
DAILY_BASIC_AUTHORITY_BARS_CONFIG = "configs/cn_stock_authority_bars_2015_2025.json"
DAILY_BASIC_AUTHORITY_INPUTS_CONFIG = "configs/cn_stock_authority_daily_basic_inputs_2015_2025.json"
DAILY_BASIC_PROMOTION_CONFIG = (
    "configs/promotion_gate_cn_stock_daily_basic_value_low_turnover_bucket_20260620.json"
)
DAILY_BASIC_VALIDATION_ROOT = "data/reports/walk_forward_cn_stock_daily_basic_value_low_turnover_bucket_20260620"
DAILY_BASIC_DATA_QUALITY_DIR = (
    "data/reports/data_quality_gap_audit_cn_stock_daily_basic_value_low_turnover_bucket_20260620"
)
DAILY_BASIC_PROGRESS_AUDIT_DIR = (
    "data/reports/walk_forward_progress_audit_cn_stock_daily_basic_value_low_turnover_bucket_20260620"
)
DAILY_BASIC_REGIME_COVERAGE_DIR = (
    "data/reports/market_regime_coverage_cn_stock_daily_basic_value_low_turnover_bucket_20260620"
)
RESIDUAL_LONG_CYCLE_REPLAY_DIR = "data/reports/long_cycle_factor_replay_tushare_moneyflow_residual_regime"
DAILY_BASIC_LONG_CYCLE_REPLAY_DIR = (
    "data/reports/long_cycle_factor_replay_cn_stock_daily_basic_value_low_turnover_bucket_20260620"
)
DAILY_BASIC_VALUE_SIZE_LIQUIDITY_VALIDATION_CONFIG = (
    "configs/walk_forward_cn_stock_daily_basic_value_size_liquidity_20260620.json"
)
DAILY_BASIC_VALUE_SIZE_LIQUIDITY_PROMOTION_CONFIG = (
    "configs/promotion_gate_cn_stock_daily_basic_value_size_liquidity_20260620.json"
)
DAILY_BASIC_VALUE_SIZE_LIQUIDITY_VALIDATION_ROOT = (
    "data/reports/walk_forward_cn_stock_daily_basic_value_size_liquidity_20260620"
)
DAILY_BASIC_VALUE_SIZE_LIQUIDITY_DATA_QUALITY_DIR = (
    "data/reports/data_quality_gap_audit_cn_stock_daily_basic_value_size_liquidity_20260620"
)
DAILY_BASIC_VALUE_SIZE_LIQUIDITY_PROGRESS_AUDIT_DIR = (
    "data/reports/walk_forward_progress_audit_cn_stock_daily_basic_value_size_liquidity_20260620"
)
DAILY_BASIC_VALUE_SIZE_LIQUIDITY_REGIME_COVERAGE_DIR = (
    "data/reports/market_regime_coverage_cn_stock_daily_basic_value_size_liquidity_20260620"
)
DAILY_BASIC_VALUE_SIZE_LIQUIDITY_LONG_CYCLE_REPLAY_DIR = (
    "data/reports/long_cycle_factor_replay_cn_stock_daily_basic_value_size_liquidity_20260620"
)
PRICE_VOLUME_TECHNICAL_VALIDATION_CONFIG = (
    "configs/walk_forward_cn_stock_price_volume_technical_20260620.json"
)
PRICE_VOLUME_TECHNICAL_PROMOTION_CONFIG = (
    "configs/promotion_gate_cn_stock_price_volume_technical_20260620.json"
)
PRICE_VOLUME_TECHNICAL_VALIDATION_ROOT = "data/reports/walk_forward_cn_stock_price_volume_technical_20260620"
PRICE_VOLUME_TECHNICAL_DATA_QUALITY_DIR = (
    "data/reports/data_quality_gap_audit_cn_stock_price_volume_technical_20260620"
)
PRICE_VOLUME_TECHNICAL_PROGRESS_AUDIT_DIR = (
    "data/reports/walk_forward_progress_audit_cn_stock_price_volume_technical_20260620"
)
PRICE_VOLUME_TECHNICAL_REGIME_COVERAGE_DIR = (
    "data/reports/market_regime_coverage_cn_stock_price_volume_technical_20260620"
)
PRICE_VOLUME_TECHNICAL_LONG_CYCLE_REPLAY_DIR = (
    "data/reports/long_cycle_factor_replay_cn_stock_price_volume_technical_20260620"
)


def build_check_plan(python_executable: str = sys.executable, profile: str = "full") -> list[CheckStep]:
    full_plan = [
        CheckStep("unit_and_integration_tests", [python_executable, "-m", "unittest", "discover", "-s", "tests"]),
        CheckStep("compile_python", [python_executable, "-m", "compileall", "-q", "src", "scripts", "tests"]),
        CheckStep("project_audit", [python_executable, "scripts/run_project_audit.py", "--json"]),
        CheckStep("readiness_check", [python_executable, "scripts/check_readiness.py"]),
        CheckStep("provider_status", [python_executable, "scripts/show_provider_status.py", "--output", "data/reports/provider_status/provider_status.json"]),
        CheckStep("provider_evidence", [python_executable, "scripts/run_provider_evidence.py"]),
        CheckStep("provider_remediation", [python_executable, "scripts/run_provider_remediation.py"]),
        CheckStep("provider_remediation_rehearsal", [python_executable, "scripts/run_provider_remediation_rehearsal.py"]),
        CheckStep("data_catalog", [python_executable, "scripts/show_data_catalog.py", "--root", "data", "--summary-only"]),
        CheckStep("data_quality_audit", [python_executable, "scripts/run_data_quality_audit.py"]),
        CheckStep("data_gap_resolution", [python_executable, "scripts/run_data_gap_resolution.py"]),
        CheckStep("data_gap_evidence", [python_executable, "scripts/run_data_gap_evidence.py"]),
        CheckStep("data_gap_rehearsal", [python_executable, "scripts/run_data_gap_rehearsal.py"]),
        CheckStep("fixture_research", [python_executable, "scripts/run_fixture_research.py"]),
        CheckStep("research_pipeline", [python_executable, "scripts/run_research_pipeline.py", "--source", "fixture"]),
        CheckStep("experiment_grid", [python_executable, "scripts/run_experiment_grid.py", "--source", "fixture"]),
        CheckStep("walk_forward", [python_executable, "scripts/run_walk_forward.py", "--source", "fixture"]),
        CheckStep("signal_snapshot", [python_executable, "scripts/run_signal_snapshot.py", "--source", "fixture"]),
        CheckStep("paper_simulation", [python_executable, "scripts/run_paper_simulation.py", "--source", "fixture"]),
        CheckStep("paper_observation", [python_executable, "scripts/run_paper_observation.py"]),
        CheckStep("promotion_ops", [python_executable, "scripts/run_promotion_ops.py"]),
        CheckStep("duplicate_registry", [python_executable, "scripts/run_duplicate_registry.py"]),
        CheckStep("promotion_review", [python_executable, "scripts/run_promotion_review.py"]),
        CheckStep("manual_review_rehearsal", [python_executable, "scripts/run_manual_review_rehearsal.py"]),
        CheckStep("evidence_refresh", [python_executable, "scripts/run_evidence_refresh.py"]),
        CheckStep("pre_api_readiness_board", [python_executable, "scripts/run_pre_api_readiness_board.py"]),
        CheckStep("readiness_projection", [python_executable, "scripts/run_readiness_projection.py"]),
        CheckStep("blocker_worklist", [python_executable, "scripts/run_blocker_worklist.py"]),
        CheckStep("residual_blocker_focus", [python_executable, "scripts/run_residual_blocker_focus.py"]),
        CheckStep("residual_data_gap_review", [python_executable, "scripts/run_residual_data_gap_review.py"]),
        CheckStep("residual_provider_review", [python_executable, "scripts/run_residual_provider_review.py"]),
        CheckStep("daily_ops", [python_executable, "scripts/run_daily_ops.py"]),
        CheckStep("profile_observation", [python_executable, "scripts/run_profile_observation.py"]),
        CheckStep("recent_data_refresh", [python_executable, "scripts/run_recent_data_refresh.py"]),
        CheckStep("post_refresh_replay", [python_executable, "scripts/run_post_refresh_replay.py"]),
        CheckStep("observation_sufficiency", [python_executable, "scripts/run_observation_sufficiency.py"]),
        CheckStep("expanded_observation_replay", [python_executable, "scripts/run_expanded_observation_replay.py"]),
        CheckStep("iterative_observation_expansion", [python_executable, "scripts/run_iterative_observation_expansion.py"]),
        CheckStep("tushare_activation_gate", [python_executable, "scripts/run_tushare_activation_gate.py"]),
        CheckStep("paper_observation_history", [python_executable, "scripts/run_paper_observation_history.py"]),
        CheckStep("paper_ops_guardrail", [python_executable, "scripts/run_paper_ops_guardrail.py"]),
        CheckStep("paper_ops_runbook", [python_executable, "scripts/run_paper_ops_runbook.py"]),
        CheckStep("risk_candidate_selector", [python_executable, "scripts/run_risk_candidate_selector.py"]),
        CheckStep("constrained_candidate_search", [python_executable, "scripts/run_constrained_candidate_search.py"]),
        CheckStep("paper_profile_optimizer", [python_executable, "scripts/run_paper_profile_optimizer.py"]),
    ]
    if profile == "full":
        return full_plan
    if profile == "laptop":
        selected = set(LAPTOP_CHECK_NAMES)
        return [_with_laptop_context(step) for step in full_plan if step.name in selected]
    if profile == "desktop-validation":
        selected = set(DESKTOP_VALIDATION_CHECK_NAMES)
        return [
            *_desktop_validation_safety_steps(full_plan, selected, python_executable),
            CheckStep("desktop_factor_validation", [python_executable, "scripts/run_desktop_factor_validation.py"]),
            CheckStep(
                "desktop_walk_forward_progress_audit",
                [
                    python_executable,
                    "scripts/run_walk_forward_progress_audit.py",
                    "--walk-forward-root",
                    "data/reports/walk_forward_tushare_moneyflow_residual_regime",
                    "--output-dir",
                    "data/reports/walk_forward_progress_audit_tushare_moneyflow_residual_regime",
                    "--expected-folds",
                    "38",
                ],
            ),
            _long_cycle_replay_step(
                "desktop_long_cycle_factor_replay",
                python_executable=python_executable,
                validation_root="data/reports/walk_forward_tushare_moneyflow_residual_regime",
                output_dir=RESIDUAL_LONG_CYCLE_REPLAY_DIR,
            ),
            CheckStep(
                "desktop_market_regime_coverage",
                [
                    python_executable,
                    "scripts/run_market_regime_coverage.py",
                    "--regime-curve-glob",
                    "data/reports/walk_forward_tushare_moneyflow_residual_regime/fold_*/test/*/regime_curve.csv",
                    "--output-dir",
                    "data/reports/market_regime_coverage_tushare_moneyflow_residual_regime",
                    "--min-regimes",
                    "2",
                    "--min-rows-per-regime",
                    "5",
                    "--min-allowed-rows",
                    "5",
                    "--min-blocked-rows",
                    "5",
                    "--min-signal-window-allowed-rows",
                    "5",
                    "--min-signal-window-blocked-rows",
                    "5",
                    "--require-sufficient",
                ],
            ),
            CheckStep(
                "desktop_promotion_report",
                [
                    python_executable,
                    "scripts/run_promotion_report.py",
                    "--config",
                    "configs/promotion_gate_tushare_moneyflow_residual_regime.json",
                ],
            ),
            CheckStep("desktop_validation_summary", [python_executable, "scripts/run_desktop_validation_summary.py"]),
        ]
    if profile == "desktop-daily-basic-validation":
        selected = set(DESKTOP_VALIDATION_CHECK_NAMES)
        return [
            *_desktop_validation_safety_steps(
                full_plan,
                selected,
                python_executable,
                data_root=DAILY_BASIC_AUTHORITY_BARS_CONFIG,
                daily_basic_root=DAILY_BASIC_AUTHORITY_INPUTS_CONFIG,
                data_quality_output_dir=DAILY_BASIC_DATA_QUALITY_DIR,
            ),
            CheckStep(
                "desktop_daily_basic_factor_validation",
                [
                    python_executable,
                    "scripts/run_desktop_factor_validation.py",
                    "--config",
                    DAILY_BASIC_VALIDATION_CONFIG,
                    "--source",
                    "processed-bars",
                    "--data-root",
                    DAILY_BASIC_AUTHORITY_BARS_CONFIG,
                ],
            ),
            CheckStep(
                "desktop_daily_basic_walk_forward_progress_audit",
                [
                    python_executable,
                    "scripts/run_walk_forward_progress_audit.py",
                    "--walk-forward-root",
                    DAILY_BASIC_VALIDATION_ROOT,
                    "--output-dir",
                    DAILY_BASIC_PROGRESS_AUDIT_DIR,
                    "--expected-folds",
                    "38",
                ],
            ),
            _long_cycle_replay_step(
                "desktop_daily_basic_long_cycle_factor_replay",
                python_executable=python_executable,
                validation_root=DAILY_BASIC_VALIDATION_ROOT,
                output_dir=DAILY_BASIC_LONG_CYCLE_REPLAY_DIR,
            ),
            CheckStep(
                "desktop_daily_basic_market_regime_coverage",
                [
                    python_executable,
                    "scripts/run_market_regime_coverage.py",
                    "--regime-curve-glob",
                    f"{DAILY_BASIC_VALIDATION_ROOT}/fold_*/test/*/regime_curve.csv",
                    "--output-dir",
                    DAILY_BASIC_REGIME_COVERAGE_DIR,
                    "--min-regimes",
                    "2",
                    "--min-rows-per-regime",
                    "5",
                    "--min-allowed-rows",
                    "5",
                    "--min-blocked-rows",
                    "5",
                    "--min-signal-window-allowed-rows",
                    "5",
                    "--min-signal-window-blocked-rows",
                    "5",
                    "--require-sufficient",
                ],
            ),
            CheckStep(
                "desktop_daily_basic_promotion_report",
                [
                    python_executable,
                    "scripts/run_promotion_report.py",
                    "--config",
                    DAILY_BASIC_PROMOTION_CONFIG,
                ],
            ),
        ]
    if profile == "desktop-daily-basic-value-size-liquidity-validation":
        selected = set(DESKTOP_VALIDATION_CHECK_NAMES)
        return _desktop_factor_validation_gate_chain(
            full_plan,
            selected,
            python_executable,
            name_prefix="desktop_daily_basic_value_size_liquidity",
            data_root=DAILY_BASIC_AUTHORITY_BARS_CONFIG,
            daily_basic_root=DAILY_BASIC_AUTHORITY_INPUTS_CONFIG,
            data_quality_output_dir=DAILY_BASIC_VALUE_SIZE_LIQUIDITY_DATA_QUALITY_DIR,
            validation_config=DAILY_BASIC_VALUE_SIZE_LIQUIDITY_VALIDATION_CONFIG,
            validation_root=DAILY_BASIC_VALUE_SIZE_LIQUIDITY_VALIDATION_ROOT,
            progress_audit_dir=DAILY_BASIC_VALUE_SIZE_LIQUIDITY_PROGRESS_AUDIT_DIR,
            regime_coverage_dir=DAILY_BASIC_VALUE_SIZE_LIQUIDITY_REGIME_COVERAGE_DIR,
            long_cycle_replay_dir=DAILY_BASIC_VALUE_SIZE_LIQUIDITY_LONG_CYCLE_REPLAY_DIR,
            promotion_config=DAILY_BASIC_VALUE_SIZE_LIQUIDITY_PROMOTION_CONFIG,
        )
    if profile == "desktop-price-volume-technical-validation":
        selected = set(DESKTOP_VALIDATION_CHECK_NAMES)
        return _desktop_factor_validation_gate_chain(
            full_plan,
            selected,
            python_executable,
            name_prefix="desktop_price_volume_technical",
            data_root="configs/cn_stock_authority_bars_2015_2025.json",
            daily_basic_root=None,
            data_quality_output_dir=PRICE_VOLUME_TECHNICAL_DATA_QUALITY_DIR,
            validation_config=PRICE_VOLUME_TECHNICAL_VALIDATION_CONFIG,
            validation_root=PRICE_VOLUME_TECHNICAL_VALIDATION_ROOT,
            progress_audit_dir=PRICE_VOLUME_TECHNICAL_PROGRESS_AUDIT_DIR,
            regime_coverage_dir=PRICE_VOLUME_TECHNICAL_REGIME_COVERAGE_DIR,
            long_cycle_replay_dir=PRICE_VOLUME_TECHNICAL_LONG_CYCLE_REPLAY_DIR,
            promotion_config=PRICE_VOLUME_TECHNICAL_PROMOTION_CONFIG,
        )
    raise ValueError(f"Unsupported check profile: {profile}")


def _with_laptop_context(step: CheckStep) -> CheckStep:
    if step.name in {"recent_data_refresh", "tushare_activation_gate"}:
        return CheckStep(step.name, [*step.command, "--machine", "laptop"], uses_network=step.uses_network)
    return step


def _desktop_validation_safety_steps(
    full_plan: list[CheckStep],
    selected: set[str],
    python_executable: str,
    *,
    data_root: str = "configs/cn_stock_authority_bars_2015_2025.json",
    daily_basic_root: str | None = None,
    data_quality_output_dir: str = "data/reports/data_quality_gap_audit_tushare_moneyflow_residual_regime",
) -> list[CheckStep]:
    steps: list[CheckStep] = []
    for step in full_plan:
        if step.name not in selected:
            continue
        steps.append(
            _with_desktop_validation_context(
                step,
                data_root=data_root,
                data_quality_output_dir=data_quality_output_dir,
            )
        )
        if step.name == "data_catalog":
            steps.extend(
                _desktop_validation_cn_stock_preflight(
                    python_executable,
                    data_root=data_root,
                    daily_basic_root=daily_basic_root,
                )
            )
    return steps


def _desktop_validation_cn_stock_preflight(
    python_executable: str,
    *,
    data_root: str,
    daily_basic_root: str | None,
) -> list[CheckStep]:
    manifest_command = [
        python_executable,
        "scripts/run_cn_stock_data_manifest.py",
        "--data-root",
        data_root,
        "--market",
        "CN",
        "--output-dir",
        "data/reports/cn_stock_data_manifest",
    ]
    if daily_basic_root:
        manifest_command.extend(["--daily-basic-root", daily_basic_root])
    return [
        CheckStep(
            "cn_stock_factor_mining_startup_gate",
            [
                python_executable,
                "scripts/run_factor_mining_startup_gate.py",
                "--config",
                "configs/factor_mining_startup_cn_stock.json",
                "--machine",
                "office_desktop",
                "--task",
                "factor_validation",
                "--market",
                "CN",
                "--asset-type",
                "stock",
                "--confirm-start",
            ],
        ),
        CheckStep(
            "cn_stock_data_manifest",
            manifest_command,
        ),
    ]


def _desktop_factor_validation_gate_chain(
    full_plan: list[CheckStep],
    selected: set[str],
    python_executable: str,
    *,
    name_prefix: str,
    data_root: str,
    daily_basic_root: str | None,
    data_quality_output_dir: str,
    validation_config: str,
    validation_root: str,
    progress_audit_dir: str,
    regime_coverage_dir: str,
    long_cycle_replay_dir: str,
    promotion_config: str,
) -> list[CheckStep]:
    return [
        *_desktop_validation_safety_steps(
            full_plan,
            selected,
            python_executable,
            data_root=data_root,
            daily_basic_root=daily_basic_root,
            data_quality_output_dir=data_quality_output_dir,
        ),
        CheckStep(
            f"{name_prefix}_factor_validation",
            [
                python_executable,
                "scripts/run_desktop_factor_validation.py",
                "--config",
                validation_config,
                "--source",
                "processed-bars",
                "--data-root",
                data_root,
            ],
        ),
        CheckStep(
            f"{name_prefix}_walk_forward_progress_audit",
            [
                python_executable,
                "scripts/run_walk_forward_progress_audit.py",
                "--walk-forward-root",
                validation_root,
                "--output-dir",
                progress_audit_dir,
                "--expected-folds",
                "38",
            ],
        ),
        _long_cycle_replay_step(
            f"{name_prefix}_long_cycle_factor_replay",
            python_executable=python_executable,
            validation_root=validation_root,
            output_dir=long_cycle_replay_dir,
        ),
        CheckStep(
            f"{name_prefix}_market_regime_coverage",
            [
                python_executable,
                "scripts/run_market_regime_coverage.py",
                "--regime-curve-glob",
                f"{validation_root}/fold_*/test/*/regime_curve.csv",
                "--output-dir",
                regime_coverage_dir,
                "--min-regimes",
                "2",
                "--min-rows-per-regime",
                "5",
                "--min-allowed-rows",
                "5",
                "--min-blocked-rows",
                "5",
                "--min-signal-window-allowed-rows",
                "5",
                "--min-signal-window-blocked-rows",
                "5",
                "--require-sufficient",
            ],
        ),
        CheckStep(
            f"{name_prefix}_promotion_report",
            [
                python_executable,
                "scripts/run_promotion_report.py",
                "--config",
                promotion_config,
            ],
        ),
    ]


def _long_cycle_replay_step(
    name: str,
    *,
    python_executable: str,
    validation_root: str,
    output_dir: str,
) -> CheckStep:
    return CheckStep(
        name,
        [
            python_executable,
            "scripts/run_long_cycle_factor_replay.py",
            "--candidates-csv",
            f"{validation_root}/walk_forward_leaderboard.csv",
            "--manifest-json",
            "data/reports/cn_stock_data_manifest/cn_stock_data_manifest.json",
            "--market",
            "CN",
            "--required-start",
            "2015-01-01",
            "--output-dir",
            output_dir,
        ],
    )


def _with_desktop_validation_context(step: CheckStep, *, data_root: str, data_quality_output_dir: str) -> CheckStep:
    if step.name == "data_quality_audit":
        return CheckStep(
            step.name,
            [
                step.command[0],
                "scripts/run_data_quality_audit.py",
                "--data-root",
                data_root,
                "--market",
                "CN",
                "--output-dir",
                data_quality_output_dir,
            ],
            uses_network=step.uses_network,
        )
    return step


def build_child_env(base_env: dict[str, str] | None = None) -> dict[str, str]:
    env = dict(os.environ if base_env is None else base_env)
    preferred = [str(SRC_ROOT), str(PROJECT_ROOT)]
    existing = [path for path in env.get("PYTHONPATH", "").split(os.pathsep) if path]
    remainder = [path for path in existing if path not in preferred]
    env["PYTHONPATH"] = os.pathsep.join(preferred + remainder)
    return env


def execute_check_plan(plan: list[CheckStep], env: dict[str, str] | None = None) -> None:
    child_env = build_child_env(env)
    for step in plan:
        print(f"==> {step.name}", flush=True)
        subprocess.run(step.command, check=True, cwd=PROJECT_ROOT, env=child_env)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run local Quant Robot checks.")
    parser.add_argument(
        "--profile",
        choices=[
            "full",
            "laptop",
            "desktop-validation",
            "desktop-daily-basic-validation",
            "desktop-daily-basic-value-size-liquidity-validation",
            "desktop-price-volume-technical-validation",
        ],
        default="full",
        help="Select the check plan size.",
    )
    parser.add_argument("--execute", action="store_true", help="Run checks instead of printing the plan.")
    args = parser.parse_args()
    plan = build_check_plan(profile=args.profile)
    if not args.execute:
        print(json.dumps([asdict(step) for step in plan], indent=2))
        return
    execute_check_plan(plan)


if __name__ == "__main__":
    main()
