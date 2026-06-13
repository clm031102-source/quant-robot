from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd


STAGE = "phase_3_2_provider_readiness_evidence"


def build_provider_evidence_pack(provider_status: dict[str, Any]) -> dict[str, Any]:
    providers = _provider_rows(provider_status)
    matrix = _market_matrix(providers)
    pack = {
        "stage": STAGE,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "safety": _research_only_safety(),
        "summary": _summary(providers, provider_status.get("parquet", {})),
        "providers": providers,
        "market_matrix": matrix,
        "parquet": provider_status.get("parquet", {}),
    }
    pack["markdown"] = render_provider_evidence_markdown(pack)
    return pack


def write_provider_evidence_pack(output_dir: str | Path, pack: dict[str, Any]) -> None:
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "provider_evidence_pack.json").write_text(
        json.dumps(pack, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "provider_evidence_pack.md").write_text(str(pack.get("markdown", "")), encoding="utf-8")
    pd.DataFrame(pack.get("market_matrix", [])).to_csv(output_path / "provider_market_matrix.csv", index=False)
    pd.DataFrame(pack.get("providers", [])).to_csv(output_path / "provider_readiness.csv", index=False)


def render_provider_evidence_markdown(pack: dict[str, Any]) -> str:
    summary = pack.get("summary", {}) if isinstance(pack.get("summary"), dict) else {}
    lines = [
        "# Provider Readiness Evidence Pack",
        "",
        f"- Stage: {pack.get('stage', STAGE)}",
        f"- Safety: {pack.get('safety', _research_only_safety())}",
        f"- Ready providers: {summary.get('ready_providers', 0)}/{summary.get('providers', 0)}",
        f"- Blocked providers: {summary.get('blocked_providers', 0)}",
        f"- Parquet ready: {summary.get('parquet_ready', False)}",
        "",
        "## Providers",
        "",
        "| Provider | Status | Markets | Planned Markets | Missing |",
        "| --- | --- | --- | --- | --- |",
    ]
    for provider in pack.get("providers", []):
        if isinstance(provider, dict):
            lines.append(
                "| "
                f"{provider.get('provider', 'unknown')} | "
                f"{provider.get('readiness_status', 'unknown')} | "
                f"{_join(provider.get('markets', []))} | "
                f"{_join(provider.get('planned_markets', []))} | "
                f"{_join(provider.get('missing', []))} |"
            )
    lines.extend(
        [
            "",
            "## Market Matrix",
            "",
            "| Market | Provider | Coverage | Status |",
            "| --- | --- | --- | --- |",
        ]
    )
    for row in pack.get("market_matrix", []):
        if isinstance(row, dict):
            lines.append(
                "| "
                f"{row.get('market', 'unknown')} | "
                f"{row.get('provider', 'unknown')} | "
                f"{row.get('coverage_status', 'unknown')} | "
                f"{row.get('readiness_status', 'unknown')} |"
            )
    lines.extend(["", "## Parquet", ""])
    parquet = pack.get("parquet", {}) if isinstance(pack.get("parquet"), dict) else {}
    lines.append(f"- Ready: {parquet.get('ready', False)}")
    missing = parquet.get("missing", [])
    if missing:
        lines.append(f"- Missing: {_join(missing)}")
    else:
        lines.append("- Missing: none")
    return "\n".join(lines) + "\n"


def _provider_rows(provider_status: dict[str, Any]) -> list[dict[str, Any]]:
    providers = provider_status.get("providers", {})
    if not isinstance(providers, dict):
        return []
    rows: list[dict[str, Any]] = []
    for name, raw in providers.items():
        config = raw if isinstance(raw, dict) else {}
        markets = _list(config.get("markets", []))
        planned_markets = _list(config.get("planned_markets", []))
        missing = _list(config.get("missing", []))
        rows.append(
            {
                "provider": str(name),
                "ready": bool(config.get("ready", False)),
                "readiness_status": _readiness_status(config),
                "package": config.get("package"),
                "implemented": bool(config.get("implemented", False)),
                "requires_token": bool(config.get("requires_token", False)),
                "credential": config.get("credential"),
                "markets": markets,
                "planned_markets": planned_markets,
                "missing": missing,
            }
        )
    return rows


def _market_matrix(providers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for provider in providers:
        markets = _dedupe([*_list(provider.get("markets", [])), *_list(provider.get("planned_markets", []))])
        for market in markets:
            implemented_market = market in _list(provider.get("markets", []))
            planned_market = market in _list(provider.get("planned_markets", []))
            if implemented_market:
                coverage = "implemented_ready" if provider.get("ready") else "implemented_blocked"
            elif planned_market:
                coverage = "planned"
            else:
                coverage = "unknown"
            rows.append(
                {
                    "market": market,
                    "provider": provider.get("provider"),
                    "coverage_status": coverage,
                    "readiness_status": provider.get("readiness_status"),
                    "ready": bool(provider.get("ready", False)),
                    "implemented": bool(provider.get("implemented", False)),
                }
            )
    return rows


def _summary(providers: list[dict[str, Any]], parquet: Any) -> dict[str, Any]:
    parquet_status = parquet if isinstance(parquet, dict) else {}
    ready = sum(1 for provider in providers if provider.get("ready"))
    planned = sum(1 for provider in providers if provider.get("readiness_status") == "planned_adapter")
    implemented = sum(1 for provider in providers if provider.get("implemented"))
    return {
        "providers": len(providers),
        "ready_providers": ready,
        "blocked_providers": len(providers) - ready,
        "implemented_providers": implemented,
        "planned_providers": planned,
        "parquet_ready": bool(parquet_status.get("ready", False)),
    }


def _readiness_status(provider: dict[str, Any]) -> str:
    if provider.get("ready"):
        return "ready"
    if not bool(provider.get("implemented", False)):
        return "planned_adapter"
    missing = [str(item).lower() for item in _list(provider.get("missing", []))]
    credential = str(provider.get("credential") or "").lower()
    has_dependency_gap = any("package" in item or "dependency" in item for item in missing)
    has_token_gap = any("token" in item or (credential and credential in item) or "credential" in item for item in missing)
    if has_dependency_gap and has_token_gap:
        return "missing_dependency_and_token"
    if has_dependency_gap:
        return "missing_dependency"
    if has_token_gap:
        return "missing_token"
    return "blocked"


def _list(value: Any) -> list[Any]:
    if value is None:
        return []
    if isinstance(value, list):
        return value
    if isinstance(value, tuple):
        return list(value)
    return [value]


def _dedupe(values: list[Any]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = str(value)
        if text in seen:
            continue
        seen.add(text)
        result.append(text)
    return result


def _join(values: Any) -> str:
    items = _list(values)
    if not items:
        return "none"
    return ", ".join(_table_text(item) for item in items)


def _table_text(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def _research_only_safety() -> str:
    return "Research only. No broker connection, no account reads, no order placement, no live trading."
