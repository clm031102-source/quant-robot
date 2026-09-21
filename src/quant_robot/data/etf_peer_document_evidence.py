"""Extract scoped document observations without inventing historical validity."""
from __future__ import annotations

from datetime import date
import hashlib
import io
import json
from pathlib import Path
import re
import unicodedata
from typing import Any, Mapping


def review_peer_document_text(*, symbol: str, expected_fund_name: str,
                              index_title: str, published_date: str, cover: str,
                              evidence_pages: Mapping[int, str],
                              expected_manager_name: str | None = None) -> dict[str, Any]:
    if not re.fullmatch(r"[0-9]{6}\.SH", symbol):
        raise ValueError("source reviewer requires an explicit SSE symbol")
    published = _publication_date(published_date)
    if (not evidence_pages or any(type(n) is not int or n < 1 or not isinstance(t, str)
                                 for n, t in evidence_pages.items())):
        raise ValueError("explicit physical page numbers and text are required")
    fund, title, first = map(_compact, (expected_fund_name, index_title, cover))
    if not fund.endswith("证券投资基金") or "交易型开放式" not in fund:
        raise ValueError("explicit historical ETF legal identity is required")
    result: dict[str, Any] = {
        "symbol": symbol, "expected_fund_name": expected_fund_name,
        "index_publication_date": published_date, "document_announcement_date": None,
        "status": "manual_field_review", "declared_tracking_index": None,
        "declared_benchmark": None, "evidence_pages": [],
        "known_from": None, "valid_from": None, "valid_to": None,
        "mapping_eligible": False,
        "scope": "selected_document_pages_only; no continuous historical assignment",
    }
    # A multi-fund notice may quote a different fund as its amendment example.
    # Neither its association with this code nor an index sentence proves identity.
    if "关于" in title and "公告" in title:
        result["status"] = "manual_amendment_review"
        return result
    if title.startswith(symbol[:6] + "_"):
        title = title[7:]
    role = re.escape(fund) + r"[-_]?(?:(?:更新的)?招募说明书|基金合同|基金产品资料概要)"
    if not re.match(role, title):
        raise ValueError("index title does not establish the target fund identity")
    first = re.sub(r"^[0-9]{1,3}/[0-9]{1,3}", "", first)
    first = re.sub(r"^" + re.escape(fund) + r"[0-9]{1,3}", "", first)
    if expected_manager_name is not None:
        manager = _compact(expected_manager_name)
        if first.startswith(manager):
            first = first[len(manager):]
    if not re.match(role, first):
        raise ValueError("PDF cover does not establish the target fund identity")
    dates = {date(int(y), int(m), int(d)) for y, m, d in
             re.findall(r"([0-9]{4})年([0-9]{1,2})月([0-9]{1,2})日公告", first)}
    dates.update(date(int(y), int(m), int(d)) for y, m, d in
                 re.findall(r"送出日期:?([0-9]{4})年([0-9]{1,2})月([0-9]{1,2})日", first))
    if len(dates) > 1 or (dates and dates != {published}):
        raise ValueError("document announcement date differs from the official index")
    if dates:
        result["document_announcement_date"] = published_date
    indexes: dict[str, list[int]] = {}
    benchmarks: set[str] = set()
    for number, text in sorted(evidence_pages.items()):
        compact = _compact(text)
        for match in re.finditer(r"本基金(?:的)?标的指数(?:为|是)([^。；;]{1,120})[。；;]", compact):
            prefix = compact[:match.start()]
            clause = re.split(r"[。；;]", prefix)[-1]
            if (re.search(r"假设|例如|示例|以[^。；;]{0,120}为例|(?:修订|修改|变更)[前后]", prefix)
                    or re.search(r"若|如果|假如|倘若", clause)):
                result["status"] = "manual_scope_review"
                return result
            indexes.setdefault(match.group(1), []).append(number)
        benchmarks.update(re.findall(r"业绩比较基准[:：]?([^。；;]{1,120}?)风险收益特征", compact))
    if len(indexes) > 1 or len(benchmarks) > 1:
        raise ValueError("conflicting declarations require manual scope review")
    if indexes:
        value = next(iter(indexes))
        result.update(status="tracking_index_observed", declared_tracking_index=value,
                      evidence_pages=sorted(set(indexes[value])))
    elif benchmarks:
        result.update(status="benchmark_only", declared_benchmark=next(iter(benchmarks)))
    return result


def _compact(value: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("nonempty source text is required")
    return "".join(unicodedata.normalize("NFKC", value).split())


def _publication_date(value: str) -> date:
    if not isinstance(value, str):
        raise ValueError("invalid publication date or sealed holdout")
    published = date.fromisoformat(value)
    if published.isoformat() != value or published >= date(2026, 1, 1):
        raise ValueError("invalid publication date or sealed holdout")
    return published


def review_peer_document_bundle(config: Mapping[str, Any]) -> dict[str, Any]:
    """Re-read selected PDF pages; a field candidate packet is not source authority."""
    source = Path(config["field_candidates_path"])
    raw = source.read_bytes()
    if hashlib.sha256(raw).hexdigest() != config["field_candidates_sha256"]:
        raise ValueError("field candidate packet fingerprint changed")
    payload = json.loads(raw)
    records = [*payload["records"], *config.get("extra_documents", [])]
    if not 1 <= len(records) <= 60:
        raise ValueError("document review exceeds bounded scope")
    # Preflight the entire packet before opening even the first PDF.
    for record in records:
        _publication_date(record["published_date"])
    fingerprints = {str(source): config["field_candidates_sha256"]}
    output = []
    for record in records:
        path = Path(record["path"])
        pdf = path.read_bytes()
        if (not pdf.startswith(b"%PDF") or len(pdf) > 10_000_000
                or hashlib.sha256(pdf).hexdigest() != record["sha256"]):
            raise ValueError("PDF source fingerprint or size is invalid")
        if str(path) in fingerprints:
            raise ValueError("duplicate PDF source path")
        fingerprints[str(path)] = record["sha256"]
        numbers = sorted({x["physical_page"] for x in record["explicit_tracking_statements"]}) or [1]
        if len(numbers) > 8 or any(type(n) is not int or n < 1 for n in numbers):
            raise ValueError("selected PDF page scope is invalid")
        first, pages = _pdf_pages(pdf, numbers)
        try:
            item = review_peer_document_text(
                symbol=record["symbol"], expected_fund_name=config["fund_identities"][record["symbol"]],
                index_title=record["title"], published_date=record["published_date"],
                cover=first, evidence_pages=pages,
                expected_manager_name=config.get("fund_managers", {}).get(record["symbol"]),
            )
        except ValueError as exc:
            item = {"symbol": record["symbol"], "status": "rejected_document_fields",
                    "reason": str(exc), "mapping_eligible": False, "known_from": None}
        output.append({**item, "path": str(path), "sha256": record["sha256"],
                       "url": record["url"], "published_date": record["published_date"]})
    for filename, expected in fingerprints.items():
        if hashlib.sha256(Path(filename).read_bytes()).hexdigest() != expected:
            raise ValueError("source changed during document review")
    counts = {status: sum(x["status"] == status for x in output)
              for status in sorted({x["status"] for x in output})}
    return {"stage": "historical_peer_document_observations", "documents": output,
            "counts": counts, "input_fingerprints": fingerprints,
            "complete_chronology_verified": False, "historical_mapping_written": False,
            "metadata_readiness_cleared": False, "factor_generation_allowed": False,
            "note": "PDF identity and selected fields only; publication chronology, effective dates, "
                    "lifecycle, archive versions and whole-window coverage require separate review."}


def _pdf_pages(raw: bytes, numbers: list[int]) -> tuple[str, dict[int, str]]:
    try:
        from pypdf import PdfReader
    except ImportError as exc:
        raise RuntimeError("Install the pdf-sources optional dependency for source PDF review") from exc
    reader = PdfReader(io.BytesIO(raw))
    if reader.is_encrypted or not 1 <= len(reader.pages) <= 250 or max(numbers) > len(reader.pages):
        raise ValueError("PDF physical page selection is invalid")
    return reader.pages[0].extract_text() or "", {
        n: reader.pages[n - 1].extract_text() or "" for n in numbers}
