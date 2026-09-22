"""Synthetic format-repair transport; consumed URLs cannot be requested twice."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from scripts import repair_cn_etf_currency_gold_history as subject
from tests.unit.test_term_structure_source_collection import Response, Session


class CurrencyRepairTransportTests(unittest.TestCase):
    def setUp(self):
        tmp=tempfile.TemporaryDirectory();self.addCleanup(tmp.cleanup)
        self.path=Path(tmp.name)/'20170925'
        self.item=dict(id='20170925',release_date='2017-09-25',quarter_end='2017-09-30',
                       url='https://www.federalreserve.gov/releases/h10/20170925/')
        self.response=Response(b'synthetic');self.session=Session(self.response)

    def fetch(self):
        with patch('requests.Session',return_value=self.session),\
                patch.object(subject,'endpoint_snapshot',return_value={'source_rows':[{}]*5}):
            return subject.fetch(self.path,self.item,'0'*64)

    def test_success_checks_TLS_and_no_repeated_request(self):
        self.assertEqual(self.fetch()['rows'],5)
        self.assertFalse(self.session.trust_env)
        self.assertTrue(self.session.calls[0][1]['verify'])
        self.assertFalse(self.session.calls[0][1]['allow_redirects'])
        with self.assertRaises(FileExistsError):self.fetch()
        self.assertEqual(len(self.session.calls),1)

    def test_HTTP_failure_keeps_raw_and_receipt(self):
        self.response.status_code=403
        with self.assertRaisesRegex(ValueError,'HTTP'):self.fetch()
        self.assertEqual(self.path.with_suffix('.html').read_bytes(),b'synthetic')
        self.assertEqual(json.loads(self.path.with_suffix('.receipt.json').read_bytes())['status'],'failed')

    def test_oversize_body_keeps_claim_without_partial_raw(self):
        self.response.raw=b'x'*3_000_001
        with self.assertRaisesRegex(ValueError,'size cap'):self.fetch()
        self.assertTrue(self.path.with_suffix('.claim.json').exists())
        self.assertFalse(self.path.with_suffix('.html').exists())
