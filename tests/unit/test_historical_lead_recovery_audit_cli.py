import json
import tempfile
import unittest
from pathlib import Path

from scripts.run_historical_lead_recovery_audit import run_historical_lead_recovery_audit_cli
from tests.unit.test_historical_lead_recovery_audit import (
    _dedup_packet,
    _public_reference_replay_packet,
    _turnover_conversion_packet,
)


class HistoricalLeadRecoveryAuditCliTests(unittest.TestCase):
    def test_cli_reads_historical_evidence_and_writes_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            turnover_path = root / "turnover.json"
            market_path = root / "market.json"
            alpha_path = root / "alpha.json"
            replay_path = root / "replay.json"
            output_dir = root / "output"
            turnover_path.write_text(json.dumps(_turnover_conversion_packet()), encoding="utf-8")
            market_path.write_text(
                json.dumps(
                    _dedup_packet(
                        factor_name="beta_adjusted_range_contraction_60",
                        blockers=["twenty_fifteen_regime_failure_unexplained"],
                        yearly_failure=True,
                    )
                ),
                encoding="utf-8",
            )
            alpha_path.write_text(
                json.dumps(
                    _dedup_packet(
                        factor_name="qlib_alpha158_return_std_position_blend_20",
                        blockers=["lead_highly_redundant_with_reference_factor"],
                    )
                ),
                encoding="utf-8",
            )
            replay_path.write_text(json.dumps(_public_reference_replay_packet()), encoding="utf-8")

            audit = run_historical_lead_recovery_audit_cli(
                turnover_conversion_json=turnover_path,
                market_residual_dedup_json=market_path,
                public_alpha101_dedup_json=alpha_path,
                public_reference_replay_json=replay_path,
                output_dir=output_dir,
            )

            self.assertEqual(audit["status"], "historical_leads_rejected_rotate_family")
            self.assertEqual(audit["summary"]["candidate_count"], 5)
            self.assertTrue((output_dir / "historical_lead_recovery_audit.json").exists())
            self.assertTrue((output_dir / "historical_lead_recovery_audit.md").exists())
            self.assertTrue((output_dir / "historical_lead_recovery_rows.csv").exists())
            saved = json.loads((output_dir / "historical_lead_recovery_audit.json").read_text(encoding="utf-8"))
            self.assertEqual(saved["decision"]["next_direction"], audit["decision"]["next_direction"])


if __name__ == "__main__":
    unittest.main()
