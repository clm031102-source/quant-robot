import tempfile
import unittest
from pathlib import Path

from quant_robot.ops.factor_mining_candidate_plan_gate import (
    build_factor_mining_candidate_plan_gate,
    write_factor_mining_candidate_plan_gate,
)
from quant_robot.ops.profitability_event_revision_preregistration import (
    build_profitability_event_revision_preregistration,
    write_profitability_event_revision_preregistration,
)
from scripts.run_profitability_event_revision_controlled_ic_neutral_prescreen import (
    run_profitability_event_revision_controlled_ic_neutral_prescreen_cli,
)
from tests.unit.test_profitability_event_revision_controlled_ic_neutral_prescreen import (
    _financial_rows,
    _write_bars,
    _write_daily_basic,
    _write_fina_indicator_inputs,
    _write_stock_basic,
)


class ProfitabilityEventRevisionControlledIcNeutralPrescreenCliTests(unittest.TestCase):
    def test_cli_writes_outputs_and_keeps_promotion_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            financial_root = root / "financial"
            bars_root = root / "bars"
            daily_basic_root = root / "daily_basic"
            stock_basic_root = root / "stock_basic"
            prereg_dir = root / "prereg"
            gate_dir = root / "gate"
            output_dir = root / "output"
            financial = _financial_rows(assets=6)
            _write_fina_indicator_inputs(financial_root, financial)
            _write_bars(bars_root, financial["asset_id"].unique().tolist())
            _write_daily_basic(daily_basic_root, financial["asset_id"].unique().tolist())
            _write_stock_basic(stock_basic_root, financial["asset_id"].unique().tolist())
            prereg = build_profitability_event_revision_preregistration(
                input_root=financial_root,
                min_assets=6,
                min_passed_candidates=6,
                min_families=3,
            )
            write_profitability_event_revision_preregistration(prereg_dir, prereg)
            gate = build_factor_mining_candidate_plan_gate(prereg, gate_stage="discovery")
            write_factor_mining_candidate_plan_gate(gate_dir, gate)

            result = run_profitability_event_revision_controlled_ic_neutral_prescreen_cli(
                financial_root=financial_root,
                bars_roots=[bars_root],
                preregistration_json=prereg_dir / "profitability_event_revision_preregistration.json",
                candidate_plan_gate_json=gate_dir / "factor_mining_candidate_plan_gate.json",
                stock_basic_path=stock_basic_root,
                daily_basic_roots=[daily_basic_root],
                output_dir=output_dir,
                horizons=(5,),
                min_cross_section=4,
                min_ic_observations=2,
                min_neutral_ic_t_stat=0.0,
            )

            self.assertEqual(result["stage"], "profitability_event_revision_controlled_ic_neutral_prescreen")
            self.assertFalse(result["promotion_policy"]["promotion_allowed"])
            self.assertTrue((output_dir / "profitability_event_revision_controlled_ic_neutral_prescreen.json").exists())
            self.assertTrue((output_dir / "profitability_event_revision_controlled_ic_results.csv").exists())


if __name__ == "__main__":
    unittest.main()
