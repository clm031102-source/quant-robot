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

from quant_robot.data.etf_manager_notice_index import review_chinaamc_notice_bundle  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Review retained official manager notice pagination offline")
    parser.add_argument("--config", default="configs/cn_etf_manager_notice_review_20260912.json")
    parser.add_argument("--output-dir", default="data/reports/cn_etf_manager_notice_review_20260912")
    args = parser.parse_args()
    raw = Path(args.config).read_bytes()
    result = review_chinaamc_notice_bundle(json.loads(raw))
    result["configuration"] = {"path": args.config, "sha256": hashlib.sha256(raw).hexdigest()}
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    path = out / "manager_notice_review.json"
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"report": str(path), "pages": len(result["pages"]),
                      "articles": len(result["records"]), "historical_coverage_verified": False}))


if __name__ == "__main__":
    main()
