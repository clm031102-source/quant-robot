import json
import tempfile
import unittest
from pathlib import Path

from quant_robot.storage.dataset_store import DatasetStore
from scripts.run_daily_basic_non_price_public_carry_prescreen import (
    run_daily_basic_non_price_public_carry_prescreen_cli,
)
from tests.unit.test_daily_basic_non_price_public_carry_prescreen import (
    _synthetic_bars,
    _synthetic_daily_basic,
)


class DailyBasicNonPricePublicCarryPrescreenCliTests(unittest.TestCase):
    def test_cli_writes_json_markdown_results_coverage_and_ic_csvs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "processed"
            output = Path(tmp) / "output"
            store = DatasetStore(root)
            store.write_frame(
                _synthetic_bars(),
                "bars",
                {"frequency": "1d", "market": "CN", "year": "2025"},
            )
            store.write_frame(
                _synthetic_daily_basic(),
                "processed/factor_inputs",
                {"frequency": "1d", "market": "CN", "year": "2025"},
            )

            result = run_daily_basic_non_price_public_carry_prescreen_cli(
                bars_roots=[root],
                daily_basic_roots=[root],
                output_dir=output,
                analysis_end_date="2025-12-31",
                horizons=(5,),
                min_cross_section=20,
                min_ic_observations=4,
            )

            self.assertEqual(result["summary"]["candidate_count"], 10)
            self.assertTrue((output / "daily_basic_non_price_public_carry_prescreen.json").exists())
            self.assertTrue((output / "daily_basic_non_price_public_carry_prescreen.md").exists())
            self.assertTrue((output / "daily_basic_non_price_public_carry_prescreen_results.csv").exists())
            self.assertTrue((output / "daily_basic_non_price_public_carry_prescreen_field_coverage.csv").exists())
            self.assertTrue((output / "daily_basic_non_price_public_carry_prescreen_ic_observations.csv").exists())
            payload = json.loads(
                (output / "daily_basic_non_price_public_carry_prescreen.json").read_text(encoding="utf-8")
            )
            self.assertEqual(payload["summary"]["candidate_count"], result["summary"]["candidate_count"])
            self.assertFalse(payload["promotion_policy"]["promotion_allowed"])

    def test_cli_accepts_custom_candidate_spec_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "processed"
            output = Path(tmp) / "output"
            spec_path = Path(tmp) / "candidate_specs.json"
            store = DatasetStore(root)
            store.write_frame(
                _synthetic_bars(),
                "bars",
                {"frequency": "1d", "market": "CN", "year": "2025"},
            )
            store.write_frame(
                _synthetic_daily_basic(),
                "processed/factor_inputs",
                {"frequency": "1d", "market": "CN", "year": "2025"},
            )
            spec_path.write_text(
                json.dumps(
                    {
                        "candidate_specs": [
                            {
                                "factor_name": "daily_basic_valuation_reversion_dvratio_quality_60",
                                "family": "valuation_stability_coverage_repair",
                                "formula_template": (
                                    "0.45*cs_z(-pb_z_60)+0.30*cs_z(-ps_ttm_z_60)+0.25*cs_z(dv_ratio)"
                                ),
                                "direction": "higher_is_better",
                                "windows": [60],
                                "required_fields": ["pb", "ps_ttm", "dv_ratio"],
                                "economic_rationale": "Coverage-repaired valuation reversion.",
                                "public_reference_tags": ["value_reversion", "coverage_repair"],
                                "expected_failure_modes": ["field_substitution_changes_economics"],
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            result = run_daily_basic_non_price_public_carry_prescreen_cli(
                bars_roots=[root],
                daily_basic_roots=[root],
                candidate_spec_json=spec_path,
                output_dir=output,
                analysis_end_date="2025-12-31",
                horizons=(5,),
                min_cross_section=20,
                min_ic_observations=4,
            )

            self.assertEqual(result["summary"]["candidate_count"], 1)
            self.assertEqual(
                {row["factor_name"] for row in result["coverage_preflight"]["field_coverage"]},
                {"daily_basic_valuation_reversion_dvratio_quality_60"},
            )

    def test_cli_accepts_default_candidate_name_filter(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "processed"
            output = Path(tmp) / "output"
            store = DatasetStore(root)
            store.write_frame(
                _synthetic_bars(),
                "bars",
                {"frequency": "1d", "market": "CN", "year": "2025"},
            )
            store.write_frame(
                _synthetic_daily_basic(),
                "processed/factor_inputs",
                {"frequency": "1d", "market": "CN", "year": "2025"},
            )

            result = run_daily_basic_non_price_public_carry_prescreen_cli(
                bars_roots=[root],
                daily_basic_roots=[root],
                candidate_names=["daily_basic_free_float_supply_quality_20"],
                output_dir=output,
                analysis_end_date="2025-12-31",
                horizons=(5,),
                min_cross_section=20,
                min_ic_observations=4,
            )

            self.assertEqual(result["summary"]["candidate_count"], 1)
            self.assertEqual(
                {row["factor_name"] for row in result["coverage_preflight"]["field_coverage"]},
                {"daily_basic_free_float_supply_quality_20"},
            )


if __name__ == "__main__":
    unittest.main()
