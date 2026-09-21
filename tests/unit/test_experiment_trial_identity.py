import json
import os
import subprocess
import sys
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

import pandas as pd

from quant_robot.data.fixtures import load_demo_market_bars
from quant_robot.experiments.runner import ExperimentGridConfig, _load_completed_grid, run_experiment_grid
from quant_robot.ops.factor_statistical_reality_check import build_factor_statistical_reality_check
from quant_robot.research.trial_identity import bind_experiment_trial_ids


class ExperimentTrialIdentityTests(unittest.TestCase):
    def config(self, output, **kwargs):
        return ExperimentGridConfig(
            markets=("CN_ETF",), factor_names=("momentum_2",), factor_windows=(2,),
            top_n_values=(1,), cost_bps_values=(5.0,), write_case_artifacts=False,
            output_dir=output, **kwargs,
        )

    def test_same_local_case_name_has_distinct_identity_for_different_exposure(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = self.config(Path(tmp)/"half", target_gross_exposure=.5)
            first = run_experiment_grid(load_demo_market_bars(), config)
            second = run_experiment_grid(
                load_demo_market_bars(), replace(config, output_dir=Path(tmp)/"six", target_gross_exposure=.6),
            )
            left, right = first["leaderboard"][0], second["leaderboard"][0]
            self.assertEqual(left["case_id"], right["case_id"])
            self.assertNotEqual(left["trial_id"], right["trial_id"])
            self.assertEqual(left["experiment_fingerprint"], first["reproducibility"]["fingerprint"])
            saved = pd.read_csv(Path(tmp)/"half"/"leaderboard.csv")
            self.assertEqual(saved.iloc[0]["trial_id"], left["trial_id"])
            self.assertEqual(saved.iloc[0]["experiment_fingerprint"], left["experiment_fingerprint"])

    def test_export_directory_is_not_a_new_trial(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = self.config(Path(tmp)/"first")
            first = run_experiment_grid(load_demo_market_bars(), config)
            second = run_experiment_grid(load_demo_market_bars(), replace(config, output_dir=Path(tmp)/"copy"))
            self.assertEqual(first["leaderboard"][0]["trial_id"], second["leaderboard"][0]["trial_id"])

    def test_cached_identity_reloads_without_running_research(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = self.config(Path(tmp), resume_completed_cases=True)
            original = run_experiment_grid(load_demo_market_bars(), config)
            with patch("quant_robot.experiments.runner.run_research_pipeline") as pipeline:
                cached = run_experiment_grid(load_demo_market_bars(), config)
            pipeline.assert_not_called()
            self.assertEqual(cached["leaderboard"][0]["trial_id"], original["leaderboard"][0]["trial_id"])

    def test_cached_mismatched_identity_is_rejected_without_rewriting_it(self):
        with tempfile.TemporaryDirectory() as tmp:
            config = self.config(Path(tmp), resume_completed_cases=True)
            original = run_experiment_grid(load_demo_market_bars(), config)
            path = Path(tmp)/"leaderboard.json"
            rows = json.loads(path.read_text(encoding="utf-8"))
            rows[0]["trial_id"] = "changed"
            path.write_text(json.dumps(rows), encoding="utf-8")
            self.assertIsNone(_load_completed_grid(config, original["reproducibility"]))
            self.assertEqual(json.loads(path.read_text(encoding="utf-8"))[0]["trial_id"], "changed")


class StatisticalTrialScopeTests(unittest.TestCase):
    def records(self):
        return pd.DataFrame([
            {"case_id": "same_local_name", "trial_id": "trial_a", "experiment_fingerprint": "a"*64,
             "sharpe": 1.0, "observations": 120, "p_value": .001},
            {"case_id": "same_local_name", "trial_id": "trial_b", "experiment_fingerprint": "b"*64,
             "sharpe": .7, "observations": 120, "p_value": .01},
        ])

    def test_local_case_collision_between_experiments_cannot_be_scored(self):
        with self.assertRaisesRegex(ValueError, "multiple experiment fingerprints"):
            build_factor_statistical_reality_check(self.records(), observations_column="observations")

    def test_qualified_trial_column_counts_both_executions(self):
        report = build_factor_statistical_reality_check(
            self.records(), case_column="trial_id", observations_column="observations",
        )
        self.assertEqual(report["summary"]["hypothesis_count"], 2)
        self.assertFalse(report["inference_scope"]["complete_research_history_verified"])
        self.assertEqual(report["inference_scope"]["experiment_fingerprint_count"], 2)
        self.assertEqual({row["source_case_id"] for row in report["rows"]}, {"same_local_name"})
        self.assertEqual({row["experiment_fingerprint"] for row in report["rows"]}, {"a"*64, "b"*64})

    def test_cli_rejects_ambiguous_csv_and_accepts_explicit_qualified_column(self):
        repo = Path(__file__).resolve().parents[2]
        env = {**os.environ, "OPENBLAS_NUM_THREADS": "1", "OMP_NUM_THREADS": "1", "MKL_NUM_THREADS": "1"}
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp)/"synthetic_trials.csv"
            output = Path(tmp)/"report"
            rows = []
            for row in self.records().drop(columns="trial_id").to_dict("records"):
                rows.extend(bind_experiment_trial_ids([row], row["experiment_fingerprint"]))
            pd.DataFrame(rows).to_csv(source, index=False)
            command = [sys.executable, "scripts/run_factor_statistical_reality_check.py",
                       "--experiments-path", str(source), "--output-dir", str(output),
                       "--observations-column", "observations"]
            rejected = subprocess.run(command, cwd=repo, env=env, capture_output=True, text=True, timeout=60)
            self.assertNotEqual(rejected.returncode, 0)
            self.assertIn("multiple experiment fingerprints", rejected.stderr)
            self.assertFalse(output.exists())
            accepted = subprocess.run(command+["--case-column", "trial_id"], cwd=repo, env=env,
                                      capture_output=True, text=True, timeout=60)
            self.assertEqual(accepted.returncode, 0, msg=accepted.stderr)
            report = json.loads((output/"factor_statistical_reality_check.json").read_text(encoding="utf-8"))
            self.assertEqual(report["summary"]["hypothesis_count"], 2)
            self.assertFalse(report["inference_scope"]["complete_research_history_verified"])
            self.assertEqual({row["trial_id"] for row in report["rows"]}, {row["trial_id"] for row in rows})

    def test_partial_provenance_cannot_drop_rows_during_identity_validation(self):
        for missing in (None, "", float("nan")):
            with self.subTest(missing=missing):
                frame = self.records()
                frame.loc[1, "experiment_fingerprint"] = missing
                with self.assertRaisesRegex(ValueError, "experiment fingerprint"):
                    build_factor_statistical_reality_check(frame, case_column="trial_id")

    def test_changed_export_trial_id_cannot_merge_distinct_cases(self):
        rows = bind_experiment_trial_ids([
            {"case_id": "a", "sharpe": 1.0}, {"case_id": "b", "sharpe": .5},
        ], "a"*64)
        rows[1]["trial_id"] = rows[0]["trial_id"]
        with self.assertRaisesRegex(ValueError, "trial identity"):
            build_factor_statistical_reality_check(pd.DataFrame(rows), case_column="trial_id")

    def test_declared_identity_schema_requires_complete_binding(self):
        rows = bind_experiment_trial_ids([{"case_id": "a", "sharpe": 1.0}], "a"*64)
        del rows[0]["trial_id"]
        with self.assertRaisesRegex(ValueError, "trial identity"):
            build_factor_statistical_reality_check(pd.DataFrame(rows))

    def test_cpcv_keeps_qualified_variants_separate(self):
        rows = []
        for index, date in enumerate(pd.date_range("2024-01-01", periods=8)):
            for row in self.records().to_dict("records"):
                positive = row["trial_id"] == "trial_a"
                rows.append({**row, "date": date, "period_return": (1 if positive else -1)*(.01+.001*index)})
        report = build_factor_statistical_reality_check(
            pd.DataFrame(rows), case_column="trial_id", observations_column="observations",
            date_column="date", cpcv_return_column="period_return", cpcv_groups=2, cpcv_test_group_count=1,
        )
        self.assertEqual(report["cpcv_evaluation"]["case_count"], 2)
        self.assertEqual(report["cpcv_evaluation"]["passed_case_count"], 1)

    def test_legacy_input_is_explicitly_limited_to_provided_rows(self):
        frame = self.records().drop(columns=["experiment_fingerprint", "trial_id"])
        report = build_factor_statistical_reality_check(frame, observations_column="observations")
        self.assertFalse(report["inference_scope"]["complete_research_history_verified"])
        self.assertIsNone(report["inference_scope"]["experiment_fingerprint_count"])
        self.assertIn("provided experiment rows", report["markdown"])


if __name__ == "__main__":
    unittest.main()
