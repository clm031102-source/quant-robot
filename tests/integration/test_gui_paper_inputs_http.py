import json
from pathlib import Path
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import urlopen
from unittest.mock import patch

from quant_robot.gui.app import create_gui_handler
from quant_robot.gui.fixtures.mock_data import demo_bars
from quant_robot.gui.operation_ledger import append_operation_ledger_entry, build_operation_ledger_snapshot


class GuiPaperInputsHttpTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        bars = demo_bars().query("market == 'CN_ETF'")
        self.actions = self.root/'actions.json'
        self.actions.write_text(json.dumps({'schema_version':1, 'source_ref':'fixture only',
            'coverage_start':str(bars.date.min()), 'coverage_end':str(bars.date.max()),
            'asset_ids':sorted(set(bars.asset_id)), 'events':[]}), encoding='utf-8')
        self.entries = self.root/'entries.json'
        self.entries.write_text(json.dumps({'schema_version':1, 'entries':[
            {'asset_id':'CN_ETF_XSHG_510300','quantity':100,'limit_price':10}]}), encoding='utf-8')
        self.params = {'source':'fixture','market':'CN_ETF','initial_cash':10000,
            'minimum_commission':5,'slippage_bps':0,'market_impact_bps':2,'max_participation_rate':.01,
            'max_asset_weight':.1,'max_gross_exposure':.1,
            'corporate_actions_path':str(self.actions),'fixed_hold_benchmark_path':str(self.entries)}
        self.server = ThreadingHTTPServer(('127.0.0.1',0),create_gui_handler())
        self.thread = threading.Thread(target=self.server.serve_forever,daemon=True)
        self.thread.start()
        self.addCleanup(self.stop)

    def stop(self):
        self.server.shutdown()
        self.thread.join(timeout=5)
        self.server.server_close()

    def get(self, path, params):
        with urlopen(f'http://127.0.0.1:{self.server.server_port}{path}?{urlencode(params)}',timeout=15) as response:
            return json.load(response)

    def test_prepare_then_run_persists_actual_comparison_without_recording_preparation_as_a_run(self):
        def record(**kwargs):
            kwargs.pop('retain_paper', None)
            return append_operation_ledger_entry(repo_root=self.root, **kwargs)
        with patch('quant_robot.gui.app._record_operation',side_effect=record) as saved:
            prepared = self.get('/api/paper/inputs',self.params)
            saved.assert_not_called()
            result = self.get('/api/paper',{**self.params,**prepared['pins']})
        self.assertEqual(saved.call_count,1)
        self.assertEqual(result['request']['execution_economics'],result['fixed_hold_benchmark']['request']['execution_economics'])
        ledger = build_operation_ledger_snapshot(self.root)
        row = ledger['rows'][0]
        self.assertEqual(row['request']['corporate_actions_fingerprint'],prepared['pins']['corporate_actions_fingerprint'])
        self.assertEqual(row['account_comparison'],result['account_comparison'])
        self.assertFalse(row['account_comparison']['source_quality_verified'])

    def test_changed_and_invalid_input_get_explained_errors_without_success_receipts(self):
        prepared = self.get('/api/paper/inputs',self.params)
        self.actions.write_text(self.actions.read_text()+'\n',encoding='utf-8')
        for changes in ({**prepared['pins']},{'market_impact_bps':'nan'}):
            with self.subTest(changes=changes), patch('quant_robot.gui.app._record_operation') as saved:
                with self.assertRaises(HTTPError) as caught:
                    self.get('/api/paper',{**self.params,**changes})
                with caught.exception as response:
                    self.assertEqual(response.code,400)
                    payload = json.load(response)
                self.assertEqual(payload['status'],'paper_input_error')
                self.assertTrue(payload['error'])
                saved.assert_not_called()

    def test_protected_prepare_refuses_before_opening_user_files(self):
        with patch.object(Path,'open',side_effect=AssertionError('must not read')):
            with self.assertRaises(HTTPError) as caught:
                self.get('/api/paper/inputs',{**self.params,'source':'processed-bars'})
            with caught.exception as response:
                self.assertEqual(response.code,403)
                self.assertEqual(json.load(response)['status'],'research_access_denied')

    def test_demo_endpoint_preserves_all_pinned_execution_conditions(self):
        prepared = self.get('/api/paper/inputs',self.params)
        result = self.get('/api/paper/demo',{**self.params,**prepared['pins']})
        self.assertEqual(result['request']['market_impact_bps'],2)
        self.assertEqual(result['request']['max_participation_rate'],.01)
        self.assertEqual(result['request']['execution_economics'],result['fixed_hold_benchmark']['request']['execution_economics'])
        self.assertFalse(result['account_comparison']['risk_adjusted_alpha_verified'])
