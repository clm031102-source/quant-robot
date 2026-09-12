import copy
import json
import tempfile
import unittest
from pathlib import Path

from quant_robot.promotion.gate import PromotionGateConfig, _paper_summary, build_promotion_report
from quant_robot.ops.promotion_console import build_promotion_operations_console
from scripts.run_daily_ops import run_daily_ops, _execution_params


def economics():
    return {
        "schema_version": 3, "commission_model": "per_order_minimum_v1",
        "valuation_model": "daily_raw_close_cash_actions_v1", "corporate_actions_fingerprint": None,
        "initial_cash": 3000.0, "commission_bps": 0.5, "minimum_commission": 5.0,
        "slippage_bps": 10.0, "market_impact_bps": 0.0, "max_participation_rate": 0.01,
    }


class PaperExecutionEconomicsTests(unittest.TestCase):
    def evidence(self):
        row = {
            "case_id": "CN_ETF_momentum_2_top1_cost5_reb1", "market": "CN_ETF",
            "factor_name": "momentum_2", "factor_source": "technical", "top_n": 1,
            "factor_windows": [2],
            "cost_bps": 5, "rebalance_interval": 1, "universe_id": "test-universe",
            "data_fingerprint": "same-frozen-data", "start_date": "2024-01-01",
            "end_date": "2024-01-31", "execution_economics": economics(),
        }
        request = {**copy.deepcopy(row), **economics()}
        paper = {"data_mode": "research", "request": request,
                 "metrics": {"total_return": 0.1, "sharpe": 1, "max_equity_drawdown": -0.02}}
        return row, paper

    def summary(self, row, paper):
        return _paper_summary(row, [paper], PromotionGateConfig(
            require_paper_provenance=True, require_execution_economics=True,
        ))

    def test_identical_frozen_economics_can_match(self):
        self.assertTrue(self.summary(*self.evidence())["paper_matched"])

    def test_legacy_optimizer_config_preserves_its_costs_and_capital(self):
        legacy = {key: value for key, value in economics().items()
                  if key not in {"schema_version", "commission_model"}}
        actual, frozen = _execution_params({"config": legacy}, {}, {}, None)
        self.assertEqual(actual, economics())
        self.assertFalse(frozen)

    def test_verified_economics_survive_promotion_and_operations_console(self):
        row, paper = self.evidence()
        row.update({"validation_status": "accepted", "data_mode": "research", "test_trades": 80,
                    "test_sharpe": 0.8, "test_relative_return": 0.06, "test_max_drawdown": -0.12,
                    "stability_score": 0.7})
        report = build_promotion_report(
            walk_forward_rows=[row], paper_manifest=paper,
            config=PromotionGateConfig(require_paper_provenance=True, require_execution_economics=True),
        )
        candidate = report["candidates"][0]
        self.assertEqual(candidate["promotion_status"], "paper_ready")
        self.assertEqual(candidate.get("execution_economics"), economics())
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "promotion.json"
            path.write_text(json.dumps(report))
            console = build_promotion_operations_console(path)
        self.assertEqual(console["top_candidate"].get("execution_economics"), economics())
        actual, frozen = _execution_params({}, {}, console["top_candidate"], None)
        self.assertTrue(frozen)
        self.assertEqual(actual, economics())
        with self.assertRaisesRegex(ValueError, "do not match"):
            _execution_params({}, {"execution_economics": {**economics(), "minimum_commission": 0}},
                              console["top_candidate"], None)

    def test_changed_fees_or_capital_cannot_reuse_the_same_case(self):
        for field, value in [("minimum_commission", 0), ("commission_bps", 5),
                             ("slippage_bps", 0), ("market_impact_bps", 10),
                             ("max_participation_rate", 0.1), ("initial_cash", 100000)]:
            with self.subTest(field=field):
                row, paper = self.evidence()
                paper["request"][field] = value
                paper["request"]["execution_economics"][field] = value
                result = self.summary(row, paper)
                self.assertFalse(result["paper_matched"])
                self.assertIn("paper_execution_economics_missing_or_mismatched", result["blocking"])

    def test_manifest_declaration_must_match_actual_request_parameters(self):
        row, paper = self.evidence()
        paper["request"]["minimum_commission"] = 0
        self.assertFalse(self.summary(row, paper)["paper_matched"])

    def test_missing_or_nonfinite_economics_do_not_become_zero_cost_evidence(self):
        for value in [None, {**economics(), "minimum_commission": float("nan")},
                      {**economics(), "minimum_commission": -1},
                      {**economics(), "unmodeled_broker_fee": 5},
                      {**economics(), "schema_version": True}]:
            with self.subTest(value=value):
                row, paper = self.evidence()
                paper["request"]["execution_economics"] = value
                self.assertFalse(self.summary(row, paper)["paper_matched"])

    def test_old_rebalance_only_valuation_cannot_be_reused_as_daily_evidence(self):
        row, paper = self.evidence()
        for item in (row["execution_economics"], paper["request"]["execution_economics"]):
            item["schema_version"] = 1
            item.pop("valuation_model", None)
        self.assertFalse(self.summary(row, paper)["paper_matched"])

    def test_daily_ops_uses_selected_profile_capital_and_fees(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            row, _ = self.evidence()
            files = {
                "promotion": {"selected_candidate": {**row, "promotion_status": "paper_ready"}},
                "readiness": {},
                "profile": {"selected_profile": {"profile_id": "fees", "execution_economics": economics()}},
                "signal": {"signal_date": "2024-01-10", "as_of_date": "2024-01-10", "targets": [], "rebalance_plan": []},
            }
            for name, payload in files.items():
                (root / (name + ".json")).write_text(json.dumps(payload))
            run_daily_ops(
                promotion_review=root / "promotion.json", readiness_board=root / "readiness.json",
                paper_profile_pack=root / "profile.json", signal_snapshot=root / "signal.json",
                source="fixture", output_dir=root / "out", run_date="2024-01-10",
            )
            manifest = json.loads((root / "out/paper_simulation/manifest.json").read_text())
            cached = root / "cached.json"
            cached.write_text(json.dumps(manifest))
            run_daily_ops(
                promotion_review=root / "promotion.json", readiness_board=root / "readiness.json",
                paper_profile_pack=root / "profile.json", signal_snapshot=root / "signal.json",
                paper_simulation=cached, output_dir=root / "cached_out", run_date="2024-01-10",
            )
            stale = copy.deepcopy(manifest)
            stale["request"]["minimum_commission"] = 0
            stale["request"]["execution_economics"]["minimum_commission"] = 0
            cached.write_text(json.dumps(stale))
            with self.assertRaisesRegex(ValueError, "execution_economics"):
                run_daily_ops(
                    promotion_review=root / "promotion.json", readiness_board=root / "readiness.json",
                    paper_profile_pack=root / "profile.json", signal_snapshot=root / "signal.json",
                    paper_simulation=cached, output_dir=root / "stale_out", run_date="2024-01-10",
                )
            with self.assertRaisesRegex(ValueError, "portfolio_value"):
                run_daily_ops(
                    promotion_review=root / "promotion.json", readiness_board=root / "readiness.json",
                    paper_profile_pack=root / "profile.json", signal_snapshot=root / "signal.json",
                    source="fixture", portfolio_value=100000, output_dir=root / "wrong_capital",
                )
        self.assertEqual(manifest["request"]["initial_cash"], 3000)
        self.assertEqual(manifest["request"]["commission_bps"], 0.5)
        self.assertEqual(manifest["request"]["minimum_commission"], 5)
        self.assertEqual(manifest["request"]["execution_economics"], economics())
