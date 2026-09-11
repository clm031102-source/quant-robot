from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import tempfile
from threading import Barrier
import unittest

from quant_robot.execution.offline_journal import OfflineOrderJournal
from tests.unit.test_offline_order_admission import NOW, SYMBOL, OTHER, context, instrument, intent, policy


class GuardedOrderConcurrencyTests(unittest.TestCase):
    def test_two_admissions_cannot_both_use_same_snapshot_and_exceed_position_limit(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "guarded.sqlite"
            with OfflineOrderJournal.create(path, initial_cash="3000", initial_positions={},
                    commission_bps="0.5", minimum_commission="5", admission_policy=policy()) as original:
                packet = context(original)
                packet.update(instruments={s: instrument(s) for s in (SYMBOL, OTHER)}, sellable_positions={})
                original.begin_session(packet, clock=lambda: NOW)
                barrier = Barrier(2)

                def writer(key):
                    with OfflineOrderJournal(path) as book:
                        packet = context(book)
                        barrier.wait(timeout=10)
                        try:
                            book.admit(intent(key, quantity=200), packet, clock=lambda: NOW)
                            return "admitted"
                        except ValueError as exc:
                            return str(exc)
                with ThreadPoolExecutor(max_workers=2) as pool:
                    outcomes = list(pool.map(writer, ["one", "two"]))
                self.assertCountEqual(outcomes, ["admitted", "risk context has a stale journal anchor"])
                self.assertEqual(len(original.snapshot()["orders"]), 1)
                self.assertFalse(original.snapshot()["executable"])


if __name__ == "__main__":
    unittest.main()
