from pathlib import Path
import tempfile
import unittest

from quant_robot.execution.offline_runtime_health import health_record
from quant_robot.execution.offline_supervisor import _latch, assess_worker, validate_supervisor_limits
from quant_robot.execution.offline_journal import OfflineOrderJournal


class OfflineSupervisorContractTests(unittest.TestCase):
    def setUp(self):
        self.identity=dict(instance_id="a"*32,journal_path=str(Path("fixture.sqlite").resolve()),genesis_hash="b"*64)

    def worker(self, **changes):
        row=health_record("worker",**self.identity,process_id=123,monotonic_ns=10000000000,
            phase="idle",owns_journal=True,completed_ticks=3,last_completed_monotonic_ns=9900000000,last_tick_status="ready")
        row.update(changes)
        return row

    def assess(self, row, **extra):
        return assess_worker(row,**self.identity,process_id=123,now_ns=11000000000,max_age_seconds=2,**extra)

    def test_stopped_tick_is_explicitly_stopped_not_current_ready(self):
        self.assertEqual(self.assess(self.worker(phase="stopped"))["phase"],"stopped")

    def test_tick_completion_cannot_go_backward(self):
        with self.assertRaisesRegex(ValueError,"regress"):
            self.assess(self.worker(),previous_ticks=4)

    def test_invalid_phase_counter_completion_or_ownership_fails_closed(self):
        for changes in ({"phase":"ready"},{"completed_ticks":True},{"completed_ticks":-1},
                {"last_completed_monotonic_ns":11000000000},{"last_completed_monotonic_ns":None},
                {"owns_journal":False},{"last_tick_status":"profit_ready"}):
            with self.subTest(changes=changes),self.assertRaises(ValueError):self.assess(self.worker(**changes))

    def test_idle_interval_cannot_exceed_stall_budget(self):
        validate_supervisor_limits(1,.1,10,5)
        for values in ((5,.1,10,5),(1,0,10,5),(1,.1,float('inf'),5),(1,.1,10,True)):
            with self.subTest(values=values),self.assertRaises(ValueError):validate_supervisor_limits(*values)

    def test_pause_refuses_a_replaced_journal_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'journal.sqlite'
            with OfflineOrderJournal.create(path,initial_cash='3000',initial_positions={},commission_bps='.5',minimum_commission='5') as book:
                before=book.snapshot()
                result=_latch(path,'f'*64,'wrong journal')
                self.assertEqual(result['status'],'failed')
                self.assertIn('replaced',result['reason'])
                self.assertEqual(book.snapshot(),before)


if __name__ == "__main__": unittest.main()
