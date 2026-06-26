import tempfile
import unittest
from pathlib import Path

import pandas as pd

from quant_robot.ops.event_contextual_underreaction_reference_dedup import (
    NEXT_HIBERNATE_OR_ORTHOGONALIZE_DIRECTION,
    NEXT_WALK_FORWARD_PREFLIGHT_DIRECTION,
    compute_event_contextual_underreaction_reference_frame,
    summarize_event_contextual_underreaction_reference_dedup,
    write_event_contextual_underreaction_reference_dedup,
)
from tests.unit.test_event_contextual_underreaction_prescreen import _event_frames, _predictive_bars
from tests.unit.test_event_factor_pit_ic_prescreen import _stock_basic


class EventContextualUnderreactionReferenceDedupTests(unittest.TestCase):
    def test_blocks_highly_redundant_contextual_event_lead(self) -> None:
        factor_frame, labels, reference_frame, report = _frames(duplicate_reference=True)

        result = summarize_event_contextual_underreaction_reference_dedup(
            factor_frame,
            labels,
            reference_factor_frame=reference_frame,
            prescreen_report=report,
            min_cross_section=30,
            min_ic_observations=5,
        )

        lead = result["lead_results"][0]
        self.assertEqual(result["stage"], "event_contextual_underreaction_reference_dedup")
        self.assertEqual(lead["lead_factor_name"], "event_holder_contraction_low_vol_20")
        self.assertIn("lead_highly_redundant_with_reference_factor", lead["gate"]["blockers"])
        self.assertEqual(lead["next_direction"], NEXT_HIBERNATE_OR_ORTHOGONALIZE_DIRECTION)
        self.assertFalse(lead["promotion_policy"]["promotion_allowed"])
        self.assertEqual(result["summary"]["dedup_pass_count"], 0)

    def test_allows_unique_stable_lead_to_walk_forward_preflight(self) -> None:
        factor_frame, labels, reference_frame, report = _frames(duplicate_reference=False)

        result = summarize_event_contextual_underreaction_reference_dedup(
            factor_frame,
            labels,
            reference_factor_frame=reference_frame,
            prescreen_report=report,
            min_cross_section=30,
            min_ic_observations=5,
        )

        lead = result["lead_results"][0]
        self.assertEqual(lead["gate"]["blockers"], [])
        self.assertEqual(lead["next_direction"], NEXT_WALK_FORWARD_PREFLIGHT_DIRECTION)
        self.assertEqual(result["summary"]["dedup_pass_count"], 1)
        self.assertEqual(result["next_direction"], NEXT_WALK_FORWARD_PREFLIGHT_DIRECTION)

    def test_compute_reference_frame_includes_raw_event_and_context_components(self) -> None:
        bars = _predictive_bars(days=55, assets=8)
        stock_basic = _stock_basic(8)
        refs = compute_event_contextual_underreaction_reference_frame(
            _event_frames(assets=8, dates=("2024-01-30", "2024-02-13", "2024-02-27", "2024-03-12")),
            bars,
            stock_basic,
            include_price_volume_references=False,
        )

        self.assertIn("raw_event_repurchase_amount_to_mv_20", set(refs["factor_name"]))
        self.assertIn("raw_event_holder_number_contraction_2q", set(refs["factor_name"]))
        self.assertIn("context_repurchase_pre_signal_underreaction_20", set(refs["factor_name"]))
        self.assertIn("context_holder_low_vol_20", set(refs["factor_name"]))

    def test_write_outputs_reference_dedup_artifacts(self) -> None:
        factor_frame, labels, reference_frame, report = _frames(duplicate_reference=False)
        result = summarize_event_contextual_underreaction_reference_dedup(
            factor_frame,
            labels,
            reference_factor_frame=reference_frame,
            prescreen_report=report,
            min_cross_section=30,
            min_ic_observations=5,
        )

        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)
            write_event_contextual_underreaction_reference_dedup(output_dir, result)
            self.assertTrue((output_dir / "event_contextual_underreaction_reference_dedup.json").exists())
            self.assertTrue((output_dir / "event_contextual_underreaction_reference_dedup.md").exists())
            self.assertTrue((output_dir / "event_contextual_underreaction_reference_correlations.csv").exists())
            self.assertTrue((output_dir / "event_contextual_underreaction_reference_yearly_ic.csv").exists())


def _frames(*, duplicate_reference: bool) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, dict]:
    dates = pd.bdate_range("2024-01-02", periods=8)
    factor_rows = []
    label_rows = []
    reference_rows = []
    for date_idx, signal_date in enumerate(dates):
        for asset_idx in range(36):
            asset_id = f"CN_XSHE_{asset_idx:06d}"
            lead_value = float(asset_idx + date_idx * 0.01)
            forward_return = lead_value * 0.001
            factor_rows.append(
                {
                    "date": signal_date,
                    "asset_id": asset_id,
                    "market": "CN",
                    "factor_name": "event_holder_contraction_low_vol_20",
                    "factor_value": lead_value,
                    "adv20_amount": 50_000_000.0 + asset_idx,
                }
            )
            label_rows.append(
                {
                    "date": signal_date,
                    "asset_id": asset_id,
                    "market": "CN",
                    "horizon": 20,
                    "forward_return": forward_return,
                }
            )
            reference_rows.append(
                {
                    "date": signal_date,
                    "asset_id": asset_id,
                    "market": "CN",
                    "factor_name": "duplicate_reference" if duplicate_reference else "independent_reference",
                    "factor_value": lead_value if duplicate_reference else float((asset_idx * 7 + date_idx) % 36),
                }
            )
    report = {
        "results": [
            {
                "factor_name": "event_holder_contraction_low_vol_20",
                "horizon": 20,
                "research_lead": True,
            }
        ],
        "summary": {"research_lead_count": 1, "candidate_count": 4, "test_count": 8},
    }
    return pd.DataFrame(factor_rows), pd.DataFrame(label_rows), pd.DataFrame(reference_rows), report


if __name__ == "__main__":
    unittest.main()
