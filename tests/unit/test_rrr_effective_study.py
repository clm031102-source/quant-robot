import copy
from datetime import datetime, timezone, timedelta
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd
from quant_robot.research import rrr_effective_study as study
from quant_robot.research.monthly_diagnostic_registration import canonical, sha256, runtime_environment
from quant_robot.research.pm_startup_gate import build_quant_pm_startup_gate

REPO = Path(__file__).resolve().parents[2]


class RRREffectiveStudyTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(); self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name); self.inputs = {}
        def put(role, content, path=None):
            path = path or 'data/'+role+'.json'
            target = self.root/path; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(content)
            self.inputs[role] = dict(path=path, sha256=sha256(content))
        for role in study.ROLES-{'proposal', 'source_review'}:
            put(role, b'{}')
        proposal=json.loads((REPO/study.PROPOSAL).read_bytes())
        for role in ('original_proposal','event_ledger','annual_reconciliation'):
            proposal[role]=self.inputs[role]
        raw_proposal=canonical(proposal)
        override=patch.object(study,'PROPOSAL_SHA256',sha256(raw_proposal));override.start();self.addCleanup(override.stop)
        put('proposal', raw_proposal, study.PROPOSAL)
        put('source_review', canonical(dict(status='conditional_source_use_reviewed', inputs=self.inputs.copy(),
            returns_calculated=False, factor_generated=False, historical_availability_verified=False, net_account_allowed=False)))
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

    def test_event_ledger_cannot_be_swapped_through_new_registration(self):
        replacement=b'{"replacement":true}'
        (self.root/self.inputs['event_ledger']['path']).write_bytes(replacement)
        self.packet['inputs']['event_ledger']['sha256']=sha256(replacement)
        raw=canonical(study.build_registration(**{k:self.packet[k] for k in ('inputs','code_files','branch','environment')}))
        (self.root/study.REGISTRATION).write_bytes(raw)
        self.family[study.DECISION]=study.admission(json.loads(raw),raw)
        with self.assertRaisesRegex(ValueError,'Source identities differ from frozen proposal'):
            study.execute(self.root,self.family,self.gate)
        self.assertFalse((self.root/study.DIRECTORY/'attempt_claim.json').exists())

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
