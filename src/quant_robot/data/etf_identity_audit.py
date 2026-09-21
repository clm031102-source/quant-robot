"""Identity-only diagnostics; never grants historical membership or promotion."""
from __future__ import annotations

from datetime import date, datetime, timezone
import json
from pathlib import Path
import re
from typing import Any

import numpy as np
import pandas as pd

from quant_robot.data.etf_execution_price_audit import (
    FINAL_HOLDOUT_START, _asset_id, _inventory, _read_partition,
)
from quant_robot.storage.fingerprints import sha256_file

IDENTITY_COLUMNS = ("date", "symbol", "asset_id")
CATALOG_COLUMNS = ("symbol", "name", "is_etf", "status", "list_date", "delist_date")


def audit_identity_frames(bars: pd.DataFrame, catalogues: dict[str, pd.DataFrame],
                          observations: pd.DataFrame) -> dict[str, Any]:
    """Compare labels and dated roster appearances without imputing absences."""
    bars = _identities(bars)
    observations = _identities(observations)
    if bars.empty:
        raise ValueError("empty bounded bar identities")
    if bars.duplicated(["symbol", "date"]).any():
        raise ValueError("duplicate bar identity keys")
    if observations.duplicated(["symbol", "date"]).any():
        raise ValueError("duplicate roster identity keys")
    invalid = bars.asset_id.ne(bars.symbol.map(_asset_id)) | bars.symbol.map(_asset_id).isna()
    if (observations.asset_id.ne(observations.symbol.map(_asset_id))
            | observations.symbol.map(_asset_id).isna()).any():
        raise ValueError("invalid roster identities")
    summaries, changes, previous = [], [], None
    for captured, supplied in sorted(catalogues.items()):
        date.fromisoformat(captured)
        frame = _catalogue(supplied)
        joined = bars.merge(frame, on="symbol", how="left", validate="many_to_one", indicator=True)
        present = joined._merge.eq("both")
        label = joined.is_etf.astype("boolean")
        counts = {
            "snapshot_etf": _count(joined, present & label.fillna(False)),
            "snapshot_non_etf": _count(joined, present & ~label.fillna(False)),
            "missing_metadata": _count(joined, ~present),
        }
        before_listing = present & joined.list_date.notna() & joined.date.lt(joined.list_date)
        after_delisting = present & joined.delist_date.notna() & joined.date.gt(joined.delist_date)
        summaries.append({"captured_on": captured, "rows": len(frame),
            "status_counts": frame.status.fillna("unknown").value_counts().to_dict(),
            "label_counts": {"etf": int(frame.is_etf.sum()), "non_etf": int((~frame.is_etf).sum())},
            "bar_classification": counts, "missing_list_dates": int(frame.list_date.isna().sum()),
            "bars_before_snapshot_list_date": _count(joined, before_listing),
            "bars_after_snapshot_delist_date": _count(joined, after_delisting),
            "historical_known_at_verified": False})
        if previous is not None:
            old_date, old = previous
            paired = old[["symbol", "is_etf"]].merge(frame[["symbol", "is_etf", "name"]],
                on="symbol", suffixes=("_old", "_new"), validate="one_to_one")
            for item in paired.loc[paired.is_etf_old.ne(paired.is_etf_new)].to_dict("records"):
                changes.append({"symbol": item["symbol"], "name": item["name"],
                    "from_snapshot": old_date, "to_snapshot": captured,
                    "from_is_etf": bool(item["is_etf_old"]), "to_is_etf": bool(item["is_etf_new"])})
        previous = captured, frame
    seen = bars.merge(observations[["symbol", "date"]], on=["symbol", "date"],
        how="left", validate="one_to_one", indicator=True)
    matched = seen._merge.eq("both")
    result = {"schema_version": 1, "stage": "cn_etf_identity_source_review",
        "scope": "dates_codes_catalogue_labels_only", "historical_membership_verified": False,
        "bar_rows": len(bars), "bar_assets": int(bars.symbol.nunique()),
        "invalid_bar_identities": _count(bars, invalid), "catalogues": summaries,
        "classification_changes": changes,
        "cached_roster_observations": {"rows": len(observations),
            "assets": int(observations.symbol.nunique()), "bar_rows_with_same_day_observation": _count(seen, matched),
            "bar_rows_without_same_day_observation": _count(seen, ~matched),
            "bar_assets_never_observed": sorted(set(bars.symbol) - set(observations.symbol)),
            "absence_is_negative_classification": False},
        "remaining_requirements": ["historical_classification_and_corrections_known_at",
            "listing_delisting_conversion_and_suspension_evidence",
            "transport_payload_retention_and_authenticity",
            "unexplained_roster_absences", "corporate_actions_and_adjustment_history"],
        "boundaries": {"source_mutated": False, "provider_requested": False,
            "price_or_nav_values_read": False, "factor_or_return_values_read": False,
            "final_holdout_read": False, "eligibility_generated": False,
            "promotion_allowed": False, "broker_connection_allowed": False}}
    # Pandas missing scalars and numpy scalars become portable strict JSON types.
    return json.loads(pd.Series({"report": result}).to_json(date_format="iso"))["report"]


def run_identity_audit(*, data_root: str | Path, catalogues: list[dict[str, str]],
                       share_root: str | Path, start_date: str, end_date: str) -> dict[str, Any]:
    start, end = date.fromisoformat(start_date), date.fromisoformat(end_date)
    if start > end or end >= FINAL_HOLDOUT_START:
        raise ValueError("identity audit requires an ordered window before final holdout")
    inventory: dict[str, dict[str, Any]] = {}
    bar_frames = []
    base = Path(data_root) / "processed/bars/frequency=1d/market=CN_ETF"
    for year in range(start.year, end.year + 1):
        bar_frames.extend(_read_partition(base / f"year={year}", IDENTITY_COLUMNS, start, end,
            inventory, partition_year=year))
    snapshots = {}
    for item in catalogues:
        captured, path = item["captured_on"], Path(item["path"])
        date.fromisoformat(captured)
        if captured in snapshots or f"snapshot={captured}" not in path.parts:
            raise ValueError("duplicate or mismatched catalogue snapshot date")
        _inventory(path, inventory)
        if path.suffix == ".parquet":
            snapshots[captured] = pd.read_parquet(path, columns=list(CATALOG_COLUMNS))
        elif path.suffix == ".csv":
            snapshots[captured] = pd.read_csv(path, usecols=list(CATALOG_COLUMNS))
        else:
            raise ValueError("unsupported catalogue format")
    if not snapshots:
        raise ValueError("at least one dated catalogue is required")
    rosters, evidence = _cached_rosters(Path(share_root), start, end, inventory)
    result = audit_identity_frames(pd.concat(bar_frames, ignore_index=True), snapshots, rosters)
    result.update({"window": {"start": start_date, "end": end_date},
        "generated_at": datetime.now(timezone.utc).isoformat(), "cached_roster_evidence": evidence,
        "input_files": list(inventory.values()), "source_changed_during_audit": [item["path"]
            for item in inventory.values() if sha256_file(item["path"]) != item["sha256"]],
        "implementation_sha256": sha256_file(Path(__file__))})
    return result


def _cached_rosters(root: Path, start: date, end: date,
                    inventory: dict[str, dict[str, Any]]) -> tuple[pd.DataFrame, dict[str, Any]]:
    manifest_path = root / "public_source_manifest.json"
    _inventory(manifest_path, inventory)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    frames, used, unavailable = [], [], []
    # Follow only the current manifest; obsolete six-month files are not scanned.
    for key, item in manifest["requests"].items():
        if not key.startswith(("sse:", "szse:")):
            continue
        parts = key.split(":")
        if len(parts) != (2 if parts[0] == "sse" else 3):
            raise ValueError("invalid roster request key")
        first, last = date.fromisoformat(parts[1]), date.fromisoformat(parts[-1])
        if first > last or last >= FINAL_HOLDOUT_START:
            raise ValueError("invalid or final holdout roster window")
        if last < start or first > end:
            continue
        if item["status"] != "completed":
            unavailable.append(key)
            continue
        sse = parts[0] == "sse"
        dataset = "source/sse_share" if sse else "source/szse_share"
        partition = f"date={first}" if sse else f"window={first}_{last}"
        source = "sse_official_etf_scale" if sse else "szse_official_fund_scale"
        expected_parameters = {"trade_date": str(first)} if sse else {
            "start_date": str(first), "end_date": str(last)}
        expected_partitions = {"date": str(first)} if sse else {"window": f"{first}_{last}"}
        folder = (root / dataset / partition).resolve()
        stored = item.get("stored_path")
        if not isinstance(stored, str) or not stored:
            raise ValueError("roster stored path missing")
        stored_path = Path(stored.replace("\\", "/")).resolve()
        if (item.get("dataset") != dataset or item.get("source") != source
                or item.get("parameters") != expected_parameters
                or item.get("partitions") != expected_partitions or stored_path.parent != folder
                or not re.fullmatch(r"[0-9a-f]{64}", item.get("response_sha256", ""))):
            raise ValueError("roster request provenance mismatch")
        loaded = _read_partition(folder, (*IDENTITY_COLUMNS, "share_source"),
            max(start, first), min(end, last), inventory, partition_date=first if sse else None,
            partition_start=first, partition_end=last)
        read_paths = {Path(value["path"]) for value in inventory.values()
            if Path(value["path"]).parent == folder and Path(value["path"]).suffix in {".parquet", ".csv"}}
        if read_paths != {stored_path}:
            raise ValueError("roster stored path differs from selected source file")
        frame = pd.concat(loaded, ignore_index=True)
        if not frame.share_source.eq(source).all():
            raise ValueError("roster source labels disagree with manifest")
        if not frame.symbol.astype(str).str.endswith(".SH" if sse else ".SZ").all():
            raise ValueError("roster symbol exchange disagrees with request source")
        if start <= first and last <= end and len(frame) != item.get("rows"):
            raise ValueError("roster cached row count disagrees with manifest")
        frames.append(frame[list(IDENTITY_COLUMNS)])
        used.append(key)
    if not frames:
        raise ValueError("no completed cached roster requests in audit window")
    return pd.concat(frames, ignore_index=True), {"completed_requests_used": len(used),
        "sse_requests_used": sum(key.startswith("sse:") for key in used),
        "szse_requests_used": sum(key.startswith("szse:") for key in used),
        "unavailable_requests": unavailable,
        "transport_response_hashes_recorded": True, "transport_payloads_reverified": False,
        "note": "Mapped local records with request manifest; not an independently authenticated archive."}


def _identities(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame[list(IDENTITY_COLUMNS)].copy()
    if result.isna().any().any():
        raise ValueError("missing identity keys")
    result["date"] = pd.to_datetime(result.date, errors="raise").dt.normalize()
    if result.date.ge(pd.Timestamp(FINAL_HOLDOUT_START)).any():
        raise ValueError("final holdout identity dates")
    for column in ("symbol", "asset_id"):
        result[column] = result[column].astype(str)
    return result


def _catalogue(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame[list(CATALOG_COLUMNS)].copy()
    if result.symbol.isna().any() or result.symbol.duplicated().any():
        raise ValueError("missing or duplicate catalogue symbols")
    result["is_etf"] = result.is_etf.map(_strict_bool).astype(bool)
    for column in ("list_date", "delist_date"):
        result[column] = pd.to_datetime(result[column], errors="raise").dt.normalize()
    return result


def _strict_bool(value: Any) -> bool:
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if isinstance(value, str) and value.casefold() in {"true", "false"}:
        return value.casefold() == "true"
    raise ValueError("catalogue is_etf must be an explicit boolean")


def _count(frame: pd.DataFrame, mask: pd.Series) -> dict[str, Any]:
    selected = frame.loc[mask]
    return {"rows": len(selected), "assets": int(selected.symbol.nunique()),
        "example_symbols": sorted(selected.symbol.unique())[:10]}
