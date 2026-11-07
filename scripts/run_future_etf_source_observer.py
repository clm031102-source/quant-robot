"""Preview an exact released future ETF observation; --execute is separately gated."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"src"))
from quant_robot.ops.future_etf_source_observer import capture, implementation


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date")
    parser.add_argument("--scope-sha256")
    parser.add_argument("--execute", action="store_true")
    parser.add_argument("--describe-implementation", action="store_true")
    args = parser.parse_args()
    try:
        if args.describe_implementation and not args.execute:
            result = implementation(ROOT)
        else:
            outcome = capture(args.date, repo_root=ROOT, expected_scope_sha256=args.scope_sha256, execute=args.execute)
            result = {k: outcome.get(k) for k in ("status", "date", "paired_session_complete", "attempts_started",
                      "attempts_started_lower_bound", "received_bytes", "qualified", "real_forward")}
        print(json.dumps(result))
        return int(result.get("status") == "failed_consumed")
    except BaseException:
        print(json.dumps({"status": "closed_or_failed_no_exception_text", "retry_authorized": False}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
