"""One completed-close whole-share sizing question; no strategy or account run."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
from fractions import Fraction
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import urllib.request
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
from bootstrap import ensure_workspace_imports
ensure_workspace_imports()
from quant_robot.research.us_unit_feasibility import calculate

BRANCH = "codex/factor-review-us-unit-feasibility-20261107"
DAY = "2026-11-06"
SYMBOLS = ("SPY", "EFA", "IEF", "GLD", "SPYM", "GLDM")
CODE = ("scripts/bootstrap.py", "scripts/run_us_unit_feasibility.py",
        "src/quant_robot/research/us_unit_feasibility.py", "tests/unit/test_us_unit_feasibility.py",
        "tests/unit/test_us_unit_feasibility_controller.py")
DEADLINE = datetime.fromisoformat("2026-11-09T16:21:39+00:00")


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def now():
    return datetime.now(timezone.utc)


def pin(path):
    p = Path(path).resolve()
    raw = p.read_bytes()
    return dict(path=str(p), sha256=hashlib.sha256(raw).hexdigest(), bytes=len(raw))


def bound(ref):
    raw = Path(ref["path"]).read_bytes()
    require(len(raw) == ref["bytes"] and hashlib.sha256(raw).hexdigest() == ref["sha256"], "changed_input")
    return raw


def save(path, value):
    raw = (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + "\n").encode()
    return save_raw(path, raw)


def save_raw(path, raw):
    path = Path(path).resolve()
    path.parent.mkdir(parents=True, exist_ok=True)
    ref = dict(path=str(path), bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())
    with path.open("xb") as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())
    bound(ref)
    return ref


def load(path):
    return json.loads(Path(path).read_bytes())


def environment():
    return dict(python=platform.python_version(), executable=str(Path(sys.executable).resolve()),
                platform=platform.platform(), tzdata=importlib.metadata.version("tzdata"))


def branch():
    return subprocess.run(["git", "symbolic-ref", "--short", "HEAD"], cwd=ROOT,
                          check=True, capture_output=True, text=True, timeout=10).stdout.strip()


def validate(packet, directory):
    require(packet["schema"] == "us_unit_feasibility_registration_v1", "registration_schema")
    require(branch() == packet["branch"] == BRANCH, "branch")
    require(packet["evidence_dir"] == str(directory.resolve()) and packet["environment"] == environment(), "context")
    require(set(packet["code"]) == set(CODE), "code_set")
    for relative, ref in packet["code"].items():
        require(ref == pin(ROOT / relative), "changed_code")
    gate = json.loads(bound(packet["gate"]))
    require(gate["status"] == "ready" and gate["selected"]["machine"] == "office_desktop"
            and gate["selected"]["task"] == "factor_review" and gate["selected"]["current_branch"] == BRANCH, "PM_gate")
    draft = json.loads(bound(packet["draft"]))
    require([item["symbol"] for item in draft["inputs"]] == list(SYMBOLS), "six_input_roles")
    for item in draft["inputs"][:4]:
        for key in ("raw", "receipt"):
            bound(item[key])
    for ref in draft["supporting_refs"].values():
        bound(ref)
    require(now() < DEADLINE, "campaign_expired")
    return draft


def registration(stage, directory, draft_path):
    gate = ROOT / "data/reports/quant_pm_startup_gate/quant_pm_startup_gate_pack.json"
    packet = dict(schema="us_unit_feasibility_registration_v1", stage=stage, at=now().isoformat(),
                  branch=BRANCH, evidence_dir=str(directory.resolve()), draft=pin(draft_path),
                  code={p: pin(ROOT / p) for p in CODE}, environment=environment(), gate=pin(gate),
                  account_count=0, return_study_count=0, qualified=False, live_boundary_allowed=False)
    draft = validate(packet, directory)
    if stage == "capture":
        packet["urls"] = {item["symbol"]: item["draft_url"] for item in draft["inputs"][4:]}
        packet["policy"] = dict(max_requests=2, retries=0, redirects=False, timeout_seconds=20,
                                bytes_per_response=100000, financial_values_decoded=0)
    else:
        capture_ref = pin(directory / "capture_outcome.json")
        capture = json.loads(bound(capture_ref))
        require(capture["status"] == "captured" and set(capture["sources"]) == {"SPYM", "GLDM"}, "capture_required")
        packet["capture"] = capture_ref
        packet["sources"] = {item["symbol"]: {key: item[key] for key in ("raw", "receipt")} for item in draft["inputs"][:4]}
        packet["sources"].update(capture["sources"])
        packet["structure"] = {symbol: select_close(refs, symbol)[1] for symbol, refs in packet["sources"].items()}
        packet["numeric_budget"] = dict(selected_close_values=6, calculator_invocations=1, basket_cost_results=4)
    return save(directory / f"{stage}_registration.json", packet)


def admit(stage, directory):
    ref = pin(directory / f"{stage}_registration.json")
    packet = json.loads(bound(ref))
    validate(packet, directory)
    require(packet["stage"] == stage, "wrong_stage")
    reviews = {}
    for role in ("root", "manager"):
        review_ref = pin(directory / f"{stage}_{role}_review.json")
        review = json.loads(bound(review_ref))
        require(review["status"] == "accepted" and review["packet_sha256"] == ref["sha256"]
                and review["stage"] == stage and review["reviewer"] == ("root" if role == "root" else "quant_manager_72h"), "review")
        reviews[role] = review_ref
    release_ref = pin(directory / f"{stage}_release.json")
    release = json.loads(bound(release_ref))
    require(release["status"] == "released_once" and release["packet_sha256"] == ref["sha256"]
            and release["stage"] == stage and release["reviews"] == reviews
            and release["max_actions"] == (2 if stage == "capture" else 1), "release")
    start, end = (datetime.fromisoformat(release[k]) for k in ("not_before", "expires_at"))
    require(start.tzinfo is not None and end.tzinfo is not None and start <= now() <= end <= DEADLINE, "release_window")
    return packet, dict(registration=ref, reviews=reviews, release=release_ref)


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise RuntimeError("redirect_not_allowed")


def capture(directory):
    packet, proof = admit("capture", directory)
    save(directory / "capture_claim.json", dict(at=now().isoformat(), proof=proof))
    sources = {}
    try:
        for symbol in ("SPYM", "GLDM"):
            admit("capture", directory)
            url = packet["urls"][symbol]
            save(directory / "sources" / f"{symbol}_request.json", dict(at=now().isoformat(), url=url, attempt=1))
            request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 QuantRobotResearch/1.0", "Accept-Encoding": "identity"})
            with urllib.request.build_opener(NoRedirect).open(request, timeout=20) as response:
                require(response.status == 200 and "json" in response.headers.get("Content-Type", "").lower(), "json_HTTP200")
                body = response.read(100001)
                require(len(body) <= 100000, "response_size")
                headers = {k: response.headers.get(k) for k in ("Content-Type", "Date", "ETag", "Last-Modified")}
            raw_ref = save_raw(directory / "sources" / f"{symbol}.json", body)
            receipt = save(directory / "sources" / f"{symbol}_receipt.json", dict(symbol=symbol, url=url, raw=raw_ref,
                           HTTP_status=200, raw_complete=True, at=now().isoformat(), headers=headers, financial_values_decoded=0))
            sources[symbol] = dict(raw=raw_ref, receipt=receipt)
        admit("capture", directory)
        return save(directory / "capture_outcome.json", dict(status="captured", at=now().isoformat(), sources=sources, proof=proof))
    except Exception as exc:
        save(directory / "capture_failure.json", dict(at=now().isoformat(), status="failed_no_retry", error=str(exc), completed=sources))
        raise


def select_close(refs, symbol):
    receipt = json.loads(bound(refs["receipt"]))
    require(receipt["raw"] == refs["raw"] and receipt["HTTP_status"] == 200 and receipt["raw_complete"], "receipt")
    # All numeric JSON tokens stay strings; only timestamps are converted for date selection.
    def invalid_constant(value):
        raise ValueError("nonstandard_JSON_constant")
    chart = json.loads(bound(refs["raw"]), parse_float=str, parse_int=str, parse_constant=invalid_constant)["chart"]
    require(chart["error"] is None and len(chart["result"]) == 1, "chart_result")
    data = chart["result"][0]
    meta = data["meta"]
    require(meta["symbol"] == symbol and meta["currency"] == "USD" and meta["instrumentType"] == "ETF"
            and meta["exchangeTimezoneName"] == "America/New_York" and meta["dataGranularity"] == "1d", "identity")
    dates = [datetime.fromtimestamp(int(t), ZoneInfo("America/New_York")).date().isoformat() for t in data["timestamp"]]
    require(len(dates) == len(set(dates)) and dates.count(DAY) == 1, "date_selection")
    if symbol in ("SPYM", "GLDM"):
        require(dates == [DAY], "new_source_one_date_only")
    quotes = data["indicators"]["quote"]
    require(len(quotes) == 1 and len(quotes[0]["close"]) == len(dates), "close_alignment")
    for kind, events in data.get("events", {}).items():
        for event in events.values():
            event_day = datetime.fromtimestamp(int(event["date"]), ZoneInfo("America/New_York")).date().isoformat()
            require(event_day != DAY, "selected_date_action_requires_separate_review")
    value = quotes[0]["close"][dates.index(DAY)]
    require(isinstance(value, str), "close_token")
    return value, dict(symbol=symbol, date=DAY, currency="USD", field="quote.close", selected=1, numeric_conversions=0)


def run(directory):
    packet, proof = admit("numeric", directory)
    bound(packet["capture"])
    save(directory / "numeric_claim.json", dict(at=now().isoformat(), proof=proof, numeric_budget=packet["numeric_budget"]))
    try:
        require(set(packet["sources"]) == set(SYMBOLS), "source_set")
        prices = {}
        for symbol, refs in packet["sources"].items():
            prices[symbol], structure = select_close(refs, symbol)
            require(structure == packet["structure"][symbol], "source_structure_changed")
        save(directory / "financial_decode_started.json", dict(at=now().isoformat(), proof=proof, selected_closes=6, calculator_invocations=1))
        result = calculate(prices)
        result.update(at=now().isoformat(), date=DAY, selected_closes=prices, proof=proof,
                      return_study_count=0, account_count=0, qualified=False, deployed_model_changed=False)
        admit("numeric", directory)
        for refs in packet["sources"].values():
            for ref in refs.values():
                bound(ref)
        result_ref = save(directory / "result.json", result)
        verification = verify(json.loads(bound(result_ref)))
        verification_ref = save(directory / "verification.json", dict(result=result_ref, **verification))
        return save(directory / "outcome.json", dict(status="completed_single_point_quantity_only", at=now().isoformat(), result=result_ref,
                                                     verification=verification_ref, proof=proof))
    except Exception as exc:
        save(directory / "numeric_failure.json", dict(at=now().isoformat(), status="failed_no_retry", error=str(exc)))
        raise


def verify(result):
    """Check retained quantities with rational inequalities, not the sizing search."""
    prices = {s: Fraction(v) for s, v in result["selected_closes"].items()}
    checked = 0
    ceil = lambda x: -(-x.numerator // x.denominator)
    baskets = {"old": ("SPY", "EFA", "IEF", "GLD"), "proposed": ("SPYM", "EFA", "IEF", "GLDM")}
    require(set(result["results"]) == {b + "_" + c for b in baskets for c in ("primary", "stress")}, "four_cases")
    for basket, symbols in baskets.items():
        for cost, minimum, bps in (("primary", Fraction(1), 10), ("stress", Fraction("2.50"), 30)):
            case = result["results"][basket + "_" + cost]
            require([leg["symbol"] for leg in case["legs"]] == list(symbols), "basket_identity")
            spent = fees = marked = filled = Fraction(0)
            for leg in case["legs"]:
                q = leg["quantity"]
                require(type(q) is int and q >= 0, "integer_quantity")
                p = Fraction(ceil(prices[leg["symbol"]] * Fraction(10000 + bps, 100)), 100)
                fee = lambda n: Fraction(0) if n == 0 else max(minimum, Fraction(ceil(Fraction(n, 2)), 100))
                require(q * p + fee(q) <= Fraction("247.50") < (q + 1) * p + fee(q + 1), "independent_maximality")
                require(Fraction(leg["buy_price_usd"]) == p and Fraction(leg["commission_usd"]) == fee(q), "independent_price_fee")
                require(Fraction(leg["budget_remainder_usd"]) == Fraction("247.50") - q * p - fee(q), "leg_cash")
                spent += q * p + fee(q)
                filled += q * p
                fees += fee(q)
                marked += q * prices[leg["symbol"]]
                checked += 1
            summary = case["summary"]
            require(Fraction(summary["cash_remaining_usd"]) == 1000 - spent >= 10, "independent_cash")
            require(Fraction(summary["commission_usd"]) == fees and Fraction(summary["fill_notional_usd"]) == filled, "independent_totals")
            require(abs(Fraction(summary["economic_exposure_usd"]) - marked) < Fraction(1, 10**40), "independent_exposure")
    return dict(status="passed", approach="independent_Fraction_maximality_cash_and_exposure", legs_checked=checked, cases_checked=4)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("operation", choices=("capture-preview", "capture", "numeric-preview", "run"))
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--draft", type=Path)
    args = parser.parse_args()
    directory = args.output.resolve()
    if args.operation.endswith("preview"):
        require(args.draft is not None, "draft_required")
        value = registration(args.operation.split("-")[0], directory, args.draft)
    else:
        value = capture(directory) if args.operation == "capture" else run(directory)
    print(json.dumps(value, indent=2))
