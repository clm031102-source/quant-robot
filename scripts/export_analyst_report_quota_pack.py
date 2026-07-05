from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import date
from pathlib import Path
from typing import Any

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()


DEFAULT_OUTPUT_DIR = Path("data/reports/analyst_report_quota_pack")
SAFETY = "Research-to-review only. No broker connection, no account reads, no order placement, no live trading."
QUOTA_PACK_MANIFEST = "analyst_report_quota_pack_manifest.json"


def export_analyst_report_quota_pack(
    *,
    report_roots: list[str | Path],
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    machine: str = "",
    task: str = "",
    branch: str = "",
) -> dict[str, Any]:
    output_path = Path(output_dir)
    reports_path = output_path / "quota_report_roots"
    if reports_path.exists():
        shutil.rmtree(reports_path)
    reports_path.mkdir(parents=True, exist_ok=True)

    exported: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []
    for source_path in _cache_report_paths(report_roots, exclude_roots=[output_path]):
        payload = _load_json(source_path)
        if payload.get("stage") != "tushare_analyst_report_cache" or payload.get("source") != "tushare_report_rc":
            skipped.append({"source_path": str(source_path), "reason": "not_tushare_report_rc_cache"})
            continue
        source_fingerprint = _source_fingerprint(source_path, payload)
        export_path = reports_path / _report_dir_name(source_path) / "tushare_analyst_report_cache.json"
        export_path.parent.mkdir(parents=True, exist_ok=True)
        export_payload = dict(payload)
        export_payload.setdefault("quota_pack_source_path", str(source_path))
        export_payload["quota_pack_source_fingerprint"] = source_fingerprint
        export_path.write_text(json.dumps(export_payload, indent=2, sort_keys=True), encoding="utf-8")
        exported.append(
            {
                "source_path": str(source_path),
                "export_path": str(export_path),
                "source_fingerprint": source_fingerprint,
                "generated_at": str(payload.get("generated_at", "")),
                "window_rows": len(payload.get("rows_by_window", [])) if isinstance(payload.get("rows_by_window"), list) else 0,
            }
        )

    manifest = {
        "stage": "analyst_report_quota_pack",
        "generated_at": date.today().isoformat(),
        "quota_pack_root": str(output_path),
        "provenance": {
            "machine": str(machine).strip(),
            "task": str(task).strip(),
            "branch": str(branch).strip(),
        },
        "summary": {
            "report_root_count": len(report_roots),
            "exported_report_count": len(exported),
            "skipped_report_count": len(skipped),
        },
        "exported_reports": exported,
        "skipped_reports": skipped,
        "safety": SAFETY,
        "live_boundary_allowed": False,
    }
    (output_path / "analyst_report_quota_pack_manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "analyst_report_quota_pack_manifest.md").write_text(
        _render_markdown(manifest),
        encoding="utf-8",
    )
    return manifest


def _cache_report_paths(report_roots: list[str | Path], *, exclude_roots: list[Path] | None = None) -> list[Path]:
    paths: list[Path] = []
    excluded = [path.resolve() for path in exclude_roots or []]
    for root in report_roots:
        root_path = Path(root)
        if root_path.is_file() and root_path.name == "tushare_analyst_report_cache.json":
            if not _is_under_any(root_path, excluded) and not _is_inside_quota_pack(root_path):
                paths.append(root_path)
        elif root_path.exists():
            paths.extend(
                path
                for path in root_path.rglob("tushare_analyst_report_cache.json")
                if not _is_under_any(path, excluded) and not _is_inside_quota_pack(path)
            )
    return sorted(set(paths))


def _is_under_any(path: Path, roots: list[Path]) -> bool:
    resolved = path.resolve()
    return any(resolved == root or root in resolved.parents for root in roots)


def _is_inside_quota_pack(path: Path) -> bool:
    return any((parent / QUOTA_PACK_MANIFEST).exists() for parent in path.parents)


def _load_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return value if isinstance(value, dict) else {}


def _report_dir_name(path: Path) -> str:
    digest = hashlib.sha1(str(path.resolve()).encode("utf-8")).hexdigest()[:12]
    return f"report_{digest}"


def _source_fingerprint(path: Path, payload: dict[str, Any]) -> str:
    existing = str(payload.get("quota_pack_source_fingerprint", "")).strip()
    if existing:
        return existing
    evidence = {
        "source_path": str(path.resolve()),
        "payload": payload,
    }
    encoded = json.dumps(evidence, ensure_ascii=False, sort_keys=True).encode("utf-8")
    return hashlib.sha1(encoded).hexdigest()


def _render_markdown(manifest: dict[str, Any]) -> str:
    summary = manifest.get("summary", {})
    summary_dict = summary if isinstance(summary, dict) else {}
    lines = [
        "# Analyst Report Quota Pack",
        "",
        f"- Stage: {manifest.get('stage', '')}",
        f"- Generated at: {manifest.get('generated_at', '')}",
        f"- Quota pack root: {manifest.get('quota_pack_root', '')}",
        f"- Machine: {_dict(manifest.get('provenance')).get('machine', '')}",
        f"- Task: {_dict(manifest.get('provenance')).get('task', '')}",
        f"- Branch: {_dict(manifest.get('provenance')).get('branch', '')}",
        f"- Exported reports: {summary_dict.get('exported_report_count', 0)}",
        f"- Skipped reports: {summary_dict.get('skipped_report_count', 0)}",
        f"- Safety: {manifest.get('safety', SAFETY)}",
        "",
        "## Exported Reports",
        "",
    ]
    exported = manifest.get("exported_reports", [])
    exported_list = exported if isinstance(exported, list) else []
    if exported_list:
        lines.extend(f"- {item.get('export_path', '')}" for item in exported_list if isinstance(item, dict))
    else:
        lines.append("- none")
    lines.extend(["", "## Usage", ""])
    lines.append("- Pass this directory as `--quota-report-root` on another workstation.")
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export local analyst-report cache summaries as a portable quota preflight report root.",
        epilog="Writes generated data/reports evidence; share out of band; do not commit.",
    )
    parser.add_argument("--report-root", action="append", default=None, help="Local report root to scan; repeatable.")
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR), help="Portable quota pack output directory.")
    parser.add_argument("--machine", default="", help="Source workstation name for cross-machine review.")
    parser.add_argument("--task", default="", help="Source task type for cross-machine review.")
    parser.add_argument("--branch", default="", help="Source git branch for cross-machine review.")
    args = parser.parse_args()

    manifest = export_analyst_report_quota_pack(
        report_roots=args.report_root or ["data/reports"],
        output_dir=args.output_dir,
        machine=args.machine,
        task=args.task,
        branch=args.branch,
    )
    print(
        json.dumps(
            {
                "status": "exported",
                "summary": manifest["summary"],
                "quota_pack_root": manifest["quota_pack_root"],
                "provenance": manifest["provenance"],
                "safety": manifest["safety"],
            },
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
    )


def _dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


if __name__ == "__main__":
    main()
