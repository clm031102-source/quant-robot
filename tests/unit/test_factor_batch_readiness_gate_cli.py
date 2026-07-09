import json
import tempfile
import unittest
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from quant_robot.ops.factor_mining_candidate_plan_gate import (
    default_cn_stock_pre_mining_control_plan,
    default_cn_stock_promotion_policy,
)
from scripts.run_factor_batch_readiness_gate import main


class FactorBatchReadinessGateCliTests(unittest.TestCase):
    def test_cli_runs_source_queue_before_candidate_plan_gate_and_writes_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            processed = root / "processed"
            reports = root / "reports"
            output = root / "readiness"
            plan = root / "candidate_plan.json"
            (processed / "round701_analyst_report_revision_cache_202406_20260709").mkdir(parents=True)
            (reports / "round701_analyst_report_revision_cache_202406_20260709").mkdir(parents=True)
            plan.write_text(json.dumps(_candidate_plan()), encoding="utf-8")
            stdout = StringIO()

            with redirect_stdout(stdout):
                exit_code = main(
                    [
                        "--candidate-plan",
                        str(plan),
                        "--processed-root",
                        str(processed),
                        "--reports-root",
                        str(reports),
                        "--output-dir",
                        str(output),
                        "--allow-blocked",
                    ]
                )

            payload = json.loads(stdout.getvalue())
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["status"], "blocked")
            self.assertFalse(payload["decision"]["factor_batch_ready"])
            self.assertTrue((output / "source_queue" / "cn_stock_local_source_queue_audit.json").exists())
            self.assertTrue((output / "candidate_plan_gate" / "factor_mining_candidate_plan_gate.json").exists())
            self.assertTrue((output / "factor_batch_readiness_gate.json").exists())


def _candidate_plan() -> dict:
    return {
        "stage": "example_preregistration",
        "research_control_plan": default_cn_stock_pre_mining_control_plan(),
        "promotion_policy": default_cn_stock_promotion_policy(),
        "candidates": [
            {
                "factor_name": "analyst_target_upside_60",
                "family": "analyst_expectation_revision",
                "market": "CN",
                "asset_type": "stock",
                "registration_status": "pre_registered",
                "source_id": "analyst_report_revision",
                "hypothesis_source": "Tushare report_rc target price and report date.",
                "economic_rationale": "Target-price upside proxies analyst expectation imbalance.",
                "portfolio_backtest_allowed": False,
                "promotion_allowed": False,
            }
        ],
    }


if __name__ == "__main__":
    unittest.main()
