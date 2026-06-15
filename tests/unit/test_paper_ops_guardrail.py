import tempfile
import unittest
from pathlib import Path

from quant_robot.ops.paper_ops_guardrail import build_paper_ops_guardrail_pack, write_paper_ops_guardrail_pack


class PaperOpsGuardrailTests(unittest.TestCase):
    def test_guardrail_allows_paper_continuation_but_warns_short_history_and_provider_gaps(self):
        history = _history_pack(
            history_clear=True,
            run_count=1,
            ready_runs=1,
            provider_missing=226,
            blockers=[],
        )

        pack = build_paper_ops_guardrail_pack(history, min_live_readiness_runs=20)

        self.assertEqual(pack["stage"], "phase_5_14_paper_ops_guardrail")
        self.assertEqual(pack["status"], "paper_ops_watch")
        self.assertTrue(pack["decision"]["continued_paper_observation_allowed"])
        self.assertFalse(pack["decision"]["live_readiness_candidate"])
        self.assertEqual(pack["decision"]["blockers"], [])
        self.assertEqual(pack["decision"]["warnings"], ["short_paper_history", "provider_missing_date_rows"])
        self.assertEqual(pack["summary"]["ready_run_deficit_for_live_readiness"], 19)
        self.assertFalse(pack["live_boundary_allowed"])

    def test_guardrail_blocks_when_history_is_not_clear(self):
        history = _history_pack(
            history_clear=False,
            run_count=2,
            ready_runs=1,
            provider_missing=0,
            blockers=["minimum_fills_observed"],
        )

        pack = build_paper_ops_guardrail_pack(history)

        self.assertEqual(pack["status"], "paper_ops_blocked")
        self.assertFalse(pack["decision"]["continued_paper_observation_allowed"])
        self.assertFalse(pack["decision"]["live_readiness_candidate"])
        self.assertEqual(pack["decision"]["blockers"], ["history_not_clear", "minimum_fills_observed"])

    def test_guardrail_blocks_on_live_boundary_violation(self):
        history = _history_pack(
            history_clear=True,
            run_count=20,
            ready_runs=20,
            provider_missing=0,
            blockers=[],
            live_boundary_violations=1,
        )

        pack = build_paper_ops_guardrail_pack(history)

        self.assertEqual(pack["status"], "paper_ops_blocked")
        self.assertEqual(pack["decision"]["blockers"], ["live_boundary_violation"])
        self.assertFalse(pack["live_boundary_allowed"])

    def test_write_guardrail_pack_outputs_artifacts(self):
        pack = build_paper_ops_guardrail_pack(_history_pack())
        with tempfile.TemporaryDirectory() as tmp:
            output_dir = Path(tmp)

            write_paper_ops_guardrail_pack(output_dir, pack)

            self.assertTrue((output_dir / "paper_ops_guardrail_pack.json").exists())
            self.assertTrue((output_dir / "paper_ops_guardrail_pack.md").exists())
            self.assertTrue((output_dir / "paper_ops_guardrail_checks.csv").exists())


def _history_pack(
    *,
    history_clear: bool = True,
    run_count: int = 20,
    ready_runs: int = 20,
    provider_missing: int = 0,
    blockers: list[str] | None = None,
    live_boundary_violations: int = 0,
) -> dict:
    blockers = blockers or []
    return {
        "stage": "phase_5_13_paper_observation_history",
        "decision": {
            "history_clear_for_continued_paper_observation": history_clear,
            "blockers": blockers,
        },
        "summary": {
            "run_count": run_count,
            "paper_observation_ready_runs": ready_runs,
            "latest_provider_missing_date_rows": provider_missing,
            "live_boundary_violations": live_boundary_violations,
            "latest_status": "paper_observation_ready" if history_clear else "paper_gate_blocked",
            "latest_required_assets": ["CN_ETF_XSHG_516160"],
            "latest_final_fills": 21,
            "latest_required_fills": 20,
        },
        "live_boundary_allowed": False,
    }


if __name__ == "__main__":
    unittest.main()
