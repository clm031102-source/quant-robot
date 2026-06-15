import json
import tempfile
import unittest
from pathlib import Path

from scripts.run_tushare_alpha_factory_gate import run_tushare_alpha_factory_gate


class TushareAlphaFactoryGateTests(unittest.TestCase):
    def test_gate_blocks_real_tushare_before_runner_calls_when_readiness_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            calls: list[str] = []

            pack = run_tushare_alpha_factory_gate(
                report_dir=root / "gate",
                data_root=root / "data",
                source="tushare",
                market="CN",
                execute=True,
                readiness={"source": "tushare", "ready": False, "missing": ["TUSHARE_TOKEN is not set"]},
                ingest_runner=lambda **_: calls.append("ingest") or {},
                alpha_factory_runner=lambda **_: calls.append("alpha") or {},
            )

            artifact_exists = (root / "gate" / "tushare_alpha_factory_gate_pack.json").exists()
            serialized = json.dumps(pack, ensure_ascii=False)

        self.assertEqual(pack["status"], "blocked_missing_readiness")
        self.assertEqual(calls, [])
        self.assertIn("TUSHARE_TOKEN is not set", pack["decision"]["blockers"])
        self.assertEqual(pack["next_actions"][0]["action"], "set_tushare_token_env")
        self.assertTrue(artifact_exists)
        self.assertNotIn(("f" * 64), serialized)
        self.assertFalse(pack["live_boundary_allowed"])

    def test_gate_executes_fixture_ingest_factor_ingest_and_alpha_factory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            calls: list[str] = []

            def ingest_runner(**kwargs):
                calls.append(f"ingest:{kwargs['source']}")
                return {"source": kwargs["source"], "market": kwargs["market"], "processed_rows": 20}

            def alpha_factory_runner(**kwargs):
                calls.append(f"alpha:{kwargs['source']}")
                return {
                    "summary": {
                        "hypothesis_count": 9,
                        "completed": 9,
                        "adjusted_significant": 1,
                        "paper_eligible": 1,
                        "rejected_after_multiple_testing": 8,
                    },
                    "candidate_leaderboard": [
                        {
                            "case_id": "CN_total_mv_log_top1_cost5_reb1",
                            "factor_source": "tushare_daily_basic",
                            "adjusted_ic_p_value": 0.01,
                            "passes_adjusted_ic_p_value": True,
                            "significance_status": "significant_positive",
                            "paper_candidate_allowed": True,
                        }
                    ],
                }

            pack = run_tushare_alpha_factory_gate(
                report_dir=root / "gate",
                data_root=root / "data",
                source="tushare-fixture",
                market="CN",
                execute=True,
                readiness={"source": "tushare-fixture", "ready": True, "missing": []},
                ingest_runner=ingest_runner,
                alpha_factory_runner=alpha_factory_runner,
            )

        self.assertEqual(pack["status"], "alpha_candidates_found")
        self.assertEqual(calls, ["ingest:tushare-fixture", "ingest:tushare-factor-fixture", "alpha:processed-bars"])
        self.assertTrue(pack["decision"]["alpha_factory_completed"])
        self.assertTrue(pack["decision"]["paper_candidate_allowed"])
        self.assertEqual(pack["alpha_factory"]["summary"]["adjusted_significant"], 1)
        self.assertEqual(pack["next_actions"][0]["action"], "run_paper_batch_for_alpha_candidates")
        self.assertFalse(pack["live_boundary_allowed"])

    def test_gate_passes_capacity_controls_to_alpha_factory(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            alpha_kwargs: dict[str, object] = {}

            def ingest_runner(**kwargs):
                return {"source": kwargs["source"], "market": kwargs["market"], "processed_rows": 20}

            def alpha_factory_runner(**kwargs):
                alpha_kwargs.update(kwargs)
                return {
                    "summary": {
                        "hypothesis_count": 9,
                        "completed": 9,
                        "adjusted_significant": 0,
                        "paper_eligible": 0,
                        "rejected_after_multiple_testing": 9,
                    },
                    "candidate_leaderboard": [],
                }

            run_tushare_alpha_factory_gate(
                report_dir=root / "gate",
                data_root=root / "data",
                source="tushare-fixture",
                market="CN",
                execute=True,
                readiness={"source": "tushare-fixture", "ready": True, "missing": []},
                ingest_runner=ingest_runner,
                alpha_factory_runner=alpha_factory_runner,
                min_trades=3,
                portfolio_value=500000.0,
                market_impact_bps=10.0,
                max_participation_rate=0.05,
            )

        self.assertEqual(alpha_kwargs["min_trades"], 3)
        self.assertAlmostEqual(alpha_kwargs["portfolio_value"], 500000.0)
        self.assertAlmostEqual(alpha_kwargs["market_impact_bps"], 10.0)
        self.assertAlmostEqual(alpha_kwargs["max_participation_rate"], 0.05)

    def test_gate_does_not_allow_paper_when_only_negative_direction_is_significant(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            def ingest_runner(**kwargs):
                return {"source": kwargs["source"], "market": kwargs["market"], "processed_rows": 20}

            def alpha_factory_runner(**_):
                return {
                    "summary": {
                        "hypothesis_count": 9,
                        "completed": 9,
                        "adjusted_significant": 1,
                        "paper_eligible": 0,
                        "rejected_after_multiple_testing": 8,
                    },
                    "candidate_leaderboard": [
                        {
                            "case_id": "CN_turnover_rate_top1_cost5_reb1",
                            "factor_source": "tushare_daily_basic",
                            "adjusted_ic_p_value": 0.001,
                            "passes_adjusted_ic_p_value": True,
                            "significance_status": "significant_negative",
                            "paper_candidate_allowed": False,
                        }
                    ],
                }

            pack = run_tushare_alpha_factory_gate(
                report_dir=root / "gate",
                data_root=root / "data",
                source="tushare-fixture",
                market="CN",
                execute=True,
                readiness={"source": "tushare-fixture", "ready": True, "missing": []},
                ingest_runner=ingest_runner,
                alpha_factory_runner=alpha_factory_runner,
            )

        self.assertEqual(pack["status"], "no_paper_eligible_alpha")
        self.assertFalse(pack["decision"]["paper_candidate_allowed"])
        self.assertEqual(pack["decision"]["adjusted_significant_candidates"], 1)
        self.assertEqual(pack["decision"]["paper_eligible_candidates"], 0)
        self.assertIn("no_directionally_valid_paper_alpha", pack["decision"]["blockers"])


if __name__ == "__main__":
    unittest.main()
