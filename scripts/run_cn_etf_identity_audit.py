from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.data.etf_identity_audit import run_identity_audit
from quant_robot.storage.atomic import atomic_write_text
from quant_robot.storage.fingerprints import sha256_file


def main() -> None:
    parser = argparse.ArgumentParser(description="Identity-only ETF catalogue and cached roster diagnostics")
    parser.add_argument("--config", default="configs/cn_etf_identity_audit_20260912.json")
    parser.add_argument("--output-dir", default="data/reports/cn_etf_identity_audit_20260912")
    args = parser.parse_args()
    config_path = Path(args.config)
    result = run_identity_audit(**json.loads(config_path.read_text(encoding="utf-8-sig")))
    result["config_sha256"] = sha256_file(config_path)
    path = Path(args.output_dir) / "identity_audit.json"
    atomic_write_text(path, json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
    print(json.dumps({"report": str(path), "bar_rows": result["bar_rows"],
        "classification_changes": len(result["classification_changes"]),
        "historical_membership_verified": False, "source_changed_during_audit": result["source_changed_during_audit"]},
        ensure_ascii=False))
    # Completion means diagnostics were produced, not that any candidate passed.
    if result["source_changed_during_audit"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
