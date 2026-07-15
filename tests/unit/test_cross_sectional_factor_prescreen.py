import unittest

import pandas as pd

from quant_robot.research.cross_sectional_factor_prescreen import (
    CrossSectionalPrescreenThresholds,
    summarize_cross_sectional_factor_prescreen,
)


class CrossSectionalFactorPrescreenTests(unittest.TestCase):
    def test_stable_independent_signal_passes_shared_gate(self) -> None:
        factors, labels, references = _statistical_frames(mode="stable", years=(2021, 2022, 2023))

        result = summarize_cross_sectional_factor_prescreen(
            factors,
            labels,
            references,
            candidate_names=("candidate",),
            reference_names=("reference",),
            horizons=(5,),
            thresholds=_thresholds(),
        )

        self.assertEqual(result["summary"]["candidate_count"], 1)
        self.assertEqual(result["summary"]["reference_count"], 1)
        self.assertEqual(result["summary"]["test_count"], 1)
        row = result["results"][0]
        self.assertTrue(row["fdr_significant"])
        self.assertTrue(row["research_lead"])
        self.assertEqual(row["blockers"], [])
        self.assertGreater(row["mean_rank_ic"], 0.02)
        self.assertLess(row["max_abs_reference_correlation"], 0.85)

    def test_rank_equivalent_reference_blocks_signal(self) -> None:
        factors, labels, _ = _statistical_frames(mode="stable", years=(2021, 2022, 2023))
        references = factors.copy()
        references["factor_name"] = "reference"

        result = summarize_cross_sectional_factor_prescreen(
            factors,
            labels,
            references,
            candidate_names=("candidate",),
            reference_names=("reference",),
            horizons=(5,),
            thresholds=_thresholds(),
        )

        row = result["results"][0]
        self.assertGreaterEqual(row["max_abs_reference_correlation"], 0.999)
        self.assertFalse(row["research_lead"])
        self.assertIn("historical_reference_duplicate", row["blockers"])

    def test_missing_named_reference_fails_closed(self) -> None:
        factors, labels, references = _statistical_frames(mode="stable", years=(2021, 2022, 2023))

        result = summarize_cross_sectional_factor_prescreen(
            factors,
            labels,
            references,
            candidate_names=("candidate",),
            reference_names=("reference", "missing_reference"),
            horizons=(5,),
            thresholds=_thresholds(),
        )

        self.assertEqual(result["summary"]["missing_reference_names"], ["missing_reference"])
        self.assertFalse(result["results"][0]["research_lead"])
        self.assertIn("historical_reference_evidence_incomplete", result["results"][0]["blockers"])

    def test_duplicate_factor_rows_are_rejected(self) -> None:
        factors, labels, references = _statistical_frames(mode="stable", years=(2021, 2022, 2023))
        factors = pd.concat([factors, factors.iloc[[0]]], ignore_index=True)

        with self.assertRaisesRegex(ValueError, "duplicate factor rows"):
            summarize_cross_sectional_factor_prescreen(
                factors,
                labels,
                references,
                candidate_names=("candidate",),
                reference_names=("reference",),
                horizons=(5,),
                thresholds=_thresholds(),
            )


def _thresholds() -> CrossSectionalPrescreenThresholds:
    return CrossSectionalPrescreenThresholds(
        min_cross_section=20,
        min_ic_observations=15,
        min_year_ic_observations=5,
        min_usable_years=3,
    )


def _statistical_frames(*, mode: str, years: tuple[int, ...]) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    factor_rows = []
    label_rows = []
    reference_rows = []
    date_index = 0
    for year in years:
        for signal_date in pd.bdate_range(f"{year}-01-04", periods=8):
            for asset_index in range(30):
                asset_id = f"CN_ETF_XSHG_{510000 + asset_index}"
                signal = float(asset_index)
                if mode == "stable":
                    forward_score = signal + float((asset_index * (date_index % 5 + 1)) % 7) * 0.75
                else:
                    forward_score = float((asset_index * 11 + date_index * 7) % 31)
                reference_value = float((asset_index * 13 + date_index * 5) % 31)
                factor_rows.append(
                    {
                        "date": signal_date,
                        "asset_id": asset_id,
                        "market": "CN_ETF",
                        "factor_name": "candidate",
                        "factor_value": signal,
                        "lookback_window": 65,
                    }
                )
                label_rows.append(
                    {
                        "date": signal_date,
                        "asset_id": asset_id,
                        "market": "CN_ETF",
                        "horizon": 5,
                        "execution_lag": 1,
                        "forward_return": forward_score / 10_000.0,
                    }
                )
                reference_rows.append(
                    {
                        "date": signal_date,
                        "asset_id": asset_id,
                        "market": "CN_ETF",
                        "factor_name": "reference",
                        "factor_value": reference_value,
                        "lookback_window": 60,
                    }
                )
            date_index += 1
    return pd.DataFrame(factor_rows), pd.DataFrame(label_rows), pd.DataFrame(reference_rows)
