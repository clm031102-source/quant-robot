import copy
from datetime import datetime, timezone, timedelta
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd
from quant_robot.research import electricity_activity_study as study
from quant_robot.research.monthly_diagnostic_registration import canonical, sha256, runtime_environment
from quant_robot.research.pm_startup_gate import build_quant_pm_startup_gate

REPO = Path(__file__).resolve().parents[2]


class ElectricityActivityStudyTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(); self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name); self.inputs = {}
        def put(role, content, path=None):
            path = path or 'data/'+role+'.json'
            target = self.root/path; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(content)
            self.inputs[role] = dict(path=path, sha256=sha256(content))
        for role in study.ROLES-{'proposal', 'source_review', 'reconciliation_review'}:
            put(role, b'{}')
        put('reconciliation_review', canonical(dict(conditional_selection_ready=True,same_release_conflicts=0,
            different_release_conflicts=1,financial_states_generated=False)))
        proposal=json.loads((REPO/study.PROPOSAL).read_bytes())
        proposal['source_selection_review']=self.inputs['reconciliation_review']
        raw_proposal=canonical(proposal)
        frozen=patch.object(study,'PROPOSAL_SHA256',sha256(raw_proposal));frozen.start();self.addCleanup(frozen.stop)
        put('proposal',raw_proposal,study.PROPOSAL)
        put('source_review',canonical(dict(status='conditional_electricity_inputs_reviewed_before_states',
            inputs=self.inputs.copy(),conditional_selection_ready=True,raw_prices_decoded_this_preparation=False,
            factor_generated=False,returns_computed=False,historical_vintage_verified=False,net_account_allowed=False)))
        code = {}
        for name in study.IMPLEMENTATION:
            path = self.root/name; path.parent.mkdir(parents=True, exist_ok=True); path.write_bytes(b'# fixture')
            code[name] = dict(path=name, sha256=sha256(path.read_bytes()))
        self.packet = study.build_registration(inputs=self.inputs, code_files=code,
            branch='codex/factor-review-synthetic', environment=runtime_environment())
        raw = canonical(self.packet)
        target = self.root/study.REGISTRATION; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(raw)
        self.family = json.loads((REPO/'configs/research_family_scheduler_cn_etf.json').read_bytes())
        self.family[study.DECISION] = study.admission(self.packet, raw)
        self.gate_config = json.loads((REPO/'configs/quant_pm_startup_gate_cn_etf.json').read_bytes())
        self.workstations = json.loads((REPO/'configs/workstations.json').read_bytes())
        for row in self.gate_config['required_reading']:
            path = self.root/row['path']; path.parent.mkdir(parents=True, exist_ok=True); path.write_text('fixture')

    def gate(self):
        return build_quant_pm_startup_gate(gate_config=self.gate_config, workstations_config=self.workstations,
            repo_root=self.root, machine='office_desktop', task='factor_batch', branch=self.packet['branch'],
            current_branch=self.packet['branch'], family_config=self.family)

    def test_gate_opens_only_exact_diagnostic_and_preflight_reads_no_prices(self):
        gate = self.gate()
        self.assertEqual(gate['status'], 'ready', gate['blockers'])
        self.assertEqual(gate['mode'], study.MODE)
        self.assertFalse(gate['safety']['factor_batch_allowed'])
        self.assertFalse(gate['safety']['final_holdout_allowed'])
        with patch('pandas.read_parquet', side_effect=AssertionError('early price read')):
            study.preflight(self.root, self.family, self.gate)
        self.assertFalse((self.root/study.DIRECTORY/'attempt_claim.json').exists())

    def test_mutation_fails_before_claim_or_calculation(self):
        (self.root/self.inputs['bars_2021']['path']).write_bytes(b'changed')
        with patch.object(study, 'calculate') as calculate:
            with self.assertRaisesRegex(ValueError, 'Pinned file changed'):
                study.execute(self.root, self.family, self.gate)
            calculate.assert_not_called()
        self.assertFalse((self.root/study.DIRECTORY/'attempt_claim.json').exists())

    def test_exact_admission_expansion_is_rejected(self):
        self.family[study.DECISION]['net_account_allowed'] = True
        self.assertEqual(self.gate()['status'], 'blocked')
        with self.assertRaises(ValueError): study.preflight(self.root, self.family, self.gate)

    def test_stale_gate_rejected(self):
        gate = self.gate(); gate['generated_at'] = (datetime.now(timezone.utc)-timedelta(minutes=1)).isoformat()
        with self.assertRaisesRegex(ValueError, 'Fresh exact'):
            study.preflight(self.root, self.family, lambda: gate)

    def test_claim_precedes_calculation_and_failure_stays_consumed(self):
        def fail(_):
            self.assertTrue((self.root/study.DIRECTORY/'attempt_claim.json').exists())
            raise ValueError('synthetic failure')
        with patch.object(study, 'calculate', side_effect=fail):
            with self.assertRaisesRegex(ValueError, 'synthetic failure'):
                study.execute(self.root, self.family, self.gate)
        self.assertEqual(self.gate()['status'], 'blocked')
        with self.assertRaisesRegex(ValueError, 'consumed'):
            study.execute(self.root, self.family, self.gate)
        terminal = json.loads((self.root/study.DIRECTORY/'outcome.json').read_bytes())
        self.assertEqual(terminal['status'], 'failed_consumed')

    def test_success_cannot_repeat(self):
        with patch.object(study, 'calculate', return_value={'synthetic': True}):
            result = study.execute(self.root, self.family, self.gate)
        self.assertTrue(result['synthetic'])
        self.assertEqual(self.gate()['status'], 'blocked')
        with self.assertRaises(ValueError): study.execute(self.root, self.family, self.gate)
