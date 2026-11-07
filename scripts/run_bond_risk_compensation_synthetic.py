"""Run only the fixed invented2001fixture; accepts output path, never input data."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from quant_robot.paper import annual_allocation, bond_risk_compensation, daily_recovery


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--split-demo", action="store_true", help="Fixed36session artificial split10 case only")
    args = parser.parse_args()
    if args.output_dir is None:
        args.output_dir = ROOT / "data/reports/bond_risk_compensation_engineering" / ("split_artificial_demo" if args.split_demo else "fixed_artificial_demo")
    origins = {m.__name__: str(Path(m.__file__).resolve()) for m in (annual_allocation, bond_risk_compensation, daily_recovery)}
    if not all(Path(path).is_relative_to(ROOT / "src") for path in origins.values()):
        raise RuntimeError("Worktree module origin mismatch")
    fixture = bond_risk_compensation.fixed_split_artificial_fixture() if args.split_demo else bond_risk_compensation.fixed_artificial_fixture()
    started = datetime.now(timezone.utc).isoformat()
    bundle = bond_risk_compensation.run_synthetic_bundle(fixture,
        split_mode=bond_risk_compensation.SPLIT_MODE if args.split_demo else None)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    raw = (json.dumps(bundle, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")
    path = args.output_dir / "synthetic_bundle.json"
    with path.open("xb") as stream:
        stream.write(raw); stream.flush(); os.fsync(stream.fileno())
    receipt = {"artifact_type": "fixed_artificial_bond_demo_receipt_v1", "started_at": started,
        "finished_at": datetime.now(timezone.utc).isoformat(), "python": platform.python_version(),
        "module_origins": origins, "module_sha256": {name: hashlib.sha256(Path(origin).read_bytes()).hexdigest()
                                                      for name, origin in origins.items()},
        "artifact": {"path": str(path.resolve()), "sha256": hashlib.sha256(raw).hexdigest(), "bytes": len(raw)},
        "account_count": 10, "additional_nontrading_reference_count": 1, "artificial_sessions": len(fixture["sessions"]),
        "invented_values": True, "network_requests": 0, "financial_data_files_read": 0,
        "historical_returns_computed": False, "new_financial_studies": 0, "qualified": False,
        "account_ledgers_reconciled": all(a["summary"]["cash_quantity_NAV_reconciled"] for a in bundle["fee_accounts"]),
        "all_results_retained": True}
    if args.split_demo:
        receipt["split_mode"] = bond_risk_compensation.SPLIT_MODE
    with (args.output_dir / "receipt.json").open("xb") as stream:
        stream.write((json.dumps(receipt, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
        stream.flush(); os.fsync(stream.fileno())
    print(json.dumps(receipt, ensure_ascii=False))


if __name__ == "__main__":
    main()
