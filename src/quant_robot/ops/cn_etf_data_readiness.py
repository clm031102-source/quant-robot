from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd

from quant_robot.data.gap_audit import build_data_quality_gap_audit
from quant_robot.storage.cn_etf_rotation_membership import load_cn_etf_rotation_membership
from quant_robot.storage.etf_moneyflow_baskets import load_etf_moneyflow_baskets
from quant_robot.storage.etf_share_size import load_etf_share_size_inputs
from quant_robot.storage.processed_bars import load_processed_bars


STAGE = "cn_etf_data_readiness_gate"
PRIMARY_MARKET = "CN_ETF"
SYNC_PACK_NAME = "tushare_cn_etf_sync_pack.json"
READY_SYNC_STATUSES = {"completed", "up_to_date"}


def build_cn_etf_data_readiness_gate(
    *,
    data_root: str | Path,
    sync_report_dir: str | Path | None = None,
    require_etf_share_size: bool = True,
    require_etf_moneyflow_baskets: bool = True,
    allow_missing_date_rows: bool = False,
) -> dict[str, Any]:
    root = Path(data_root)
    blockers: list[str] = []
    warnings: list[str] = []

    bars, bars_summary, bars_error = _load_bars(root)
    if bars_error:
        blockers.append(bars_error)

    data_quality = _data_quality_summary(
        bars,
        root,
        blockers,
        warnings,
        allow_missing_date_rows=allow_missing_date_rows,
    )
    rotation_membership = _rotation_membership_summary(root, bars, blockers, warnings)
    sync_pack = _sync_pack_summary(sync_report_dir, blockers, warnings)
    auxiliary = _auxiliary_dataset_summary(
        root,
        require_etf_share_size=require_etf_share_size,
        require_etf_moneyflow_baskets=require_etf_moneyflow_baskets,
        blockers=blockers,
    )
    status = "blocked" if blockers else "ready"
    pack = {
        "stage": STAGE,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "status": status,
        "primary_market": PRIMARY_MARKET,
        "data_root": str(root),
        "sync_report_dir": str(sync_report_dir) if sync_report_dir is not None else None,
        "bars": bars_summary,
        "data_quality": data_quality,
        "rotation_membership": rotation_membership,
        "sync_pack": sync_pack,
        "auxiliary_datasets": auxiliary,
        "auxiliary_feature_policy": {
            "cn_stock_moneyflow": "auxiliary_only",
            "direct_cn_stock_selection": "forbidden",
        },
        "data_quality_policy": {
            "allow_missing_date_rows": bool(allow_missing_date_rows),
            "missing_date_rows": "warning" if allow_missing_date_rows else "blocker",
        },
        "lookahead_policy": {
            "signal_date": "T",
            "earliest_trade_date": "T+1",
            "factor_assets": "CN_ETF",
            "future_return_assets": "CN_ETF",
            "rotation_membership": "point_in_time",
        },
        "survivorship_policy": {
            "historical_delisted_etfs": "preserved_when_listed_on_date",
            "current_tradable_pool": "excluded_only_at_signal_date",
        },
        "live_boundary_allowed": False,
        "safety": "Research-to-paper only. No broker connection, no account reads, no order placement, no live trading.",
        "blockers": blockers,
        "warnings": warnings,
    }
    pack["next_actions"] = _next_actions(pack)
    pack["markdown"] = render_cn_etf_data_readiness_gate_markdown(pack)
    return _sanitize(pack)


def write_cn_etf_data_readiness_gate(output_dir: str | Path, pack: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "cn_etf_data_readiness_gate.json").write_text(
        json.dumps(pack, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "cn_etf_data_readiness_gate.md").write_text(str(pack.get("markdown", "")), encoding="utf-8")


def render_cn_etf_data_readiness_gate_markdown(pack: dict[str, Any]) -> str:
    bars = pack.get("bars", {}) if isinstance(pack.get("bars"), dict) else {}
    data_quality = pack.get("data_quality", {}) if isinstance(pack.get("data_quality"), dict) else {}
    rotation = pack.get("rotation_membership", {}) if isinstance(pack.get("rotation_membership"), dict) else {}
    sync_pack = pack.get("sync_pack", {}) if isinstance(pack.get("sync_pack"), dict) else {}
    auxiliary = pack.get("auxiliary_datasets", {}) if isinstance(pack.get("auxiliary_datasets"), dict) else {}
    lines = [
        "# CN ETF Data Readiness Gate",
        "",
        f"- Stage: {pack.get('stage', STAGE)}",
        f"- Status: {pack.get('status', 'unknown')}",
        f"- Primary market: {pack.get('primary_market', PRIMARY_MARKET)}",
        f"- Data root: {pack.get('data_root')}",
        f"- Bar rows: {bars.get('rows', 0)}",
        f"- Bar assets: {bars.get('assets', 0)}",
        f"- Window: {bars.get('start_date')} to {bars.get('end_date')}",
        f"- Missing date rows: {data_quality.get('missing_date_rows', 0)}",
        f"- Rotation member rows: {rotation.get('member_rows', 0)}",
        f"- Sync pack status: {sync_pack.get('status', 'not_found')}",
        f"- ETF share-size rows: {_dataset_rows(auxiliary, 'etf_share_size')}",
        f"- ETF moneyflow basket rows: {_dataset_rows(auxiliary, 'etf_moneyflow_baskets')}",
        f"- Live boundary allowed: {pack.get('live_boundary_allowed', False)}",
        "",
        "## Blockers",
        "",
    ]
    blockers = pack.get("blockers", []) if isinstance(pack.get("blockers"), list) else []
    lines.extend(f"- {blocker}" for blocker in blockers) if blockers else lines.append("- none")
    lines.extend(["", "## Warnings", ""])
    warnings = pack.get("warnings", []) if isinstance(pack.get("warnings"), list) else []
    lines.extend(f"- {warning}" for warning in warnings) if warnings else lines.append("- none")
    lines.extend(["", "## Next Actions", ""])
    next_actions = pack.get("next_actions", []) if isinstance(pack.get("next_actions"), list) else []
    lines.extend(f"- {action}" for action in next_actions) if next_actions else lines.append("- none")
    return "\n".join(lines) + "\n"


def _load_bars(root: Path) -> tuple[pd.DataFrame, dict[str, Any], str | None]:
    try:
        bars = load_processed_bars(root, PRIMARY_MARKET)
    except FileNotFoundError:
        return pd.DataFrame(), _empty_bars_summary(), "missing_cn_etf_processed_bars"
    if bars.empty:
        return bars, _empty_bars_summary(), "empty_cn_etf_processed_bars"
    frame = bars.copy()
    frame["date"] = pd.to_datetime(frame["date"], errors="coerce").dt.date
    dates = frame["date"].dropna()
    summary = {
        "rows": int(len(frame)),
        "assets": int(frame["asset_id"].nunique()) if "asset_id" in frame.columns else 0,
        "markets": sorted(str(value) for value in frame.get("market", pd.Series(dtype=str)).dropna().unique()),
        "start_date": dates.min().isoformat() if not dates.empty else None,
        "end_date": dates.max().isoformat() if not dates.empty else None,
        "source": "processed-bars",
    }
    return frame, summary, None


def _empty_bars_summary() -> dict[str, Any]:
    return {
        "rows": 0,
        "assets": 0,
        "markets": [],
        "start_date": None,
        "end_date": None,
        "source": "processed-bars",
    }


def _data_quality_summary(
    bars: pd.DataFrame,
    root: Path,
    blockers: list[str],
    warnings: list[str],
    *,
    allow_missing_date_rows: bool,
) -> dict[str, Any]:
    if bars.empty:
        return {
            "status": "blocked",
            "rows": 0,
            "assets": 0,
            "missing_date_rows": 0,
            "assets_with_gaps": 0,
            "zero_volume_rows": 0,
        }
    try:
        audit = build_data_quality_gap_audit(bars, source_root=root)
    except (KeyError, ValueError) as exc:
        blockers.append("data_quality_audit_failed")
        return {"status": "blocked", "error": str(exc)}
    summary = audit.get("summary", {}) if isinstance(audit.get("summary"), dict) else {}
    missing_date_rows = int(_number(summary.get("missing_date_rows"), 0))
    zero_volume_rows = int(_number(summary.get("zero_volume_rows"), 0))
    if missing_date_rows > 0:
        if allow_missing_date_rows:
            warnings.append("data_quality_missing_date_rows_allowed")
        else:
            blockers.append("data_quality_missing_date_rows")
    if zero_volume_rows > 0:
        warnings.append("data_quality_zero_volume_rows_present")
    return {
        "status": "warning" if missing_date_rows > 0 and allow_missing_date_rows else "blocked" if missing_date_rows > 0 else "ready",
        "rows": int(_number(summary.get("rows"), 0)),
        "assets": int(_number(summary.get("assets"), 0)),
        "start_date": summary.get("start_date"),
        "end_date": summary.get("end_date"),
        "missing_date_rows": missing_date_rows,
        "assets_with_gaps": int(_number(summary.get("assets_with_gaps"), 0)),
        "zero_volume_rows": zero_volume_rows,
    }


def _rotation_membership_summary(
    root: Path,
    bars: pd.DataFrame,
    blockers: list[str],
    warnings: list[str],
) -> dict[str, Any]:
    try:
        membership = load_cn_etf_rotation_membership(root, PRIMARY_MARKET)
    except FileNotFoundError:
        blockers.append("missing_rotation_membership")
        return _empty_rotation_membership_summary()
    except ValueError as exc:
        blockers.append("rotation_membership_invalid")
        summary = _empty_rotation_membership_summary()
        summary["error"] = str(exc)
        return summary
    if membership.empty:
        blockers.append("empty_rotation_membership")
        return _empty_rotation_membership_summary()
    members = membership[membership["is_rotation_member"].astype(bool)]
    if members.empty:
        blockers.append("no_rotation_member_rows")
    dates = pd.to_datetime(membership["date"], errors="coerce").dropna().dt.date
    member_dates = pd.to_datetime(members["date"], errors="coerce").dropna().dt.date if not members.empty else pd.Series(dtype=object)
    if not bars.empty and "asset_id" in bars.columns:
        bar_assets = set(bars["asset_id"].astype(str).unique())
        member_assets = set(membership["asset_id"].astype(str).unique())
        missing_assets = sorted(bar_assets - member_assets)
        if missing_assets:
            warnings.append("rotation_membership_missing_some_bar_assets")
    return {
        "rows": int(len(membership)),
        "member_rows": int(len(members)),
        "assets": int(membership["asset_id"].nunique()),
        "member_assets": int(members["asset_id"].nunique()) if not members.empty else 0,
        "start_date": dates.min().isoformat() if not dates.empty else None,
        "end_date": dates.max().isoformat() if not dates.empty else None,
        "member_start_date": member_dates.min().isoformat() if not member_dates.empty else None,
        "member_end_date": member_dates.max().isoformat() if not member_dates.empty else None,
        "dataset": "metadata/cn_etf_rotation_membership",
    }


def _empty_rotation_membership_summary() -> dict[str, Any]:
    return {
        "rows": 0,
        "member_rows": 0,
        "assets": 0,
        "member_assets": 0,
        "start_date": None,
        "end_date": None,
        "member_start_date": None,
        "member_end_date": None,
        "dataset": "metadata/cn_etf_rotation_membership",
    }


def _sync_pack_summary(
    sync_report_dir: str | Path | None,
    blockers: list[str],
    warnings: list[str],
) -> dict[str, Any]:
    if sync_report_dir is None:
        warnings.append("sync_report_dir_not_provided")
        return {"status": "not_checked", "path": None}
    path = Path(sync_report_dir) / SYNC_PACK_NAME
    if not path.exists():
        blockers.append("missing_tushare_cn_etf_sync_pack")
        return {"status": "not_found", "path": str(path)}
    try:
        pack = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        blockers.append("invalid_tushare_cn_etf_sync_pack")
        return {"status": "invalid", "path": str(path), "error": str(exc)}
    status = str(pack.get("status", "unknown"))
    if status not in READY_SYNC_STATUSES:
        blockers.append("sync_pack_not_ready")
    policy = pack.get("auxiliary_feature_policy", {}) if isinstance(pack.get("auxiliary_feature_policy"), dict) else {}
    if policy.get("cn_stock_moneyflow") not in {None, "auxiliary_only"}:
        blockers.append("cn_stock_moneyflow_not_auxiliary_only")
    return {
        "status": status,
        "path": str(path),
        "source": pack.get("source"),
        "start_date": pack.get("start_date"),
        "end_date": pack.get("end_date"),
        "as_of": pack.get("as_of"),
        "primary_market": pack.get("primary_market"),
        "date_resolution": pack.get("date_resolution", {}) if isinstance(pack.get("date_resolution"), dict) else {},
        "blockers": pack.get("blockers", []) if isinstance(pack.get("blockers"), list) else [],
    }


def _auxiliary_dataset_summary(
    root: Path,
    *,
    require_etf_share_size: bool,
    require_etf_moneyflow_baskets: bool,
    blockers: list[str],
) -> dict[str, Any]:
    return {
        "etf_share_size": _dataset_summary(
            "etf_share_size",
            lambda: load_etf_share_size_inputs(root, PRIMARY_MARKET),
            require=require_etf_share_size,
            blocker="missing_etf_share_size",
            blockers=blockers,
        ),
        "etf_moneyflow_baskets": _dataset_summary(
            "etf_moneyflow_baskets",
            lambda: load_etf_moneyflow_baskets(root, PRIMARY_MARKET),
            require=require_etf_moneyflow_baskets,
            blocker="missing_etf_moneyflow_baskets",
            blockers=blockers,
        ),
        "cn_stock_moneyflow": {
            "status": "auxiliary_only",
            "direct_cn_stock_selection": "forbidden",
        },
    }


def _dataset_summary(
    name: str,
    loader: Any,
    *,
    require: bool,
    blocker: str,
    blockers: list[str],
) -> dict[str, Any]:
    try:
        frame = loader()
    except FileNotFoundError:
        if require:
            blockers.append(blocker)
        return {"status": "missing", "dataset": name, "required": require, "rows": 0}
    if frame.empty:
        if require:
            blockers.append(blocker)
        return {"status": "empty", "dataset": name, "required": require, "rows": 0}
    summary: dict[str, Any] = {
        "status": "ready",
        "dataset": name,
        "required": require,
        "rows": int(len(frame)),
    }
    if "asset_id" in frame.columns:
        summary["assets"] = int(frame["asset_id"].nunique())
    if "date" in frame.columns:
        dates = pd.to_datetime(frame["date"], errors="coerce").dropna().dt.date
        summary["start_date"] = dates.min().isoformat() if not dates.empty else None
        summary["end_date"] = dates.max().isoformat() if not dates.empty else None
    return summary


def _next_actions(pack: dict[str, Any]) -> list[str]:
    blockers = pack.get("blockers", []) if isinstance(pack.get("blockers"), list) else []
    if not blockers:
        return [
            "Run CN_ETF walk-forward factor batches with rotation membership filtering enabled.",
            "Keep CN stock moneyflow as ETF-level auxiliary breadth/theme features only.",
        ]
    actions = []
    if "missing_cn_etf_processed_bars" in blockers or "empty_cn_etf_processed_bars" in blockers:
        actions.append("Run the Tushare CN_ETF sync before factor mining.")
    if "missing_rotation_membership" in blockers or "empty_rotation_membership" in blockers:
        actions.append("Rebuild the point-in-time CN_ETF rotation membership dataset.")
    if "data_quality_missing_date_rows" in blockers:
        actions.append("Run the data-quality audit and repair missing CN_ETF bar dates.")
    if "missing_etf_share_size" in blockers:
        actions.append("Sync ETF share-size inputs before share/size pressure research.")
    if "missing_etf_moneyflow_baskets" in blockers:
        actions.append("Sync fund portfolio baskets before ETF moneyflow aggregation research.")
    if "sync_pack_not_ready" in blockers or "missing_tushare_cn_etf_sync_pack" in blockers:
        actions.append("Generate a ready Tushare CN_ETF sync pack before factor mining.")
    return actions


def _dataset_rows(auxiliary: dict[str, Any], key: str) -> Any:
    dataset = auxiliary.get(key, {}) if isinstance(auxiliary.get(key), dict) else {}
    return dataset.get("rows", 0)


def _number(value: Any, default: float = 0.0) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return number if math.isfinite(number) else default


def _sanitize(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _sanitize(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_sanitize(item) for item in value]
    if isinstance(value, tuple):
        return [_sanitize(item) for item in value]
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, pd.Timestamp):
        return value.isoformat()
    if hasattr(value, "isoformat") and value.__class__.__module__ == "datetime":
        return value.isoformat()
    if isinstance(value, float):
        return value if math.isfinite(value) else None
    return value
