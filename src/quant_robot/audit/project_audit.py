from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from quant_robot.data.readiness import check_parquet_readiness, check_tushare_readiness
from quant_robot.factors.etf_moneyflow_basket import ETF_MONEYFLOW_BASKET_FACTOR_NAMES
from quant_robot.factors.etf_share_size import ETF_SHARE_SIZE_FACTOR_NAMES
from quant_robot.factors.moneyflow_technical import MONEYFLOW_TECHNICAL_COMBO_FACTOR_NAMES
from quant_robot.factors.tushare_inputs import DAILY_BASIC_FACTOR_NAMES
from quant_robot.factors.tushare_moneyflow import MONEYFLOW_FACTOR_NAMES

SCAN_ROOTS = ("src", "scripts", "tests", "README.md", "docs", "configs", "quant_robot")
IMPLEMENTATION_ROOTS = ("src/", "scripts/", "quant_robot/")
SELF_AUDIT_FILES = {"src/quant_robot/audit/project_audit.py"}
TEXT_SUFFIXES = {".py", ".md", ".txt", ".yaml", ".yml", ".toml", ".json", ".html", ".css", ".js"}
FORBIDDEN_PATTERNS = (
    "place_order",
    "submit_order",
    "send_order",
    "cancel_order",
    "broker_adapter",
    "live_order",
    "account_login",
)
BOUNDARY_PHRASES = (
    "no broker",
    "not connect to broker",
    "without live trading",
    "no live trading",
    "no order placement",
    "does not place",
    "research-only",
    "research only",
)
DISABLED_LIVE_BOUNDARY_FIELDS = ("live_order_allowed",)
TECHNICAL_FACTOR_PREFIXES = (
    "momentum",
    "risk_adjusted_momentum",
    "reversal",
    "volatility",
    "low_volatility",
    "low_downside_volatility",
    "drawdown_resilience",
    "volume_change",
    "liquidity",
    "liquidity_resilience",
    "amount_stability",
    "trend_resilience",
    "risk_confirmed_momentum",
    "defensive_reversal",
    "liquidity_confirmed_breakout",
    "market_relative_strength",
    "momentum_dispersion_breakout",
    "crash_recovery",
    "recovery_quality",
    "demand_pressure",
    "quiet_accumulation",
)
DEFAULT_FACTOR_SOURCE = "technical"
DEFAULT_FACTOR_WINDOWS = (2, 3)


def collect_project_audit(root: str | Path = ".") -> dict[str, Any]:
    root_path = Path(root)
    files = _scan_files(root_path)
    forbidden_hits = []
    boundary_mentions = 0
    mock_files = []
    for path in files:
        relative = _relative(path, root_path)
        text = path.read_text(encoding="utf-8", errors="ignore")
        lower = text.lower()
        if _is_mock_file(relative):
            mock_files.append(relative)
        boundary_mentions += sum(1 for line in lower.splitlines() if any(phrase in line for phrase in BOUNDARY_PHRASES))
        if not _is_implementation_file(relative):
            continue
        for line_number, line in enumerate(text.splitlines(), start=1):
            if _is_allowed_boundary_line(line):
                continue
            for pattern in FORBIDDEN_PATTERNS:
                if pattern in line:
                    forbidden_hits.append(
                        {
                            "path": relative,
                            "line": line_number,
                            "pattern": pattern,
                            "text": line.strip(),
                        }
                    )
    tushare = check_tushare_readiness()
    parquet = check_parquet_readiness()
    factor_config_registry = _audit_factor_config_registry(root_path)
    safety_passes = not forbidden_hits
    mock_passes = all("mock" in file.lower() or "fixture" in file.lower() for file in mock_files)
    factor_config_passes = bool(factor_config_registry["passes"])
    return {
        "summary": {
            "passes": safety_passes and mock_passes and factor_config_passes,
            "files_scanned": len(files),
        },
        "safety": {
            "passes": safety_passes,
            "forbidden_hits": forbidden_hits,
            "boundary_mentions": boundary_mentions,
        },
        "mock_boundaries": {
            "passes": mock_passes,
            "mock_files": sorted(mock_files),
        },
        "real_data": {
            "tushare_ready": bool(tushare["ready"]),
            "tushare_missing": list(tushare["missing"]),
            "parquet_ready": bool(parquet["ready"]),
            "parquet_missing": list(parquet["missing"]),
        },
        "factor_config_registry": factor_config_registry,
    }


def render_markdown_report(audit: dict[str, Any]) -> str:
    safety = audit["safety"]
    mock = audit["mock_boundaries"]
    real_data = audit.get("real_data", {})
    factor_registry = audit.get("factor_config_registry", {})
    lines = [
        "# Quant Robot Project Audit",
        "",
        f"- Overall pass: {audit['summary']['passes']}",
        f"- Files scanned: {audit['summary']['files_scanned']}",
        "",
        "## Safety Boundary",
        "",
        f"- Passes: {safety['passes']}",
        f"- Boundary mentions: {safety['boundary_mentions']}",
        f"- Forbidden implementation hits: {len(safety['forbidden_hits'])}",
    ]
    for hit in safety["forbidden_hits"]:
        lines.append(f"  - {hit['path']}:{hit['line']} `{hit['pattern']}`")
    lines.extend(
        [
            "",
            "## Mock Data Boundary",
            "",
            f"- Passes: {mock['passes']}",
            f"- Mock/fixture files: {len(mock['mock_files'])}",
        ]
    )
    for file in mock["mock_files"]:
        lines.append(f"  - `{file}`")
    lines.extend(
        [
            "",
            "## Factor Config Registry",
            "",
            f"- Passes: {factor_registry.get('passes', False)}",
            f"- Configs scanned: {factor_registry.get('configs_scanned', 0)}",
            f"- Unknown factor refs: {len(factor_registry.get('unknown_factor_refs', []))}",
            f"- Unsupported factor sources: {len(factor_registry.get('unsupported_factor_sources', []))}",
            f"- Window mismatches: {len(factor_registry.get('window_mismatches', []))}",
        ]
    )
    for hit in factor_registry.get("unknown_factor_refs", []):
        lines.append(f"  - {hit['path']} `{hit['factor_source']}` `{hit['factor_name']}`")
    for hit in factor_registry.get("unsupported_factor_sources", []):
        lines.append(f"  - {hit['path']} unsupported `{hit['factor_source']}`")
    for hit in factor_registry.get("window_mismatches", []):
        lines.append(
            "  - "
            f"{hit['path']} `{hit['factor_name']}` window {hit['factor_window']} "
            f"not in {hit['configured_windows']}"
        )
    lines.extend(
        [
            "",
            "## Real Data Readiness",
            "",
            f"- Tushare ready: {real_data.get('tushare_ready', False)}",
            f"- Parquet ready: {real_data.get('parquet_ready', False)}",
        ]
    )
    return "\n".join(lines) + "\n"


def write_audit_reports(root: str | Path, output_dir: str | Path) -> dict[str, Path]:
    audit = collect_project_audit(root)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    json_path = output_path / "project_audit.json"
    markdown_path = output_path / "project_audit.md"
    json_path.write_text(json.dumps(audit, indent=2, sort_keys=True), encoding="utf-8")
    markdown_path.write_text(render_markdown_report(audit), encoding="utf-8")
    return {"json": json_path, "markdown": markdown_path}


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit Quant Robot project boundaries and readiness.")
    parser.add_argument("--root", default=".")
    parser.add_argument("--output-dir", default="data/reports/project_audit")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    if args.json:
        print(json.dumps(collect_project_audit(args.root), indent=2, sort_keys=True))
        return
    paths = write_audit_reports(args.root, args.output_dir)
    print(json.dumps({key: str(value) for key, value in paths.items()}, indent=2, sort_keys=True))


def _scan_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for entry in SCAN_ROOTS:
        path = root / entry
        if path.is_file() and _is_text_file(path):
            files.append(path)
        elif path.is_dir():
            files.extend(candidate for candidate in path.rglob("*") if candidate.is_file() and _is_text_file(candidate))
    return sorted(files)


def _is_text_file(path: Path) -> bool:
    return path.suffix.lower() in TEXT_SUFFIXES


def _relative(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _is_allowed_boundary_line(line: str) -> bool:
    lower = line.lower()
    return any(phrase in lower for phrase in BOUNDARY_PHRASES) or _is_disabled_live_boundary_line(lower)


def _is_disabled_live_boundary_line(lower_line: str) -> bool:
    stripped = lower_line.strip()
    for field in DISABLED_LIVE_BOUNDARY_FIELDS:
        quoted_field = rf"[\"']{re.escape(field)}[\"']"
        field_reference = rf"{quoted_field}\s*,?$"
        single_item_collection = rf"\w+\s*=\s*[\(\[\{{]\s*{quoted_field}\s*,?\s*[\)\]\}}]\s*"
        disabled_mapping = rf"{quoted_field}\s*:\s*false\b"
        disabled_assignment = rf"\b{re.escape(field)}\s*=\s*false\b"
        if re.fullmatch(field_reference, stripped) or re.fullmatch(single_item_collection, stripped):
            return True
        if re.search(disabled_mapping, stripped) or re.search(disabled_assignment, stripped):
            return True
    return False


def _is_mock_file(relative_path: str) -> bool:
    lower = relative_path.lower()
    return "mock" in lower or "fixture" in lower


def _is_implementation_file(relative_path: str) -> bool:
    if relative_path in SELF_AUDIT_FILES:
        return False
    return relative_path.endswith(".py") and relative_path.startswith(IMPLEMENTATION_ROOTS)


def _audit_factor_config_registry(root: Path) -> dict[str, Any]:
    configs_scanned = 0
    unknown_factor_refs = []
    unsupported_factor_sources = []
    window_mismatches = []
    invalid_config_files = []
    config_dir = root / "configs"
    if not config_dir.exists():
        return {
            "passes": True,
            "configs_scanned": 0,
            "unknown_factor_refs": [],
            "unsupported_factor_sources": [],
            "window_mismatches": [],
            "invalid_config_files": [],
        }
    for path in sorted(config_dir.glob("*.json")):
        relative = _relative(path, root)
        try:
            data = json.loads(path.read_text(encoding="utf-8-sig"))
        except json.JSONDecodeError as exc:
            invalid_config_files.append({"path": relative, "error": str(exc)})
            continue
        grid = _factor_grid_mapping(data)
        if grid is None:
            continue
        configs_scanned += 1
        factor_source = str(grid.get("factor_source", DEFAULT_FACTOR_SOURCE))
        factor_names = tuple(str(name) for name in grid.get("factor_names", ()))
        factor_windows = _factor_windows(grid.get("factor_windows", DEFAULT_FACTOR_WINDOWS))
        registered = _registered_factor_names(factor_source, factor_windows)
        if registered is None:
            unsupported_factor_sources.append({"path": relative, "factor_source": factor_source})
            continue
        for factor_name in factor_names:
            window = _parse_technical_factor_window(factor_name)
            if factor_source in {"technical", "combined"} and window is not None and window not in factor_windows:
                window_mismatches.append(
                    {
                        "path": relative,
                        "factor_name": factor_name,
                        "factor_window": window,
                        "configured_windows": list(factor_windows),
                    }
                )
                continue
            if factor_name not in registered:
                unknown_factor_refs.append(
                    {
                        "path": relative,
                        "factor_source": factor_source,
                        "factor_name": factor_name,
                    }
                )
    passes = not unknown_factor_refs and not unsupported_factor_sources and not window_mismatches and not invalid_config_files
    return {
        "passes": passes,
        "configs_scanned": configs_scanned,
        "unknown_factor_refs": unknown_factor_refs,
        "unsupported_factor_sources": unsupported_factor_sources,
        "window_mismatches": window_mismatches,
        "invalid_config_files": invalid_config_files,
    }


def _factor_grid_mapping(data: Any) -> dict[str, Any] | None:
    if not isinstance(data, dict):
        return None
    nested = data.get("experiment_grid")
    if isinstance(nested, dict) and "factor_names" in nested:
        return nested
    if "factor_names" in data:
        return data
    return None


def _factor_windows(value: Any) -> tuple[int, ...]:
    if not isinstance(value, (list, tuple)):
        return DEFAULT_FACTOR_WINDOWS
    windows = []
    for item in value:
        try:
            windows.append(int(item))
        except (TypeError, ValueError):
            continue
    return tuple(windows) or DEFAULT_FACTOR_WINDOWS


def _registered_factor_names(factor_source: str, factor_windows: tuple[int, ...]) -> set[str] | None:
    if factor_source == "technical":
        return _technical_factor_names(factor_windows)
    if factor_source == "tushare_daily_basic":
        return set(DAILY_BASIC_FACTOR_NAMES)
    if factor_source == "tushare_moneyflow":
        return set(MONEYFLOW_FACTOR_NAMES)
    if factor_source == "moneyflow_technical_combo":
        return set(MONEYFLOW_TECHNICAL_COMBO_FACTOR_NAMES)
    if factor_source == "etf_share_size":
        return set(ETF_SHARE_SIZE_FACTOR_NAMES)
    if factor_source == "etf_moneyflow_basket":
        return set(ETF_MONEYFLOW_BASKET_FACTOR_NAMES)
    if factor_source == "combined":
        return _technical_factor_names(factor_windows) | set(DAILY_BASIC_FACTOR_NAMES)
    return None


def _technical_factor_names(windows: tuple[int, ...]) -> set[str]:
    return {f"{prefix}_{window}" for prefix in TECHNICAL_FACTOR_PREFIXES for window in windows}


def _parse_technical_factor_window(factor_name: str) -> int | None:
    for prefix in sorted(TECHNICAL_FACTOR_PREFIXES, key=len, reverse=True):
        marker = f"{prefix}_"
        if factor_name.startswith(marker):
            try:
                return int(factor_name.removeprefix(marker))
            except ValueError:
                return None
    return None


if __name__ == "__main__":
    main()
