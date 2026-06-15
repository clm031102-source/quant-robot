from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


STAGE = "phase_4_16_data_gap_evidence_pack"


def build_data_gap_evidence_pack(gap_rows: list[dict[str, Any]], raw_dir: str | Path) -> dict[str, Any]:
    raw_root = Path(raw_dir)
    raw_index = _load_raw_index(raw_root)
    rows = [_evidence_row(row, raw_index) for row in gap_rows if isinstance(row, dict)]
    pack = {
        "stage": STAGE,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_raw_dir": str(raw_root),
        "safety": _research_only_safety(),
        "summary": _summary(rows),
        "evidence_rows": rows,
        "action_queue": _action_queue(rows),
    }
    pack["markdown"] = render_data_gap_evidence_markdown(pack)
    return pack


def write_data_gap_evidence_pack(output_dir: str | Path, pack: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "data_gap_evidence_pack.json").write_text(
        json.dumps(pack, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "data_gap_evidence_pack.md").write_text(str(pack.get("markdown", "")), encoding="utf-8")
    pd.DataFrame(pack.get("evidence_rows", [])).to_csv(output_path / "data_gap_evidence_rows.csv", index=False)
    pd.DataFrame(pack.get("action_queue", [])).to_csv(output_path / "data_gap_evidence_action_queue.csv", index=False)


def render_data_gap_evidence_markdown(pack: dict[str, Any]) -> str:
    summary = pack.get("summary", {}) if isinstance(pack.get("summary"), dict) else {}
    lines = [
        "# Data Gap Evidence Pack",
        "",
        f"- Stage: {pack.get('stage', STAGE)}",
        f"- Gap rows: {summary.get('gap_rows', 0)}",
        f"- Target raw rows found: {summary.get('target_raw_rows_found', 0)}",
        f"- Gaps with peer trading: {summary.get('gaps_with_peer_trading', 0)}",
        f"- Safety: {pack.get('safety', _research_only_safety())}",
        "",
        "## Evidence Rows",
        "",
        "| Gap ID | Symbol | Missing Date | Target Raw Row | Peer Rows | Previous | Next | Hint |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in pack.get("evidence_rows", []):
        if not isinstance(row, dict):
            continue
        lines.append(
            "| "
            f"{row.get('gap_id', '')} | "
            f"{row.get('symbol', '')} | "
            f"{row.get('missing_date', '')} | "
            f"{row.get('target_raw_row_found', False)} | "
            f"{row.get('peer_rows_on_missing_date', 0)} | "
            f"{row.get('previous_target_date', '')} | "
            f"{row.get('next_target_date', '')} | "
            f"{_table_text(row.get('review_hint', ''))} |"
        )
    if not pack.get("evidence_rows"):
        lines.append("| none | none | none | False | 0 | none | none | none |")
    lines.extend(["", "## Action Queue", ""])
    for action in pack.get("action_queue", []):
        if isinstance(action, dict):
            lines.append(f"{action.get('priority')}. `{action.get('command')}`")
            lines.append(f"   - {action.get('reason', '')}")
    if not pack.get("action_queue"):
        lines.append("- none")
    return "\n".join(lines) + "\n"


def _load_raw_index(raw_root: Path) -> dict[str, dict[str, Any]]:
    index: dict[str, dict[str, Any]] = {}
    for path in sorted(raw_root.glob("*.csv")):
        symbol = _symbol_from_raw_path(path)
        if not symbol:
            continue
        dates = _read_raw_dates(path)
        index[symbol] = {
            "path": str(path),
            "dates": dates,
            "date_set": set(dates),
        }
    return index


def _read_raw_dates(path: Path) -> list[str]:
    frame = pd.read_csv(path, usecols=["time"])
    dates = pd.to_datetime(frame["time"], errors="coerce").dt.date.dropna()
    return [str(value) for value in sorted(set(dates))]


def _evidence_row(gap_row: dict[str, Any], raw_index: dict[str, dict[str, Any]]) -> dict[str, Any]:
    symbol = str(gap_row.get("symbol", "")).strip()
    missing_date = str(gap_row.get("missing_date", "")).strip()
    target = raw_index.get(symbol, {})
    target_dates = list(target.get("dates", []))
    target_date_set = set(target.get("date_set", set()))
    target_found = missing_date in target_date_set
    peer_symbols = sorted(
        peer_symbol
        for peer_symbol, peer in raw_index.items()
        if peer_symbol != symbol and missing_date in set(peer.get("date_set", set()))
    )
    previous_date, next_date = _neighbor_dates(target_dates, missing_date)
    evidence_note = _evidence_note(target_found, target, peer_symbols, previous_date, next_date)
    return {
        "gap_id": str(gap_row.get("gap_id", "")),
        "asset_id": str(gap_row.get("asset_id", "")),
        "symbol": symbol,
        "missing_date": missing_date,
        "resolution_status": str(gap_row.get("resolution_status", "needs_review")),
        "target_raw_file": str(target.get("path", "")),
        "target_raw_row_found": target_found,
        "peer_rows_on_missing_date": len(peer_symbols),
        "peer_symbols_on_missing_date": ";".join(peer_symbols),
        "previous_target_date": previous_date,
        "next_target_date": next_date,
        "evidence_note": evidence_note,
        "review_hint": _review_hint(target_found, peer_symbols),
        "local_only": True,
    }


def _neighbor_dates(dates: list[str], missing_date: str) -> tuple[str, str]:
    previous = ""
    following = ""
    for value in dates:
        if value < missing_date:
            previous = value
        elif value > missing_date:
            following = value
            break
    return previous, following


def _evidence_note(target_found: bool, target: dict[str, Any], peer_symbols: list[str], previous_date: str, next_date: str) -> str:
    target_state = "raw target row exists" if target_found else "raw target row absent"
    target_file = target.get("path") or "target raw file not found"
    peer_state = f"peer_rows_on_missing_date={len(peer_symbols)}"
    neighbors = f"previous_target_date={previous_date or 'none'}, next_target_date={next_date or 'none'}"
    return f"{target_state} in {target_file}; {peer_state}; {neighbors}"


def _review_hint(target_found: bool, peer_symbols: list[str]) -> str:
    if target_found:
        return "raw target row exists; rerun batch import/backfill before accepting this gap."
    if peer_symbols:
        return "raw target row absent while peer ETFs traded; verify suspension/no-trade or obtain external backfill before changing status."
    return "raw target row absent and no peer raw rows found; verify raw coverage and exchange calendar before changing status."


def _summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "gap_rows": len(rows),
        "target_raw_rows_found": sum(1 for row in rows if row.get("target_raw_row_found")),
        "gaps_with_peer_trading": sum(1 for row in rows if int(row.get("peer_rows_on_missing_date", 0)) > 0),
        "raw_target_files_found": sum(1 for row in rows if row.get("target_raw_file")),
        "blocks_api_boundary": True if rows else False,
    }


def _action_queue(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    actions = [
        {
            "priority": 1,
            "track_id": "data_gap_resolution",
            "command": "python scripts\\run_data_gap_resolution.py --resolution-file data\\reports\\residual_data_gap_review\\residual_gap_review_template.csv --output-dir data\\reports\\data_gap_resolution",
            "reason": "Apply reviewed data-gap statuses only after evidence notes are filled.",
            "local_only": True,
        }
    ]
    if any(row.get("target_raw_row_found") for row in rows):
        actions.insert(
            0,
            {
                "priority": 1,
                "track_id": "data_quality",
                "command": "python scripts\\batch_import_etf_csv.py --input-dir data\\raw\\tradingview_etf_csv --raw-dir data\\raw\\tradingview_etf_csv --output-dir data\\processed\\etf_csv",
                "reason": "At least one target raw row exists, so refresh processed ETF CSV before reviewing the gap.",
                "local_only": True,
            },
        )
        for index, action in enumerate(actions, start=1):
            action["priority"] = index
    return actions


def _symbol_from_raw_path(path: Path) -> str:
    match = re.search(r"(?<!\d)(\d{6})[_-]?(SH|SZ)(?![A-Z0-9])", path.stem.upper())
    if not match:
        return ""
    return f"{match.group(1)}.{match.group(2)}"


def _table_text(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def _research_only_safety() -> str:
    return "Research only. Local data-gap evidence only; No broker connection, no account reads, no order placement, no live trading."
