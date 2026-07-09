import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.ops.lpr_macro_regime_state_prescreen import (
    build_lpr_macro_regime_state_frame,
    run_lpr_macro_regime_state_prescreen,
)
from quant_robot.storage.dataset_store import DatasetStore


def _macro_rates(rows: list[dict[str, object]]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "date": row["date"],
                "available_date": row["available_date"],
                "market": "CN",
                "source": "synthetic",
                "lpr_1y": row.get("lpr_1y", 3.0),
                "lpr_5y": row.get("lpr_5y", 3.5),
                "shibor_3m": row.get("shibor_3m", 2.0),
            }
            for row in rows
        ]
    )


def _ready_gate(path: Path) -> Path:
    payload = {
        "stage": "factor_batch_readiness_gate",
        "generated_at": pd.Timestamp.today().date().isoformat(),
        "status": "ready",
        "decision": {
            "factor_batch_ready": True,
            "research_screen_allowed": True,
            "portfolio_grid_allowed": False,
            "promotion_allowed": False,
            "blockers": [],
        },
        "live_boundary_allowed": False,
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _candidate_plan(path: Path) -> Path:
    payload = {
        "candidates": [
            {
                "factor_name": "lpr_shibor_credit_gap_regime_60",
                "family": "external_macro_lpr_regime",
                "registration_status": "pre_registered",
                "portfolio_backtest_allowed": False,
                "promotion_allowed": False,
            },
            {
                "factor_name": "lpr_term_premium_easing_regime_60",
                "family": "external_macro_lpr_regime",
                "registration_status": "blocked_by_state_degenerate",
                "portfolio_backtest_allowed": False,
                "promotion_allowed": False,
            },
        ]
    }
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


class LPRMacroRegimeStatePrescreenTests(unittest.TestCase):
    def test_state_frame_uses_available_date_and_classifies_gap_change(self) -> None:
        frame = _macro_rates(
            [
                {"date": "2024-01-01", "available_date": "2024-01-02", "shibor_3m": 2.00},
                {"date": "2024-01-02", "available_date": "2024-01-03", "shibor_3m": 1.90},
                {"date": "2024-01-03", "available_date": "2024-01-04", "shibor_3m": 1.70},
                {"date": "2024-01-04", "available_date": "2024-01-05", "shibor_3m": 2.10},
            ]
        )

        states = build_lpr_macro_regime_state_frame(frame, lookback_days=2, min_abs_gap_change=0.05)

        by_available = dict(zip(states["available_date"].dt.strftime("%Y-%m-%d"), states["lpr_shibor_gap_state"]))
        self.assertEqual(by_available["2024-01-02"], "insufficient_lookback")
        self.assertEqual(by_available["2024-01-04"], "gap_widening")
        self.assertEqual(by_available["2024-01-05"], "gap_narrowing")
        self.assertTrue((states["signal_date"] == states["available_date"]).all())

    def test_prescreen_excludes_final_holdout_and_never_allows_promotion(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rows = []
            for idx, available in enumerate(pd.date_range("2025-12-22", periods=12, freq="D")):
                rows.append(
                    {
                        "date": (available - pd.Timedelta(days=1)).strftime("%Y-%m-%d"),
                        "available_date": available.strftime("%Y-%m-%d"),
                        "shibor_3m": 2.0 - idx * 0.08,
                    }
                )
            DatasetStore(root).write_frame(
                _macro_rates(rows),
                "processed/external_macro_rates",
                {"frequency": "1d", "market": "CN", "year": "2025"},
            )

            result = run_lpr_macro_regime_state_prescreen(
                processed_root=root,
                readiness_gate_path=_ready_gate(root / "ready.json"),
                candidate_plan_path=_candidate_plan(root / "plan.json"),
                output_dir=root / "out",
                analysis_start_date="2025-12-22",
                analysis_end_date="2026-01-10",
                lookback_days=2,
                min_abs_gap_change=0.01,
                min_state_dates=1,
                min_nonzero_gap_changes=1,
            )

        self.assertTrue(result["summary"]["passes"])
        self.assertEqual(result["data_window"]["last_available_date"], "2025-12-31")
        self.assertGreater(result["holdout_policy"]["excluded_final_holdout_rows"], 0)
        self.assertFalse(result["decision"]["portfolio_grid_allowed"])
        self.assertFalse(result["decision"]["promotion_allowed"])
        self.assertFalse(result["live_boundary_allowed"])

    def test_prescreen_blocks_degenerate_gap_state(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            rows = [
                {
                    "date": (pd.Timestamp("2025-01-01") + pd.Timedelta(days=idx)).strftime("%Y-%m-%d"),
                    "available_date": (pd.Timestamp("2025-01-02") + pd.Timedelta(days=idx)).strftime("%Y-%m-%d"),
                    "shibor_3m": 2.0,
                }
                for idx in range(8)
            ]
            DatasetStore(root).write_frame(
                _macro_rates(rows),
                "processed/external_macro_rates",
                {"frequency": "1d", "market": "CN", "year": "2025"},
            )

            result = run_lpr_macro_regime_state_prescreen(
                processed_root=root,
                readiness_gate_path=_ready_gate(root / "ready.json"),
                candidate_plan_path=_candidate_plan(root / "plan.json"),
                output_dir=root / "out",
                analysis_start_date="2025-01-01",
                analysis_end_date="2025-01-31",
                lookback_days=2,
                min_abs_gap_change=0.01,
                min_state_dates=1,
                min_nonzero_gap_changes=1,
            )

        candidate = result["candidate_results"][0]
        self.assertFalse(result["summary"]["passes"])
        self.assertFalse(candidate["state_ready_for_regime_control"])
        self.assertIn("nonzero_gap_change_below_threshold", candidate["blockers"])
        self.assertIn("state_distribution_degenerate", candidate["blockers"])


if __name__ == "__main__":
    unittest.main()
