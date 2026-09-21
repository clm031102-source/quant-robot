"""Bounded transport, claims and immutable failures using synthetic responses."""
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from scripts import collect_cn_etf_credit_premium_history as subject
from tests.unit.test_term_structure_source_collection import Response, Session


class CreditCollectionTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        (self.root/'configs').mkdir()
        (self.root/subject.SCOPE).write_text('{}')
        (self.root/subject.DIRECTORY).mkdir(parents=True)
        self.response=Response(b'synthetic')
        self.session=Session(self.response)

    def run_collection(self):
        scope=dict(requests=subject.expected_requests()[:1],max_bytes_per_response=1_000_000)
        with patch.object(subject,'load_scope',return_value=scope),patch('requests.Session',return_value=self.session),patch.object(subject,'parse_credit_history',return_value=[{}]):
            subject.collect(self.root)

    def test_success_preserves_receipt_and_refuses_second_request(self):
        self.run_collection()
        receipt=json.loads((self.root/subject.DIRECTORY/'corpus/2011.receipt.json').read_bytes())
        self.assertEqual(receipt['status'],'source_parsed')
        self.assertFalse(self.session.trust_env)
        self.assertEqual(self.session.calls[0][1]['verify'],True)
        self.assertEqual(self.session.calls[0][1]['allow_redirects'],False)
        with self.assertRaises(FileExistsError): self.run_collection()
        self.assertEqual(len(self.session.calls),1)

    def test_http_error_retained_without_retry(self):
        self.response.status_code=403
        with self.assertRaisesRegex(ValueError,'HTTP'): self.run_collection()
        receipt=json.loads((self.root/subject.DIRECTORY/'corpus/2011.receipt.json').read_bytes())
        self.assertEqual(receipt['status'],'failed')
        self.assertEqual((self.root/subject.DIRECTORY/'corpus/2011.html').read_bytes(),b'synthetic')
        with self.assertRaises(FileExistsError): self.run_collection()

    def test_size_limit_keeps_failure_and_never_accepts_partial(self):
        self.response.raw=b'x'*1_000_001
        with self.assertRaisesRegex(ValueError,'size limit'): self.run_collection()
        folder=self.root/subject.DIRECTORY/'corpus'
        self.assertFalse((folder/'2011.html').exists())
        self.assertEqual(json.loads((folder/'2011.receipt.json').read_bytes())['status'],'failed')

    def test_ranges_do_not_request_the_two_reused_pilot_dates(self):
        from datetime import date,timedelta
        dates=[]
        for r in subject.expected_requests():
            start=date.fromisoformat(r['params']['startDate']);end=date.fromisoformat(r['params']['endDate'])
            dates.extend(str(start+timedelta(days=n)) for n in range((end-start).days+1))
        self.assertEqual(len(dates),len(set(dates)))
        self.assertNotIn('2019-12-31',dates)
        self.assertNotIn('2020-01-02',dates)
        dates.extend(['2019-12-31','2020-01-01','2020-01-02'])
        first,last=date(2011,12,1),date(2023,9,30)
        self.assertEqual(sorted(dates),[str(first+timedelta(days=n)) for n in range((last-first).days+1)])


if __name__=='__main__':
    unittest.main()
