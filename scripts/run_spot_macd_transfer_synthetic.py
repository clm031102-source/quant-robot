"""Run the fixed invented2001-origin spot27 fixture; output path only, no data input."""
from pathlib import Path
import argparse
from datetime import datetime, timezone
import hashlib
import json
import platform
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/"src"))
from quant_robot.research import spot_macd_transfer as model


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path,
                        default=ROOT/"data/reports/spot_transfer_engineering/fixed_artificial27_demo")
    args = parser.parse_args()
    origin = Path(model.__file__).resolve()
    if not origin.is_relative_to(ROOT/"src"):
        raise RuntimeError("Wrong worktree implementation loaded")
    started = datetime.now(timezone.utc).isoformat()
    result = model.run_synthetic_suite(model.fixed_artificial_fixture(), output_dir=args.output_dir)
    receipt = dict(started_at=started, finished_at=datetime.now(timezone.utc).isoformat(),
        module_file=str(origin), module_sha256=hashlib.sha256(origin.read_bytes()).hexdigest(),
        python=platform.python_version(), numpy=model.np.__version__, pandas=model.pd.__version__,
        method_sha256=model.METHOD_SHA, invented_only=True, source_financial_values_read=0,
        network_operations=0, historical_returns_computed=False, qualified=False,
        accounts=result["account_count"], observations=result["observations"],
        full_fixed_statistics_completed=result["full_fixed_statistics_completed"],
        all_account_reconciled=all(a["account_reconciled"] for a in result["summaries"].values()),
        summary_sha256=hashlib.sha256((args.output_dir/"summary.json").read_bytes()).hexdigest(),
        finance_context_initial=model.context_record(model.context()), signal_context_initial=model.context_record(model.context(28)),
        actual_final_context_flags="Peraccountdecimal_context;signal_states.jsonsignal_arithmetic",
        input_artifacts=result["input_artifacts"])
    model._persist(args.output_dir/"receipt.json", receipt)
    print(json.dumps(receipt, ensure_ascii=False))


if __name__ == "__main__":
    main()
