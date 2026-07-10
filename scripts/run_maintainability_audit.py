from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any


OVERSIZED_MODULE_THRESHOLD = 1_000
MIN_NON_UNIT_TEST_FILES = 2
MODULE_LINE_BASELINES = {
    "src/quant_robot/gui/control_center.py": 4_190,
    "src/quant_robot/gui/operation_ledger.py": 1_390,
    "src/quant_robot/gui/research_service.py": 2_934,
    "src/quant_robot/ops/accounting_quality_statement_residual_ic_shape_prescreen.py": 1_023,
    "src/quant_robot/ops/cn_tradeability_limit_event_proxy_prescreen.py": 1_026,
    "src/quant_robot/ops/daily_trade_advisory.py": 13_982,
    "src/quant_robot/ops/event_factor_pit_ic_prescreen.py": 1_503,
    "src/quant_robot/ops/factor_mining_startup.py": 1_372,
    "src/quant_robot/ops/industry_leader_lag_residual_prescreen.py": 1_579,
    "src/quant_robot/ops/profitability_event_revision_controlled_ic_neutral_prescreen.py": 1_110,
    "src/quant_robot/ops/public_technical_failure_reversal_neutral_dedup.py": 1_136,
    "src/quant_robot/ops/public_tradeable_indicator_composite_residual_prescreen.py": 1_304,
    "src/quant_robot/promotion/gate.py": 1_039,
}


def collect_maintainability_audit(
    root: str | Path = ".",
    *,
    oversized_threshold: int = OVERSIZED_MODULE_THRESHOLD,
    module_line_baselines: dict[str, int] | None = None,
    min_non_unit_test_files: int = MIN_NON_UNIT_TEST_FILES,
) -> dict[str, Any]:
    if oversized_threshold < 1:
        raise ValueError("oversized_threshold must be positive")
    root_path = Path(root)
    baselines = MODULE_LINE_BASELINES if module_line_baselines is None else module_line_baselines
    modules = _python_file_rows(root_path, root_path / "src" / "quant_robot")
    oversized = [row for row in modules if row["lines"] >= oversized_threshold]
    test_topology = _test_topology(root_path)
    blockers = _baseline_blockers(
        oversized,
        baselines,
        non_unit_test_files=test_topology["non_unit_test_files"],
        min_non_unit_test_files=min_non_unit_test_files,
    )
    known_debt = _known_debt(oversized, test_topology)
    largest = max(modules, key=lambda row: row["lines"], default={"path": None, "lines": 0})
    return {
        "stage": "maintainability_baseline_audit",
        "status": "baseline_passed_with_known_debt" if not blockers else "baseline_regressed",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "source_module_count": len(modules),
            "source_lines": sum(int(row["lines"]) for row in modules),
            "oversized_threshold": oversized_threshold,
            "oversized_module_count": len(oversized),
            "largest_module": largest,
            "test_file_count": test_topology["test_file_count"],
        },
        "oversized_modules": [
            {
                **row,
                "baseline_lines": baselines.get(str(row["path"])),
                "baseline_status": _module_baseline_status(row, baselines),
            }
            for row in sorted(oversized, key=lambda item: (-int(item["lines"]), str(item["path"])))
        ],
        "test_topology": test_topology,
        "decision": {
            "maintainability_baseline_passed": not blockers,
            "blockers": blockers,
            "known_debt": known_debt,
            "project_complete": False,
        },
    }


def render_maintainability_markdown(audit: dict[str, Any]) -> str:
    summary = audit.get("summary", {})
    decision = audit.get("decision", {})
    topology = audit.get("test_topology", {})
    lines = [
        "# Maintainability Baseline Audit",
        "",
        f"- Status: {audit.get('status', 'unknown')}",
        f"- Baseline passed: {decision.get('maintainability_baseline_passed', False)}",
        f"- Source modules: {summary.get('source_module_count', 0)}",
        f"- Oversized modules: {summary.get('oversized_module_count', 0)}",
        f"- Unit / integration / e2e tests: {topology.get('unit_test_files', 0)} / {topology.get('integration_test_files', 0)} / {topology.get('e2e_test_files', 0)}",
        "",
        "## Oversized Modules",
        "",
        "| Path | Lines | Baseline | Status |",
        "| --- | ---: | ---: | --- |",
    ]
    for row in audit.get("oversized_modules", []):
        lines.append(
            f"| {row.get('path')} | {row.get('lines')} | {row.get('baseline_lines')} | {row.get('baseline_status')} |"
        )
    lines.extend(["", "## Known Debt", ""])
    for item in decision.get("known_debt", []):
        lines.append(f"- {item}")
    if not decision.get("known_debt"):
        lines.append("- none")
    lines.extend(["", "## Baseline Regressions", ""])
    for item in decision.get("blockers", []):
        lines.append(f"- {item}")
    if not decision.get("blockers"):
        lines.append("- none")
    return "\n".join(lines) + "\n"


def write_maintainability_audit(output_dir: str | Path, audit: dict[str, Any]) -> dict[str, Path]:
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    json_path = output / "maintainability_audit.json"
    markdown_path = output / "maintainability_audit.md"
    json_path.write_text(json.dumps(audit, indent=2, sort_keys=True), encoding="utf-8")
    markdown_path.write_text(render_maintainability_markdown(audit), encoding="utf-8")
    return {"json": json_path, "markdown": markdown_path}


def _python_file_rows(root: Path, source_root: Path) -> list[dict[str, Any]]:
    if not source_root.exists():
        return []
    rows = []
    for path in sorted(source_root.rglob("*.py")):
        rows.append(
            {
                "path": path.relative_to(root).as_posix(),
                "lines": len(path.read_text(encoding="utf-8", errors="ignore").splitlines()),
            }
        )
    return rows


def _test_topology(root: Path) -> dict[str, Any]:
    tests_root = root / "tests"
    files = sorted(tests_root.rglob("test_*.py")) if tests_root.exists() else []
    unit = [path for path in files if _test_layer(path, tests_root) == "unit"]
    integration = [path for path in files if _test_layer(path, tests_root) == "integration"]
    e2e = [path for path in files if _test_layer(path, tests_root) == "e2e"]
    non_unit = len(files) - len(unit)
    return {
        "test_file_count": len(files),
        "unit_test_files": len(unit),
        "integration_test_files": len(integration),
        "e2e_test_files": len(e2e),
        "non_unit_test_files": non_unit,
        "unit_test_share": float(len(unit) / len(files)) if files else 0.0,
    }


def _test_layer(path: Path, tests_root: Path) -> str:
    relative = path.relative_to(tests_root)
    return relative.parts[0].casefold() if len(relative.parts) > 1 else "unclassified"


def _baseline_blockers(
    oversized: list[dict[str, Any]],
    baselines: dict[str, int],
    *,
    non_unit_test_files: int,
    min_non_unit_test_files: int,
) -> list[str]:
    blockers = []
    for row in oversized:
        path = str(row["path"])
        baseline = baselines.get(path)
        if baseline is None:
            blockers.append(f"new_oversized_module:{path}")
        elif int(row["lines"]) > int(baseline):
            blockers.append(f"module_line_baseline_exceeded:{path}")
    if non_unit_test_files < min_non_unit_test_files:
        blockers.append("non_unit_test_file_baseline_regressed")
    return sorted(blockers)


def _module_baseline_status(row: dict[str, Any], baselines: dict[str, int]) -> str:
    baseline = baselines.get(str(row["path"]))
    if baseline is None:
        return "new_oversized_module"
    return "within_baseline" if int(row["lines"]) <= baseline else "baseline_exceeded"


def _known_debt(oversized: list[dict[str, Any]], topology: dict[str, Any]) -> list[str]:
    debt = []
    if oversized:
        debt.append("oversized_modules_present")
    if int(topology.get("integration_test_files", 0)) < 10:
        debt.append("integration_test_layer_sparse")
    if int(topology.get("e2e_test_files", 0)) == 0:
        debt.append("e2e_test_layer_missing")
    if float(topology.get("unit_test_share", 0.0)) > 0.90:
        debt.append("unit_test_topology_concentrated")
    return debt


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit non-growing maintainability baselines and known debt.")
    parser.add_argument("--root", default=".")
    parser.add_argument("--output-dir", default="data/reports/maintainability_audit")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--fail-on-regression", action="store_true")
    args = parser.parse_args()
    audit = collect_maintainability_audit(args.root)
    write_maintainability_audit(args.output_dir, audit)
    if args.json:
        print(json.dumps(audit, indent=2, sort_keys=True))
    else:
        print(render_maintainability_markdown(audit), end="")
    if args.fail_on_regression and not audit["decision"]["maintainability_baseline_passed"]:
        raise SystemExit(2)


if __name__ == "__main__":
    main()
