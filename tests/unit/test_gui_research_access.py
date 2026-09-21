import json
import threading
import unittest
import shutil
import subprocess
from pathlib import Path
from http.server import ThreadingHTTPServer
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import urlopen

from quant_robot.gui import research_service as service
from quant_robot.gui.app import create_gui_handler
from quant_robot.gui.fixtures.mock_data import demo_bars


class GuiResearchAccessTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('node'), 'Node.js is needed for the browser-state regression cases')
    def test_browser_denial_state_and_completion_receipts(self):
        root = Path(__file__).resolve().parents[2]
        result = subprocess.run([shutil.which('node'), '--test', 'tests/gui_research_access.test.cjs'],
                                cwd=root, capture_output=True, text=True, encoding='utf-8', timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_protected_research_paths_refuse_before_reading_processed_bars(self):
        for function in (service.run_gui_research, service.run_gui_signal_snapshot,
                         service.run_gui_paper_simulation):
            for market in ('CN_ETF', 'CN', 'ALL', ' cn_etf '):
                with self.subTest(function=function.__name__, market=market):
                    with patch.object(service, 'load_processed_bars') as load:
                        with self.assertRaisesRegex(ValueError, '专用入口'):
                            function(source='processed-bars', market=market,
                                     data_root='fixture-sealed-data-must-not-open')
                        load.assert_not_called()

    def test_source_alias_cannot_bypass_research_access(self):
        with patch.object(service, 'load_processed_bars', return_value=demo_bars()) as load:
            with self.assertRaisesRegex(ValueError, '专用入口'):
                service.run_gui_research(source=' PROCESSED_BARS ', market='cn_etf')
            load.assert_not_called()

    def test_daily_advisory_refuses_before_reading_old_candidates(self):
        with patch.object(service, 'build_factor_leaderboard_snapshot') as candidates, \
                patch.object(service, 'load_processed_bars') as load:
            with self.assertRaisesRegex(ValueError, '专用入口'):
                service.build_daily_trade_advisory_snapshot()
            candidates.assert_not_called()
            load.assert_not_called()

    def test_demo_paths_use_bundled_fixture_even_when_data_root_is_supplied(self):
        for function in (service.run_gui_research, service.run_gui_signal_snapshot,
                         service.run_gui_paper_simulation):
            with self.subTest(function=function.__name__):
                with patch.object(service, 'load_processed_bars') as load:
                    result = function(source='fixture', market='CN_ETF',
                                      data_root='fixture-sealed-data-must-not-open')
                    self.assertEqual(result['data_source'], 'demo_fixture')
                    load.assert_not_called()

    def test_non_cn_processed_loader_behavior_is_preserved(self):
        with patch.object(service, 'load_processed_bars', return_value='fixture-result') as load:
            result = service._load_gui_bars('processed-bars', 'fixture-root', 'US')
            self.assertEqual(result, 'fixture-result')
            self.assertEqual(load.call_args.args[1], 'US')

    def test_http_returns_explained_denial_without_success_receipt(self):
        server = ThreadingHTTPServer(('127.0.0.1', 0), create_gui_handler())
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            for path in ('/api/research', '/api/signals', '/api/paper', '/api/trade/daily-advisory'):
                with self.subTest(path=path):
                    query = urlencode({'source': 'processed-bars', 'market': 'CN_ETF',
                                       'data_root': 'fixture-sealed-data-must-not-open',
                                       'authorized': 'true', 'final_holdout_allowed': 'true'})
                    with patch.object(service, 'load_processed_bars') as load, \
                            patch('quant_robot.gui.app._record_operation') as record:
                        with self.assertRaises(HTTPError) as caught:
                            urlopen(f'http://127.0.0.1:{server.server_port}{path}?{query}', timeout=10)
                        with caught.exception as response:
                            self.assertEqual(response.code, 403)
                            payload = json.load(response)
                        self.assertEqual(payload['status'], 'research_access_denied')
                        self.assertIn('专用入口', payload['error'])
                        self.assertFalse(payload['factor_generation_allowed'])
                        self.assertFalse(payload['forward_return_read_allowed'])
                        self.assertFalse(payload['paper_signal_allowed'])
                        self.assertFalse(payload['live_boundary_allowed'])
                        load.assert_not_called()
                        record.assert_not_called()
        finally:
            server.shutdown()
            thread.join(timeout=5)
            server.server_close()
