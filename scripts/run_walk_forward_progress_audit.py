from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.ops.walk_forward_progress_audit import (
    DEFAULT_EXPECTED_FOLDS,
    audit_walk_forward_progress,
    render_progress_markdown,
)


DEFAULT_WALK_FORWARD_ROOT = Path("data/reports/walk_forward_tushare_moneyflow_residual_regime")
DEFAULT_OUTPUT_DIR = Path("data/reports/walk_forward_progress_audit")


def run_walk_forward_progress_audit(
    *,
    walk_forward_root: str | Path = DEFAULT_WALK_FORWARD_ROOT,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    expected_folds: int = DEFAULT_EXPECTED_FOLDS,
    generated_at: str | None = None,
) -> dict[str, Any]:
    audit = audit_walk_forward_progress(
        Path(walk_forward_root),
        expected_folds=expected_folds,
        generated_at=generated_at,
    )
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    (output_path / "walk_forward_progress_audit.json").write_text(
        json.dumps(audit, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    (output_path / "walk_forward_progress_audit.md").write_text(
        render_progress_markdown(audit),
        encoding="utf-8",
    )
    return audit


def main() -> None:
    parser = argparse.ArgumentParser(description="Audit partial or completed walk-forward validation progress.")
    parser.add_argument("--walk-forward-root", default=str(DEFAULT_WALK_FORWARD_ROOT))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--expected-folds", type=int, default=DEFAULT_EXPECTED_FOLDS)
    args = parser.parse_args()
    audit = run_walk_forward_progress_audit(
        walk_forward_root=Path(args.walk_forward_root),
        output_dir=Path(args.output_dir),
        expected_folds=args.expected_folds,
    )
    print(json.dumps({"summary": audit["summary"]}, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
