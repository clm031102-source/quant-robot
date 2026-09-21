"""Synthetic transport checks; no actual Federal Reserve requests."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import collect_cn_etf_currency_gold_history as subject
from tests.unit.test_term_structure_source_collection import Response, Session


class CurrencyCollectionTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root=Path(temporary.name)
        (self.root/'configs').mkdir()
        (self.root/subject.SCOPE).write_text('{}')
        self.response=Response(b'synthetic')
        self.session=Session(self.response)

    def run_collection(self):
        item=dict(id='20130923',quarter_end='2013-09-30',release_date='2013-09-23',
                  url='https://www.federalreserve.gov/releases/h10/20130923/')
        scope=dict(requests=[item],max_bytes_per_response=3_000_000)
        with patch.object(subject,'load_scope',return_value=scope),\
                patch('requests.Session',return_value=self.session),\
                patch.object(subject,'endpoint_snapshot',return_value={'source_rows':[{}]*5}):
            subject.collect(self.root)

    def test_transport_and_exactly_once_success(self):
        self.run_collection()
        folder=self.root/subject.DIRECTORY/'corpus'
        receipt=json.loads((folder/'20130923.receipt.json').read_bytes())
        self.assertEqual(receipt['status'],'source_parsed')
        self.assertEqual(receipt['rows'],5)
        self.assertFalse(self.session.trust_env)
        self.assertTrue(self.session.calls[0][1]['verify'])
        self.assertFalse(self.session.calls[0][1]['allow_redirects'])
        with self.assertRaises(FileExistsError):self.run_collection()
        self.assertEqual(len(self.session.calls),1)

    def test_HTTP_error_preserved_without_retry(self):
        self.response.status_code=403
        with self.assertRaisesRegex(ValueError,'HTTP'):self.run_collection()
        folder=self.root/subject.DIRECTORY/'corpus'
        self.assertEqual((folder/'20130923.html').read_bytes(),b'synthetic')
        self.assertEqual(json.loads((folder/'20130923.receipt.json').read_bytes())['status'],'failed')
        with self.assertRaises(FileExistsError):self.run_collection()
        self.assertEqual(len(self.session.calls),1)

    def test_oversize_body_keeps_failed_claim_but_no_partial_source(self):
        self.response.raw=b'x'*3_000_001
        with self.assertRaisesRegex(ValueError,'size cap'):self.run_collection()
        folder=self.root/subject.DIRECTORY/'corpus'
        self.assertFalse((folder/'20130923.html').exists())
        self.assertEqual(json.loads((folder/'20130923.receipt.json').read_bytes())['status'],'failed')

    def test_changed_pin_blocks_before_network(self):
        target=self.root/'source.html'
        target.write_bytes(b'changed')
        scope=dict(pins=[dict(path='source.html',sha256='0'*64)])
        (self.root/subject.SCOPE).write_text(json.dumps(scope))
        with patch('requests.Session') as session:
            with self.assertRaisesRegex(ValueError,'Pinned source/code'):
                subject.collect(self.root)
            session.assert_not_called()
