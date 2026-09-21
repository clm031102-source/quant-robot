import copy
from datetime import datetime, timezone, timedelta
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from quant_robot.research import cash_carry_study as study
from quant_robot.research.monthly_diagnostic_registration import canonical, sha256, runtime_environment
from quant_robot.research.pm_startup_gate import build_quant_pm_startup_gate

REPO = Path(__file__).resolve().parents[2]


class CashCarryStudyTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(); self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name); self.inputs = {}
        def put(role, raw, path=None):
            path = path or 'data/'+role+'.json'
            target = self.root/path; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(raw)
            self.inputs[role] = dict(path=path, sha256=sha256(raw))
        proposal = json.loads((REPO/study.PROPOSAL).read_bytes())
        amendment = proposal['source_semantics_amendment']
        paths = [r['path'] for r in [amendment['quota_schema'], amendment['active_quota_notice'],
                 *amendment['income_formula_sources']]]
        anchors = []
        for day in proposal['source_scope']['PCF_anchor_dates']:
            path = proposal['source_scope']['reuse_PCF'].get(day, {}).get('path',
                study.SOURCE_DIRECTORY+'/pcf_original_'+day.replace('-', '')+'.response')
            paths.append(path); anchors.append(dict(date=day, source=path))
        paths += [study.SOURCE_DIRECTORY+f'/income_{year}.response' for year in range(2015, 2025)]
        paths += [f'data/fixture_source_{i}.response' for i in range(54-len(paths))]
        source = dict(responses_total=54, PCF_anchors=anchors,
                      all_retained_responses=[dict(path=p) for p in paths])
        for i, row in enumerate(source['all_retained_responses']):
            path = Path(row['path'])
            put(f'evidence_{i}', b'{}', row['path'])
            put(f'claim_{i}', canonical(dict(url='https://example.test/fixed', scope_sha256='a'*64)),
                path.with_name(path.stem+'_claim.json').as_posix())
            put(f'receipt_{i}', canonical(dict(url='https://example.test/fixed', http_status=200,
                sha256=sha256(b'{}'), bytes=2)), path.with_name(path.stem+'_receipt.json').as_posix())
            row.update(sha256=sha256(b'{}'), bytes=2, claim_sha256=self.inputs[f'claim_{i}']['sha256'],
                       receipt_sha256=self.inputs[f'receipt_{i}']['sha256'])
        for role in ('calendar', 'calendar_manifest', 'source_ledger_v2', 'date_coverage'):
            put(role, b'{}')
        by_path = {x['path']: x for x in self.inputs.values()}
        for row in source['PCF_anchors']:
            row['sha256'] = by_path[row['source']]['sha256']
            self.inputs['pcf_'+row['date'][:4]] = by_path[row['source']]
        for year in range(2015, 2025):
            self.inputs[f'income_{year}'] = by_path[study.SOURCE_DIRECTORY+f'/income_{year}.response']
        proposal['source_ledger_v2'] = self.inputs['source_ledger_v2']
        proposal['calendar'] = self.inputs['calendar']
        proposal['source_semantics_amendment']['date_review'] = self.inputs['date_coverage']
        def rewrite(value):
            if isinstance(value, dict):
                if set(value) == {'path', 'sha256'} and value['path'] in by_path:
                    value['sha256'] = by_path[value['path']]['sha256']
                for child in value.values(): rewrite(child)
            elif isinstance(value, list):
                for child in value: rewrite(child)
        rewrite(proposal)
        put('proposal', canonical(proposal), study.PROPOSAL)
        source['proposal'] = self.inputs['proposal']
        source['previous_source_ledger_v2_sha256'] = self.inputs['source_ledger_v2']['sha256']
        put('source_preflight', canonical(source), study.SOURCE_PREFLIGHT)
        for name, role in [('PROPOSAL_SHA256', 'proposal'), ('SOURCE_PREFLIGHT_SHA256', 'source_preflight')]:
            override = patch.object(study, name, self.inputs[role]['sha256']); override.start(); self.addCleanup(override.stop)
        put('source_review', canonical(dict(status='conditional_source_use_reviewed', inputs=copy.deepcopy(self.inputs),
            returns_calculated=False, factor_generated=False, historical_availability_verified=False,
            net_account_allowed=False, income_values_inspected=False)))
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

    def test_gate_and_preflight_never_decode_income(self):
        gate = self.gate()
        self.assertEqual(gate['status'], 'ready', gate['blockers'])
        self.assertEqual(gate['mode'], study.MODE)
        self.assertFalse(gate['safety']['factor_batch_allowed'])
        self.assertFalse(gate['safety']['final_holdout_allowed'])
        # Income is deliberately not a valid API response; only byte hashes may be read here.
        with patch.object(study, 'calculate', side_effect=AssertionError('early income decode')):
            study.preflight(self.root, self.family, self.gate)
        self.assertFalse((self.root/study.DIRECTORY/'attempt_claim.json').exists())

    def test_mutation_prevents_claim(self):
        (self.root/self.inputs['income_2021']['path']).write_bytes(b'changed')
        with patch.object(study, 'calculate') as calculate:
            with self.assertRaisesRegex(ValueError, 'Pinned file changed'):
                study.execute(self.root, self.family, self.gate)
            calculate.assert_not_called()
        self.assertFalse((self.root/study.DIRECTORY/'attempt_claim.json').exists())

    def test_rebinding_alias_cannot_change_frozen_source(self):
        self.packet['inputs']['income_2021'] = self.packet['inputs']['income_2022']
        self._replace_registration()
        with self.assertRaisesRegex(ValueError, 'Income source alias'):
            study.preflight(self.root, self.family, self.gate)

    def test_swapping_calendar_cannot_change_proposal(self):
        self.packet['inputs']['calendar'] = self.packet['inputs']['calendar_manifest']
        self._replace_registration()
        with self.assertRaisesRegex(ValueError, 'Source identities'):
            study.preflight(self.root, self.family, self.gate)

    def _replace_registration(self):
        self.packet = study.build_registration(**{k:self.packet[k] for k in ('inputs', 'code_files', 'branch', 'environment')})
        raw = canonical(self.packet); (self.root/study.REGISTRATION).write_bytes(raw)
        self.family[study.DECISION] = study.admission(self.packet, raw)

    def test_expanded_admission_and_stale_gate_are_rejected(self):
        gate = self.gate(); gate['generated_at'] = (datetime.now(timezone.utc)-timedelta(minutes=1)).isoformat()
        with self.assertRaisesRegex(ValueError, 'Fresh exact'):
            study.preflight(self.root, self.family, lambda: gate)
        self.family[study.DECISION]['net_account_allowed'] = True
        self.assertEqual(self.gate()['status'], 'blocked')
        with self.assertRaises(ValueError): study.preflight(self.root, self.family, self.gate)

    def test_failed_identity_check_consumes_attempt(self):
        def fail(_):
            self.assertTrue((self.root/study.DIRECTORY/'attempt_claim.json').exists())
            raise ValueError('synthetic source identity failure')
        with patch.object(study, 'calculate', side_effect=fail):
            with self.assertRaisesRegex(ValueError, 'synthetic source identity failure'):
                study.execute(self.root, self.family, self.gate)
        self.assertEqual(self.gate()['status'], 'blocked')
        with self.assertRaisesRegex(ValueError, 'consumed'):
            study.execute(self.root, self.family, self.gate)
        terminal = json.loads((self.root/study.DIRECTORY/'outcome.json').read_bytes())
        self.assertEqual(terminal['status'], 'failed_consumed')
        self.assertEqual(terminal['error_message'], 'synthetic source identity failure')

    def test_success_cannot_repeat(self):
        with patch.object(study, 'calculate', return_value={'synthetic': True}):
            result = study.execute(self.root, self.family, self.gate)
        self.assertTrue(result['synthetic'])
        self.assertEqual(self.gate()['status'], 'blocked')
        with self.assertRaises(ValueError): study.execute(self.root, self.family, self.gate)
