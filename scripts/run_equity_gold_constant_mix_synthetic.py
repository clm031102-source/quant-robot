"""Run only the fixed invented engineering fixture; no financial input option."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from quant_robot.research import equity_gold_constant_mix as model


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = model.run_matrix(model.make_full_demo_fixture(), args.output)
    print(json.dumps(dict(status="completed_artificial_27_accounts", module_file=model.__file__,
                          python=sys.version, output=str(args.output.resolve()),
                          account_count=result["account_count"], source_nature=model.SOURCE,
                          qualified=False, real_forward=0, historical_returns_computed=False),
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
