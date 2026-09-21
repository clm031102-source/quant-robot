"""One public current-curve observation per local weekday; no research admission.

Receipt time is never backdated to the curve's observation date. This archive
does not certify original publication, unobserved historical revisions or fills.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import hashlib
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re


SOURCE_URL = "https://yield.chinabond.com.cn/cbweb-cbrc-web/cbrc/showCbrc"
_CHINA = timezone(timedelta(hours=8))
_LIMIT = 1_000_000
_NAMES = {
    "ChinaBond Government Bond Yield Curve": "government",
    "ChinaBond Financial Bond of Commercial Bank Yield Curve (AAA)": "bank",
    "ChinaBond CP&Note Yield Curve (AAA)": "aaa_cp_note",
}


def _utc_now():
    return datetime.now(timezone.utc)


def _new_session():
    import requests

    return requests.Session()


def _write_json(path, value):
    with path.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(value, handle, ensure_ascii=False, indent=2)
        handle.flush()
        os.fsync(handle.fileno())


class _CurveTable(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.depth = self.regions = self.tables = 0
        self.rows = []
        self.row = self.cell = None

    def handle_starttag(self, tag, attrs):
        if tag == "div":
            if dict(attrs).get("id") == "gjqxData":
                self.regions += 1
                if self.depth:
                    raise ValueError("nested source region")
                self.depth = 1
            elif self.depth:
                self.depth += 1
        if not self.depth:
            return
        if tag == "table":
            self.tables += 1
        elif tag == "tr":
            if self.row is not None:
                raise ValueError("nested source row")
            self.row = []
        elif tag in {"td", "th"}:
            if self.row is None or self.cell is not None:
                raise ValueError("invalid source cell")
            self.cell = []

    def handle_endtag(self, tag):
        if not self.depth:
            return
        if tag in {"td", "th"}:
            if self.cell is None or self.row is None:
                raise ValueError("unmatched source cell")
            self.row.append(" ".join("".join(self.cell).split()))
            self.cell = None
        elif tag == "tr":
            if self.row is None or self.cell is not None:
                raise ValueError("unfinished source row")
            self.rows.append(self.row)
            self.row = None
        elif tag == "div":
            self.depth -= 1

    def handle_data(self, data):
        if self.cell is not None:
            self.cell.append(data)


def parse_current_page(raw: bytes, *, observed_at: datetime) -> dict:
    if not isinstance(raw, bytes) or len(raw) > _LIMIT:
        raise ValueError("invalid response size")
    if observed_at.tzinfo is None:
        raise ValueError("receipt clock must be timezone aware")
    parser = _CurveTable()
    parser.feed(raw.decode("utf-8"))
    parser.close()
    if (parser.regions != 1 or parser.tables != 1 or parser.depth
            or parser.row is not None or parser.cell is not None or len(parser.rows) != 4):
        raise ValueError("source table shape changed")
    header = parser.rows[0]
    if len(header) != 9 or header[1:] != ["3月", "6月", "1年", "3年", "5年", "7年", "10年", "30年"]:
        raise ValueError("source units or tenors changed")
    if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}\(%\)", header[0]):
        raise ValueError("source date or unit missing")
    day = date.fromisoformat(header[0][:10])
    if day > observed_at.astimezone(_CHINA).date():
        raise ValueError("source observation lies after receipt date")
    values = {}
    for row in parser.rows[1:]:
        if len(row) != 9 or row[0] not in _NAMES or _NAMES[row[0]] in values:
            raise ValueError("source curve identity changed")
        value = row[3]
        if not re.fullmatch(r"-?[0-9]+(?:\.[0-9]+)?", value) or not Decimal(value).is_finite():
            raise ValueError("missing or invalid one-year yield")
        values[_NAMES[row[0]]] = value
    if set(values) != {"government", "bank", "aaa_cp_note"}:
        raise ValueError("source curves incomplete")
    return {"observation_date": day.isoformat(), "tenor_years": 1,
            "yields_percent": {key: values[key] for key in ("government", "aaa_cp_note")}}


def capture_current_observation(*, repo_root: Path, run_gate, execute=False) -> dict:
    started = _utc_now()
    local = started.astimezone(_CHINA)
    due = local.weekday() < 5 and (local.hour, local.minute) >= (18, 5)
    common = {"research_admission_granted": False, "historical_vintage_verified": False}
    if not execute:
        return {**common, "status": "preview", "due": due, "source_url": SOURCE_URL,
                "maximum_requests": 1, "maximum_response_bytes": _LIMIT}
    if not due:
        return {**common, "status": "not_due"}
    root = Path(repo_root).resolve()
    folder = (root / "data/reports/chinabond_forward_observations" / local.date().isoformat()).resolve()
    if not folder.is_relative_to(root):
        raise ValueError("archive leaves workspace")
    record_path, raw_path = folder / "record.json", folder / "response.html"
    claim_path = folder / "claim.json"
    if claim_path.exists():
        try:
            prior = json.loads(record_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return {**common, "status": "attempt_incomplete", "record_path": str(record_path)}
        if not isinstance(prior, dict) or prior.get("status") not in {
                "observed_unqualified", "stale_observation_unqualified", "source_rejected"}:
            return {**common, "status": "archive_integrity_failed", "record_path": str(record_path)}
        if prior.get("raw_sha256"):
            try:
                with raw_path.open("rb") as handle:
                    kept = handle.read(_LIMIT + 1)
                if len(kept) > _LIMIT or hashlib.sha256(kept).hexdigest() != prior["raw_sha256"]:
                    raise ValueError("saved response fingerprint changed")
            except (OSError, ValueError):
                return {**common, "status": "archive_integrity_failed", "record_path": str(record_path)}
        return {**common, "status": "already_attempted", "previous_status": prior.get("status"),
                "record_path": str(record_path)}
    folder.mkdir(parents=True, exist_ok=True)
    gate = run_gate(folder / "startup_gate")
    if gate.get("status") != "ready" or gate.get("blockers") or gate.get("primary_market") != "CN_ETF":
        return {**common, "status": "gate_blocked"}
    claim = {"schema_version": 1, "source_url": SOURCE_URL, "started_at": started.isoformat(),
             "local_attempt_date": local.date().isoformat(), "maximum_requests": 1,
             "collector_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
             "purpose": "forward_source_observation_only", **common}
    try:
        _write_json(claim_path, claim)
    except FileExistsError:
        return {**common, "status": "attempt_incomplete", "record_path": str(record_path)}
    record = {**claim, "status": "source_rejected", "source_published_at": None,
              "record_path": str(record_path), "raw_path": str(raw_path)}
    try:
        record["failure_stage"] = "request"
        with _new_session() as session:
            session.trust_env = False
            with session.get(SOURCE_URL, timeout=(10, 20), stream=True,
                             allow_redirects=False) as response:
                record["http_status"] = response.status_code
                if response.status_code != 200:
                    raise ValueError("HTTP response rejected")
                raw = bytearray()
                record["failure_stage"] = "response_read"
                for chunk in response.iter_content(65536):
                    raw.extend(chunk)
                    if len(raw) > _LIMIT:
                        raise ValueError("response exceeds size budget")
                received = _utc_now()
                if received < started:
                    raise ValueError("receipt clock moved backwards")
                record["observed_at"] = received.isoformat()
                record["server_date_header"] = str(response.headers.get("Date", ""))[:200]
                record["raw_sha256"] = hashlib.sha256(raw).hexdigest()
                record["raw_bytes"] = len(raw)
                record["failure_stage"] = "raw_archive"
                with raw_path.open("xb") as handle:
                    handle.write(raw)
                    handle.flush()
                    os.fsync(handle.fileno())
        record["failure_stage"] = "source_parse"
        record.update(parse_current_page(bytes(raw), observed_at=received))
        record["status"] = ("observed_unqualified" if record["observation_date"] == local.date().isoformat()
                            else "stale_observation_unqualified")
        record.pop("failure_stage", None)
    except Exception as exc:
        # Preserve the attempt and any acquired raw body; never retry implicitly.
        record["failure_kind"] = type(exc).__name__
    _write_json(record_path, record)
    return {key: record[key] for key in ("status", "record_path", "raw_path",
            "research_admission_granted", "historical_vintage_verified")}
