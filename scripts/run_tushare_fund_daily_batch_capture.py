"""Preview or execute an independently reviewed fixed source-only batch."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"src"))
from quant_robot.ops.tushare_fund_daily_batch import capture, implementation


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scope")
    parser.add_argument("--scope-sha256")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--describe-implementation", action="store_true")
    args = parser.parse_args()
    try:
        if args.describe_implementation and not args.execute:
            result = implementation(ROOT)
        else:
            result = capture(args.scope, repo_root=ROOT, expected_scope_sha256=args.scope_sha256, execute=args.execute)
        # No request bodies, provider messages, credentials or numerical values.
        print(json.dumps({key: value for key, value in result.items() if key not in ("request_receipts",)}))
        return 1 if result.get("status") == "failed_consumed" else 0
    except BaseException:
        print(json.dumps({"status": "failed_no_exception_text", "retry_authorized": False}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
