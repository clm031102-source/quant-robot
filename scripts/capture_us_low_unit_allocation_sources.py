"""Capture four fixed opaque sources for the five-year unit-comparison question."""
from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path
import urllib.request

import run_us_unit_feasibility as H

ROOT = Path(__file__).resolve().parents[1]
BRANCH = "codex/factor-review-us-low-unit-allocation-20261107"
FILES = ("scripts/bootstrap.py", "scripts/run_us_unit_feasibility.py",
         "src/quant_robot/research/us_unit_feasibility.py",
         "scripts/capture_us_low_unit_allocation_sources.py",
         "tests/unit/test_us_low_unit_source_capture.py")
REQUESTS = tuple(dict(role=symbol + "_" + kind, symbol=symbol, kind=kind,
                     url=f"https://query2.finance.yahoo.com/v8/finance/chart/{symbol}?period1=1606798800&period2={end}&interval={interval}&events=div%2Csplits%2CcapitalGains&includeAdjustedClose=true")
                 for symbol in ("SPYM", "GLDM")
                 for kind, end, interval in (("daily", 1767243600, "1d"), ("actions", 1794114000, "1mo")))


def validate(packet, directory):
    H.require(packet["schema"] == "low_unit_source_capture_v1" and packet["branch"] == H.branch() == BRANCH, "source_context")
    H.require(packet["output"] == str(directory.resolve()) and packet["environment"] == H.environment(), "source_environment")
    H.require(packet["requests"] == list(REQUESTS) and packet["financial_decode_allowed"] is False, "fixed_requests")
    H.require(set(packet["code"]) == set(FILES), "code_set")
    for name, ref in packet["code"].items():
        H.require(ref == H.pin(ROOT / name), "changed_capture_code")
    for ref in packet["evidence"].values():
        H.bound(ref)
    gate = json.loads(H.bound(packet["gate"]))
    selected = gate["selected"]
    H.require(gate["status"] == "ready" and selected["machine"] == "office_desktop"
              and selected["task"] == "factor_review" and selected["current_branch"] == BRANCH, "source_PM_context")
    H.require(H.now() < H.DEADLINE, "campaign_expired")


def preview(directory, evidence):
    packet = dict(schema="low_unit_source_capture_v1", at=H.now().isoformat(), branch=BRANCH,
                  output=str(directory.resolve()), environment=H.environment(),
                  gate=H.pin(ROOT / "data/reports/quant_pm_startup_gate/quant_pm_startup_gate_pack.json"),
                  code={p: H.pin(ROOT / p) for p in FILES},
                  evidence={Path(p).name: H.pin(p) for p in evidence}, requests=list(REQUESTS),
                  financial_decode_allowed=False, request_count=4, retries=0, redirects=False,
                  max_bytes_per_response=1000000, per_request_timeout_seconds=20,
                  daily_window="2020-12-01 through2025-12-31", action_metadata_through="2026-11-07",
                  action_quote_arrays="retained_opaque_not_authorized_for_financial_decode", account_runs=0)
    H.require(packet["evidence"], "prospective_decision_evidence_required")
    validate(packet, directory)
    return H.save(directory / "capture_registration.json", packet)


def admit(directory):
    packet_ref = H.pin(directory / "capture_registration.json")
    packet = json.loads(H.bound(packet_ref))
    validate(packet, directory)
    reviews = {}
    for role in ("root", "manager"):
        ref = H.pin(directory / f"capture_{role}_review.json")
        review = json.loads(H.bound(ref))
        H.require(review["status"] == "accepted" and review["packet_sha256"] == packet_ref["sha256"]
                  and review["stage"] == "capture" and review["reviewer"] == ("root" if role == "root" else "quant_manager_72h"), "independent_review")
        reviews[role] = ref
    release_ref = H.pin(directory / "capture_release.json")
    release = json.loads(H.bound(release_ref))
    H.require(release["status"] == "released_once" and release["packet_sha256"] == packet_ref["sha256"]
              and release["reviews"] == reviews and release["max_actions"] == 4 and release["stage"] == "capture", "exact_source_release")
    start, end = (datetime.fromisoformat(release[k]) for k in ("not_before", "expires_at"))
    H.require(start.tzinfo is not None and end.tzinfo is not None and start <= H.now() <= end <= H.DEADLINE, "source_release_window")
    return packet, dict(registration=packet_ref, reviews=reviews, release=release_ref)


def capture(directory):
    packet, proof = admit(directory)
    H.save(directory / "capture_claim.json", dict(at=H.now().isoformat(), proof=proof, requests=4, financial_decode_allowed=False))
    sources = {}
    try:
        for item in packet["requests"]:
            admit(directory)
            role = item["role"]
            attempt = H.save(directory / "sources" / f"{role}_attempt.json", dict(at=H.now().isoformat(), **item, attempt=1))
            request = urllib.request.Request(item["url"], headers={"User-Agent": "Mozilla/5.0 QuantRobotResearch/1.0", "Accept-Encoding": "identity"})
            with urllib.request.build_opener(H.NoRedirect).open(request, timeout=20) as response:
                H.require(response.status == 200 and "json" in response.headers.get("Content-Type", "").lower(), "JSON_HTTP200")
                body = response.read(1000001)
                H.require(len(body) <= 1000000, "source_byte_cap")
                headers = {k: response.headers.get(k) for k in ("Content-Type", "Date", "ETag", "Last-Modified")}
            raw = H.save_raw(directory / "sources" / f"{role}.body", body)
            receipt = H.save(directory / "sources" / f"{role}_receipt.json", dict(at=H.now().isoformat(), **item, attempt=attempt,
                                raw=raw, HTTP_status=200, raw_complete=True, headers=headers, numeric_conversions=0))
            sources[role] = dict(raw=raw, receipt=receipt)
        admit(directory)
        return H.save(directory / "capture_outcome.json", dict(status="captured_opaque", at=H.now().isoformat(), proof=proof,
                         sources=sources, requests_completed=4, financial_decode_allowed=False, account_runs=0))
    except Exception as exc:
        H.save(directory / "capture_failure.json", dict(at=H.now().isoformat(), status="failed_no_retry", error=str(exc), completed_sources=sources))
        raise


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("preview", "capture"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--evidence", type=Path, nargs="*")
    args = parser.parse_args()
    if args.operation == "preview":
        H.require(args.evidence, "decision_evidence_required")
        result = preview(args.output.resolve(), args.evidence)
    else:
        result = capture(args.output.resolve())
    print(json.dumps(result, indent=2))
