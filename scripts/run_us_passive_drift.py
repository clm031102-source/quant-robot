"""Two-account passive-drift diagnosis using the already saved Study29 input."""
from __future__ import annotations

import argparse
from datetime import datetime
from decimal import Decimal, localcontext
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from bootstrap import ensure_workspace_imports
ensure_workspace_imports()
from run_us_unit_feasibility import pin, bound, save, environment, require, now, DEADLINE
from quant_robot.research.us_passive_drift_allocation import run_known_history
from quant_robot.research.us_passive_drift_verification import verify_account, CONTEXT

BRANCH = "codex/factor-review-us-passive-drift-20261107"
BASELINE_SHA = "82bd3f862ed7084c184417e157b0458dbc5971d2715c74702799a36116b70626"
ROLES = ("primary", "stress")
ASSETS = ["SPYM", "EFA", "IEF", "GLDM"]
BUDGET = dict(new_source_requests=0, raw_source_conversions=0, saved_fixture_loads=1,
              account_roles=list(ROLES), account_runs=2, baseline_reruns=0, retries=0)
CODE = (
    "scripts/bootstrap.py", "scripts/run_us_unit_feasibility.py",
    "src/quant_robot/research/us_unit_feasibility.py",
    "src/quant_robot/__init__.py", "src/quant_robot/research/__init__.py",
    "src/quant_robot/research/us_monthly_rotation.py",
    "src/quant_robot/research/us_monthly_rotation_verification.py",
    "src/quant_robot/research/us_low_unit_allocation.py",
    "src/quant_robot/research/us_passive_drift_allocation.py",
    "src/quant_robot/research/us_passive_drift_verification.py",
    "scripts/run_us_passive_drift.py",
    "tests/unit/test_us_low_unit_allocation.py",
    "tests/unit/test_us_passive_drift_allocation.py",
    "tests/unit/test_us_passive_drift_verification.py",
    "tests/unit/test_us_passive_drift_controller.py",
)


def branch():
    return subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=ROOT,
        check=True, capture_output=True, text=True, timeout=10).stdout.strip()


def comparison_refs(result):
    refs = dict(fixture=result["fixtures"]["new"], QA=result["QA"], original_method=result["method"])
    for role in ("new_primary", "new_stress", "cash"):
        refs[role] = result["accounts"][role]
        refs[role+"_verification"] = result["verifications"][role]
    return refs


def validate(packet, directory):
    require(packet["schema"] == "us_passive_drift_registration_v1", "packet_schema")
    require(branch() == packet["branch"] == BRANCH and packet["environment"] == environment()
            and packet["directory"] == str(directory.resolve()), "context")
    require(set(packet["code"]) == set(CODE), "exact_code_set")
    for relative, ref in packet["code"].items():
        require(ref == pin(ROOT / relative), "code_changed")
    gate = json.loads(bound(packet["gate"]))
    require(gate["status"] == "ready" and gate["selected"]["machine"] == "office_desktop"
            and gate["selected"]["task"] == "factor_review"
            and gate["selected"]["current_branch"] == BRANCH, "PM_gate")
    method = json.loads(bound(packet["method"]))
    require(method["schema"] == "us_passive_drift_method_v1" and method["assets"] == ASSETS
            and [a["scenario_role"] for a in method["new_accounts"]] == list(ROLES)
            and method["holding_policy"] == "no_regular_rebalance_while_any_inventory", "fixed_method")
    require(packet["comparison"]["sha256"] == BASELINE_SHA, "fixed_Study29_comparison")
    baseline = json.loads(bound(packet["comparison"]))
    require(baseline["account_count"] == 5 and baseline["schema"] == "us_low_unit_allocation_result_v1"
            and baseline["qualified"] is False, "baseline_identity")
    require(packet["saved_evidence"] == comparison_refs(baseline), "exact_saved_evidence")
    for ref in packet["saved_evidence"].values():
        bound(ref)  # Hash bytes only; no saved-fixture financial parsing here.
    for role in ("new_primary", "new_stress", "cash"):
        check = json.loads(bound(packet["saved_evidence"][role+"_verification"]))
        require(check["status"] == "recorded_account_consistent"
                and check["account"] == packet["saved_evidence"][role], "baseline_verification")
    require(json.loads(bound(packet["saved_evidence"]["QA"]))["status"] == "passed", "prior_units_QA")
    require(packet["budget"] == BUDGET and now() < DEADLINE, "budget_and_deadline")
    return baseline


def preview(directory, method, comparison):
    baseline = json.loads(Path(comparison).read_bytes())
    packet = dict(schema="us_passive_drift_registration_v1", at=now().isoformat(),
        branch=BRANCH, directory=str(directory.resolve()), environment=environment(),
        gate=pin(ROOT / "data/reports/quant_pm_startup_gate/quant_pm_startup_gate_pack.json"),
        code={name: pin(ROOT / name) for name in CODE}, method=pin(method), comparison=pin(comparison),
        saved_evidence=comparison_refs(baseline), budget=BUDGET,
        question="One predeclared passive-drift execution policy; no search or baseline rerun",
        practical_improvement_assessment="Stress net profit higher AND total execution cost lower than saved monthly; report separately from the fixed positive-profit/DD gate",
        qualified=False, real_forward=0, deployed_changes=False)
    validate(packet, directory)
    return save(directory / "registration.json", packet)


def admit(directory):
    ref = pin(directory / "registration.json")
    packet = json.loads(bound(ref))
    baseline = validate(packet, directory)
    reviews = {}
    for role, reviewer in (("root", "root"), ("manager", "quant_manager_72h")):
        rr = pin(directory / f"{role}_review.json")
        review = json.loads(bound(rr))
        require(review["status"] == "accepted" and review["reviewer"] == reviewer
                and review["packet_sha256"] == ref["sha256"], "review")
        reviews[role] = rr
    release_ref = pin(directory / "release.json")
    release = json.loads(bound(release_ref))
    require(release["status"] == "released_once" and release["packet_sha256"] == ref["sha256"]
            and release["reviews"] == reviews and release["budget"] == BUDGET, "release")
    start, end = (datetime.fromisoformat(release[k]) for k in ("not_before", "expires_at"))
    require(start.tzinfo is not None and end.tzinfo is not None and start <= now() <= end <= DEADLINE, "window")
    return packet, baseline, dict(registration=ref, reviews=reviews, release=release_ref)


def comparison_summary(summaries, baseline):
    with localcontext(CONTEXT):
        changes = {}
        for role in ROLES:
            current, prior = summaries[role], baseline["summaries"]["new_"+role]
            changes[role] = {key: str(Decimal(current[key])-Decimal(prior[key])) for key in
                ("cash_and_locked_sale_proceeds_net_profit", "same_path_total_execution_cost",
                 "observed_maxDD", "book_CAGR", "average_market_deployment_ratio")}
            changes[role]["fills"] = current["fills"]-prior["fills"]
        passed = all(Decimal(summaries[r]["cash_and_locked_sale_proceeds_net_profit"]) > 0
            and Decimal(summaries[r]["observed_maxDD"]) < Decimal(".40")
            and summaries[r]["terminal_inventory_closed"] for r in ROLES)
        improvement = (Decimal(changes["stress"]["cash_and_locked_sale_proceeds_net_profit"]) > 0
                       and Decimal(changes["stress"]["same_path_total_execution_cost"]) < 0)
        return dict(fixed_conditional_evaluation_passed=passed, stress_practical_improvement=improvement,
                    differences_from_saved_monthly=changes)


def run(directory):
    packet, baseline, proof = admit(directory)
    claim = save(directory / "claim.json", dict(at=now().isoformat(), proof=proof, budget=BUDGET))
    accounts, verifications = {}, {}
    try:
        marker = save(directory / "financial_started.json", dict(at=now().isoformat(), claim=claim,
            method=packet["method"], saved_fixture=packet["saved_evidence"]["fixture"], budget=BUDGET))
        # Original construction provenance is retained; the NEW analysis authorization is above.
        fixture = json.loads(bound(packet["saved_evidence"]["fixture"]))
        require(fixture["assets"] == ASSETS and fixture["provenance"]["constructed_from_market_data"] is True,
                "saved_new_fixture_identity")
        for role in ROLES:
            admit(directory)
            save(directory / f"{role}_claim.json", dict(at=now().isoformat(), role=role, marker=marker))
            result = run_known_history(fixture, role, method_sha256=packet["method"]["sha256"],
                registration_sha256=proof["registration"]["sha256"], numeric_marker_sha256=marker["sha256"])
            account_ref = save(directory / f"{role}_account.json", result)
            accounts[role] = account_ref
            saved = json.loads(bound(account_ref))
            require(saved["role"] == "new_"+role and saved["scenario_role"] == role
                    and saved["assets"] == ASSETS, "registered_scenario_identity")
            check = verify_account(fixture, saved, expected_method=packet["method"]["sha256"],
                expected_registration=proof["registration"]["sha256"], expected_marker=marker["sha256"])
            verifications[role] = save(directory / f"{role}_verification.json", dict(account=account_ref, **check))
        admit(directory)  # Rebind saved fixture, baseline, its QA and all prior checks.
        for role, ref in verifications.items():
            check = json.loads(bound(ref))
            require(check["status"] == "recorded_account_consistent"
                    and check["account"] == accounts[role], "final_verification")
        summaries = {r: json.loads(bound(ref))["summary"] for r, ref in accounts.items()}
        result = dict(schema="us_passive_drift_result_v1", at=now().isoformat(), proof=proof,
            method=packet["method"], fixture=packet["saved_evidence"]["fixture"], baseline=packet["comparison"],
            accounts=accounts, verifications=verifications, summaries=summaries,
            **comparison_summary(summaries, baseline), account_count=2, return_study_count=1,
            new_source_requests=0, baseline_account_reruns=0, qualified=False, real_forward=0,
            deployed_changes=False, interpretation="Known-history selected execution-cost diagnosis, not alpha or independent holdout")
        result_ref = save(directory / "result.json", result)
        return save(directory / "outcome.json", dict(status="completed_once_conditional_diagnosis", at=now().isoformat(),
            result=result_ref, proof=proof, accounts_run=2, qualified=False, real_forward=0))
    except Exception as exc:
        save(directory / "failure.json", dict(status="failed_no_retry", at=now().isoformat(), error=str(exc),
            completed_accounts=accounts, completed_verifications=verifications, proof=proof))
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("preview", "run"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--method", type=Path)
    parser.add_argument("--comparison", type=Path)
    args = parser.parse_args()
    if args.operation == "preview":
        require(args.method is not None and args.comparison is not None, "preview_paths")
        result = preview(args.output.resolve(), args.method, args.comparison)
    else:
        result = run(args.output.resolve())
    print(json.dumps(result, indent=2))
