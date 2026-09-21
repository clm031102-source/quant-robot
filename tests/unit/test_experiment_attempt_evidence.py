import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

from quant_robot.data.fixtures import load_demo_market_bars
from quant_robot.experiments.runner import ExperimentGridConfig, run_experiment_grid


class ExperimentAttemptEvidenceTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.output = Path(self.temp.name) / "grid"
        self.bars = load_demo_market_bars()

    def config(self, **kwargs):
        return ExperimentGridConfig(markets=("CN_ETF",), factor_names=("momentum_2",),
            factor_windows=(2,), top_n_values=(1,), cost_bps_values=(5.0,),
            write_case_artifacts=False, output_dir=self.output, **kwargs)

    def attempts(self):
        return [json.loads(path.read_text()) for path in sorted(self.output.glob("attempts/*/attempt.json"))]

    def test_precompute_failure_leaves_frozen_plan_before_any_case_starts(self):
        def fail_factory():
            records = self.attempts()
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]["phase"], "precompute")
            raise RuntimeError("synthetic factory failure")
        with self.assertRaisesRegex(RuntimeError, "synthetic factory failure"):
            run_experiment_grid(self.bars, self.config(precompute_factor_matrix=True),
                precomputed_factor_factory=fail_factory)
        record = self.attempts()[0]
        self.assertEqual(record["status"], "failed")
        self.assertEqual(record["failure_kind"], "RuntimeError")
        self.assertEqual(record["started_cases"], 0)
        self.assertEqual(record["planned_cases"], 1)
        self.assertFalse((self.output / "leaderboard.json").exists())

    def test_interrupt_retains_started_case_as_unfinished_without_saving_error_text(self):
        def interrupt(*args):
            record = self.attempts()[0]
            self.assertEqual(record["started_cases"], 1)
            self.assertEqual(record["finished_cases"], 0)
            self.assertTrue(record["active_case_id"])
            raise KeyboardInterrupt("private synthetic message")
        with patch("quant_robot.experiments.runner._run_case", side_effect=interrupt):
            with self.assertRaises(KeyboardInterrupt):
                run_experiment_grid(self.bars, self.config())
        record = self.attempts()[0]
        self.assertEqual(record["status"], "interrupted")
        self.assertEqual(record["failure_kind"], "KeyboardInterrupt")
        self.assertNotIn("private synthetic message", json.dumps(record))

    def test_repeated_execution_keeps_prior_attempt_and_same_trial_identity(self):
        first = run_experiment_grid(self.bars, self.config())
        original_paths = list(self.output.glob("attempts/*/*.json"))
        original = {path: path.read_bytes() for path in original_paths}
        second = run_experiment_grid(self.bars, self.config())
        records = self.attempts()
        self.assertEqual(len(records), 2)
        self.assertEqual(len({row["attempt_id"] for row in records}), 2)
        self.assertEqual(len({row["experiment_fingerprint"] for row in records}), 1)
        self.assertEqual(first["leaderboard"][0]["trial_id"], second["leaderboard"][0]["trial_id"])
        for row in records:
            self.assertEqual(row["status"], "completed")
            self.assertEqual(row["finished_cases"], 1)
        self.assertEqual(original, {path: path.read_bytes() for path in original_paths})

    def test_cache_reuse_is_not_recorded_as_another_computation(self):
        config = self.config(resume_completed_cases=True)
        run_experiment_grid(self.bars, config)
        with patch("quant_robot.experiments.runner._run_case") as research:
            run_experiment_grid(self.bars, config)
        research.assert_not_called()
        self.assertEqual(len(self.attempts()), 1)

    def test_export_failure_keeps_completed_case_count_and_failed_run(self):
        with patch("quant_robot.experiments.runner._write_grid_artifacts", side_effect=OSError("synthetic disk failure")):
            with self.assertRaises(OSError):
                run_experiment_grid(self.bars, self.config())
        record = self.attempts()[0]
        self.assertEqual(record["status"], "failed")
        self.assertEqual(record["phase"], "export")
        self.assertEqual(record["finished_cases"], 1)

    def test_record_write_failure_blocks_precompute_and_case_execution(self):
        with patch("quant_robot.research.experiment_attempt.atomic_write_json", side_effect=OSError("disk unavailable")), \
                patch("quant_robot.experiments.runner._precompute_factor_matrix") as precompute, \
                patch("quant_robot.experiments.runner._run_case") as research:
            with self.assertRaises(OSError):
                run_experiment_grid(self.bars, self.config(precompute_factor_matrix=True))
        precompute.assert_not_called()
        research.assert_not_called()

    def test_abrupt_process_exit_retains_unknown_running_state_and_plan(self):
        code = """
import os, sys
from pathlib import Path
from quant_robot.data.fixtures import load_demo_market_bars
from quant_robot.experiments.runner import ExperimentGridConfig, run_experiment_grid
config = ExperimentGridConfig(markets=('CN_ETF',), factor_names=('momentum_2',),
    factor_windows=(2,), top_n_values=(1,), cost_bps_values=(5.0,),
    write_case_artifacts=False, output_dir=Path(sys.argv[1]), precompute_factor_matrix=True)
run_experiment_grid(load_demo_market_bars(), config, precomputed_factor_factory=lambda: os._exit(23))
"""
        repo = Path(__file__).resolve().parents[2]
        env = dict(os.environ, PYTHONPATH=os.pathsep.join([str(repo / "src"), str(repo)]))
        completed = subprocess.run([sys.executable, "-c", code, str(self.output)], cwd=repo,
            env=env, capture_output=True, text=True, timeout=60, check=False)
        self.assertEqual(completed.returncode, 23, completed.stderr)
        record = self.attempts()[0]
        self.assertEqual(record["status"], "running")
        self.assertEqual(record["phase"], "precompute")
        self.assertEqual(record["started_cases"], 0)
        self.assertNotIn("finished_at", record)
        plan = json.loads(next(self.output.glob("attempts/*/plan.json")).read_text())
        self.assertEqual(len(plan["ordered_trials"]), 1)
        self.assertTrue(plan["ordered_trials"][0]["trial_id"])


if __name__ == "__main__":
    unittest.main()
