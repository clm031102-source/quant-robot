import unittest

from quant_robot.ops.market_regime_coverage import build_market_regime_coverage_pack


class MarketRegimeCoverageTests(unittest.TestCase):
    def test_pack_clears_when_multiple_market_regimes_are_observed(self):
        pack = build_market_regime_coverage_pack(
            [
                {"date": "2026-01-01", "regime_momentum": 0.06},
                {"date": "2026-01-02", "regime_momentum": 0.01},
                {"date": "2026-01-03", "regime_momentum": -0.05},
                {"date": "2026-01-04", "regime_momentum": 0.04},
            ],
            min_regimes=3,
            min_rows_per_regime=1,
        )

        self.assertEqual(pack["stage"], "phase_6_0_market_regime_coverage")
        self.assertEqual(pack["status"], "sufficient")
        self.assertTrue(pack["decision"]["market_regime_coverage_cleared"])
        self.assertEqual(pack["summary"]["covered_regimes"], 3)
        self.assertEqual(set(pack["summary"]["regimes"]), {"bull", "bear", "sideways"})
        self.assertFalse(pack["live_boundary_allowed"])
        self.assertIn("No broker", pack["safety"])
        self.assertIn("Market Regime Coverage", pack["markdown"])

    def test_pack_blocks_when_regime_sample_is_one_sided(self):
        pack = build_market_regime_coverage_pack(
            [
                {"date": "2026-01-01", "regime_momentum": 0.06},
                {"date": "2026-01-02", "regime_momentum": 0.04},
                {"date": "2026-01-03", "regime_momentum": 0.03},
            ],
            min_regimes=2,
            min_rows_per_regime=1,
        )

        self.assertEqual(pack["status"], "insufficient")
        self.assertFalse(pack["decision"]["market_regime_coverage_cleared"])
        self.assertEqual(pack["summary"]["covered_regimes"], 1)
        self.assertIn("market_regimes_below_minimum", pack["decision"]["blockers"])

    def test_pack_deduplicates_repeated_case_regime_rows_before_counting_coverage(self):
        repeated_rows = [{"date": "2026-01-01", "regime_momentum": 0.06} for _ in range(10)]

        pack = build_market_regime_coverage_pack(
            repeated_rows,
            min_regimes=1,
            min_rows_per_regime=2,
        )

        self.assertEqual(pack["summary"]["rows"], 1)
        self.assertEqual(pack["summary"]["regime_counts"], {"bull": 1})
        self.assertEqual(pack["status"], "insufficient")
        self.assertIn("market_regimes_below_minimum", pack["decision"]["blockers"])

    def test_pack_blocks_when_allowed_or_blocked_regime_filter_states_are_missing(self):
        pack = build_market_regime_coverage_pack(
            [
                {"date": "2026-01-01", "regime_momentum": 0.05, "regime_allowed": True},
                {"date": "2026-01-02", "regime_momentum": -0.04, "regime_allowed": True},
            ],
            min_regimes=2,
            min_rows_per_regime=1,
            min_allowed_rows=1,
            min_blocked_rows=1,
        )

        self.assertEqual(pack["summary"]["allowed_rows"], 2)
        self.assertEqual(pack["summary"]["blocked_rows"], 0)
        self.assertEqual(pack["status"], "insufficient")
        self.assertIn("market_regime_blocked_rows_below_minimum", pack["decision"]["blockers"])

    def test_pack_blocks_when_signal_window_allowed_rows_are_missing(self):
        pack = build_market_regime_coverage_pack(
            [
                {
                    "date": "2026-01-01",
                    "regime_momentum": 0.05,
                    "regime_allowed": True,
                    "signal_window_member": False,
                },
                {
                    "date": "2026-01-02",
                    "regime_momentum": -0.04,
                    "regime_allowed": False,
                    "signal_window_member": True,
                },
                {
                    "date": "2026-01-03",
                    "regime_momentum": -0.03,
                    "regime_allowed": False,
                    "signal_window_member": True,
                },
            ],
            min_regimes=2,
            min_rows_per_regime=1,
            min_allowed_rows=1,
            min_blocked_rows=1,
            min_signal_window_allowed_rows=1,
            min_signal_window_blocked_rows=1,
        )

        self.assertEqual(pack["summary"]["allowed_rows"], 1)
        self.assertEqual(pack["summary"]["blocked_rows"], 2)
        self.assertEqual(pack["summary"]["signal_window_rows"], 2)
        self.assertEqual(pack["summary"]["signal_window_allowed_rows"], 0)
        self.assertEqual(pack["summary"]["signal_window_blocked_rows"], 2)
        self.assertEqual(pack["status"], "insufficient")
        self.assertIn("market_regime_signal_window_allowed_rows_below_minimum", pack["decision"]["blockers"])


if __name__ == "__main__":
    unittest.main()
