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
            *(_with_desktop_validation_context(step) for step in full_plan if step.name in selected),
            CheckStep("desktop_factor_validation", [python_executable, "scripts/run_desktop_factor_validation.py"]),
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
    raise ValueError(f"Unsupported check profile: {profile}")


def _with_laptop_context(step: CheckStep) -> CheckStep:
    if step.name in {"recent_data_refresh", "tushare_activation_gate"}:
        return CheckStep(step.name, [*step.command, "--machine", "laptop"], uses_network=step.uses_network)
    return step


def _with_desktop_validation_context(step: CheckStep) -> CheckStep:
    if step.name == "data_quality_audit":
        return CheckStep(
            step.name,
            [
                step.command[0],
                "scripts/run_data_quality_audit.py",
                "--data-root",
                "configs/cn_stock_authority_bars_2015_2025.json",
                "--market",
                "CN",
                "--output-dir",
                "data/reports/data_quality_gap_audit_tushare_moneyflow_residual_regime",
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
        choices=["full", "laptop", "desktop-validation"],
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
