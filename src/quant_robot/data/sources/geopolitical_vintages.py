"""Finite author-vintage acquisition and source windows; no signals or prices."""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import time

PROPOSAL_SHA = "58a5f1e9ca392eadf6f2e90468d6100257a9e994e7b278eef5065d8f1d66dae4"
LABEL = "Recent GPR Threats (Index: 1985:2019=100)"
LIMIT = 4_000_000
MONTHS = tuple(f"{y}{m:02d}" for y in range(2022, 2026) for m in range(1, 13)
               if "202203" <= f"{y}{m:02d}" <= "202512")
NEW_MONTHS = MONTHS[1:-1]
BASE = "https://api.github.com/repos/iacoviel/iacoviel.github.io/commits?path="
RAW_BASE = "https://raw.githubusercontent.com/iacoviel/iacoviel.github.io/"
SCOPE_RELATIVE = "data/reports/geopolitical_source_expansion_20261104/scope.json"


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def protocol_sha(path: Path) -> str:
    # Match pm_startup_gate._read_required_file universal-newline text hashing.
    return hashlib.sha256(path.read_text(encoding="utf-8").encode("utf-8")).hexdigest()


def write_json(path: Path, value: dict) -> None:
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2, allow_nan=False)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def source_path(month: str) -> str:
    if month not in MONTHS:
        raise ValueError("month outside frozen proposal")
    return f"gpr_archive_files/data_gpr_export_{month}.xls"


def history_url(month: str) -> str:
    return BASE + source_path(month).replace("/", "%2F") + "&per_page=100"


def raw_url(month: str, commit: str) -> str:
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("full immutable commit required")
    return RAW_BASE + commit + "/" + source_path(month)


def _timestamp(value: str) -> datetime:
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if result.tzinfo is None:
        raise ValueError("timezone missing")
    return result.astimezone(timezone.utc)


def select_commit(raw: bytes, receipt: dict, month: str) -> dict:
    source_path(month)
    if receipt.get("status_code") != 200 or receipt.get("link"):
        raise ValueError("incomplete or paginated history")
    if not receipt.get("content_type", "").startswith("application/json"):
        raise ValueError("history content type changed")
    history = json.loads(raw)
    if not isinstance(history, list) or not 0 < len(history) < 100:
        raise ValueError("history empty or completeness unproven")
    cutoff = datetime(int(month[:4]), int(month[4:]), 14, 16, tzinfo=timezone.utc)
    previous, seen, eligible = None, set(), []
    for item in history:
        commit = item["sha"]
        if not re.fullmatch(r"[0-9a-f]{40}", commit) or commit in seen:
            raise ValueError("invalid or duplicate commit")
        seen.add(commit)
        author = _timestamp(item["commit"]["author"]["date"])
        committer = _timestamp(item["commit"]["committer"]["date"])
        if author > committer or (previous is not None and committer >= previous):
            raise ValueError("ambiguous or inconsistent history clock")
        previous = committer
        if author < cutoff and committer < cutoff:
            eligible.append({"commit_sha": commit, "author_at": author.isoformat(),
                             "committer_at": committer.isoformat(), "cutoff": cutoff.isoformat()})
    if not eligible:
        raise ValueError("no version before fixed cutoff")
    return eligible[0]


def source_window(path: Path, month: str) -> list[dict]:
    import xlrd  # Optional xls-sources dependency; never runs spreadsheet code.

    source_path(month)
    book = xlrd.open_workbook(path)
    sheet = book.sheet_by_index(0)
    headers = sheet.row_values(0)
    for key in ("month", "GPRT", "var_name", "var_label"):
        if headers.count(key) != 1:
            raise ValueError("source schema is ambiguous")
    date_col, value_col = headers.index("month"), headers.index("GPRT")
    name_col, label_col = headers.index("var_name"), headers.index("var_label")
    labels = [sheet.cell_value(row, label_col) for row in range(1, sheet.nrows)
              if sheet.cell_value(row, name_col) == "GPRT"]
    if labels != [LABEL]:
        raise ValueError("source component or normalization changed")
    end = int(month[:4]) * 12 + int(month[4:]) - 1
    required = [f"{(n - 1) // 12:04d}-{(n - 1) % 12 + 1:02d}" for n in range(end - 12, end + 1)]
    values = {}
    for row in range(1, sheet.nrows):
        cell = sheet.cell(row, date_col)
        if cell.ctype != xlrd.XL_CELL_DATE:
            continue
        day = xlrd.xldate_as_datetime(cell.value, book.datemode)
        key = day.strftime("%Y-%m")
        if key not in required:
            continue
        if key in values or day.day != 1 or day.time().isoformat() != "00:00:00":
            raise ValueError("duplicate or non-monthly required date")
        value_cell = sheet.cell(row, value_col)
        value = value_cell.value
        if (value_cell.ctype != xlrd.XL_CELL_NUMBER or isinstance(value, bool)
                or not isinstance(value, (int, float)) or not math.isfinite(value) or value < 0):
            raise ValueError("required GPRT missing or invalid")
        values[key] = {"month": key, "GPRT": value, "excel_row_one_based": row + 1}
    if sorted(values) != required:
        raise ValueError("required thirteen-month window incomplete")
    return [values[key] for key in required]


def fetch_once(folder: Path, name: str, url: str, scope_sha: str, session) -> dict:
    # The caller supplies only fixed history or selected immutable raw URLs.
    claim = {"url": url, "started_at": now(), "scope_sha256": scope_sha,
             "maximum_response_bytes": LIMIT, "no_retries": True}
    write_json(folder / f"{name}_claim.json", claim)
    receipt = {**claim, "status": "failed", "body_complete": False}
    started = time.monotonic()
    try:
        with session.get(url, timeout=(10, 20), allow_redirects=False, stream=True) as response:
            receipt.update(status_code=response.status_code,
                           link=response.headers.get("Link"),
                           content_type=response.headers.get("Content-Type", ""),
                           server_date=response.headers.get("Date"),
                           rate_limit_remaining=response.headers.get("X-RateLimit-Remaining"),
                           rate_limit_reset=response.headers.get("X-RateLimit-Reset"))
            body = bytearray()
            for chunk in response.iter_content(65536):
                if time.monotonic() - started > 90 or len(body) + len(chunk) > LIMIT:
                    raise ValueError("response time or size budget exceeded")
                body.extend(chunk)
            path = folder / (name + (".json" if name.endswith("history") else ".xls"))
            with path.open("xb") as handle:
                handle.write(body)
                handle.flush()
                os.fsync(handle.fileno())
            receipt.update(body_complete=True, bytes=len(body), sha256=sha(path),
                           status="received" if response.status_code == 200 else "http_rejected")
    except Exception as exc:
        receipt["failure"] = type(exc).__name__ + ": " + str(exc)[:200]
    receipt["finished_at"] = now()
    write_json(folder / f"{name}_receipt.json", receipt)
    return receipt


def verify_scope(scope_path: Path, *, repo_root: Path) -> dict:
    if scope_path.resolve() != (repo_root / SCOPE_RELATIVE).resolve():
        raise ValueError("fixed source scope cannot be consumed from another location")
    scope = json.loads(scope_path.read_text(encoding="utf-8"))
    if (scope["stage"] != "source_only_expansion" or scope["months"] != list(NEW_MONTHS)
            or scope["maximum_requests"] != 88 or scope["maximum_response_bytes"] != LIMIT
            or scope["proposal_sha256"] != PROPOSAL_SHA
            or any(scope[key] is not False for key in (
                "signal_generation_allowed", "financial_execution_allowed", "final_holdout_allowed"))):
        raise ValueError("scope differs from finite source-only authority")
    for pin in scope["pins"]:
        if sha(Path(pin["path"])) != pin["sha256"]:
            raise ValueError("frozen input changed: " + pin["path"])
    for relative, expected in scope["required_reading_hashes"].items():
        if protocol_sha(repo_root / relative) != expected:
            raise ValueError("PM protocol changed after preparation")
    gate = json.loads(Path(scope["gate_path"]).read_text(encoding="utf-8"))
    if gate.get("status") != "ready" or gate.get("blockers") or gate.get("primary_market") != "CN_ETF":
        raise ValueError("PM review gate not ready")
    return scope


def collect(scope_path: Path, *, repo_root: Path) -> dict:
    import requests

    verify_scope(scope_path, repo_root=repo_root)
    folder = scope_path.parent
    digest = sha(scope_path)
    write_json(folder / "execution_claim.json", {"started_at": now(), "scope_sha256": digest})
    results, count, systemic_stop = [], 0, False
    with requests.Session() as session:
        session.trust_env = False
        session.headers.update({"Accept-Encoding": "identity", "User-Agent": "quant-robot-source-audit/1"})
        for month in NEW_MONTHS:
            row = {"month": month, "status": "unknown"}
            if systemic_stop:
                row["failure"] = "not_attempted_after_systemic_http_failure"
                results.append(row)
                continue
            try:
                history = fetch_once(folder, month + "_history", history_url(month), digest, session)
                count += 1
                if history.get("status_code") in {401, 403, 429}:
                    systemic_stop = True
                if history["status"] != "received":
                    raise ValueError("history request failed")
                choice = select_commit((folder / f"{month}_history.json").read_bytes(), history, month)
                row.update(choice)
                vintage = fetch_once(folder, month + "_vintage", raw_url(month, choice["commit_sha"]), digest, session)
                count += 1
                if vintage.get("status_code") in {401, 403, 429}:
                    systemic_stop = True
                if vintage["status"] != "received":
                    raise ValueError("vintage request failed")
                row["window"] = source_window(folder / f"{month}_vintage.xls", month)
                row.update(status="source_window_verified_conditionally", raw_sha256=vintage["sha256"])
            except Exception as exc:
                # Format decoders have their own exception classes. Preserve each
                # unknown month and continue; KeyboardInterrupt still aborts.
                row["failure"] = type(exc).__name__ + ": " + str(exc)[:300]
            write_json(folder / f"{month}_review.json", row)
            results.append(row)
            print(json.dumps({"month": month, "status": row["status"], "requests": count}), flush=True)
    result = {"finished_at": now(), "scope_sha256": digest, "requests": count,
              "passed": sum(r["status"] == "source_window_verified_conditionally" for r in results),
              "total_new_months": 44, "source_publication_independently_certified": False,
              "signal_generated": False, "ETF_data_accessed": False, "results": results}
    write_json(folder / "source_expansion_result.json", result)
    return result
