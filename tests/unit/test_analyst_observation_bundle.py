import hashlib
import json
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

from quant_robot.data.analyst_observation_bundle import materialize_observation_bundle
from tests.unit.test_analyst_forecast_events import BASE, payload


class AnalystObservationBundleTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.manifest = self.root / 'input.json'
        self.output = self.root / 'bundle'
        self.captures = []
        self.add_capture('first.json', '2024-01-03T02:00:00+00:00', BASE)
        self.add_capture('second.json', '2024-01-05T02:00:00+00:00', {
            **BASE, 'report_date':'20240104', 'create_time':'2024-01-04 21:00:00', 'np':'120.012',
        })
        self.write_manifest()

    def add_capture(self, name, seen, *rows):
        raw = payload(*rows)
        (self.root / name).write_bytes(raw)
        self.captures.append({'path':name, 'sha256':hashlib.sha256(raw).hexdigest(), 'observed_at':seen})

    def write_manifest(self, **changes):
        packet = {'schema_version':1, 'source':'tushare_report_rc', 'captures':self.captures, **changes}
        self.manifest.write_text(json.dumps(packet), encoding='utf-8')

    def run_bundle(self, **changes):
        return materialize_observation_bundle(self.manifest, self.output, as_of=changes.pop('as_of', '2024-02-01T00:00:00+00:00'), **changes)

    def test_end_to_end_exports_exact_raw_bytes_and_replayable_manifest(self):
        result = self.run_bundle()
        report = json.loads((self.output / 'review.json').read_text(encoding='utf-8'))
        self.assertEqual(result['status'], 'complete')
        self.assertEqual(report['summary']['new_report_revisions'], 1)
        self.assertEqual(report['transitions'][-1]['net_profit_relative_change'], '0.2')
        self.assertFalse(report['historical_availability_verified'])
        self.assertFalse(report['source_completeness_verified'])
        self.assertEqual(report['observation_clock'], 'caller_supplied_unverified')
        for capture in self.captures:
            archived = self.output / 'raw' / (capture['sha256'] + '.json')
            self.assertEqual(archived.read_bytes(), (self.root / capture['path']).read_bytes())
        for relative, expected in result['files'].items():
            self.assertEqual(hashlib.sha256((self.output / relative).read_bytes()).hexdigest(), expected)
        materialize_observation_bundle(self.output / 'manifest.json', self.root / 'replay', as_of=report['as_of'])
        replay = json.loads((self.root / 'replay' / 'review.json').read_text(encoding='utf-8'))
        self.assertEqual(report['events'], replay['events'])
        self.assertEqual(report['transitions'], replay['transitions'])

    def test_bad_source_fingerprint_creates_no_output(self):
        self.captures[0]['sha256'] = '0' * 64
        self.write_manifest()
        with self.assertRaisesRegex(ValueError, 'source_sha256_mismatch'):
            self.run_bundle()
        self.assertFalse(self.output.exists())

    def test_same_capture_correction_is_preserved_without_counting_a_clean_revision(self):
        self.captures = [self.captures[0]]
        corrected = {**BASE, 'np':'110', 'create_time':'2024-01-04 20:00:00'}
        new = {**BASE, 'np':'120', 'report_date':'20240104', 'create_time':'2024-01-04 21:00:00'}
        self.add_capture('mixed.json', '2024-01-05T02:00:00Z', corrected, new)
        self.write_manifest()
        self.run_bundle()
        report = json.loads((self.output / 'review.json').read_text(encoding='utf-8'))
        self.assertEqual(report['summary']['new_report_revisions'], 0)
        self.assertEqual(report['summary']['transition_kinds']['new_report_with_baseline_change'], 1)
        self.assertEqual(len(report['events']), 3)
        self.assertIsNone(report['transitions'][-1]['net_profit_relative_change'])
        materialize_observation_bundle(self.output / 'manifest.json', self.root / 'replay', as_of=report['as_of'])
        replay = json.loads((self.root / 'replay' / 'review.json').read_text(encoding='utf-8'))
        self.assertEqual(report['transitions'], replay['transitions'])

    def test_naive_cutoff_and_observation_are_rejected(self):
        with self.assertRaisesRegex(ValueError, 'timezone_required'):
            self.run_bundle(as_of='2024-02-01')
        self.captures[0]['observed_at'] = '2024-01-03T02:00:00'
        self.write_manifest()
        with self.assertRaisesRegex(ValueError, 'timezone_required'):
            self.run_bundle()
        self.assertFalse(self.output.exists())

    def test_future_capture_is_not_opened_or_exported(self):
        (self.root / self.captures[1]['path']).unlink()
        result = self.run_bundle(as_of='2024-01-04T00:00:00+00:00')
        report = json.loads((self.output / 'review.json').read_text(encoding='utf-8'))
        self.assertEqual(report['summary']['skipped_future_captures'], 1)
        self.assertEqual(report['summary']['new_report_revisions'], 0)
        exported = json.loads((self.output / 'manifest.json').read_text(encoding='utf-8'))
        self.assertEqual(len(exported['captures']), 1)
        self.assertEqual(len(result['files']), 3)

    def test_duplicate_capture_does_not_duplicate_revision(self):
        self.add_capture('again.json', '2024-01-10T02:00:00+00:00', BASE)
        self.write_manifest()
        self.run_bundle()
        report = json.loads((self.output / 'review.json').read_text(encoding='utf-8'))
        self.assertEqual(report['summary']['captures'], 3)
        self.assertEqual(report['summary']['new_report_revisions'], 1)
        self.assertEqual(len(list((self.output / 'raw').glob('*.json'))), 2)

    def test_existing_output_is_never_overwritten(self):
        self.output.mkdir()
        sentinel = self.output / 'keep.txt'
        sentinel.write_text('original', encoding='utf-8')
        with self.assertRaises(FileExistsError):
            self.run_bundle()
        self.assertEqual(sentinel.read_text(encoding='utf-8'), 'original')
        self.assertFalse((self.output / 'result.json').exists())

    def test_write_failure_leaves_no_completion_marker(self):
        original = Path.write_bytes
        def fail_raw(path, data):
            if path.parent.name == 'raw':
                raise OSError('synthetic write failure')
            return original(path, data)
        with patch.object(Path, 'write_bytes', fail_raw), self.assertRaises(OSError):
            self.run_bundle()
        self.assertFalse((self.output / 'result.json').exists())
        with self.assertRaises(FileExistsError):
            self.run_bundle()

    def test_manifest_schema_and_unknown_keys_are_rejected(self):
        for changes in ({'schema_version':True}, {'source':'processed_cache'}, {'captures':[]}, {'token':'synthetic'}):
            with self.subTest(changes=changes):
                self.write_manifest(**changes)
                with self.assertRaises(ValueError):
                    self.run_bundle()
        self.assertFalse(self.output.exists())

    def test_duplicate_manifest_keys_are_rejected(self):
        self.manifest.write_text('{"schema_version":1,"schema_version":1}', encoding='utf-8')
        with self.assertRaisesRegex(ValueError, 'duplicate_manifest_key'):
            self.run_bundle()

    def test_empty_success_response_remains_zero_evidence(self):
        packet = json.loads(payload(BASE))
        packet['data']['items'] = []
        raw = json.dumps(packet).encode()
        (self.root / 'empty.json').write_bytes(raw)
        self.captures = [{'path':'empty.json', 'sha256':hashlib.sha256(raw).hexdigest(), 'observed_at':'2024-01-03T02:00:00Z'}]
        self.write_manifest()
        self.run_bundle()
        report = json.loads((self.output / 'review.json').read_text(encoding='utf-8'))
        self.assertEqual(report['summary']['eligible_events'], 0)
        self.assertEqual(report['summary']['empty_captures'], 1)
        self.assertFalse(report['source_completeness_verified'])

    def test_unavailable_same_day_forecast_is_excluded_from_event_export(self):
        self.captures = [self.captures[0]]
        self.captures[0]['observed_at'] = '2024-01-02T14:00:00Z'
        self.write_manifest()
        self.run_bundle(as_of='2024-01-02T15:00:00Z')
        report = json.loads((self.output / 'review.json').read_text(encoding='utf-8'))
        self.assertEqual(report['events'], [])
        self.assertEqual(report['transitions'], [])
        self.assertEqual(report['captures'][0]['raw_rows'], 1)

    def test_real_command_exports_review_without_provider_adapter(self):
        command = [sys.executable, '-X', 'utf8', 'scripts/review_analyst_observations.py',
                   '--manifest', str(self.manifest), '--as-of', '2024-02-01T00:00:00Z', '--output-dir', str(self.output)]
        result = subprocess.run(command, cwd=Path(__file__).resolve().parents[2], text=True, capture_output=True, timeout=30, encoding='utf-8')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['status'], 'complete')
        self.assertTrue((self.output / 'result.json').exists())
