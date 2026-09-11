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

from quant_robot.data.etf_peer_document_evidence import review_peer_document_bundle  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description="Review retained official ETF document fields offline")
    parser.add_argument("--config", default="configs/cn_etf_peer_document_review_20260912.json")
    parser.add_argument("--output-dir", default="data/reports/cn_etf_peer_document_review_20260912")
    args = parser.parse_args()
    raw = Path(args.config).read_bytes()
    result = review_peer_document_bundle(json.loads(raw))
    result["configuration"] = {"path": args.config, "sha256": hashlib.sha256(raw).hexdigest()}
    out = Path(args.output_dir)
    out.mkdir(parents=True, exist_ok=True)
    report = out / "peer_document_review.json"
    report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"counts": result["counts"], "report": str(report),
                      "metadata_readiness_cleared": False}, ensure_ascii=False))


if __name__ == "__main__":
    main()
