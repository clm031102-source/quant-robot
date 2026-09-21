"""Audit retained manager notice pages without claiming a complete historical archive."""
from __future__ import annotations

from datetime import date
import hashlib
from pathlib import Path
import re
from typing import Any, Mapping
from urllib.parse import urljoin


_INDEX_URL = "https://www.chinaamc.com.cn/product/publishGgList.do"


def _scope(symbol: str, start_date: str, end_date: str, title_filter: str) -> None:
    if not isinstance(symbol, str) or not re.fullmatch(r"[0-9]{6}\.SH", symbol):
        raise ValueError("explicit SSE fund code is required")
    if not isinstance(title_filter, str):
        raise ValueError("explicit title filter is required")
    for value in (start_date, end_date):
        if not isinstance(value, str) or date.fromisoformat(value).isoformat() != value:
            raise ValueError("canonical source window is required")
    if start_date > end_date or end_date >= "2026-01-01":
        raise ValueError("invalid source window or sealed holdout")


def parse_chinaamc_notice_page(raw: bytes, *, symbol: str, start_date: str,
                              end_date: str, requested_page: int,
                              title_filter: str = "") -> dict[str, Any]:
    _scope(symbol, start_date, end_date, title_filter)
    if type(requested_page) is not int or not 1 <= requested_page <= 100:
        raise ValueError("invalid requested page")
    if not isinstance(raw, bytes) or not 1 <= len(raw) <= 2_000_000:
        raise ValueError("invalid source HTML size")
    try:
        from lxml import html
    except ImportError as exc:
        raise RuntimeError("Install public-web optional dependencies for manager HTML review") from exc
    try:
        doc = html.fromstring(raw.decode("utf-8"))
    except (ValueError, UnicodeError) as exc:
        raise ValueError("invalid UTF-8 source HTML") from exc
    forms = doc.xpath('//form[@id="queryForm"]')
    if len(forms) != 1:
        raise ValueError("source query scope form is missing or ambiguous")
    for name, expected in {"fundcode": symbol[:6], "beginDate": start_date,
                           "endDate": end_date, "title": title_filter.strip()}.items():
        fields = forms[0].xpath(f'.//input[@name="{name}"]')
        if len(fields) != 1 or fields[0].get("value", "").strip() != expected:
            raise ValueError("returned query scope differs from requested scope")
    nav = doc.xpath('//div[contains(concat(" ",normalize-space(@class)," ")," page-mod ")]')
    if len(nav) != 1:
        raise ValueError("source pagination is missing or ambiguous")
    current = nav[0].xpath('.//a[contains(concat(" ",normalize-space(@class)," ")," cur ")]')
    if len(current) != 1 or current[0].text_content().strip() != str(requested_page):
        raise ValueError("returned page differs from requested page; query may have reset")
    visible = []
    for link in nav[0].xpath('.//a'):
        label = link.text_content().strip()
        handler = link.get("onclick", "")
        match = re.fullmatch(r"\s*thisPage\s*\(\s*([0-9]+)\s*\)\s*;?\s*", handler)
        if (label.isdigit() or "thisPage" in handler) and not match:
            raise ValueError("unsupported visible page marker; cannot establish pagination")
        if match:
            number = int(match.group(1))
            if not 1 <= number <= 100 or label != str(number):
                raise ValueError("invalid visible page marker")
            visible.append(number)
    if not visible or requested_page not in visible or len(set(visible)) != len(visible):
        raise ValueError("invalid visible page markers")
    rows = doc.xpath('//div[contains(concat(" ",normalize-space(@class)," ")," li ")]')
    if not 1 <= len(rows) <= 20:
        raise ValueError("empty or oversized notice page cannot certify source coverage")
    records = []
    for row in rows:
        cells = row.xpath('.//div[@class="item"]')
        links = cells[0].xpath('./a[@href]') if len(cells) == 2 else []
        if len(links) != 1:
            raise ValueError("malformed notice row")
        title = links[0].text_content().strip()
        published = cells[1].text_content().strip()
        if not title or not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}", published):
            raise ValueError("notice title or publication date is missing")
        if not start_date <= published <= end_date or date.fromisoformat(published).isoformat() != published:
            raise ValueError("publication date outside requested window")
        url = urljoin(_INDEX_URL, links[0].get("href"))
        if not re.fullmatch(r"https://www\.chinaamc\.com\.cn/c/" + re.escape(published) + r"/[0-9]+\.shtml", url):
            raise ValueError("article destination or article date differs from the index")
        records.append({"date": published, "title": title, "article_url": url})
    _check_record_sequence(records)
    return {"requested_page": requested_page, "visible_pages": sorted(visible), "records": records,
            "historical_coverage_verified": False,
            "note": "Fund-filter association is not legal identity or complete amendment coverage."}


def _check_record_sequence(records: list[dict[str, str]]) -> None:
    if len({r["article_url"] for r in records}) != len(records):
        raise ValueError("duplicate article across source rows or pages")
    dates = [r["date"] for r in records]
    if dates != sorted(dates, reverse=True):
        raise ValueError("source pages are not in reverse chronological order")


def review_chinaamc_notice_bundle(config: Mapping[str, Any]) -> dict[str, Any]:
    args = {name: config[name] for name in ("symbol", "start_date", "end_date", "title_filter")}
    _scope(**args)  # Preflight before reading any source page.
    sources = config["pages"]
    if not isinstance(sources, list) or not 1 <= len(sources) <= 100:
        raise ValueError("invalid source page manifest")
    numbers = [x["page"] for x in sources]
    if any(type(n) is not int or not 1 <= n <= 100 for n in numbers) or len(set(numbers)) != len(numbers):
        raise ValueError("duplicate or invalid requested page")
    fingerprints, parsed, records = {}, [], []
    for source in sorted(sources, key=lambda x: x["page"]):
        path = Path(source["path"]).resolve()
        if str(path) in fingerprints:
            raise ValueError("duplicate source path")
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != source["sha256"]:
            raise ValueError("source page fingerprint changed")
        fingerprints[str(path)] = source["sha256"]
        page = parse_chinaamc_notice_page(raw, requested_page=source["page"], **args)
        parsed.append(page)
        records.extend({**r, "index_path": str(path), "index_sha256": source["sha256"]} for r in page["records"])
    visible = {n for page in parsed for n in page["visible_pages"]}
    if set(numbers) != set(range(1, max(visible) + 1)):
        raise ValueError("missing visible source page or unexplained extra page")
    _check_record_sequence(records)
    for path, expected in fingerprints.items():
        if hashlib.sha256(Path(path).read_bytes()).hexdigest() != expected:
            raise ValueError("source page changed during review")
    return {"stage": "retained_chinaamc_notice_index_review", "query_scope": args,
            "pages": parsed, "records": records, "input_fingerprints": fingerprints,
            "visible_index_pagination_complete": True, "historical_coverage_verified": False,
            "mapping_authority_written": False, "factor_generation_allowed": False}
