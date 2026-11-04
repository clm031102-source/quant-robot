"""Synthetic sources exercise admission; no real index values or ETF outcomes."""
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from quant_robot.data.sources.geopolitical_vintages import history_url, raw_url
from quant_robot.research import geopolitical_cadence_study as study
from quant_robot.research.monthly_diagnostic_registration import canonical, runtime_environment, sha256
from quant_robot.research.pm_startup_gate import build_quant_pm_startup_gate

REPO = Path(__file__).resolve().parents[2]


class GeopoliticalAdmissionTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.inputs = {}

        def put(role, content):
            path = study.FROZEN[role]["path"] if role in study.FROZEN else study.AUTHORITY_PATHS[role]
            target = self.root/path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
            self.inputs[role] = dict(path=path, sha256=sha256(content))

        for role in study.FROZEN:
            put(role, b"{}")
        proposal = study.FROZEN["proposal"]
        actual_proposal = (REPO/proposal["path"]).read_bytes()
        self.assertEqual(sha256(actual_proposal), proposal["sha256"])
        put("proposal", actual_proposal)
        result_rows, pilot_rows = [], []
        for month in study.MONTHS:
            role = "pilot_scope" if month in ("202203", "202512") else "source_scope"
            stamp = f"{month[:4]}-{month[4:]}-01T00:00:00+00:00"
            commit = "a" * 40
            history = canonical([dict(sha=commit, commit=dict(author=dict(date=stamp), committer=dict(date=stamp)))])
            vintage = b"synthetic original bytes"
            for part, raw, url in (("history", history, history_url(month)), ("vintage", vintage, raw_url(month, commit))):
                claim = dict(url=url, started_at=stamp, scope_sha256=self.inputs[role]["sha256"])
                receipt = dict(claim, status_code=200, link=None, content_type="application/json", sha256=sha256(raw), bytes=len(raw))
                put(f"original_{month}_{part}", raw)
                put(f"original_{month}_{part}_claim", canonical(claim))
                put(f"original_{month}_{part}_receipt", canonical(receipt))
            row = dict(commit_sha=commit, raw_sha256=sha256(vintage))
            if role == "pilot_scope":
                pilot_rows.append(dict(row, vintage_month=month))
            else:
                result_rows.append(dict(row, month=month))
        put("pilot_review", canonical(dict(fixed_pilots=pilot_rows)))
        put("source_result", canonical(dict(passed=44, requests=88, results=result_rows,
            scope_sha256=self.inputs["source_scope"]["sha256"], signal_generated=False, ETF_data_accessed=False)))
        mapping = dict(proposal="proposal", scope="source_scope", result="source_result", claim="source_claim",
                       preflight_review="source_preflight_review", result_review="source_result_review")
        put("source_summary", canonical(dict(pins={key: self.inputs[role] for key, role in mapping.items()})))
        fixture = patch.object(study, "FROZEN", {role: self.inputs[role] for role in study.FROZEN})
        fixture.start()
        self.addCleanup(fixture.stop)
        code = {}
        for name in study.IMPLEMENTATION:
            target = self.root/name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(b"# synthetic implementation")
            code[name] = dict(path=name, sha256=sha256(target.read_bytes()))
        self.packet = study.build_registration(inputs=self.inputs, code_files=code,
            branch="codex/factor-review-synthetic", environment=runtime_environment())
        raw = canonical(self.packet)
        target = self.root/study.REGISTRATION
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        self.family = json.loads((REPO/"configs/research_family_scheduler_cn_etf.json").read_bytes())
        self.family[study.DECISION] = study.admission(self.packet, raw)
        self.gate_config = json.loads((REPO/"configs/quant_pm_startup_gate_cn_etf.json").read_bytes())
        self.workstations = json.loads((REPO/"configs/workstations.json").read_bytes())
        for row in self.gate_config["required_reading"]:
            target = self.root/row["path"]
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("fixture")

    def gate(self):
        return build_quant_pm_startup_gate(gate_config=self.gate_config, workstations_config=self.workstations,
            repo_root=self.root, machine="office_desktop", task="factor_batch", branch=self.packet["branch"],
            current_branch=self.packet["branch"], family_config=self.family)

    def test_exact_preflight_does_not_generate_states(self):
        gate = self.gate()
        self.assertEqual(gate["status"], "ready", gate["blockers"])
        self.assertEqual(gate["mode"], study.MODE)
        self.assertTrue(gate["safety"]["geopolitical_cadence_allowed"])
        self.assertFalse(gate["safety"]["factor_batch_allowed"])
        self.assertEqual(gate["safety"]["factor_batch_scope"], {})
        self.assertEqual(gate["next_actions"][0]["action"], "run_registered_geopolitical_cadence_without_outcomes")
        with patch.object(study, "calculate") as calculate:
            study.preflight(self.root, self.family, self.gate)
            calculate.assert_not_called()
        self.assertFalse((self.root/study.DIRECTORY/"attempt_claim.json").exists())

    def test_outcome_role_and_relocated_original_are_rejected(self):
        for inputs in (dict(self.inputs, bars=dict(path="data/prices.csv", sha256="0"*64)),
                       dict(self.inputs, original_202203_history=dict(path="data/elsewhere", sha256="0"*64))):
            with self.assertRaises(ValueError):
                study.build_registration(inputs=inputs, code_files=self.packet["code_files"],
                    branch=self.packet["branch"], environment=self.packet["environment"])

    def test_source_mutation_fails_before_claim(self):
        (self.root/self.inputs["original_202203_vintage"]["path"]).write_bytes(b"changed")
        with patch.object(study, "calculate") as calculate, self.assertRaisesRegex(ValueError, "Pinned file changed"):
            study.execute(self.root, self.family, self.gate)
        calculate.assert_not_called()
        self.assertFalse((self.root/study.DIRECTORY/"attempt_claim.json").exists())

    def test_expanded_permission_and_wrong_branch_are_blocked(self):
        self.family[study.DECISION]["returns_allowed"] = True
        self.assertEqual(self.gate()["status"], "blocked")
        self.family[study.DECISION] = study.admission(self.packet, canonical(self.packet))
        gate = self.gate()
        gate["selected"]["current_branch"] = "main"
        with self.assertRaises(ValueError):
            study.preflight(self.root, self.family, lambda: gate)

    def test_stale_gate_and_runtime_drift_are_rejected(self):
        gate = self.gate()
        gate["generated_at"] = (datetime.now(timezone.utc)-timedelta(minutes=1)).isoformat()
        with self.assertRaises(ValueError):
            study.preflight(self.root, self.family, lambda: gate)
        with patch.object(study, "runtime_environment", return_value={}):
            with self.assertRaises(ValueError):
                study.preflight(self.root, self.family, self.gate)

    def test_claim_precedes_states_and_failure_cannot_be_retried(self):
        def fail(_):
            self.assertTrue((self.root/study.DIRECTORY/"attempt_claim.json").exists())
            raise ValueError("synthetic calculation failure")
        with patch.object(study, "calculate", side_effect=fail), self.assertRaises(ValueError):
            study.execute(self.root, self.family, self.gate)
        self.assertEqual(self.gate()["status"], "blocked")
        with self.assertRaisesRegex(ValueError, "consumed"):
            study.execute(self.root, self.family, self.gate)
        self.assertEqual(json.loads((self.root/study.DIRECTORY/"outcome.json").read_bytes())["status"], "failed_consumed")

    def test_success_cannot_be_repeated(self):
        with patch.object(study, "calculate", return_value=dict(synthetic=True)):
            self.assertTrue(study.execute(self.root, self.family, self.gate)["synthetic"])
        with self.assertRaisesRegex(ValueError, "consumed"):
            study.execute(self.root, self.family, self.gate)

    def test_multiple_dedicated_scopes_fail_closed(self):
        with patch("quant_robot.research.pm_startup_gate.currency_gold_cadence_scope",
                   return_value=dict(mode="single_currency_gold_cadence_only", scope={})):
            gate = self.gate()
        self.assertIn("multiple_dedicated_diagnostics_authorized", gate["blockers"])
        self.assertFalse(gate["safety"]["geopolitical_cadence_allowed"])

    def test_receipt_hash_or_selected_commit_mismatch_fails_source_chain(self):
        snapshots = {role: (self.root/pin["path"]).read_bytes() for role, pin in self.inputs.items()}
        receipt = json.loads(snapshots["original_202204_vintage_receipt"])
        receipt["sha256"] = "0"*64
        snapshots["original_202204_vintage_receipt"] = canonical(receipt)
        with self.assertRaisesRegex(ValueError, "fingerprint differs"):
            study.source_chain(self.packet, snapshots)


if __name__ == "__main__":
    unittest.main()
