"""Bounded request behavior using fake public-source responses."""
import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import collect_cn_etf_term_structure_history as subject


class Response:
    status_code = 200
    headers = {'Content-Type': 'text/html'}

    def __init__(self, raw):
        self.raw = raw

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def iter_content(self, size):
        yield self.raw


class Session:
    def __init__(self, response):
        self.response, self.calls = response, []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def get(self, url, **kwargs):
        self.calls.append((url, kwargs))
        return self.response


class CollectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        (self.root / 'configs').mkdir()
        (self.root / subject.SCOPE).write_text('{}')
        (self.root / subject.DIRECTORY).mkdir(parents=True)
        self.scope = {'requests': subject.expected_requests()[:1], 'max_bytes_per_response': 1_000_000}
        self.response = Response(b'public synthetic source')
        self.session = Session(self.response)

    def run_collection(self):
        with patch.object(subject, 'load_scope', return_value=self.scope), \
                patch('requests.Session', return_value=self.session), \
                patch.object(subject, 'parse_history', return_value=[{'date': '2011-12-20'}]):
            subject.collect(self.root)

    def test_success_keeps_bytes_and_refuses_second_attempt(self):
        self.run_collection()
        receipt = json.loads((self.root / subject.DIRECTORY / 'corpus/warmup_remaining.receipt.json').read_bytes())
        self.assertEqual(receipt['sha256'], hashlib.sha256(self.response.raw).hexdigest())
        self.assertFalse(self.session.trust_env)
        self.assertFalse(self.session.calls[0][1]['allow_redirects'])
        with self.assertRaises(FileExistsError):
            self.run_collection()
        self.assertEqual(len(self.session.calls), 1)

    def test_http_failure_is_kept_and_cannot_be_retried(self):
        self.response.status_code = 403
        with self.assertRaisesRegex(ValueError, 'HTTP'):
            self.run_collection()
        folder = self.root / subject.DIRECTORY / 'corpus'
        self.assertEqual((folder / 'warmup_remaining.html').read_bytes(), self.response.raw)
        self.assertEqual(json.loads((folder / 'warmup_remaining.receipt.json').read_bytes())['status'], 'failed')
        with self.assertRaises(FileExistsError):
            self.run_collection()
        self.assertEqual(len(self.session.calls), 1)

    def test_size_failure_retains_claim_and_failure_receipt(self):
        self.response.raw = b'x' * 1_000_001
        with self.assertRaisesRegex(ValueError, 'size limit'):
            self.run_collection()
        folder = self.root / subject.DIRECTORY / 'corpus'
        self.assertTrue((folder / 'warmup_remaining.claim.json').exists())
        self.assertFalse((folder / 'warmup_remaining.html').exists())
        self.assertEqual(json.loads((folder / 'warmup_remaining.receipt.json').read_bytes())['status'], 'failed')


if __name__ == '__main__':
    unittest.main()
