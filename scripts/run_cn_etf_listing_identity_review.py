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

from quant_robot.data.etf_listing_evidence import review_listing_bundle  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description='Review retained ETF listing identities offline')
    parser.add_argument('--config', default='configs/cn_etf_listing_identity_review_20260912.json')
    parser.add_argument('--output-dir', default='data/reports/cn_etf_listing_identity_review_20260912')
    args = parser.parse_args()
    raw = Path(args.config).read_bytes()
    result = review_listing_bundle(json.loads(raw))
    result['configuration'] = {'path': args.config, 'sha256': hashlib.sha256(raw).hexdigest()}
    out = Path(args.output_dir); out.mkdir(parents=True, exist_ok=True)
    report = out / 'listing_identity_review.json'
    report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps({'counts': result['counts'], 'report': str(report),
                      'source_gate_passed': False}, ensure_ascii=False))


if __name__ == '__main__':
    main()
