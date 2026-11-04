"""Prepare or execute the fixed 44-month source-only extension."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:
    from bootstrap import ensure_workspace_imports
ensure_workspace_imports()

from quant_robot.data.sources.geopolitical_vintages import (
    LIMIT, NEW_MONTHS, PROPOSAL_SHA, SCOPE_RELATIVE, collect, now, sha, source_window, verify_scope, write_json,
)


def prepare(root: Path, folder: Path, pilot_root: Path) -> Path:
    proposal = root / "configs/cn_etf_geopolitical_gold_proposal_20260922.json"
    if sha(proposal) != PROPOSAL_SHA:
        raise ValueError("original economic proposal changed")
    gate_path = folder / "startup_gate/quant_pm_startup_gate_pack.json"
    gate = json.loads(gate_path.read_text(encoding="utf-8"))
    if gate["status"] != "ready" or gate["blockers"] or gate["primary_market"] != "CN_ETF":
        raise ValueError("review startup gate blocked")
    review_path = root / "configs/cn_etf_geopolitical_gold_pilot_review_20260922.json"
    review = json.loads(review_path.read_text(encoding="utf-8"))
    pins = []
    for pin in review["pins"].values():
        path = root / pin["path"] if pin["path"].startswith("configs/") else pilot_root / pin["path"]
        if sha(path) != pin["sha256"]:
            raise ValueError("pilot review fingerprint changed")
        pins.append({"path": str(path), "sha256": sha(path)})
    pilot_folder = pilot_root / "data/reports/positive_ev_20260922/geopolitical_source_pilot"
    prior = json.loads((pilot_folder / "source_review.json").read_text(encoding="utf-8"))
    for pin in prior["pins"]:
        path = pilot_root / pin["path"]
        if sha(path) != pin["sha256"]:
            raise ValueError("pilot evidence changed")
        pins.append({"path": str(path), "sha256": sha(path)})
    # Reuse two consumed pilots locally, without a new network request or signal.
    pilots = {m: source_window(pilot_folder / f"{m}_vintage.xls", m) for m in ("202203", "202512")}
    for path in (proposal, review_path, gate_path, Path(__file__).resolve(),
                 root / "src/quant_robot/data/sources/geopolitical_vintages.py"):
        pins.append({"path": str(path), "sha256": sha(path)})
    scope = {"schema_version": 1, "created_at": now(), "stage": "source_only_expansion",
             "proposal_sha256": PROPOSAL_SHA, "months": list(NEW_MONTHS),
             "maximum_requests": 88, "maximum_response_bytes": LIMIT,
             "no_retries": True, "no_redirects": True, "gate_path": str(gate_path),
             "required_reading_hashes": {r["path"]: r["sha256"] for r in gate["required_reading"]},
             "pins": pins, "reused_pilots": pilots,
             "signal_generation_allowed": False, "financial_execution_allowed": False,
             "final_holdout_allowed": False,
             "publication_limitation": "Conditional on faithful repository history; not independently certified first publication."}
    path = folder / "scope.json"
    write_json(path, scope)
    return path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--pilot-root", type=Path)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--prepare", action="store_true")
    mode.add_argument("--execute", action="store_true")
    mode.add_argument("--verify", action="store_true")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    folder = args.output_dir.resolve()
    if folder / "scope.json" != (root / SCOPE_RELATIVE).resolve():
        raise ValueError("this finite expansion has one fixed local evidence directory")
    if args.prepare:
        if args.pilot_root is None:
            parser.error("--pilot-root is required for preparation")
        path = prepare(root, folder, args.pilot_root.resolve())
        print(json.dumps({"scope": str(path), "sha256": sha(path), "network_requests": 0}))
    elif args.verify:
        verify_scope(folder / "scope.json", repo_root=root)
        print(json.dumps({"status": "scope_verified", "network_requests": 0}))
    else:
        result = collect(folder / "scope.json", repo_root=root)
        print(json.dumps({k: result[k] for k in ("passed", "total_new_months", "requests")}))


if __name__ == "__main__":
    main()
