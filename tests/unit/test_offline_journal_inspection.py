from pathlib import Path
import sqlite3
import tempfile
import unittest

from quant_robot.execution.offline_journal import OfflineOrderJournal, _event


class OfflineJournalInspectionTests(unittest.TestCase):
    def setUp(self):
        directory=tempfile.TemporaryDirectory();self.addCleanup(directory.cleanup)
        self.path=Path(directory.name)/'journal.sqlite'
        self.book=OfflineOrderJournal.create(self.path,initial_cash='3000',initial_positions={},
            commission_bps='0.5',minimum_commission='5')
        self.addCleanup(self.book.close)
        self.book.register(order_id='one',idempotency_key='one',symbol='510300.SH',side='BUY',quantity=100,limit_price='4')

    def test_inspection_preserves_pending_order_and_journal_anchor(self):
        before=self.book.snapshot()
        inspected=OfflineOrderJournal.inspect_snapshot(self.path)
        self.assertEqual(inspected,before)
        self.assertEqual(inspected['orders']['one']['status'],'PENDING')
        self.assertEqual(self.book.snapshot(),before)
        self.assertFalse(inspected['executable'])

    def test_inspection_does_not_create_a_missing_database(self):
        missing=self.path.parent/'missing.sqlite'
        with self.assertRaises(sqlite3.OperationalError): OfflineOrderJournal.inspect_snapshot(missing)
        self.assertFalse(missing.exists())

    def test_inspection_reads_only_committed_state_during_an_external_write(self):
        before=self.book.snapshot()
        self.book._db.execute('BEGIN IMMEDIATE')
        try:
            self.book._append(self.book._read(),_event('KILL_SWITCH',{'enabled':True,'reason':'uncommitted'}))
            self.assertEqual(OfflineOrderJournal.inspect_snapshot(self.path),before)
            self.book._db.commit()
        finally:
            if self.book._db.in_transaction:self.book._db.rollback()
        after=OfflineOrderJournal.inspect_snapshot(self.path)
        self.assertTrue(after['kill_switch'])
        self.assertEqual(after['sequence'],before['sequence']+1)
        self.assertEqual(after['orders'],before['orders'])

    def test_modified_inspection_result_cannot_change_the_next_read(self):
        first=OfflineOrderJournal.inspect_snapshot(self.path)
        first['orders']['one']['quantity']=900
        first['faults'].append('invented')
        second=OfflineOrderJournal.inspect_snapshot(self.path)
        self.assertEqual(second['orders']['one']['quantity'],100)
        self.assertNotIn('invented',second['faults'])

    def test_corrupt_journal_is_rejected_without_rewriting_it(self):
        self.book.close()
        connection=sqlite3.connect(self.path)
        try:
            connection.execute('DROP TRIGGER events_no_update')
            connection.execute("UPDATE events SET event_hash=? WHERE sequence=2",('0'*64,))
            connection.commit()
        finally:
            connection.close()
        original=self.path.read_bytes()
        with self.assertRaisesRegex(ValueError,'hash|sequence'):
            OfflineOrderJournal.inspect_snapshot(self.path)
        self.assertEqual(self.path.read_bytes(),original)

    def test_unsupported_schema_is_rejected_without_repairing_it(self):
        self.book._db.execute('PRAGMA user_version=99')
        with self.assertRaisesRegex(ValueError,'schema'):
            OfflineOrderJournal.inspect_snapshot(self.path)
        self.assertEqual(self.book._db.execute('PRAGMA user_version').fetchone()[0],99)


if __name__=='__main__':unittest.main()
