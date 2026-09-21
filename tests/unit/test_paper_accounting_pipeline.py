"""Synthetic end-to-end checks; no market-return or broker calls."""
import copy
import hashlib
import io
import json
import tempfile
import unittest
import pandas as pd
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from quant_robot.data.fixtures import load_demo_market_bars
from quant_robot.paper.accounting_evidence import paper_accounting_blockers
from quant_robot.paper.economics import VALUATION_MODEL
from quant_robot.promotion.gate import PromotionGateConfig, _paper_summary
from scripts.run_daily_ops import run_daily_ops
from scripts.run_paper_batch import load_paper_batch_config, _run_profile_attempt as batch_attempt
from scripts.run_paper_profile_optimizer import load_paper_profile_optimizer_config, _run_profile_attempt as optimizer_attempt
from scripts.run_paper_simulation import main, run_simulation


def candidate():
    return {"case_id": "CN_ETF_momentum_2_top1_cost5_reb1", "market": "CN_ETF",
            "factor_name": "momentum_2", "factor_source": "technical", "factor_windows": "(2,)",
            "top_n": 1, "cost_bps": 5, "rebalance_interval": 1}


class PaperAccountingPipelineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        bars = load_demo_market_bars()
        bars = bars[bars.market.eq("CN_ETF")]
        self.actions = self.write("actions", {"schema_version": 1, "source_ref": "synthetic fixture only",
            "coverage_start": str(bars.date.min()), "coverage_end": str(bars.date.max()),
            "asset_ids": sorted(set(bars.asset_id)), "events": []})
        self.fingerprint = hashlib.sha256(self.actions.read_bytes()).hexdigest()

    def write(self, name, payload):
        path = self.root / (name + ".json")
        path.write_text(json.dumps(payload), encoding="utf-8")
        return path

    def assert_evidence(self, request):
        self.assertEqual(request["corporate_actions_fingerprint"], self.fingerprint)
        self.assertEqual(request["valuation_model"], VALUATION_MODEL)
        self.assertEqual(request["execution_economics"]["corporate_actions_fingerprint"], self.fingerprint)
        self.assertEqual(request["corporate_actions_path"], str(self.actions))

    def test_public_cli_writes_action_identity_and_unverified_source_evidence(self):
        output = self.root / "cli"
        args = ["run_paper_simulation", "--source", "fixture", "--market", "CN_ETF",
                "--factor", "momentum_2", "--factor-windows", "2", "--top-n", "1",
                "--corporate-actions", str(self.actions), "--output-dir", str(output)]
        with patch("sys.argv", args), redirect_stdout(io.StringIO()):
            main()
        manifest = json.loads((output / "manifest.json").read_text())
        self.assert_evidence(manifest["request"])
        self.assertFalse(manifest["accounting"]["source_audit_verified"])
        self.assertTrue(manifest["accounting"]["declared_coverage_validated"])
        self.assertTrue((output / "corporate_action_events.csv").exists())
        self.assertGreater(len(pd.read_csv(output / "fills.csv")), 0)

    def test_batch_and_optimizer_load_and_preserve_action_file_identity(self):
        config_path = self.write("config", {"source": "fixture", "factor_windows": [2],
            "corporate_actions_path": str(self.actions), "output_dir": str(self.root / "attempts")})
        batch = batch_attempt(candidate(), load_paper_batch_config(config_path), {"profile_id": "synthetic"})
        self.assertEqual(batch["status"], "completed", batch)
        self.assert_evidence(batch["result"]["request"])
        attempt = optimizer_attempt(candidate(), {"profile_id": "synthetic"},
                                    load_paper_profile_optimizer_config(config_path))
        self.assertIsNone(attempt["error"], attempt)
        self.assertEqual(attempt["execution_economics"]["corporate_actions_fingerprint"], self.fingerprint)
        self.assertEqual(attempt["corporate_actions_path"], str(self.actions))

    def test_daily_ops_inherits_frozen_source_and_rejects_changed_file(self):
        result = run_simulation(source="fixture", market="CN_ETF", top_n=1,
                                factor_windows=(2,), corporate_actions_path=self.actions)
        promotion = self.write("promotion", {"selected_candidate": {**candidate(), "promotion_status": "paper_ready"}})
        profile = self.write("profile", {"selected_profile": {"profile_id": "synthetic",
            "execution_economics": result["request"]["execution_economics"],
            "corporate_actions_path": str(self.actions)}})
        kwargs = {"promotion_review": promotion, "paper_profile_pack": profile,
                  "readiness_board": self.write("readiness", {}),
                  "signal_snapshot": self.write("signal", {"signal_date": "2024-01-10",
                      "as_of_date": "2024-01-10", "targets": [], "rebalance_plan": []}),
                  "source": "fixture", "run_date": "2024-01-10"}
        run_daily_ops(**kwargs, output_dir=self.root / "daily")
        manifest = json.loads((self.root / "daily/paper_simulation/manifest.json").read_text())
        self.assert_evidence(manifest["request"])
        changed = json.loads(self.actions.read_text())
        changed["source_ref"] = "a different source version"
        self.actions.write_text(json.dumps(changed), encoding="utf-8")
        cached = self.write("cached", manifest)
        # A historical replay without an explicit new source remains possible.
        run_daily_ops(**kwargs, paper_simulation=cached, output_dir=self.root / "historical")
        with self.assertRaisesRegex(ValueError, "corporate.actions.*fingerprint"):
            run_daily_ops(**kwargs, paper_simulation=cached, corporate_actions_path=self.actions,
                          output_dir=self.root / "changed_cached")
        with self.assertRaisesRegex(ValueError, "execution_economics"):
            run_daily_ops(**kwargs, output_dir=self.root / "changed")

    def test_unverified_source_blocks_promotion_even_with_matching_fee_contract(self):
        result = run_simulation(source="fixture", market="CN_ETF", top_n=1,
                                factor_windows=(2,), corporate_actions_path=self.actions)
        # Synthetic declarations isolate the accounting gate; these are never real research evidence.
        row = {**candidate(), "universe_id": "synthetic", "data_fingerprint": "synthetic",
               "start_date": "2024-01-01", "end_date": "2024-01-31",
               "execution_economics": result["request"]["execution_economics"]}
        manifest = {"data_mode": "research", "request": {**result["request"], **row},
                    "accounting": result["accounting"],
                    "metrics": {"total_return": 0.1, "sharpe": 1, "max_equity_drawdown": -0.02}}
        summary = _paper_summary(row, [manifest], PromotionGateConfig(
            require_paper_provenance=True, require_execution_economics=True, require_execution_accounting=True))
        self.assertIn("paper_execution_accounting_source_unverified", summary["blocking"])
        tampered = copy.deepcopy(manifest)
        tampered["accounting"]["corporate_actions_fingerprint"] = "0" * 64
        self.assertIn("paper_corporate_action_fingerprint_mismatch", paper_accounting_blockers(tampered))
        self.assertEqual(paper_accounting_blockers({}), ["paper_execution_accounting_missing"])
