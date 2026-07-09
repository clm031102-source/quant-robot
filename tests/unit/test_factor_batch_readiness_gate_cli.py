import json
import tempfile
import unittest
from contextlib import redirect_stdout
from datetime import date
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

    def test_cli_clears_provider_candidate_when_provider_request_is_allowed(self) -> None:
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
                        "--provider-request-allowed",
                    ]
                )

            payload = json.loads(stdout.getvalue())
            source_queue = json.loads(
                (output / "source_queue" / "cn_stock_local_source_queue_audit.json").read_text(encoding="utf-8")
            )
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["status"], "ready")
            self.assertTrue(payload["decision"]["factor_batch_ready"])
            self.assertEqual(source_queue["decision"]["status"], "cleared")
            self.assertTrue(source_queue["decision"]["provider_factor_batch_allowed"])
            self.assertEqual(source_queue["decision"]["blockers"], [])

    def test_cli_runs_quota_preflight_before_provider_allowed_readiness(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            processed = root / "processed"
            reports = root / "reports"
            quota_reports = root / "quota_reports"
            output = root / "readiness"
            plan = root / "candidate_plan.json"
            (processed / "round701_analyst_report_revision_cache_202406_20260709").mkdir(parents=True)
            (reports / "round701_analyst_report_revision_cache_202406_20260709").mkdir(parents=True)
            quota_reports.mkdir()
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
                        "--quota-report-root",
                        str(quota_reports),
                        "--output-dir",
                        str(output),
                    ]
                )

            payload = json.loads(stdout.getvalue())
            quota_preflight = json.loads(
                (output / "analyst_quota_preflight" / "analyst_report_quota_preflight.json").read_text(
                    encoding="utf-8"
                )
            )
            source_queue = json.loads(
                (output / "source_queue" / "cn_stock_local_source_queue_audit.json").read_text(encoding="utf-8")
            )
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["status"], "ready")
            self.assertTrue(quota_preflight["decision"]["request_allowed"])
            self.assertTrue(source_queue["decision"]["provider_factor_batch_allowed"])
            self.assertEqual(payload["summary"]["provider_quota_preflight_status"], "allowed")

    def test_cli_quota_preflight_overrides_manual_provider_allowed_flag_when_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            processed = root / "processed"
            reports = root / "reports"
            quota_reports = root / "quota_reports"
            output = root / "readiness"
            plan = root / "candidate_plan.json"
            (processed / "round701_analyst_report_revision_cache_202406_20260709").mkdir(parents=True)
            (reports / "round701_analyst_report_revision_cache_202406_20260709").mkdir(parents=True)
            _write_quota_cache(quota_reports / "round_a", generated_at=date.today().isoformat(), status="ok")
            _write_quota_cache(quota_reports / "round_b", generated_at=date.today().isoformat(), status="ok")
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
                        "--quota-report-root",
                        str(quota_reports),
                        "--provider-request-allowed",
                        "--output-dir",
                        str(output),
                        "--allow-blocked",
                    ]
                )

            payload = json.loads(stdout.getvalue())
            source_queue = json.loads(
                (output / "source_queue" / "cn_stock_local_source_queue_audit.json").read_text(encoding="utf-8")
            )
            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["status"], "blocked")
            self.assertFalse(payload["decision"]["factor_batch_ready"])
            self.assertFalse(source_queue["decision"]["provider_factor_batch_allowed"])
            self.assertEqual(payload["summary"]["provider_quota_preflight_status"], "blocked")
            self.assertIn(
                "provider_quota_preflight_blocked:daily_provider_request_budget_exhausted",
                payload["decision"]["blockers"],
            )


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


def _write_quota_cache(root: Path, *, generated_at: str, status: str) -> None:
    root.mkdir(parents=True, exist_ok=True)
    payload = {
        "stage": "tushare_analyst_report_cache",
        "source": "tushare_report_rc",
        "generated_at": generated_at,
        "rows_by_window": [
            {
                "window_start": "20240401",
                "window_end": "20240430",
                "rows": 10,
                "status": status,
            }
        ],
    }
    (root / "tushare_analyst_report_cache.json").write_text(json.dumps(payload), encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
