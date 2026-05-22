from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from quant_robot.data.readiness import check_parquet_readiness, check_tushare_readiness

SCAN_ROOTS = ("src", "scripts", "tests", "README.md", "docs")
IMPLEMENTATION_ROOTS = ("src/", "scripts/")
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
    safety_passes = not forbidden_hits
    mock_passes = all("mock" in file.lower() or "fixture" in file.lower() for file in mock_files)
    return {
        "summary": {
            "passes": safety_passes and mock_passes,
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
    }


def render_markdown_report(audit: dict[str, Any]) -> str:
    safety = audit["safety"]
    mock = audit["mock_boundaries"]
    real_data = audit.get("real_data", {})
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
    return any(phrase in lower for phrase in BOUNDARY_PHRASES)


def _is_mock_file(relative_path: str) -> bool:
    lower = relative_path.lower()
    return "mock" in lower or "fixture" in lower


def _is_implementation_file(relative_path: str) -> bool:
    if relative_path in SELF_AUDIT_FILES:
        return False
    return relative_path.endswith(".py") and relative_path.startswith(IMPLEMENTATION_ROOTS)


if __name__ == "__main__":
    main()
