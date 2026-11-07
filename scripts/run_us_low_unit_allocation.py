"""Once-only five-year comparison from retained sources; never downloads data."""
from __future__ import annotations

import argparse
from datetime import datetime
from decimal import Decimal
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from bootstrap import ensure_workspace_imports
ensure_workspace_imports()
from run_us_unit_feasibility import pin, bound, save, environment, require, now, DEADLINE
from quant_robot.research.us_low_unit_allocation_inputs import (
    ROLES as SOURCE_ROLES, prepare_sources, metadata_summary, run_unit_qa, build_fixtures,
)
from quant_robot.research.us_low_unit_allocation import run_known_history
from quant_robot.research.us_low_unit_allocation_verification import verify_account
from quant_robot.research.us_monthly_rotation_inputs import _opaque, _day

BRANCH = "codex/factor-review-us-low-unit-allocation-20261107"
ROLES = ("old_primary", "old_stress", "new_primary", "new_stress", "cash")
CODE = (
    "scripts/bootstrap.py", "scripts/run_us_unit_feasibility.py",
    "src/quant_robot/research/us_unit_feasibility.py",
    "src/quant_robot/__init__.py", "src/quant_robot/research/__init__.py",
    "src/quant_robot/research/us_monthly_rotation.py",
    "src/quant_robot/research/us_monthly_rotation_inputs.py",
    "src/quant_robot/research/us_monthly_rotation_verification.py",
    "src/quant_robot/research/us_low_unit_allocation.py",
    "src/quant_robot/research/us_low_unit_allocation_inputs.py",
    "src/quant_robot/research/us_low_unit_allocation_verification.py",
    "scripts/run_us_low_unit_allocation.py",
    "tests/unit/test_us_low_unit_allocation.py",
    "tests/unit/test_us_low_unit_allocation_inputs.py",
    "tests/unit/test_us_low_unit_allocation_verification.py",
    "tests/unit/test_us_low_unit_allocation_controller.py",
)


def branch():
    return subprocess.run(["git", "rev-parse", "--abbrev-ref", "HEAD"], cwd=ROOT,
        check=True, capture_output=True, text=True, timeout=10).stdout.strip()


def source_bytes(manifest):
    require(manifest["schema"] == "us_low_unit_source_manifest_v1"
            and set(manifest["sources"]) == set(SOURCE_ROLES), "sixteen_bound_sources")
    for ref in manifest["supporting_refs"].values():
        bound(ref)
    payloads = {}
    for role, refs in manifest["sources"].items():
        raw = bound(refs["raw"])
        receipt = json.loads(bound(refs["receipt"]))
        require(receipt.get("HTTP_status", receipt.get("status")) == 200
                and receipt.get("error") is None and receipt.get("raw_complete", True) is True,
                "completed_source_receipt")
        actual = receipt.get("raw", {})
        require(actual.get("sha256", receipt.get("raw_sha256")) == refs["raw"]["sha256"]
                and actual.get("bytes", receipt.get("raw_bytes")) == refs["raw"]["bytes"],
                "receipt_source_identity")
        if role.endswith("_actions"):
            require_complete_action_months(raw)
        payloads[role] = raw
    return payloads


def require_complete_action_months(raw):
    """Only timestamp metadata is converted; monthly quote arrays stay opaque."""
    row = _opaque(raw)["chart"]["result"][0]
    timestamps = row.get("timestamp")
    require(type(timestamps) is list, "action_timestamps")
    dates = [_day(t) for t in timestamps]
    require(dates and dates == sorted(set(dates)), "action_dates_unique_order")
    # Archived Yahoo monthly arrays also carry one trailing capture-session row.
    # Its quote values remain unread; it does not substitute for a month bucket.
    stub = None
    if not dates[-1].endswith("-01"):
        stub = dates.pop()
        require(stub == "2026-11-06", "known_capture_session_stub")
    require(all(day.endswith("-01") for day in dates), "action_month_start_buckets")
    months = [day[:7] for day in dates]
    expected = ["2020-12"] + [f"{y}-{m:02d}" for y in range(2021, 2027)
                             for m in range(1, 13) if (y, m) <= (2026, 11)]
    require([m for m in months if m >= "2020-12"] == expected, "complete_actions_through_capture")
    return dict(first=expected[0], last=expected[-1], months=len(expected),
                trailing_capture_session_stub=stub, quote_conversions=0)


def validate(packet, directory):
    require(packet["schema"] == "us_low_unit_numeric_registration_v1", "registration_schema")
    require(branch() == packet["branch"] == BRANCH, "branch")
    require(packet["evidence_dir"] == str(directory.resolve())
            and packet["environment"] == environment(), "context")
    require(set(packet["code"]) == set(CODE), "code_set")
    for relative, ref in packet["code"].items():
        require(ref == pin(ROOT / relative), "changed_code")
    gate = json.loads(bound(packet["gate"]))
    require(gate["status"] == "ready" and gate["selected"]["machine"] == "office_desktop"
            and gate["selected"]["task"] == "factor_review"
            and gate["selected"]["current_branch"] == BRANCH, "PM_gate")
    method = json.loads(bound(packet["method"]))
    require(method["schema"] == "us_low_unit_five_year_method_v1"
            and method["accounts"] == list(ROLES)
            and method["window"] == ["2021-01-01", "2025-12-31"]
            and method["initial_cash_USD"] == "1000.00", "fixed_method_identity")
    manifest = json.loads(bound(packet["sources"]))
    require(packet["budget"] == dict(qa_close_values=5, fixture_builds=1,
        account_roles=list(ROLES), downloads=0, reruns=0), "fixed_budget")
    require(now() < DEADLINE, "campaign_expired")
    return source_bytes(manifest)


def preview(directory, method_path, source_path):
    packet = dict(schema="us_low_unit_numeric_registration_v1", at=now().isoformat(),
        branch=BRANCH, evidence_dir=str(directory.resolve()), environment=environment(),
        gate=pin(ROOT / "data/reports/quant_pm_startup_gate/quant_pm_startup_gate_pack.json"),
        code={relative: pin(ROOT / relative) for relative in CODE},
        method=pin(method_path), sources=pin(source_path),
        budget=dict(qa_close_values=5, fixture_builds=1, account_roles=list(ROLES), downloads=0, reruns=0),
        qualified=False, real_forward=0, broker_or_live_access=False)
    payloads = validate(packet, directory)
    prepared = prepare_sources(payloads)
    metadata = metadata_summary(prepared)
    packet["metadata"] = save(directory / "source_metadata.json", metadata)
    packet["ready_for_review"] = not metadata["blockers"]
    packet["selected_dates"] = len(metadata["dates"])
    packet["normalization_quote_values"] = 6 * (5 * (len(metadata["dates"])-1) + 1)
    packet["dividend_values"] = len(metadata["dividend_events"])
    packet["action_metadata_coverage"] = {role: require_complete_action_months(raw)
        for role, raw in payloads.items() if role.endswith("_actions")}
    return save(directory / "numeric_registration.json", packet)


def admit(directory):
    packet_ref = pin(directory / "numeric_registration.json")
    packet = json.loads(bound(packet_ref))
    payloads = validate(packet, directory)
    require(packet["ready_for_review"] is True, "metadata_blocked")
    metadata = json.loads(bound(packet["metadata"]))
    require(not metadata["blockers"] and not metadata["numeric_decode_started"], "price_free_metadata")
    reviews = {}
    for role, reviewer in (("root", "root"), ("manager", "quant_manager_72h")):
        ref = pin(directory / f"numeric_{role}_review.json")
        review = json.loads(bound(ref))
        require(review["status"] == "accepted" and review["reviewer"] == reviewer
                and review["packet_sha256"] == packet_ref["sha256"], "review")
        reviews[role] = ref
    release_ref = pin(directory / "numeric_release.json")
    release = json.loads(bound(release_ref))
    require(release["status"] == "released_once" and release["packet_sha256"] == packet_ref["sha256"]
            and release["reviews"] == reviews and release["budget"] == packet["budget"], "release")
    start, end = (datetime.fromisoformat(release[key]) for key in ("not_before", "expires_at"))
    require(start.tzinfo is not None and end.tzinfo is not None
            and start <= now() <= end <= DEADLINE, "release_window")
    return packet, payloads, dict(registration=packet_ref, reviews=reviews, release=release_ref)


def run(directory):
    packet, payloads, proof = admit(directory)
    # Exclusive durable creation: even a crash consumes this attempt.
    claim = save(directory / "numeric_claim.json", dict(at=now().isoformat(), proof=proof, budget=packet["budget"]))
    accounts, verifications = {}, {}
    try:
        prepared = prepare_sources(payloads)
        require(metadata_summary(prepared) == json.loads(bound(packet["metadata"])), "source_structure_changed")
        marker = save(directory / "financial_decode_started.json", dict(at=now().isoformat(), claim=claim,
            method=packet["method"], budget=packet["budget"]))
        qa = run_unit_qa(prepared)
        qa_ref = save(directory / "unit_qa.json", qa)
        if qa["status"] != "passed":
            return save(directory / "outcome.json", dict(status="closed_failed_fixed_unit_QA",
                at=now().isoformat(), proof=proof, QA=qa_ref, accounts_run=0,
                qualified=False, real_forward=0, retry_allowed=False))
        fixtures = build_fixtures(prepared, dict(constructed_from_market_data=True,
            method_sha256=packet["method"]["sha256"], registration_sha256=proof["registration"]["sha256"],
            financial_marker_sha256=marker["sha256"], known_history_selected_after_previous_studies=True))
        fixture_refs = {name: save(directory / f"fixture_{name}.json", value) for name, value in fixtures.items()}
        for role in ROLES:
            # Recheck authority without reparsing or numerically rebuilding the sources.
            admit(directory)
            save(directory / "accounts" / f"{role}_claim.json", dict(at=now().isoformat(), role=role, marker=marker))
            fixture = fixtures["new" if role.startswith("new_") else "old"]
            account = run_known_history(fixture, role, method_sha256=packet["method"]["sha256"],
                registration_sha256=proof["registration"]["sha256"], numeric_marker_sha256=marker["sha256"])
            account_ref = save(directory / "accounts" / f"{role}.json", account)
            accounts[role] = account_ref
            # The independent checker reads the SAVED account, never invokes the strategy.
            saved_account = json.loads(bound(account_ref))
            require(saved_account["role"] == role and saved_account["assets"] == fixture["assets"],
                    "registered_role_fixture_identity")
            saved_fixture = json.loads(bound(fixture_refs["new" if role.startswith("new_") else "old"]))
            check = verify_account(saved_fixture, saved_account, expected_method=packet["method"]["sha256"],
                expected_registration=proof["registration"]["sha256"], expected_marker=marker["sha256"])
            verifications[role] = save(directory / "accounts" / f"{role}_verification.json", dict(account=account_ref, **check))
        admit(directory)
        bound(qa_ref)
        for ref in fixture_refs.values():
            bound(ref)
        for role, ref in verifications.items():
            check = json.loads(bound(ref))
            require(check["status"] == "recorded_account_consistent" and check["account"] == accounts[role],
                    "final_saved_verification_identity")
        summaries = {role: json.loads(bound(ref))["summary"] for role, ref in accounts.items()}
        passed = all(Decimal(summaries[r]["cash_and_locked_sale_proceeds_net_profit"]) > 0
            and Decimal(summaries[r]["observed_maxDD"]) < Decimal(".40")
            and summaries[r]["terminal_inventory_closed"]
            for r in ("new_primary", "new_stress"))
        result = dict(schema="us_low_unit_allocation_result_v1", at=now().isoformat(), proof=proof,
            method=packet["method"], QA=qa_ref, fixtures=fixture_refs, accounts=accounts,
            verifications=verifications, summaries=summaries, window=["2021-01-01", "2025-12-31"],
            fixed_conditional_evaluation_passed=passed, account_count=5, return_study_count=1,
            qualified=False, real_forward=0, existing_deployment_changed=False,
            limitations=["Known history, selected after prior studies; not an untouched holdout.",
                "Conditional OHLC/volume, fee, execution, dividend and cash-in-lieu model.",
                "Independent saved-ledger arithmetic; full strategy decisions not independently rerun.",
                "Cash plus locked sale proceeds is not immediately withdrawable cash.",
                "Positive historical results do not grant qualification or deployment."])
        result_ref = save(directory / "result.json", result)
        return save(directory / "outcome.json", dict(status="completed_conditional_comparison",
            at=now().isoformat(), result=result_ref, proof=proof, accounts_run=5,
            fixed_conditional_evaluation_passed=passed, qualified=False, real_forward=0))
    except Exception as exc:
        save(directory / "numeric_failure.json", dict(status="failed_no_rerun", at=now().isoformat(),
            error=str(exc), completed_accounts=accounts, completed_verifications=verifications,
            proof=proof, qualified=False, real_forward=0))
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("preview", "run"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--method", type=Path)
    parser.add_argument("--sources", type=Path)
    args = parser.parse_args()
    if args.operation == "preview":
        require(args.method is not None and args.sources is not None, "preview_paths")
        result = preview(args.output.resolve(), args.method, args.sources)
    else:
        result = run(args.output.resolve())
    print(json.dumps(result, indent=2))
