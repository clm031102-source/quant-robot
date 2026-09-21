import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest

from quant_robot.execution.offline_journal import OfflineOrderJournal
from tests.unit.test_offline_execution_evidence import supplement


class OfflineCorporateReviewCliTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        self.directory=Path(temporary.name);self.path=self.directory/'book.sqlite'
        self.root=Path(__file__).resolve().parents[2]
        with OfflineOrderJournal.create(self.path,initial_cash='3000',initial_positions={},commission_bps='.5',minimum_commission='5') as book:
            book.register(order_id='one',idempotency_key='one',symbol='510300.SH',side='BUY',quantity=100,limit_price='4')
        self.before=self.path.read_bytes()

    def run_cli(self, output, *extra, env=None):
        return subprocess.run([sys.executable,'scripts/run_offline_corporate_review.py','--journal',str(self.path),
            '--output',str(output),*extra],cwd=self.root,env=env,capture_output=True,text=True,timeout=15)

    def test_cli_uses_workspace_and_keeps_pending_order_unchanged(self):
        legacy=self.directory/'legacy'/'quant_robot';legacy.mkdir(parents=True)
        (legacy/'__init__.py').write_text("raise RuntimeError('stale package used')",encoding='utf-8')
        env=dict(os.environ);env['PYTHONPATH']=str(legacy.parent)
        output=self.directory/'review.json';result=self.run_cli(output,env=env)
        self.assertEqual(result.returncode,0,result.stderr)
        packet=json.loads(output.read_text(encoding='utf-8'))
        self.assertEqual(packet['status'],'inspection_only')
        self.assertFalse(packet['automatic_correction_allowed'])
        self.assertEqual(self.path.read_bytes(),self.before)
        self.assertEqual(OfflineOrderJournal.inspect_snapshot(self.path)['orders']['one']['status'],'PENDING')

    def test_output_cannot_replace_journal_or_protected_sidecars(self):
        paths=[self.path,*[Path(str(self.path)+suffix) for suffix in ('-wal','-shm','.driver.lock','.supervisor.lock')]]
        for output in paths:
            with self.subTest(output=output):
                result=self.run_cli(output)
                self.assertNotEqual(result.returncode,0)
                self.assertIn('must not replace or alias',result.stderr)
        self.assertEqual(self.path.read_bytes(),self.before)

    def test_output_hard_link_alias_cannot_replace_the_journal(self):
        alias=self.directory/'alias.json';os.link(self.path,alias)
        result=self.run_cli(alias)
        self.assertNotEqual(result.returncode,0)
        self.assertIn('must not replace or alias',result.stderr)
        self.assertEqual(alias.read_bytes(),self.before)
        self.assertEqual(self.path.read_bytes(),self.before)

    def test_limit_rejection_does_not_publish_or_overwrite_a_report(self):
        output=self.directory/'existing.json';output.write_text('previous evidence',encoding='utf-8')
        result=self.run_cli(output,'--max-events','1')
        self.assertNotEqual(result.returncode,0)
        self.assertIn('no partial evidence',result.stderr)
        self.assertEqual(output.read_text(encoding='utf-8'),'previous evidence')

    def test_corrupt_chain_cannot_produce_a_verified_review(self):
        connection=sqlite3.connect(self.path)
        try:
            connection.execute('DROP TRIGGER events_no_update')
            connection.execute("UPDATE events SET event_hash=? WHERE sequence=2",('0'*64,));connection.commit()
        finally:connection.close()
        output=self.directory/'review.json';result=self.run_cli(output)
        self.assertNotEqual(result.returncode,0)
        self.assertIn('hash or sequence',result.stderr)
        self.assertFalse(output.exists())

    def test_output_byte_limit_preserves_old_report_and_cleans_partial_temp_file(self):
        output=self.directory/'review.json';output.write_text('previous report',encoding='utf-8')
        result=self.run_cli(output,'--max-output-bytes','1')
        self.assertNotEqual(result.returncode,0)
        self.assertIn('output byte limit',result.stderr)
        self.assertEqual(output.read_text(encoding='utf-8'),'previous report')
        self.assertEqual(list(self.directory.glob('.review.*.json')),[])
        self.assertEqual(self.path.read_bytes(),self.before)

    def source(self):
        with OfflineOrderJournal(self.path) as book:book.fill('one','fill1',40,'4')
        self.before=self.path.read_bytes()
        source=self.directory/'source.json'
        source.write_text(json.dumps(supplement(OfflineOrderJournal.inspect_evidence(self.path))),encoding='utf-8')
        return source

    def test_cli_attaches_bounded_assertions_and_preserves_both_inputs(self):
        source=self.source();before=source.read_bytes();output=self.directory/'review.json'
        result=self.run_cli(output,'--execution-evidence',str(source))
        self.assertEqual(result.returncode,0,result.stderr)
        packet=json.loads(output.read_text(encoding='utf-8'))
        self.assertTrue(packet['execution_supplement']['journal_and_receipt_binding_verified'])
        self.assertFalse(packet['execution_supplement']['source_authenticated'])
        self.assertEqual(source.read_bytes(),before);self.assertEqual(self.path.read_bytes(),self.before)

    def test_output_cannot_replace_execution_evidence_or_its_alias(self):
        source=self.source();before=source.read_bytes();alias=self.directory/'alias.json';os.link(source,alias)
        for output in (source,alias):
            result=self.run_cli(output,'--execution-evidence',str(source))
            self.assertNotEqual(result.returncode,0);self.assertIn('must not replace or alias',result.stderr)
        self.assertEqual(source.read_bytes(),before);self.assertEqual(self.path.read_bytes(),self.before)

    def test_invalid_or_stale_execution_evidence_preserves_previous_report(self):
        source=self.source();packet=json.loads(source.read_text());packet['journal']['sequence']+=1
        output=self.directory/'review.json';output.write_text('previous',encoding='utf-8')
        for content in ('null','{"x":NaN}',json.dumps(packet)):
            source.write_text(content,encoding='utf-8');result=self.run_cli(output,'--execution-evidence',str(source))
            self.assertNotEqual(result.returncode,0);self.assertNotIn('Traceback',result.stderr)
            self.assertEqual(output.read_text(encoding='utf-8'),'previous')
        self.assertEqual(self.path.read_bytes(),self.before)


if __name__=='__main__':unittest.main()
