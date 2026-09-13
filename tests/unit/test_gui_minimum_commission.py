import json
import shutil
import subprocess
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
from urllib.parse import urlencode
from urllib.request import urlopen

from quant_robot.gui import research_service as service
from quant_robot.gui.app import create_gui_handler
from quant_robot.gui.operation_ledger import _request_signature, _signature_mismatch_keys


class GuiMinimumCommissionTests(unittest.TestCase):
    def test_service_applies_and_records_declared_minimum(self):
        result = service.run_gui_paper_simulation(market='CN_ETF', initial_cash=10000,
            top_n=1, minimum_commission=5)
        self.assertEqual(result['request']['minimum_commission'], 5)
        self.assertEqual(result['request']['execution_economics']['minimum_commission'], 5)
        self.assertTrue(result['fills'])
        self.assertTrue(all(fill['fee'] >= 5 for fill in result['fills']))

    def test_http_passes_minimum_to_both_paper_entrypoints(self):
        server = ThreadingHTTPServer(('127.0.0.1', 0), create_gui_handler())
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            for path in ('/api/paper', '/api/paper/demo'):
                with self.subTest(path=path), patch('quant_robot.gui.app._record_operation'):
                    query = urlencode({'source': 'fixture', 'market': 'CN_ETF',
                                       'initial_cash': 10000, 'minimum_commission': 5})
                    with urlopen(f'http://127.0.0.1:{server.server_port}{path}?{query}', timeout=10) as response:
                        result = json.load(response)
                    self.assertEqual(result['request']['minimum_commission'], 5)
                    self.assertTrue(result['fills'])
                    self.assertTrue(all(fill['fee'] >= 5 for fill in result['fills']))
        finally:
            server.shutdown()
            thread.join(timeout=5)
            server.server_close()

    def test_locked_signature_distinguishes_fee_scenarios_and_legacy_zero(self):
        legacy = {'market': 'CN_ETF', 'factor': 'momentum_2'}
        five = _request_signature({**legacy, 'minimum_commission': '5'})
        self.assertEqual(five['minimum_commission'], 5)
        for expected in (legacy, {**legacy, 'minimum_commission': 0},
                         {**legacy, 'minimum_commission': None}, {**legacy, 'minimum_commission': ''}):
            self.assertIn('minimum_commission', _signature_mismatch_keys(five, _request_signature(expected)))
        self.assertEqual(_request_signature({}), {})
        self.assertEqual(_request_signature({'unrelated': 'field'}), {})

    def test_real_data_denial_still_precedes_loading(self):
        with patch.object(service, 'load_processed_bars') as load:
            with self.assertRaisesRegex(ValueError, '专用入口'):
                service.run_gui_paper_simulation(source='processed-bars', market='CN_ETF', minimum_commission=5)
            load.assert_not_called()

    @unittest.skipUnless(shutil.which('node'), 'Node.js needed for browser regression')
    def test_browser_fee_transmission_and_receipt_matching(self):
        result = subprocess.run([shutil.which('node'), '--test', 'tests/gui_minimum_commission.test.cjs'],
            cwd=Path(__file__).resolve().parents[2], capture_output=True, text=True,
            encoding='utf-8', timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
