from __future__ import annotations

import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

from quant_robot.ops.simulation_shortlist_blend_audit import (
    build_simulation_shortlist_blend_audit,
    write_simulation_shortlist_blend_audit,
)


class SimulationShortlistBlendAuditTest(unittest.TestCase):
    def test_blend_search_finds_diversifying_combination(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            left = root / "left.csv"
            right = root / "right.csv"
            _write_returns(left, [0.10, -0.05, 0.10, -0.05, 0.10, -0.05])
            _write_returns(right, [-0.05, 0.10, -0.05, 0.10, -0.05, 0.10])

            audit = build_simulation_shortlist_blend_audit(
                return_sources={"left": left, "right": right},
                periods_per_year=12.0,
                holding_period=1,
                weight_step=0.5,
                max_components=2,
                max_drawdown_floor=-0.30,
            )

            best = audit["rows"][0]
            self.assertEqual(best["case_id"], "left_50__right_50")
            self.assertEqual(best["selection_status"], "blend_candidate")
            self.assertGreater(best["annualized_return"], best["best_component_annualized_return"])
            self.assertGreater(best["max_drawdown"], best["best_component_max_drawdown"])

    def test_blend_blocks_drawdown_below_floor(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            path = root / "bad.csv"
            _write_returns(path, [0.50, -0.45, 0.10])

            audit = build_simulation_shortlist_blend_audit(
                return_sources={"bad": path},
                periods_per_year=12.0,
                holding_period=1,
                weight_step=0.5,
                max_components=1,
                max_drawdown_floor=-0.30,
            )

            self.assertEqual(audit["summary"]["pass_case_count"], 0)
            self.assertEqual(audit["rows"][0]["selection_status"], "blocked")
            self.assertIn("max_drawdown_below_floor", audit["rows"][0]["blockers"])

    def test_writer_exports_json_csv_and_best_return_stream(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            left = root / "left.csv"
            right = root / "right.csv"
            output = root / "out"
            _write_returns(left, [0.02, 0.01, -0.01, 0.03])
            _write_returns(right, [0.01, 0.02, 0.00, 0.02])

            audit = build_simulation_shortlist_blend_audit(
                return_sources={"left": left, "right": right},
                periods_per_year=12.0,
                holding_period=1,
                weight_step=0.5,
                max_components=2,
            )
            write_simulation_shortlist_blend_audit(output, audit)

            self.assertTrue((output / "simulation_shortlist_blend_audit.json").exists())
            self.assertTrue((output / "simulation_shortlist_blend_rows.csv").exists())
            self.assertTrue((output / "simulation_shortlist_blend_correlations.csv").exists())
            self.assertTrue((output / "best_blend_period_returns.csv").exists())
            payload = json.loads((output / "simulation_shortlist_blend_audit.json").read_text(encoding="utf-8"))
            self.assertEqual(payload["summary"]["best_case_id"], audit["summary"]["best_case_id"])
            best_returns = pd.read_csv(output / "best_blend_period_returns.csv")
            self.assertEqual(best_returns.columns.tolist(), ["date", "period_return"])

    def test_blend_blocks_highly_correlated_multi_component_cases(self) -> None:
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            left = root / "left.csv"
            right = root / "right.csv"
            _write_returns(left, [0.03, 0.02, -0.01, 0.03, 0.02, 0.01])
            _write_returns(right, [0.03, 0.02, -0.01, 0.03, 0.02, 0.01])

            audit = build_simulation_shortlist_blend_audit(
                return_sources={"left": left, "right": right},
                periods_per_year=12.0,
                holding_period=1,
                weight_step=0.5,
                max_components=2,
                duplicate_correlation=0.98,
            )

            rows = {row["case_id"]: row for row in audit["rows"]}
            self.assertEqual(rows["left_50__right_50"]["selection_status"], "blocked")
            self.assertIn("high_component_return_correlation", rows["left_50__right_50"]["blockers"])
            self.assertEqual(rows["left_100"]["selection_status"], "blend_candidate")


def _write_returns(path: Path, returns: list[float]) -> None:
    dates = pd.date_range("2020-01-31", periods=len(returns), freq="ME")
    pd.DataFrame({"date": dates.strftime("%Y-%m-%d"), "period_return": returns}).to_csv(path, index=False)


if __name__ == "__main__":
    unittest.main()
