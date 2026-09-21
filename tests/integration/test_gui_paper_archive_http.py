import copy
import json
from pathlib import Path
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

from quant_robot.gui.app import create_gui_handler
from quant_robot.gui.fixtures.mock_data import demo_bars
from quant_robot.gui.operation_ledger import build_operation_ledger_snapshot
from quant_robot.gui.paper_result_archive import ARCHIVE_DIRECTORY


class GuiPaperArchiveHttpTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.cwd = patch('quant_robot.gui.app.Path.cwd', return_value=self.root)
        self.cwd.start()
        self.addCleanup(self.cwd.stop)
        bars = demo_bars().query("market == 'CN_ETF'")
        actions = self.root / 'actions.json'
        actions.write_text(json.dumps({'schema_version': 1, 'source_ref': 'synthetic only',
            'coverage_start': str(bars.date.min()), 'coverage_end': str(bars.date.max()),
            'asset_ids': sorted(set(bars.asset_id)), 'events': []}), encoding='utf-8')
        entries = self.root / 'entries.json'
        entries.write_text(json.dumps({'schema_version': 1, 'entries': [
            {'asset_id': 'CN_ETF_XSHG_510300', 'quantity': 100, 'limit_price': 10}]}), encoding='utf-8')
        self.params = {'source': 'fixture', 'market': 'CN_ETF', 'initial_cash': 10000,
            'minimum_commission': 5, 'slippage_bps': 0, 'max_participation_rate': .01,
            'max_asset_weight': .1, 'max_gross_exposure': .1,
            'corporate_actions_path': str(actions), 'fixed_hold_benchmark_path': str(entries)}
        self.start()
        self.addCleanup(self.stop)

    def start(self):
        self.server = ThreadingHTTPServer(('127.0.0.1', 0), create_gui_handler())
        self.thread = threading.Thread(target=lambda: self.server.serve_forever(poll_interval=.02), daemon=True)
        self.thread.start()

    def stop(self):
        self.server.shutdown()
        self.thread.join(timeout=5)
        self.server.server_close()

    def get(self, path, params=None):
        with urlopen(f'http://127.0.0.1:{self.server.server_port}{path}?{urlencode(params or {})}', timeout=15) as response:
            return json.load(response)

    def run_case(self, endpoint='/api/paper'):
        prepared = self.get('/api/paper/inputs', self.params)
        return self.get(endpoint, {**self.params, **prepared['pins']})

    def test_real_http_archive_survives_server_restart_without_recalculation_or_extra_receipt(self):
        result = self.run_case()
        archive = result['paper_archive']
        self.assertEqual(archive['status'], 'saved')
        before = build_operation_ledger_snapshot(self.root)['rows']
        self.assertEqual(before[0]['paper_archive'], archive)
        self.stop()
        self.start()
        with patch('quant_robot.gui.app.run_gui_paper_simulation', side_effect=AssertionError('must not run')):
            restored = self.get('/api/paper/archive', {'archive_id': archive['archive_id']})
        restored_archive = restored.pop('paper_archive')
        expected = copy.deepcopy(result)
        expected.pop('paper_archive')
        self.assertEqual(restored, expected)
        self.assertTrue(restored_archive['restored'])
        self.assertFalse(restored_archive['new_forward_observation'])
        self.assertEqual(build_operation_ledger_snapshot(self.root)['rows'], before)
        self.assertTrue(restored['equity_curve'][0]['position_values'] is not None)
        self.assertEqual(restored['request']['execution_economics'],
                         restored['fixed_hold_benchmark']['request']['execution_economics'])

    def test_demo_route_saves_both_curves_and_untrusted_receipt_cannot_forge_an_archive(self):
        result = self.run_case('/api/paper/demo')
        self.assertEqual(result['paper_archive']['status'], 'saved')
        files = list((self.root / ARCHIVE_DIRECTORY).glob('*.json'))
        payload = {'workflow_id': 'paper_simulation', 'status': 'completed',
                   'paper_archive': result['paper_archive'], 'equity_curve': result['equity_curve'],
                   'retain_paper': True, 'request': result['request'], 'metrics': result['metrics']}
        request = Request(f'http://127.0.0.1:{self.server.server_port}/api/control/execution-receipt',
                          data=json.dumps(payload).encode(), headers={'Content-Type': 'application/json'})
        with urlopen(request, timeout=15) as response:
            self.assertEqual(response.status, 200)
        self.assertEqual(list((self.root / ARCHIVE_DIRECTORY).glob('*.json')), files)
        self.assertNotIn('paper_archive', build_operation_ledger_snapshot(self.root)['rows'][0])

    def test_archive_write_error_is_reported_without_claiming_a_saved_result(self):
        with patch('quant_robot.gui.paper_result_archive.atomic_write', side_effect=OSError('synthetic disk full')):
            result = self.run_case()
        self.assertEqual(result['paper_archive']['status'], 'failed')
        self.assertNotIn('archive_id', result['paper_archive'])
        self.assertTrue(result['equity_curve'])
        self.assertEqual(build_operation_ledger_snapshot(self.root)['rows'][0]['paper_archive']['status'], 'failed')

    def test_changed_archive_and_bad_ids_return_errors_without_recomputing(self):
        result = self.run_case()
        archive_id = result['paper_archive']['archive_id']
        path = self.root / ARCHIVE_DIRECTORY / (archive_id + '.json')
        path.write_bytes(path.read_bytes() + b' ')
        for value in [archive_id, '../other', 'e' * 64]:
            with self.subTest(value=value), patch('quant_robot.gui.app.run_gui_paper_simulation') as run:
                with self.assertRaises(HTTPError) as failure:
                    self.get('/api/paper/archive', {'archive_id': value})
                with failure.exception as response:
                    self.assertEqual(response.code, 400)
                    self.assertFalse(json.load(response)['executable'])
                run.assert_not_called()

    def test_research_denial_still_precedes_archiving_and_source_reads(self):
        with patch('quant_robot.gui.app.retain_paper_result') as archive, \
             patch('quant_robot.gui.research_service.load_processed_bars') as load:
            with self.assertRaises(HTTPError) as failure:
                self.get('/api/paper', {**self.params, 'source': 'processed-bars'})
            with failure.exception as response:
                self.assertEqual(response.code, 403)
            archive.assert_not_called()
            load.assert_not_called()

    def test_full_archive_preserves_actual_synthetic_fills_fees_and_changing_holdings(self):
        bars = demo_bars()
        bars[['volume', 'amount']] *= 100
        with patch('quant_robot.gui.research_service._load_gui_bars', return_value=bars):
            result = self.run_case()
        self.assertTrue(result['fills'])
        self.assertTrue(result['fixed_hold_benchmark']['fills'])
        restored = self.get('/api/paper/archive', {'archive_id': result['paper_archive']['archive_id']})
        for account, original in [(restored, result),
                                  (restored['fixed_hold_benchmark'], result['fixed_hold_benchmark'])]:
            self.assertEqual(account['fills'], original['fills'])
            self.assertEqual(account['equity_curve'], original['equity_curve'])
            self.assertTrue(all(fill['fee'] >= 5 for fill in account['fills']))
            self.assertTrue(any(row['position_values'] for row in account['equity_curve']))
