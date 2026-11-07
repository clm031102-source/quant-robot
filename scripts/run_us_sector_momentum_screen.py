"""Two-stage, once-only source capture and numeric sector-factor screening."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from bootstrap import ensure_workspace_imports
ensure_workspace_imports()
from quant_robot.research import us_sector_momentum_screen as M

BRANCH = "codex/factor-review-us-sector-screen-20261107"
METHOD = "configs/us_sector_momentum_screen_20261107.json"
CODE = [METHOD, "scripts/bootstrap.py", "src/quant_robot/research/us_sector_momentum_screen.py",
        "src/quant_robot/research/us_sector_momentum_verification.py",
        "scripts/run_us_sector_momentum_screen.py", "tests/unit/test_us_sector_momentum_screen.py",
        "tests/unit/test_us_sector_momentum_verification.py", "tests/unit/test_us_sector_momentum_controller.py"]
DEADLINE = "2026-11-09T16:21:39+00:00"


def now():
    return datetime.now(timezone.utc)


def stamp():
    return now().isoformat()


def canonical(value):
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def pin(path):
    p = Path(path).resolve()
    raw = p.read_bytes()
    return dict(path=str(p), sha256=digest(raw), bytes=len(raw))


def bound(ref):
    raw = Path(ref["path"]).read_bytes()
    M.require(digest(raw) == ref["sha256"] and len(raw) == ref["bytes"], "bound_file_changed")
    return raw


def read(path):
    return json.loads(Path(path).read_bytes())


def write(path, value):
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    raw = canonical(value)
    expected = dict(path=str(p.resolve()), sha256=digest(raw), bytes=len(raw))
    with p.open("xb") as f:
        f.write(raw)
        f.flush()
        os.fsync(f.fileno())
    bound(expected)
    return expected


def environment():
    return dict(python=platform.python_version(), executable=str(Path(sys.executable).resolve()),
                platform=platform.platform(), tzdata=importlib.metadata.version("tzdata"))


def branch():
    return subprocess.run(["git", "symbolic-ref", "--short", "HEAD"], cwd=ROOT,
                          check=True, capture_output=True, text=True, timeout=10).stdout.strip()


def common_packet(stage, directory, source_documents):
    gate = ROOT / "data/reports/quant_pm_startup_gate/quant_pm_startup_gate_pack.json"
    report = read(gate)
    M.require(report.get("status") == "ready", "PM_gate_not_ready")
    selected = report.get("selected", {})
    M.require(selected.get("machine") == "office_desktop" and selected.get("task") == "factor_review"
              and selected.get("branch") == BRANCH and selected.get("current_branch") == BRANCH, "PM_context")
    M.require(branch() == BRANCH and now() < datetime.fromisoformat(DEADLINE), "branch_or_campaign_deadline")
    originals = ["ssga_split_20251203.pdf", "xlf_2016_form8937.pdf", "ssga_2016_annual_report.html"]
    return dict(schema="sector_screen_registration_v1", stage=stage, created_at=stamp(),
                branch=BRANCH, evidence_dir=str(directory.resolve()), method=pin(ROOT / METHOD),
                code={p: pin(ROOT / p) for p in CODE}, environment=environment(),
                gate=pin(gate), source_documents={p: pin(source_documents / p) for p in originals},
                financial_run_budget=1, account_count=0, qualified=False, live_boundary_allowed=False)


def validate_packet(packet, directory):
    M.require(packet["schema"] == "sector_screen_registration_v1" and packet["branch"] == branch() == BRANCH,
              "registration_context")
    M.require(packet["evidence_dir"] == str(directory.resolve()) and packet["environment"] == environment(), "environment_or_directory")
    M.require(set(packet["code"]) == set(CODE) and packet["method"] == pin(ROOT / METHOD), "fixed_code_and_method")
    for p, ref in packet["code"].items():
        M.require(ref == pin(ROOT / p), "code_changed")
    bound(packet["gate"])
    for ref in packet["source_documents"].values():
        bound(ref)
    M.require(now() < datetime.fromisoformat(DEADLINE), "campaign_expired")


def admit(stage, directory):
    packet_file = directory / (stage + "_registration.json")
    packet_ref = pin(packet_file)
    packet = json.loads(bound(packet_ref))
    validate_packet(packet, directory)
    M.require(packet["stage"] == stage, "registration_stage")
    packet_hash = packet_ref["sha256"]
    reviews = {}
    for role in ("manager", "root"):
        p = directory / f"{stage}_{role}_review.json"
        review_ref = pin(p)
        r = json.loads(bound(review_ref))
        M.require(r.get("status") == "accepted" and r.get("reviewer") == ("quant_manager_72h" if role == "manager" else "root")
                  and r.get("packet_sha256") == packet_hash and r.get("stage") == stage, "independent_review_required")
        reviews[role] = review_ref
    release_file = directory / (stage + "_release.json")
    release_ref = pin(release_file)
    release = json.loads(bound(release_ref))
    M.require(release.get("status") == "released_once" and release.get("packet_sha256") == packet_hash
              and release.get("stage") == stage and release.get("max_actions") == (9 if stage == "capture" else 1)
              and release.get("reviews") == reviews, "exact_release")
    start = datetime.fromisoformat(release["not_before"])
    end = datetime.fromisoformat(release["expires_at"])
    M.require(start.tzinfo is not None and end.tzinfo is not None and start <= now() <= end
              <= datetime.fromisoformat(DEADLINE), "release_window")
    return packet, dict(registration=packet_ref, release=release_ref, reviews=reviews)


def capture_preview(directory, documents):
    packet = common_packet("capture", directory, documents)
    packet["urls"] = {s: f"https://query1.finance.yahoo.com/v8/finance/chart/{s}?period1=1104537600&period2=1767225600&interval=1d&events=div%2Csplits%2CcapitalGains&includeAdjustedClose=true" for s in M.ASSETS}
    packet["request_policy"] = dict(max_requests=9, per_response_bytes=4000000,
                                    per_request_timeout_seconds=20, retries=0, redirects=False,
                                    numeric_decode_allowed=False, source_window="2005-01-03 through2025-12-31")
    return write(directory / "capture_registration.json", packet)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise RuntimeError("redirect_not_allowed")


def capture(directory):
    packet, proof = admit("capture", directory)
    write(directory / "capture_claim.json", dict(started_at=stamp(), proof=proof, max_requests=9))
    refs = {}
    try:
        for symbol in M.ASSETS:
            admit("capture", directory)
            url = packet["urls"][symbol]
            write(directory / "sources" / f"{symbol}_request.json", dict(symbol=symbol, url=url, at=stamp(), attempt=1))
            started = time.monotonic()
            request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 QuantRobotResearch/1.0", "Accept-Encoding": "identity"})
            with urllib.request.build_opener(NoRedirect).open(request, timeout=20) as response:
                M.require(response.status == 200 and "json" in response.headers.get("Content-Type", "").lower(), "JSON_HTTP200_required")
                body = response.read(4000001)
                M.require(len(body) <= 4000000, "response_size_cap")
                header = {k: response.headers.get(k) for k in ("Content-Type", "Date", "ETag", "Last-Modified")}
            p = directory / "sources" / f"{symbol}.json"
            expected_raw = dict(path=str(p.resolve()), sha256=digest(body), bytes=len(body))
            with p.open("xb") as f:
                f.write(body)
                f.flush()
                os.fsync(f.fileno())
            bound(expected_raw)
            receipt = write(directory / "sources" / f"{symbol}_receipt.json",
                            dict(symbol=symbol, url=url, completed_at=stamp(), duration_seconds=time.monotonic()-started,
                                 status=200, headers=header, raw=expected_raw, financial_values_converted=0))
            refs[symbol] = dict(raw=expected_raw, receipt=receipt)
        validate_packet(packet, directory)
        return write(directory / "capture_outcome.json", dict(status="captured", at=stamp(), sources=refs, proof=proof, requests_completed=len(refs)))
    except Exception as exc:
        write(directory / "capture_failure.json", dict(status="failed_no_retry", at=stamp(), error=f"{type(exc).__name__}: {exc}", completed_sources=refs))
        raise


def saved_sources(directory):
    outcome = read(directory / "capture_outcome.json")
    M.require(outcome["status"] == "captured" and set(outcome["sources"]) == set(M.ASSETS), "complete_capture_required")
    sources = {}
    for symbol, refs in outcome["sources"].items():
        receipt = json.loads(bound(refs["receipt"]))
        M.require(receipt["raw"] == refs["raw"] and receipt["status"] == 200 and receipt["symbol"] == symbol, "source_receipt")
        sources[symbol] = bound(refs["raw"])
    return sources


def run_preview(directory, documents):
    packet = common_packet("numeric", directory, documents)
    prepared = M.inspect_sources(saved_sources(directory), read(ROOT / METHOD))
    structure = dict(sessions=len(prepared["dates"]), start=prepared["dates"][0], end=prepared["dates"][-1],
                     events=prepared["events"], price_values_converted=0, calendar_basis=prepared["calendar_basis"])
    packet["source_structure"] = write(directory / "source_structure.json", structure)
    packet["capture_outcome"] = pin(directory / "capture_outcome.json")
    packet["source_files"] = read(directory / "capture_outcome.json")["sources"]
    packet["scope"] = dict(study_number_reserved=28, qa_adjusted_close_values=2, financial_executions=1,
                           factor_screen_after_qa_pass_only=True, independent_recorded_result_verification=True,
                           no_raw_OHLC_volume_dividend_amount_conversion=True, source_retry=False)
    return write(directory / "numeric_registration.json", packet)


def run(directory):
    packet, proof = admit("numeric", directory)
    bound(packet["source_structure"])
    M.require(packet["capture_outcome"] == pin(directory / "capture_outcome.json")
              and packet["source_files"] == read(directory / "capture_outcome.json")["sources"], "fixed_saved_inputs")
    sources = saved_sources(directory)
    method = read(ROOT / METHOD)
    prepared = M.inspect_sources(sources, method)
    write(directory / "numeric_claim.json", dict(at=stamp(), proof=proof, max_executions=1))
    write(directory / "financial_decode_started.json", dict(at=stamp(), proof=proof, first_read="two_XLF_adjusted_close_QA_points"))
    try:
        qa = M.source_qa(prepared, method)
        qa_ref = write(directory / "source_qa.json", qa)
        if qa["status"] != "passed":
            validate_packet(packet, directory)
            bound(qa_ref)
            return write(directory / "outcome.json", dict(status="source_qa_failed_closed", at=stamp(), qa=qa, candidate_screens=0, qualified=False))
        # This contains strings, not tradable-price/share reconstructions.
        prepared_ref = write(directory / "prepared_adjusted_source.json", prepared)
        result = M.screen(prepared, method, qa)
        result["proof"] = dict(proof, prepared_source=prepared_ref)
        result_ref = write(directory / "result.json", result)
        from quant_robot.research.us_sector_momentum_verification import verify_recorded_screen
        verification = verify_recorded_screen(json.loads(bound(prepared_ref)), method, json.loads(bound(result_ref)))
        M.require(verification.get("status") == "passed", "independent_verification_failed")
        verification_ref = write(directory / "independent_verification.json", verification)
        validate_packet(packet, directory)
        for ref in (qa_ref, prepared_ref, result_ref, verification_ref):
            bound(ref)
        for refs in packet["source_files"].values():
            bound(refs["raw"])
            bound(refs["receipt"])
        return write(directory / "outcome.json", dict(status="completed", at=stamp(), result=result_ref,
                     verification=verification_ref, candidate_screens=1, account_count=0, qualified=False, real_forward_days=0))
    except Exception as exc:
        write(directory / "numeric_failure.json", dict(status="failed_no_rerun", at=stamp(), error=f"{type(exc).__name__}: {exc}"))
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=["capture-preview", "capture", "run-preview", "run"])
    parser.add_argument("--evidence-dir", type=Path, required=True)
    parser.add_argument("--source-documents-dir", type=Path)
    args = parser.parse_args()
    directory = args.evidence_dir.resolve()
    if args.operation.endswith("preview"):
        M.require(args.source_documents_dir is not None, "source_documents_required")
    if args.operation == "capture-preview":
        result = capture_preview(directory, args.source_documents_dir.resolve())
    elif args.operation == "capture":
        result = capture(directory)
    elif args.operation == "run-preview":
        result = run_preview(directory, args.source_documents_dir.resolve())
    else:
        result = run(directory)
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
