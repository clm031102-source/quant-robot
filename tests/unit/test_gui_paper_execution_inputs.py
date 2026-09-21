import hashlib
import json
from pathlib import Path
import tempfile
import shutil
import subprocess
import unittest
from unittest.mock import patch

from quant_robot.gui import research_service as service
from quant_robot.gui.fixtures.mock_data import demo_bars
from quant_robot.gui.paper_inputs import PaperInputError, prepare_gui_paper_inputs
from quant_robot.gui.paper_request_identity import _request_signature, _signature_mismatch_keys


class GuiPaperExecutionInputTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('node'), 'Node.js needed for browser input flow')
    def test_browser_execution_input_flow(self):
        result = subprocess.run([shutil.which('node'),'--test','tests/gui_paper_execution_inputs.test.cjs'],
            cwd=Path(__file__).resolve().parents[2],capture_output=True,text=True,encoding='utf-8',timeout=30)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        bars = demo_bars()
        bars = bars[bars.market.eq('CN_ETF')]
        self.actions = self.root/'actions.json'
        self.actions.write_text(json.dumps({'schema_version':1, 'source_ref':'fixture only',
            'coverage_start':str(bars.date.min()), 'coverage_end':str(bars.date.max()),
            'asset_ids':sorted(set(bars.asset_id)), 'events':[]}), encoding='utf-8')
        self.entries = self.root/'entries.json'
        self.entries.write_text(json.dumps({'schema_version':1, 'entries':[
            {'asset_id':'CN_ETF_XSHG_510300', 'quantity':100, 'limit_price':10}]}), encoding='utf-8')

    def prepare(self):
        return prepare_gui_paper_inputs(source='fixture', market='CN_ETF',
            corporate_actions_path=self.actions, fixed_hold_benchmark_path=self.entries)

    def run_case(self, **changes):
        inputs = self.prepare()
        args = {'source':'fixture', 'market':'CN_ETF', 'initial_cash':10000,
            'minimum_commission':5, 'slippage_bps':0, 'market_impact_bps':2,
            'max_participation_rate':.01, 'max_asset_weight':.1, 'max_gross_exposure':.1,
            'corporate_actions_path':self.actions, 'fixed_hold_benchmark_path':self.entries,
            **inputs['pins']}
        return service.run_gui_paper_simulation(**{**args, **changes})

    def test_prepare_pins_exact_files_without_market_data_or_source_certification(self):
        with patch.object(service, 'load_processed_bars') as load:
            result = self.prepare()
            load.assert_not_called()
        self.assertEqual(result['pins']['corporate_actions_fingerprint'], hashlib.sha256(self.actions.read_bytes()).hexdigest())
        self.assertEqual(result['pins']['fixed_hold_benchmark_sha256'], hashlib.sha256(self.entries.read_bytes()).hexdigest())
        self.assertFalse(result['source_quality_verified'])

    def test_real_data_scope_refuses_before_any_file_or_bar_read(self):
        for run in (prepare_gui_paper_inputs, service.run_gui_paper_simulation):
            with self.subTest(run=run.__name__), patch.object(Path, 'open', side_effect=AssertionError('must not read')):
                with self.assertRaisesRegex(ValueError, '专用入口'):
                    run(source='processed-bars', market='CN_ETF', corporate_actions_path=self.actions)

    def test_actual_gui_account_and_fixed_hold_share_economics_calendar_and_files(self):
        result = self.run_case()
        request = result['request']
        self.assertEqual(request['source'], 'demo_fixture')
        self.assertEqual(_request_signature({'source':'fixture'}), _request_signature({'source':request['source']}))
        benchmark = result['fixed_hold_benchmark']
        self.assertEqual(request['market_impact_bps'], 2)
        self.assertEqual(request['max_participation_rate'], .01)
        self.assertEqual(request['execution_economics'], benchmark['request']['execution_economics'])
        self.assertEqual([r['date'] for r in result['equity_curve']], [r['date'] for r in benchmark['equity_curve']])
        self.assertFalse(result['account_comparison']['risk_adjusted_alpha_verified'])
        self.assertFalse(result['accounting']['source_audit_verified'])
        self.assertEqual(request['fixed_hold_benchmark_sha256'], self.prepare()['pins']['fixed_hold_benchmark_sha256'])

    def test_missing_file_pin_refuses_before_loading_bars(self):
        with patch.object(service, '_load_gui_bars', side_effect=AssertionError('must not load')):
            with self.assertRaises(PaperInputError):
                service.run_gui_paper_simulation(source='fixture', market='CN_ETF', corporate_actions_path=self.actions)

    def test_changed_file_after_preparation_refuses_without_repinning_itself(self):
        pins = self.prepare()['pins']
        self.actions.write_text(self.actions.read_text()+'\n', encoding='utf-8')
        with patch.object(service, '_load_gui_bars', side_effect=AssertionError('must not load')):
            with self.assertRaisesRegex(PaperInputError, '版本'):
                service.run_gui_paper_simulation(source='fixture', market='CN_ETF',
                    corporate_actions_path=self.actions, fixed_hold_benchmark_path=self.entries,
                    max_participation_rate=.01, **pins)

    def test_mid_run_action_mutation_cannot_return_mixed_account_evidence(self):
        real_run = service.run_paper_simulation
        def change_after_run(*args, **kwargs):
            result = real_run(*args, **kwargs)
            self.actions.write_text(self.actions.read_text()+'\n', encoding='utf-8')
            return result
        with patch.object(service, 'run_paper_simulation', side_effect=change_after_run):
            with self.assertRaises((PaperInputError, ValueError)):
                self.run_case()

    def test_benchmark_requires_capacity_actions_and_cn_etf(self):
        for changes in ({'max_participation_rate':None},
                        {'corporate_actions_path':None, 'corporate_actions_fingerprint':None}, {'market':'US'}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.run_case(**changes)

    def test_capacity_and_impact_values_cannot_disable_constraints_by_invalid_numbers(self):
        for field, values in [('max_participation_rate', [0, -1, 1.1, float('nan'), True]),
                              ('market_impact_bps', [-1, float('inf'), True])]:
            for value in values:
                with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                    self.run_case(**{field:value})

    def test_request_identity_preserves_economics_and_refuses_unpinned_file_equivalence(self):
        result = self.run_case()
        actual = _request_signature(result['request'])
        for field, changed in [('market_impact_bps', 3), ('max_participation_rate', .02),
                               ('corporate_actions_fingerprint', 'a'*64), ('fixed_hold_benchmark_sha256', 'b'*64)]:
            expected = _request_signature({**result['request'], field:changed})
            self.assertIn(field, _signature_mismatch_keys(actual, expected))
        unpinned = {**result['request']}
        unpinned.pop('corporate_actions_fingerprint')
        expected = _request_signature(unpinned)
        self.assertIn('corporate_actions_fingerprint', _signature_mismatch_keys(actual, expected))

    def test_legacy_no_file_request_keeps_declared_zero_impact_and_no_capacity(self):
        result = service.run_gui_paper_simulation(source='fixture', market='CN_ETF')
        self.assertEqual(result['request']['market_impact_bps'], 0)
        self.assertIsNone(result['request']['max_participation_rate'])
        self.assertIsNone(result['request']['corporate_actions_fingerprint'])
        self.assertNotIn('fixed_hold_benchmark', result)
