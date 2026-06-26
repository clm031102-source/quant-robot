import json
import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.ops.financial_pit_post_announcement_drift_matrix_label_smoke import (
    build_financial_pit_post_announcement_drift_matrix_label_smoke,
    compute_financial_pit_post_announcement_drift_factor_frame,
    write_financial_pit_post_announcement_drift_matrix_label_smoke,
)
from quant_robot.ops.financial_pit_post_announcement_drift_preregistration import (
    build_financial_pit_post_announcement_drift_preregistration,
    write_financial_pit_post_announcement_drift_preregistration,
)
from tests.unit.test_financial_pit_post_announcement_drift_preregistration import (
    _financial_rows,
    _financial_rows_with_2026,
    _seed,
    _write_bars,
    _write_financial,
)


class FinancialPitPostAnnouncementDriftMatrixLabelSmokeTests(unittest.TestCase):
    def test_builds_factor_matrix_on_reaction_available_date_and_aligned_forward_labels(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            financial_root = root / "financial"
            bars_root = root / "bars"
            prereg_output = root / "prereg"
            seed_path = root / "seed.json"
            _write_financial(financial_root, _financial_rows())
            _write_bars(bars_root, _bar_rows_for_label_window())
            seed_path.write_text(json.dumps(_seed()), encoding="utf-8")
            _write_preregistration(financial_root, bars_root, prereg_output, seed_path)

            result = build_financial_pit_post_announcement_drift_matrix_label_smoke(
                financial_root=financial_root,
                bars_roots=[bars_root],
                preregistration_json=prereg_output / "financial_pit_post_announcement_drift_preregistration.json",
                horizons=(5, 20),
                execution_lag=1,
                min_label_coverage=0.90,
            )

            self.assertTrue(result["summary"]["passes"])
            self.assertEqual(result["summary"]["active_candidate_count"], 3)
            self.assertEqual(result["summary"]["alignment_violation_rows"], 0)
            self.assertGreater(result["summary"]["factor_value_rows"], 0)
            self.assertGreater(result["summary"]["label_aligned_rows"], 0)
            self.assertGreaterEqual(result["summary"]["label_coverage"], 0.90)
            self.assertFalse(result["alignment_policy"]["same_day_event_reaction_trading_allowed"])
            self.assertFalse(result["promotion_policy"]["portfolio_backtest_allowed"])
            self.assertFalse(result["promotion_policy"]["promotion_allowed"])

            factor_frame = compute_financial_pit_post_announcement_drift_factor_frame(
                _financial_rows(),
                result["active_candidates"],
                _bar_rows_for_label_window(),
            )
            self.assertFalse(factor_frame.empty)
            self.assertTrue((factor_frame["date"] == factor_frame["reaction_available_date"]).all())
            self.assertTrue((factor_frame["reaction_available_date"] > factor_frame["event_reaction_date"]).all())
            self.assertTrue((factor_frame["event_reaction_date"] > factor_frame["ann_date"]).all())

    def test_blocks_unknown_active_candidate_formula(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            financial_root = root / "financial"
            bars_root = root / "bars"
            prereg_path = root / "prereg.json"
            _write_financial(financial_root, _financial_rows())
            _write_bars(bars_root, _bar_rows_for_label_window())
            prereg_path.write_text(
                json.dumps(
                    {
                        "candidates": [
                            {
                                "factor_name": "pead_unknown_future_leakage_probe",
                                "family": "financial_pit_post_announcement_drift",
                                "registration_status": "pre_registered",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            result = build_financial_pit_post_announcement_drift_matrix_label_smoke(
                financial_root=financial_root,
                bars_roots=[bars_root],
                preregistration_json=prereg_path,
                min_label_coverage=0.90,
            )

            self.assertFalse(result["summary"]["passes"])
            self.assertEqual(result["summary"]["unknown_active_candidate_count"], 1)
            self.assertIn("unknown_active_candidate_formula", result["summary"]["blockers"])

    def test_blocks_when_forward_labels_do_not_cover_factor_dates(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            financial_root = root / "financial"
            bars_root = root / "bars"
            prereg_output = root / "prereg"
            seed_path = root / "seed.json"
            _write_financial(financial_root, _financial_rows())
            _write_bars(bars_root, _bar_rows_without_enough_forward_history())
            seed_path.write_text(json.dumps(_seed()), encoding="utf-8")
            _write_preregistration(financial_root, bars_root, prereg_output, seed_path, allow_not_ready=True)

            result = build_financial_pit_post_announcement_drift_matrix_label_smoke(
                financial_root=financial_root,
                bars_roots=[bars_root],
                preregistration_json=prereg_output / "financial_pit_post_announcement_drift_preregistration.json",
                horizons=(5, 20),
                execution_lag=1,
                min_label_coverage=0.90,
            )

            self.assertFalse(result["summary"]["passes"])
            self.assertIn("label_coverage_below_threshold", result["summary"]["blockers"])

    def test_excludes_final_holdout_dates_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            financial_root = root / "financial"
            bars_root = root / "bars"
            prereg_output = root / "prereg"
            seed_path = root / "seed.json"
            _write_financial(financial_root, _financial_rows_with_2026())
            _write_bars(bars_root, _bar_rows_with_2026_for_label_window())
            seed_path.write_text(json.dumps(_seed()), encoding="utf-8")
            _write_preregistration(financial_root, bars_root, prereg_output, seed_path)

            result = build_financial_pit_post_announcement_drift_matrix_label_smoke(
                financial_root=financial_root,
                bars_roots=[bars_root],
                preregistration_json=prereg_output / "financial_pit_post_announcement_drift_preregistration.json",
                horizons=(5, 20),
                execution_lag=1,
                min_label_coverage=0.90,
            )

            self.assertTrue(result["summary"]["passes"])
            self.assertEqual(result["holdout_policy"]["final_holdout_included"], False)
            self.assertLessEqual(result["summary"]["max_signal_date"], "2025-12-31")
            self.assertLessEqual(result["summary"]["max_factor_date"], "2025-12-31")
            self.assertLessEqual(result["summary"]["max_label_date"], "2025-12-31")

    def test_write_outputs_json_markdown_and_candidate_summary(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            financial_root = root / "financial"
            bars_root = root / "bars"
            prereg_output = root / "prereg"
            output_dir = root / "output"
            seed_path = root / "seed.json"
            _write_financial(financial_root, _financial_rows())
            _write_bars(bars_root, _bar_rows_for_label_window())
            seed_path.write_text(json.dumps(_seed()), encoding="utf-8")
            _write_preregistration(financial_root, bars_root, prereg_output, seed_path)

            result = build_financial_pit_post_announcement_drift_matrix_label_smoke(
                financial_root=financial_root,
                bars_roots=[bars_root],
                preregistration_json=prereg_output / "financial_pit_post_announcement_drift_preregistration.json",
            )
            write_financial_pit_post_announcement_drift_matrix_label_smoke(output_dir, result)

            self.assertTrue((output_dir / "financial_pit_post_announcement_drift_matrix_label_smoke.json").exists())
            self.assertTrue((output_dir / "financial_pit_post_announcement_drift_matrix_label_smoke.md").exists())
            self.assertTrue((output_dir / "financial_pit_post_announcement_drift_matrix_candidate_summary.csv").exists())


def _write_preregistration(
    financial_root: Path,
    bars_root: Path,
    output_dir: Path,
    seed_path: Path,
    allow_not_ready: bool = False,
) -> None:
    result = build_financial_pit_post_announcement_drift_preregistration(
        financial_root=financial_root,
        bars_roots=[bars_root],
        candidate_seed_json=seed_path,
        min_assets=3,
        min_signal_dates=2,
        min_event_reaction_coverage=0.20 if allow_not_ready else 0.80,
    )
    write_financial_pit_post_announcement_drift_preregistration(output_dir, result)


def _bar_rows_for_label_window() -> pd.DataFrame:
    return _make_bar_rows(pd.bdate_range("2024-01-02", "2024-05-31"))


def _bar_rows_without_enough_forward_history() -> pd.DataFrame:
    return _make_bar_rows(pd.bdate_range("2024-01-02", "2024-04-04"))


def _bar_rows_with_2026_for_label_window() -> pd.DataFrame:
    return pd.concat(
        [
            _bar_rows_for_label_window(),
            _make_bar_rows(pd.bdate_range("2026-05-06", "2026-06-30"), price_base=20.0),
        ],
        ignore_index=True,
    )


def _make_bar_rows(dates: pd.DatetimeIndex, price_base: float = 10.0) -> pd.DataFrame:
    rows = []
    for asset_index, asset_id in enumerate(["CN_XSHE_000001", "CN_XSHG_600000", "CN_XSHE_000002"]):
        for day_index, day in enumerate(dates):
            rows.append(
                {
                    "date": day,
                    "asset_id": asset_id,
                    "market": "CN",
                    "open": price_base + asset_index + day_index * 0.03,
                    "close": price_base + asset_index + day_index * 0.03 + 0.12,
                    "adj_close": price_base + asset_index + day_index * 0.03 + 0.12,
                    "volume": 1000000 + asset_index * 1000 + day_index * 10,
                    "amount": 20000000 + asset_index * 1000 + day_index * 100,
                }
            )
    return pd.DataFrame(rows)


if __name__ == "__main__":
    unittest.main()
