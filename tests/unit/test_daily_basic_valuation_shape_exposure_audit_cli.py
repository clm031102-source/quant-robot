import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from scripts.run_daily_basic_valuation_shape_exposure_audit import (
    run_daily_basic_valuation_shape_exposure_audit_cli,
)


class DailyBasicValuationShapeExposureAuditCliTests(unittest.TestCase):
    def test_cli_records_gate_packet_trace_in_result_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            output_dir = root / "audit"
            startup_gate = root / "startup_gate.json"
            data_manifest = root / "data_manifest.json"
            candidate_plan_gate = root / "candidate_plan_gate.json"
            result = {
                "stage": "daily_basic_valuation_shape_exposure_audit",
                "summary": {"passes": False, "blockers": ["diagnostic_only"]},
                "shape_audit": {"quantile_summary": [], "quantile_date_rows": []},
                "exposure_audit": {
                    "factor_summary": [],
                    "style_exposure_rows": [],
                    "industry_date_rows": [],
                    "residual_factor_rows": [],
                },
                "promotion_policy": {"portfolio_grid_allowed": False, "promotion_allowed": False},
                "live_boundary_allowed": False,
            }

            with patch(
                "scripts.run_daily_basic_valuation_shape_exposure_audit._read_frame",
                return_value=pd.DataFrame({"asset_id": ["000001.SZ"], "industry": ["bank"]}),
            ):
                with patch(
                    "scripts.run_daily_basic_valuation_shape_exposure_audit.build_valuation_shape_exposure_audit_from_roots",
                    return_value=result,
                ):
                    actual = run_daily_basic_valuation_shape_exposure_audit_cli(
                        bars_roots=(root / "bars",),
                        daily_basic_roots=(root / "daily_basic",),
                        stock_basic=root / "stock_basic.parquet",
                        output_dir=output_dir,
                        startup_gate_packet=startup_gate,
                        data_manifest_packet=data_manifest,
                        candidate_plan_gate_packet=candidate_plan_gate,
                    )

            gate_packets = {
                "startup_gate_packet": str(startup_gate),
                "data_manifest_packet": str(data_manifest),
                "candidate_plan_gate_packet": str(candidate_plan_gate),
            }
            self.assertEqual(actual["gate_packets"], gate_packets)
            packet = json.loads((output_dir / "daily_basic_valuation_shape_exposure_audit.json").read_text(encoding="utf-8"))
            self.assertEqual(packet["gate_packets"], gate_packets)


if __name__ == "__main__":
    unittest.main()
