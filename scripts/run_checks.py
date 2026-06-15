from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import asdict, dataclass


@dataclass(frozen=True)
class CheckStep:
    name: str
    command: list[str]
    uses_network: bool = False


def build_check_plan(python_executable: str = sys.executable) -> list[CheckStep]:
    return [
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


def main() -> None:
    parser = argparse.ArgumentParser(description="Run local Quant Robot checks.")
    parser.add_argument("--execute", action="store_true", help="Run checks instead of printing the plan.")
    args = parser.parse_args()
    plan = build_check_plan()
    if not args.execute:
        print(json.dumps([asdict(step) for step in plan], indent=2))
        return
    for step in plan:
        print(f"==> {step.name}", flush=True)
        subprocess.run(step.command, check=True)


if __name__ == "__main__":
    main()
