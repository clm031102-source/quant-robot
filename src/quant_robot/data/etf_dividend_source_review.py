"""Review retained notices and complete index pages; no network or market data."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
from typing import Any

from quant_robot.data.etf_dividend_notice import parse_cash_dividend_notice, validate_announcement_page
from quant_robot.paper.corporate_actions import CorporateActionLedger
from quant_robot.storage.atomic import atomic_write_json
from quant_robot.storage.fingerprints import sha256_file


def review_dividend_sources(config: dict[str, Any], *, output_dir: str | Path) -> dict[str, Any]:
    symbol = config["symbol"]
    inventory: dict[str, str] = {}
    indexed, windows = [], []
    for item in config["index_pages"]:
        record = json.loads(_read_pinned(item["request_record"], item["request_record_sha256"], inventory))
        params = record["params"]
        if (params.get("TITLE") != "" or params.get("BULLETIN_TYPE") != ""
                or params.get("SECURITY_CODE") != symbol[:6]
                or params.get("sqlId") != "COMMON_PL_JJXX_JJGG_NEW_L"):
            raise ValueError("index request must use the unfiltered official fund catalogue")
        first, last = params["START_DATE"], params["END_DATE"]
        raw = _read_pinned(item["response"], record["response_sha256"], inventory)
        indexed.extend(validate_announcement_page(json.loads(raw), symbol=symbol, start=first, end=last))
        windows.append((date.fromisoformat(first), date.fromisoformat(last)))
    ordered = sorted(windows)
    if (not ordered or ordered[0][0].isoformat() != config["window_start"]
            or ordered[-1][1].isoformat() != config["window_end"]
            or any(a[1] + timedelta(days=1) != b[0] for a, b in zip(ordered, ordered[1:]))):
        raise ValueError("index windows overlap or do not cover the requested range")
    if len({row["URL"] for row in indexed}) != len(indexed):
        raise ValueError("duplicate index URLs across windows")
    manual = [row["URL"] for row in indexed if row["review_kind"] == "manual_action_review"]
    candidates = {row["URL"]: row for row in indexed if row["review_kind"] == "cash_distribution_notice"}
    if manual:
        raise ValueError("nonstandard actions or corrections require manual source review")
    supplied = {item["url_path"]: item for item in config["notices"]}
    if len(supplied) != len(config["notices"]) or set(supplied) != set(candidates):
        raise ValueError("notice documents do not match all indexed cash distributions")
    notices = []
    for url, item in supplied.items():
        raw = _read_pinned(item["pdf"], item["sha256"], inventory)
        pages, extractor = _pdf_text(raw)
        parsed = parse_cash_dividend_notice("\n".join(pages), symbol=symbol,
            announcement_date=candidates[url]["SSEDATE"])
        notices.append({**parsed, "source_url": "https://www.sse.com.cn" + url,
            "source_sha256": item["sha256"], "pdf_pages": len(pages), "extractor": extractor})
    notices.sort(key=lambda item: item["ex_date"])
    keys = {(item["symbol"], item["ex_date"]) for item in notices}
    if len(keys) != len(notices):
        raise ValueError("duplicate or conflicting cash dividend economic events")
    if not notices:
        raise ValueError("no cash notices; an empty catalogue is not zero-event proof")
    result = {"schema_version": 1, "stage": "official_dividend_notice_field_review",
        "symbol": symbol, "window_start": config["window_start"], "window_end": config["window_end"],
        "index_records": len(indexed), "complete_index_pages": len(config["index_pages"]),
        "notices": notices, "notice_fields_reconciled": True,
        "all_corporate_actions_coverage_verified": False, "execution_accounting_source_verified": False,
        "remaining_requirements": ["independent_distribution_completeness_check",
            "share_conversion_history_and_original_disclosure_versions",
            "actual_broker_tax_fee_rounding_and_payment_availability",
            "other_etf_assets_and_raw_price_adjustment_reconciliation"],
        "boundaries": {"network_requested": False, "market_dataset_read": False,
            "factor_or_strategy_run": False, "final_holdout_read": False,
            "broker_connected": False, "promotion_allowed": False},
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "input_files": [{"path": path, "sha256": digest} for path, digest in inventory.items()]}
    if any(sha256_file(path) != digest for path, digest in inventory.items()):
        raise ValueError("source changed during review")
    result["fixture_drill"] = _fixture_drill(notices, Path(output_dir))
    result["implementation_sha256"] = {Path(path).name: sha256_file(path)
        for path in (Path(__file__), Path(__file__).with_name("etf_dividend_notice.py"))}
    return result


def _read_pinned(path: str, expected: str, inventory: dict[str, str]) -> bytes:
    raw = Path(path).read_bytes()
    observed = hashlib.sha256(raw).hexdigest()
    if observed != expected:
        raise ValueError("source fingerprint mismatch: " + str(path))
    inventory[str(Path(path).resolve())] = observed
    return raw


def _pdf_text(raw: bytes) -> tuple[list[str], str]:
    import io
    try:
        import pypdf
    except ImportError as exc:
        raise RuntimeError("PDF source review requires the optional pdf-sources dependency") from exc
    if not raw.startswith(b"%PDF"):
        raise ValueError("retained notice is not a PDF")
    reader = pypdf.PdfReader(io.BytesIO(raw))
    if reader.is_encrypted or not 1 <= len(reader.pages) <= 6:
        raise ValueError("encrypted or nonstandard notice needs manual review")
    pages = [page.extract_text() or "" for page in reader.pages]
    if not all(pages) or sum(map(len, pages)) > 80_000:
        raise ValueError("empty or nonstandard PDF text extraction")
    return pages, "pypdf " + pypdf.__version__


def _fixture_drill(notices: list[dict[str, Any]], output_dir: Path) -> dict[str, Any]:
    if not all(item["notice_states_tax_exemption"] for item in notices):
        return {"ran": False, "reason": "notice tax statement missing; no net cash assumed"}
    events = [{"event_id": f"sse-fixture:{item['symbol']}:{item['ex_date']}",
        "asset_id": "CN_ETF_XSHG_" + item["symbol"][:6], "kind": "cash_dividend",
        **{key: item[key] for key in ("announced_date", "record_date", "ex_date", "pay_date")},
        "net_cash_per_share": float(item["cash_per_share"])} for item in notices]
    sessions = sorted({date.fromisoformat(item[key]) for item in events for key in ("record_date", "ex_date", "pay_date")})
    path = output_dir / "notice_ledger_fixture.json"
    assets = {item["asset_id"] for item in events}
    dataset = {"schema_version": 1,
        "source_ref": "OFFLINE FIXTURE ONLY: notice cash, stated tax exemption, assumed zero broker dividend fee; no coverage certification",
        "coverage_start": str(sessions[0]), "coverage_end": str(sessions[-1]),
        "asset_ids": sorted(assets), "events": events}
    atomic_write_json(path, dataset)
    positions = dict.fromkeys(assets, 100)
    ledger = CorporateActionLedger(path, assets, sessions, positions)
    steps, cash = [], 0.0
    for session in sessions:
        paid_before, _ = ledger.before_session(session, positions, [])
        receivable_before = ledger.receivable
        paid_after = ledger.after_session(session, positions)
        cash += paid_before + paid_after
        steps.append({"date": str(session), "cash_before_close": paid_before,
            "receivable_before_close": receivable_before, "cash_after_close": paid_after})
    return {"ran": True, "held_shares_per_asset": 100,
        "assumptions": "synthetic unchanged holdings, notice tax exemption, zero unverified broker dividend fee",
        "cash_received": round(cash, 2), "unpaid_receivable": ledger.receivable, "steps": steps,
        "source_audit_verified": ledger.evidence()["source_audit_verified"],
        "counts_as_forward_paper_days": 0, "qualifies_for_promotion": False,
        "fixture_path": str(path), "fixture_sha256": sha256_file(path)}
