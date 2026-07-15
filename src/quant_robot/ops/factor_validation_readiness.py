from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd

from quant_robot.data.cn_trading_calendar import validate_cn_trading_calendar_artifact
from quant_robot.storage.atomic import atomic_write_json, atomic_write_text
from quant_robot.storage.fingerprints import fingerprint_research_source, sha256_file
from quant_robot.validation.walk_forward import load_walk_forward_config


SCHEMA_VERSION = 1
STAGE = "factor_validation_readiness"
VALIDATION_BRANCH_PREFIX = "codex/factor-validation-cn-stock-"
FINAL_HOLDOUT_START = "2026-01-01"
SAFETY_TEXT = "Research-to-review only. No broker connection, no account reads, no order placement, no live trading."


def build_factor_validation_readiness(
    *,
    config_path: str | Path,
    source: str,
    data_root: str | Path,
    startup_gate_packet: dict[str, Any],
    startup_gate_path: str | Path,
    data_manifest_packet: dict[str, Any],
    data_manifest_path: str | Path,
    calendar_manifest: dict[str, Any],
    calendar_path: str | Path,
    calendar_manifest_path: str | Path,
) -> dict[str, Any]:
    config_file = Path(config_path)
    data_path = Path(data_root)
    config = load_walk_forward_config(config_file)
    moneyflow_root = config.experiment_grid.moneyflow_input_root
    factors = [str(value) for value in config.experiment_grid.factor_names]
    markets = [str(value).upper() for value in config.experiment_grid.markets]
    startup_summary = _dict(startup_gate_packet.get("summary"))
    data_summary = _dict(data_manifest_packet.get("summary"))
    calendar_effective = _dict(calendar_manifest.get("effective_range"))
    blockers = _build_blockers(
        source=source,
        data_root=data_path,
        config_markets=markets,
        factor_names=factors,
        config_bar_start=config.bar_start_date,
        config_bar_end=config.bar_end_date,
        moneyflow_root=moneyflow_root,
        startup_gate=startup_gate_packet,
        startup_summary=startup_summary,
        data_manifest=data_manifest_packet,
        data_summary=data_summary,
        calendar_manifest=calendar_manifest,
        calendar_effective=calendar_effective,
    )
    bar_fingerprint = fingerprint_research_source(data_path, dataset="processed/bars")
    moneyflow_fingerprint = (
        fingerprint_research_source(moneyflow_root, dataset="processed/moneyflow_inputs")
        if moneyflow_root is not None
        else _empty_fingerprint()
    )
    if not bar_fingerprint["exists"]:
        blockers.append("authority_bars_data_missing")
    if not moneyflow_fingerprint["exists"]:
        blockers.append("authority_moneyflow_data_missing")
    if _load_json_or_none(startup_gate_path) != startup_gate_packet:
        blockers.append("startup_packet_path_mismatch")
    if _load_json_or_none(data_manifest_path) != data_manifest_packet:
        blockers.append("data_manifest_packet_path_mismatch")
    blockers = _unique(blockers)
    ready = not blockers
    packet = {
        "factor_validation_readiness_schema_version": SCHEMA_VERSION,
        "stage": STAGE,
        "generated_at": date.today().isoformat(),
        "status": "ready" if ready else "blocked",
        "summary": {
            "task": startup_summary.get("task"),
            "branch": startup_summary.get("branch"),
            "market": startup_summary.get("market"),
            "asset_type": startup_summary.get("asset_type"),
            "factor_count": len(factors),
            "data_start": data_summary.get("date_start"),
            "data_end": data_summary.get("date_end"),
        },
        "config": {
            "path": str(config_file),
            "sha256": sha256_file(config_file),
            "source": source,
            "markets": markets,
            "factor_names": factors,
            "bar_start_date": config.bar_start_date,
            "bar_end_date": config.bar_end_date,
            "moneyflow_source_root": str(moneyflow_root) if moneyflow_root is not None else None,
        },
        "authority_data": {
            "bars_source_root": str(data_path),
            "bars_content_sha256": bar_fingerprint["content_sha256"],
            "bars_file_count": bar_fingerprint["file_count"],
            "bars_exists": bar_fingerprint["exists"],
            "moneyflow_source_root": str(moneyflow_root) if moneyflow_root is not None else None,
            "moneyflow_content_sha256": moneyflow_fingerprint["content_sha256"],
            "moneyflow_file_count": moneyflow_fingerprint["file_count"],
            "moneyflow_exists": moneyflow_fingerprint["exists"],
        },
        "upstream_packets": {
            "startup_gate_path": str(Path(startup_gate_path)),
            "startup_gate_sha256": sha256_file(startup_gate_path),
            "data_manifest_path": str(Path(data_manifest_path)),
            "data_manifest_sha256": sha256_file(data_manifest_path),
        },
        "calendar": {
            "calendar_path": str(Path(calendar_path)),
            "manifest_path": str(Path(calendar_manifest_path)),
            "manifest_sha256": sha256_file(calendar_manifest_path),
            "artifact_sha256": _dict(calendar_manifest.get("artifact")).get("sha256"),
            "effective_range": calendar_effective,
        },
        "final_holdout_allowed": False,
        "decision": {
            "factor_validation_allowed": ready,
            "promotion_allowed": False,
            "blockers": blockers,
        },
        "live_boundary_allowed": False,
        "safety": SAFETY_TEXT,
    }
    packet["markdown"] = render_factor_validation_readiness_markdown(packet)
    return packet


def write_factor_validation_readiness(output_dir: str | Path, packet: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    clean = {key: value for key, value in packet.items() if key != "markdown"}
    atomic_write_json(output_path / "factor_validation_readiness.json", clean)
    atomic_write_text(
        output_path / "factor_validation_readiness.md",
        render_factor_validation_readiness_markdown(clean),
    )


def validate_factor_validation_readiness_packet(
    packet_path: str | Path | None,
    *,
    expected_config_path: str | Path,
    expected_source: str,
    expected_data_root: str | Path,
    expected_factor_names: list[str] | tuple[str, ...] | set[str] | None = None,
    require_generated_today: bool = True,
    context: str = "CN stock factor validation",
) -> dict[str, Any]:
    if packet_path is None:
        raise ValueError(f"{context} requires a factor validation readiness packet")
    path = Path(packet_path)
    if not path.is_file():
        raise ValueError(f"{context} requires a factor validation readiness packet: {path}")
    packet = json.loads(path.read_text(encoding="utf-8-sig"))
    if int(packet.get("factor_validation_readiness_schema_version") or 0) != SCHEMA_VERSION:
        raise ValueError(f"{context} readiness schema mismatch: {path}")
    if require_generated_today and packet.get("generated_at") != date.today().isoformat():
        raise ValueError(f"{context} readiness packet must be generated today: {path}")
    decision = _dict(packet.get("decision"))
    if packet.get("status") != "ready" or decision.get("factor_validation_allowed") is not True:
        raise ValueError(f"{context} readiness packet is not ready: {path}")
    if decision.get("promotion_allowed") is not False:
        raise ValueError(f"{context} readiness packet grants promotion permission: {path}")
    if packet.get("final_holdout_allowed") is not False:
        raise ValueError(f"{context} readiness packet opens the final holdout: {path}")
    if packet.get("live_boundary_allowed") is not False:
        raise ValueError(f"{context} readiness packet violates live boundary: {path}")

    config_file = Path(expected_config_path)
    config_info = _dict(packet.get("config"))
    if _path_text(config_info.get("path")) != _path_text(config_file):
        raise ValueError(f"{context} config path mismatch: {path}")
    if config_info.get("source") != expected_source:
        raise ValueError(f"{context} source mismatch: {path}")
    if config_info.get("sha256") != sha256_file(config_file):
        raise ValueError(f"{context} config fingerprint mismatch: {path}")
    effective_config = load_walk_forward_config(config_file)
    effective_factors = {str(value) for value in effective_config.experiment_grid.factor_names}
    packet_factors = {str(value) for value in config_info.get("factor_names", [])}
    if packet_factors != effective_factors:
        raise ValueError(f"{context} factor names changed after readiness: {path}")
    if expected_factor_names is not None and packet_factors != {str(value) for value in expected_factor_names}:
        raise ValueError(f"{context} expected factor names mismatch: {path}")

    authority = _dict(packet.get("authority_data"))
    if _path_text(authority.get("bars_source_root")) != _path_text(expected_data_root):
        raise ValueError(f"{context} authority data root mismatch: {path}")
    current_bars = fingerprint_research_source(expected_data_root, dataset="processed/bars")
    if (
        authority.get("bars_content_sha256") != current_bars["content_sha256"]
        or int(authority.get("bars_file_count") or 0) != current_bars["file_count"]
    ):
        raise ValueError(f"{context} authority data fingerprint mismatch: {path}")
    moneyflow_root = effective_config.experiment_grid.moneyflow_input_root
    if moneyflow_root is None:
        raise ValueError(f"{context} moneyflow authority root is missing: {path}")
    current_moneyflow = fingerprint_research_source(moneyflow_root, dataset="processed/moneyflow_inputs")
    if (
        authority.get("moneyflow_content_sha256") != current_moneyflow["content_sha256"]
        or int(authority.get("moneyflow_file_count") or 0) != current_moneyflow["file_count"]
    ):
        raise ValueError(f"{context} moneyflow authority data fingerprint mismatch: {path}")

    upstream = _dict(packet.get("upstream_packets"))
    _validate_file_sha(upstream, "startup_gate_path", "startup_gate_sha256", path, context)
    _validate_file_sha(upstream, "data_manifest_path", "data_manifest_sha256", path, context)
    calendar = _dict(packet.get("calendar"))
    manifest_file = Path(str(calendar.get("manifest_path", "")))
    if calendar.get("manifest_sha256") != sha256_file(manifest_file):
        raise ValueError(f"{context} calendar manifest fingerprint mismatch: {path}")
    validate_cn_trading_calendar_artifact(
        Path(str(calendar.get("calendar_path", ""))),
        manifest_file,
    )
    return packet


def render_factor_validation_readiness_markdown(packet: dict[str, Any]) -> str:
    summary = _dict(packet.get("summary"))
    decision = _dict(packet.get("decision"))
    config = _dict(packet.get("config"))
    blockers = [str(value) for value in decision.get("blockers", [])]
    lines = [
        "# Factor Validation Readiness",
        "",
        f"- Status: {packet.get('status', 'unknown')}",
        f"- Task: {summary.get('task')}",
        f"- Branch: {summary.get('branch')}",
        f"- Config: `{config.get('path')}`",
        f"- Source: {config.get('source')}",
        f"- Factors: {', '.join(str(value) for value in config.get('factor_names', []))}",
        f"- Validation allowed: {decision.get('factor_validation_allowed', False)}",
        f"- Promotion allowed: {decision.get('promotion_allowed', False)}",
        f"- Final holdout allowed: {packet.get('final_holdout_allowed', False)}",
        f"- Live boundary allowed: {packet.get('live_boundary_allowed', False)}",
        f"- Safety: {packet.get('safety', SAFETY_TEXT)}",
        "",
        "## Blockers",
        "",
    ]
    lines.extend(f"- {value}" for value in blockers) if blockers else lines.append("- none")
    return "\n".join(lines) + "\n"


def _build_blockers(
    *,
    source: str,
    data_root: Path,
    config_markets: list[str],
    factor_names: list[str],
    config_bar_start: str | None,
    config_bar_end: str | None,
    moneyflow_root: Path | None,
    startup_gate: dict[str, Any],
    startup_summary: dict[str, Any],
    data_manifest: dict[str, Any],
    data_summary: dict[str, Any],
    calendar_manifest: dict[str, Any],
    calendar_effective: dict[str, Any],
) -> list[str]:
    blockers: list[str] = []
    if source != "authority-bars":
        blockers.append("source_not_authority_bars")
    if not data_root.is_file():
        blockers.append("authority_bars_config_missing")
    if config_markets != ["CN"]:
        blockers.append("config_market_not_cn")
    if not factor_names:
        blockers.append("config_factor_names_missing")
    if config_bar_start is None or config_bar_end is None:
        blockers.append("config_bar_window_not_explicit")
    if config_bar_end is not None and _iso_date(config_bar_end) >= FINAL_HOLDOUT_START:
        blockers.append("config_opens_final_holdout")
    if moneyflow_root is None or not moneyflow_root.is_file():
        blockers.append("moneyflow_authority_config_missing")
    startup_decision = _dict(startup_gate.get("decision"))
    if startup_gate.get("status") != "cleared" or startup_decision.get("startup_gate_cleared") is not True:
        blockers.append("startup_gate_not_cleared")
    if startup_gate.get("generated_at") != date.today().isoformat():
        blockers.append("startup_gate_not_generated_today")
    if startup_summary.get("task") != "factor_validation":
        blockers.append("task_not_factor_validation")
    if not str(startup_summary.get("branch", "")).startswith(VALIDATION_BRANCH_PREFIX):
        blockers.append("branch_not_factor_validation")
    if str(startup_summary.get("market", "")).upper() != "CN":
        blockers.append("startup_market_not_cn")
    if str(startup_summary.get("asset_type", "")).lower() != "stock":
        blockers.append("startup_asset_type_not_stock")
    if startup_gate.get("live_boundary_allowed") is not False:
        blockers.append("startup_live_boundary_violation")
    data_decision = _dict(data_manifest.get("decision"))
    if data_manifest.get("status") not in {"cleared", "review_required"} or data_decision.get("blockers"):
        blockers.append("data_manifest_not_usable")
    if data_manifest.get("generated_at") != date.today().isoformat():
        blockers.append("data_manifest_not_generated_today")
    if _path_text(data_summary.get("source_root")) != _path_text(data_root):
        blockers.append("data_manifest_bars_root_mismatch")
    if moneyflow_root is not None and _path_text(data_summary.get("moneyflow_source_root")) != _path_text(moneyflow_root):
        blockers.append("data_manifest_moneyflow_root_mismatch")
    if int(data_summary.get("bar_rows") or 0) <= 0 or int(data_summary.get("bar_symbols") or 0) <= 0:
        blockers.append("data_manifest_has_no_bars")
    data_end = str(data_summary.get("date_end") or "")
    if data_end and _iso_date(data_end) >= FINAL_HOLDOUT_START:
        blockers.append("final_holdout_data_present")
    if data_manifest.get("live_boundary_allowed") is not False:
        blockers.append("data_manifest_live_boundary_violation")
    if calendar_manifest.get("status") != "cleared" or _dict(calendar_manifest.get("decision")).get("calendar_cleared") is not True:
        blockers.append("calendar_not_cleared")
    data_start = str(data_summary.get("date_start") or "")
    calendar_start = str(calendar_effective.get("start") or "")
    calendar_end = str(calendar_effective.get("end") or "")
    if data_start and (not calendar_start or calendar_start > _iso_date(data_start)):
        blockers.append("calendar_starts_after_data")
    if data_end and (not calendar_end or calendar_end < _iso_date(data_end)):
        blockers.append("calendar_ends_before_data")
    if calendar_manifest.get("live_boundary_allowed") is not False:
        blockers.append("calendar_live_boundary_violation")
    return _unique(blockers)


def _validate_file_sha(packet: dict[str, Any], path_key: str, sha_key: str, readiness_path: Path, context: str) -> None:
    source_path = Path(str(packet.get(path_key, "")))
    if not source_path.is_file() or packet.get(sha_key) != sha256_file(source_path):
        raise ValueError(f"{context} upstream packet fingerprint mismatch: {readiness_path}")


def _empty_fingerprint() -> dict[str, Any]:
    return {"exists": False, "file_count": 0, "content_sha256": ""}


def _load_json_or_none(path: str | Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    except (FileNotFoundError, json.JSONDecodeError, OSError):
        return None
    return payload if isinstance(payload, dict) else None


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _path_text(value: Any) -> str:
    return Path(str(value)).as_posix() if value not in (None, "") else ""


def _iso_date(value: str) -> str:
    return pd.Timestamp(value).date().isoformat()


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))
