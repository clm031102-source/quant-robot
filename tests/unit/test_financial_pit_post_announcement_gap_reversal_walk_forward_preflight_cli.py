import json
import tempfile
import unittest
from pathlib import Path

from quant_robot.ops.financial_pit_post_announcement_gap_reversal_preregistration import (
    build_financial_pit_post_announcement_gap_reversal_preregistration,
    write_financial_pit_post_announcement_gap_reversal_preregistration,
)
from scripts.run_financial_pit_post_announcement_gap_reversal_walk_forward_preflight import (
    run_financial_pit_post_announcement_gap_reversal_walk_forward_preflight_cli,
)
from tests.unit.test_financial_pit_post_announcement_drift_residual_prescreen import (
    _financial_rows,
    _write_bars,
    _write_financial,
)
from tests.unit.test_financial_pit_post_announcement_gap_reversal_preregistration import _seed
from tests.unit.test_financial_pit_post_announcement_gap_reversal_walk_forward_preflight import (
    _portfolio_policy,
    _regime_policy,
    _residual_report,
    _startup_gate,
)


class FinancialPitPostAnnouncementGapReversalWalkForwardPreflightCliTests(unittest.TestCase):
    def test_cli_runner_writes_preflight_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            financial_root = root / "financial"
            bars_root = root / "bars"
            prereg_output = root / "prereg"
            output_dir = root / "output"
            seed_path = root / "seed.json"
            residual_path = root / "residual.json"
            startup_path = root / "startup.json"
            portfolio_path = root / "portfolio.json"
            regime_path = root / "regime.json"
            financial = _financial_rows(assets=6)
            asset_ids = financial["asset_id"].drop_duplicates().tolist()
            _write_financial(financial_root, financial)
            _write_bars(bars_root, asset_ids)
            seed_path.write_text(json.dumps(_seed()), encoding="utf-8")
            prereg = build_financial_pit_post_announcement_gap_reversal_preregistration(
                financial_root=financial_root,
                bars_roots=[bars_root],
                candidate_seed_json=seed_path,
                min_assets=6,
                min_signal_dates=4,
                min_event_reaction_coverage=0.80,
            )
            write_financial_pit_post_announcement_gap_reversal_preregistration(prereg_output, prereg)
            residual_path.write_text(json.dumps(_residual_report()), encoding="utf-8")
            startup_path.write_text(json.dumps(_startup_gate()), encoding="utf-8")
            portfolio_path.write_text(json.dumps(_portfolio_policy()), encoding="utf-8")
            regime_path.write_text(json.dumps(_regime_policy()), encoding="utf-8")

            result = run_financial_pit_post_announcement_gap_reversal_walk_forward_preflight_cli(
                financial_root=financial_root,
                bars_roots=[bars_root],
                preregistration_json=prereg_output / "financial_pit_post_announcement_gap_reversal_preregistration.json",
                residual_prescreen_json=residual_path,
                startup_gate_json=startup_path,
                portfolio_policy_json=portfolio_path,
                regime_policy_json=regime_path,
                output_dir=output_dir,
                min_pair_observations=1,
                min_corr_cross_section=4,
                allow_not_ready=True,
            )

            self.assertEqual(result["stage"], "financial_pit_post_announcement_gap_reversal_reference_dedup_walk_forward_preflight")
            self.assertTrue((output_dir / "financial_pit_post_announcement_gap_reversal_walk_forward_preflight.json").exists())
            self.assertTrue((output_dir / "financial_pit_post_announcement_gap_reversal_walk_forward_preflight.md").exists())


if __name__ == "__main__":
    unittest.main()
