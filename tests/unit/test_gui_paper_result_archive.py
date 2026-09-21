import copy
import json
import shutil
import subprocess
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch

from quant_robot.gui.paper_result_archive import (
    ARCHIVE_DIRECTORY, archive_paper_result, load_paper_result, operation_result_fields,
)


def result_fixture():
    strategy = [{'date': '2024-01-02', 'equity': 10000, 'cash': 9000,
                 'position_values': {'ETF': {'quantity': 100, 'market_value': 1000}}},
                {'date': '2024-01-03', 'equity': 9995, 'cash': 8995,
                 'position_values': {'ETF': {'quantity': 100, 'market_value': 1000}}}]
    return {'stage': 'synthetic_archive_fixture', 'request': {'initial_cash': 10000,
                'minimum_commission': 5, 'source': 'demo_fixture',
                'corporate_actions_fingerprint': 'a' * 64},
            'metrics': {'ending_equity': 9995}, 'equity_curve': strategy,
            'fills': [{'asset_id': 'ETF', 'quantity': 100, 'fee': 5}],
            'accounting': {'source_audit_verified': False},
            'fixed_hold_benchmark': {'request': {'initial_cash': 10000},
                'metrics': {'ending_equity': 9990}, 'fills': [{'fee': 10}],
                'equity_curve': [{'date': r['date'], 'equity': 9990} for r in strategy]},
            'account_comparison': {'relative_return': .0005, 'risk_adjusted_alpha_verified': False}}


class GuiPaperResultArchiveTests(unittest.TestCase):
    @unittest.skipUnless(shutil.which('node'), 'Node.js needed for archive UI regression')
    def test_browser_archive_restore_behavior(self):
        result = subprocess.run([shutil.which('node'), '--test', 'tests/gui_paper_archive.test.cjs'],
            cwd=Path(__file__).resolve().parents[2], capture_output=True, text=True, encoding='utf-8', timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def test_full_result_roundtrip_preserves_both_accounts_and_input_conditions(self):
        result = result_fixture()
        expected = copy.deepcopy(result)
        ref = archive_paper_result(self.root, result)
        result['equity_curve'][0]['equity'] = 1
        loaded = load_paper_result(self.root, ref['archive_id'])
        archived_ref = loaded.pop('paper_archive')
        self.assertEqual(loaded, expected)
        self.assertTrue(archived_ref['restored'])
        self.assertEqual(archived_ref['status'], 'verified')
        self.assertFalse(archived_ref['source_quality_verified'])
        self.assertFalse(archived_ref['new_forward_observation'])
        self.assertEqual(ref['sha256'], ref['archive_id'])
        self.assertEqual(operation_result_fields({**expected, 'paper_archive': ref})['paper_archive'], ref)

    def test_original_result_without_benchmark_or_prior_archive_stays_distinct(self):
        result = result_fixture()
        result.pop('fixed_hold_benchmark')
        result.pop('account_comparison')
        ref = archive_paper_result(self.root, result)
        loaded = load_paper_result(self.root, ref['archive_id'])
        self.assertNotIn('fixed_hold_benchmark', loaded)
        self.assertNotIn('paper_archive', operation_result_fields({'metrics': {'total_return': .1}}))

    def test_tampered_or_missing_archive_never_returns_a_result(self):
        ref = archive_paper_result(self.root, result_fixture())
        path = self.root / ARCHIVE_DIRECTORY / (ref['archive_id'] + '.json')
        path.write_bytes(path.read_bytes().replace(b'9995', b'9996'))
        with self.assertRaisesRegex(ValueError, 'fingerprint'):
            load_paper_result(self.root, ref['archive_id'])
        with self.assertRaises(FileNotFoundError):
            load_paper_result(self.root, 'f' * 64)

    def test_bad_identifiers_rejected_before_file_read(self):
        for value in ['../../outside', 'A' * 64, '', 'a' * 63, None]:
            with self.subTest(value=value), patch.object(Path, 'open', side_effect=AssertionError('read')):
                with self.assertRaises(ValueError):
                    load_paper_result(self.root, value)

    def test_partial_nonfinite_and_oversized_results_are_not_saved(self):
        invalid = [{'request': {}, 'metrics': {}},
                   {**result_fixture(), 'metrics': {'ending_equity': float('nan')}},
                   {**result_fixture(), 'fixed_hold_benchmark': {'metrics': {}}}]
        for result in invalid:
            with self.subTest(keys=list(result)), self.assertRaises(ValueError):
                archive_paper_result(self.root, result)
        with patch('quant_robot.gui.paper_result_archive.MAX_ARCHIVE_BYTES', 100):
            with self.assertRaisesRegex(ValueError, 'size'):
                archive_paper_result(self.root, result_fixture())
        self.assertFalse(list(self.root.rglob('*.json')))

    def test_interrupted_atomic_write_never_advertises_partial_archive(self):
        with patch('quant_robot.storage.atomic.os.replace', side_effect=OSError('synthetic crash')):
            with self.assertRaises(OSError):
                archive_paper_result(self.root, result_fixture())
        self.assertFalse(list(self.root.rglob('*.json')))

    def test_parallel_archive_writes_keep_independent_results(self):
        def write(value):
            result = result_fixture()
            result['request']['case_id'] = value
            return archive_paper_result(self.root, result)
        with ThreadPoolExecutor(max_workers=2) as pool:
            refs = list(pool.map(write, ['left', 'right']))
        self.assertEqual(len({r['archive_id'] for r in refs}), 2)
        self.assertEqual({load_paper_result(self.root, r['archive_id'])['request']['case_id'] for r in refs},
                         {'left', 'right'})
