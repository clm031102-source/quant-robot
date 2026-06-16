import tempfile
import unittest
from pathlib import Path

from quant_robot.ops.paper_observation_history import (
    build_paper_observation_history_pack,
    write_paper_observation_history_pack,
)


class PaperObservationHistoryTests(unittest.TestCase):
    def test_history_pack_summarizes_activation_gate_runs(self):
        ready = _gate_pack(
            status="paper_observation_ready",
            generated_at="2026-06-15",
            blockers=[],
            final_fills=21,
            provider_missing=226,
        )
        blocked = _gate_pack(
            status="paper_gate_blocked",
            generated_at="2026-06-16",
            blockers=["minimum_fills_observed"],
            final_fills=5,
            provider_missing=240,
            paper_allowed=False,
        )

        pack = build_paper_observation_history_pack([ready, blocked])

        self.assertEqual(pack["stage"], "phase_5_13_paper_observation_history")
        self.assertEqual(pack["summary"]["run_count"], 2)
        self.assertEqual(pack["summary"]["paper_observation_ready_runs"], 1)
        self.assertEqual(pack["summary"]["blocked_runs"], 1)
        self.assertEqual(pack["summary"]["latest_status"], "paper_gate_blocked")
        self.assertEqual(pack["summary"]["latest_required_assets"], ["CN_ETF_XSHG_516160"])
        self.assertFalse(pack["decision"]["history_clear_for_continued_paper_observation"])
        self.assertEqual(pack["decision"]["blockers"], ["minimum_fills_observed"])
        self.assertEqual(pack["ledger"][0]["status"], "paper_observation_ready")
        self.assertEqual(pack["ledger"][0]["final_fills"], 21)
        self.assertEqual(pack["ledger"][0]["provider_missing_date_rows"], 226)
        self.assertEqual(pack["ledger"][1]["blockers"], "minimum_fills_observed")
        self.assertFalse(pack["live_boundary_allowed"])

    def test_history_pack_blocks_on_any_live_boundary_violation(self):
        pack = build_paper_observation_history_pack(
            [
                _gate_pack(
                    status="paper_observation_ready",
                    generated_at="2026-06-15",
                    blockers=[],
                    live_boundary_allowed=True,
                )
            ]
        )

        self.assertFalse(pack["decision"]["history_clear_for_continued_paper_observation"])
        self.assertEqual(pack["decision"]["blockers"], ["live_boundary_violation"])
        self.assertEqual(pack["summary"]["live_boundary_violations"], 1)
        self.assertFalse(pack["live_boundary_allowed"])

    def test_empty_history_recommends_machine_scoped_activation_gate(self):
        pack = build_paper_observation_history_pack([])

        self.assertEqual(pack["next_actions"][0]["action"], "run_tushare_activation_gate")
        self.assertIn("--machine", pack["next_actions"][0]["command"])
        self.assertIn("highspec_desktop", pack["next_actions"][0]["command"])
        self.assertIn("--execute", pack["next_actions"][0]["command"])

    def test_write_history_pack_outputs_artifacts(self):
        pack = build_paper_observation_history_pack([_gate_pack(status="paper_observation_ready")])
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)

            write_paper_observation_history_pack(output_dir, pack)

            self.assertTrue((output_dir / "paper_observation_history_pack.json").exists())
            self.assertTrue((output_dir / "paper_observation_history_pack.md").exists())
            csv_text = (output_dir / "paper_observation_history_ledger.csv").read_text(encoding="utf-8")
            self.assertIn("paper_observation_ready", csv_text)


def _gate_pack(
    *,
    status: str,
    generated_at: str = "2026-06-15",
    blockers: list[str] | None = None,
    final_fills: int = 21,
    required_fills: int = 20,
    provider_missing: int = 226,
    paper_allowed: bool = True,
    live_boundary_allowed: bool = False,
) -> dict:
    blockers = blockers or []
    return {
        "stage": "phase_5_12_tushare_activation_gate",
        "generated_at": generated_at,
        "status": status,
        "source": "tushare",
        "mode": "execute",
        "live_boundary_allowed": live_boundary_allowed,
        "decision": {
            "recent_data_ready": True,
            "activation_chain_allowed": paper_allowed,
            "paper_continuation_allowed": paper_allowed,
            "blockers": blockers,
        },
        "recent_data_refresh": {
            "coverage": {
                "coverage_scope": "required_assets",
                "required_asset_ids": ["CN_ETF_XSHG_516160"],
                "expected_trade_dates_count": 15,
                "required_asset_missing_date_rows": 0,
                "provider_missing_date_rows": provider_missing,
            }
        },
        "final_observation_sufficiency": {
            "fills": {
                "observed_fills": final_fills,
                "required_fills": required_fills,
            }
        },
        "iterative_observation_expansion": {"round_count": 2},
    }


if __name__ == "__main__":
    unittest.main()
