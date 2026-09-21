import copy
from datetime import datetime, timezone, timedelta
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd
from quant_robot.research import option_activity_study as study
from quant_robot.research.monthly_diagnostic_registration import canonical, sha256, runtime_environment
from quant_robot.research.pm_startup_gate import build_quant_pm_startup_gate

REPO = Path(__file__).resolve().parents[2]


class OptionActivityStudyTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(); self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name); self.inputs = {}
        def put(role, content, path=None):
            path = path or 'data/'+role+'.json'
            target = self.root/path; target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(content)
            self.inputs[role] = dict(path=path, sha256=sha256(content))
        for role in study.ROLES-{'proposal', 'source_review', 'history', 'history_claim'}:
            put(role, b'{}')
        put('proposal', (REPO/study.PROPOSAL).read_bytes(), study.PROPOSAL)
        history = {'scope_sha256': self.inputs['history_scope']['sha256']}
        put('history', canonical(history))
        put('history_claim', canonical(dict(status='completed', result_sha256=self.inputs['history']['sha256'])))
        put('source_review', canonical(dict(status='conditional_source_use_reviewed', inputs=self.inputs.copy(),
            prices_decoded=False, factor_generated=False, historical_availability_verified=False, net_account_allowed=False)))
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
        (self.root/self.inputs['bars_2020']['path']).write_bytes(b'changed')
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

    def test_synthetic_full_calculation_keeps_final_holdout_closed(self):
        dates = list(pd.bdate_range('2020-01-02', '2024-06-28').date)
        # Deterministic artificial holiday set, not a market calendar assertion.
        remove = set(dates[::10][:len(dates)-1087]); dates = [d for d in dates if d not in remove]
        self.assertEqual(len(dates), 1087)
        counts = [dict(date=str(d), CALL_VOLUME=100+d.month, PUT_VOLUME=106,
            LEAVES_CALL_QTY=100, LEAVES_PUT_QTY=100) for d in dates]
        snapshots = {'history': canonical(dict(status='count_structure_qualified', all_monthly_checks_passed=True, daily=counts)),
            'calendar': b'', 'calendar_manifest': b'', 'actions': canonical(dict(schema_version=3,
                source_ref='synthetic', asset_ids=['CN_ETF_XSHG_510050'], coverage_start=str(dates[0]),
                coverage_end=str(dates[-1]), events=[]))}
        for year in range(2020, 2025):
            frame = pd.DataFrame(dict(date=[d for d in dates if d.year == year],
                close=10., asset_id='CN_ETF_XSHG_510050', market='CN_ETF', currency='CNY'))
            output = io.BytesIO(); frame.to_parquet(output, index=False); snapshots['bars_'+str(year)] = output.getvalue()
        with patch('quant_robot.data.cn_calendar_snapshot.calendar_rows_from_snapshot', return_value=[(d, True) for d in dates]):
            result = study.calculate(snapshots)
        self.assertEqual(len(result['observations']), 52)
        self.assertFalse(result['diagnostic']['gross_screen_passed'])
        self.assertFalse(result['net_account_result'])


if __name__ == '__main__': unittest.main()
