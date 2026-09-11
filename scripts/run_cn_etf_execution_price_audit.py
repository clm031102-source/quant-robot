from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.data.etf_execution_price_audit import run_execution_price_audit
from quant_robot.storage.atomic import atomic_write_json
from quant_robot.storage.fingerprints import sha256_file


def main() -> None:
    parser = argparse.ArgumentParser(description="Read-only bounded ETF price lineage audit; no returns or provider requests")
    parser.add_argument("--config", default="configs/cn_etf_execution_price_audit_20260912.json")
    parser.add_argument("--output-dir", default="data/reports/cn_etf_execution_price_audit_20260912")
    args = parser.parse_args()
    config = json.loads(Path(args.config).read_text(encoding="utf-8-sig"))
    result = run_execution_price_audit(**config, progress=lambda value: print(value, file=sys.stderr, flush=True))
    result["request_config_sha256"] = sha256_file(Path(args.config))
    path = Path(args.output_dir) / "price_source_audit.json"
    atomic_write_json(path, result)
    print(json.dumps({"report": str(path), "local_raw_reconciliation_passed": result["local_raw_reconciliation_passed"],
        "blockers": result["blockers"], "summary": result["summary"],
        "execution_accounting_source_verified": False}, ensure_ascii=False, indent=2))
    if not result["local_raw_reconciliation_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
