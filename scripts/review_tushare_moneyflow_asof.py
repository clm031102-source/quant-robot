"""Review pinned prospective moneyflow receipts at a frozen decision cutoff."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:  # pragma: no cover - direct script execution
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.data.moneyflow_receipt_asof import read_moneyflow_asof  # noqa: E402
from quant_robot.storage.atomic import atomic_write_json  # noqa: E402
from scripts.run_quant_pm_startup_gate import run_quant_pm_startup_gate  # noqa: E402


def _unique_object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("duplicate source scope key")
        value[key] = item
    return value


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scope", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--machine", required=True)
    parser.add_argument("--branch", required=True)
    args = parser.parse_args(argv)
    try:
        root = Path.cwd().resolve()
        output = (root / args.output).resolve()
        reports = (root / "data/reports").resolve()
        if not reports.is_relative_to(root) or not output.is_relative_to(reports) or output == reports:
            raise ValueError("source review output must be under repository reports")
        with (root / args.scope).open("rb") as handle:
            raw = handle.read(64_001)
        if len(raw) > 64_000:
            raise ValueError("source scope exceeds byte budget")
        manifest = json.loads(raw.decode("utf-8-sig"), object_pairs_hook=_unique_object)
        output.mkdir(parents=True, exist_ok=False)
        (output / "scope.json").write_bytes(raw)
        gate = run_quant_pm_startup_gate(output_dir=output / "startup_gate",
            machine=args.machine, task="factor_review", branch=args.branch)
        atomic_write_json(output / "gate.json", gate)
        if gate.get("status") != "ready" or gate.get("primary_market") != "CN_ETF" or gate.get("blockers") != []:
            result = {"status": "gate_blocked", "research_admission_granted": False}
        else:
            result = read_moneyflow_asof(manifest, repo_root=root)
        result["scope_file_sha256"] = hashlib.sha256(raw).hexdigest()
        atomic_write_json(output / "result.json", result)
    except (OSError, ValueError) as exc:
        print(json.dumps({"status": "rejected", "failure_kind": type(exc).__name__,
                          "research_admission_granted": False}))
        return 1
    summary = {key: result[key] for key in ("status", "source_selection_complete", "source_review_blockers",
        "observed_numeric_cells", "unknown_cells", "research_admission_granted") if key in result}
    summary["result_path"] = str(output / "result.json")
    print(json.dumps(summary, sort_keys=True, indent=2))
    return 0 if result.get("source_selection_complete") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
