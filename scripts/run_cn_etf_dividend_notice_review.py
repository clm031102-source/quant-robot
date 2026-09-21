from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.data.etf_dividend_source_review import review_dividend_sources
from quant_robot.storage.atomic import atomic_write_json


def main() -> None:
    parser = argparse.ArgumentParser(description="Review retained official cash notices; offline fixture only")
    parser.add_argument("--config", default="configs/cn_etf_dividend_notice_review_20260912.json")
    parser.add_argument("--output-dir", default="data/reports/cn_etf_dividend_notice_review_20260912")
    args = parser.parse_args()
    config_bytes = Path(args.config).read_bytes()
    config = json.loads(config_bytes.decode("utf-8-sig"))
    report = review_dividend_sources(config, output_dir=args.output_dir)
    report["config_sha256"] = hashlib.sha256(config_bytes).hexdigest()
    path = Path(args.output_dir) / "dividend_notice_review.json"
    atomic_write_json(path, report)
    print(json.dumps({"report": str(path), "index_records": report["index_records"],
        "notices": len(report["notices"]), "fixture_cash": report["fixture_drill"].get("cash_received"),
        "execution_accounting_source_verified": False}))


if __name__ == "__main__":
    main()
