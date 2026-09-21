"""Projection reuse must preserve the durable journal's observable semantics."""
from contextlib import closing
from decimal import Decimal
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

from quant_robot.execution import offline_journal
from quant_robot.execution.offline_journal import OfflineOrderJournal, _event


class OfflineJournalProjectionTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.path = Path(directory.name) / "journal.sqlite"
        self.book = OfflineOrderJournal.create(self.path, initial_cash="3000", initial_positions={},
            commission_bps="0.5", minimum_commission="5")
        self.addCleanup(self.book.close)

    def order(self, key="one"):
        self.book.register(order_id=key, idempotency_key=key, symbol="510300.SH",
            side="BUY", quantity=100, limit_price="4")

    def test_growing_local_history_does_not_replay_old_events_each_observation(self):
        self.book.snapshot()
        with patch.object(offline_journal, "apply_event", wraps=offline_journal.apply_event) as apply:
            for index in range(250):
                self.book.set_kill_switch(index % 2 == 0, reason="synthetic growth probe")
                self.book.snapshot()
                self.book.snapshot()
            self.assertLessEqual(apply.call_count, 500)
        self.assertEqual(self.book.snapshot()["sequence"], 251)

    def test_callers_cannot_mutate_reused_nested_state(self):
        self.order()
        state = self.book._read()
        state["cash"] = Decimal("999999")
        state["orders"]["one"]["quantity"] = 900
        state["faults"].add("invented")
        snapshot = self.book.snapshot()
        snapshot["orders"]["one"]["quantity"] = 800
        actual = self.book.snapshot()
        self.assertEqual(Decimal(actual["cash"]), 3000)
        self.assertEqual(actual["orders"]["one"]["quantity"], 100)
        self.assertEqual(actual["faults"], [])

    def test_external_committed_event_invalidates_warm_projection(self):
        with OfflineOrderJournal(self.path) as other:
            self.book.snapshot()
            other.set_kill_switch(True, reason="external stop")
            self.assertTrue(self.book.snapshot()["paused"])
            with self.assertRaisesRegex(ValueError, "paused"):
                self.order()

    def test_warm_projection_still_detects_modified_old_payload(self):
        for external in (False, True):
            with self.subTest(external=external):
                self.book.snapshot()
                connection = sqlite3.connect(self.path) if external else self.book._db
                try:
                    connection.execute("DROP TRIGGER IF EXISTS events_no_update")
                    original = connection.execute("SELECT payload FROM events WHERE sequence=1").fetchone()[0]
                    connection.execute("UPDATE events SET payload=? WHERE sequence=1", (original + " ",))
                    connection.commit()
                    with self.assertRaisesRegex(ValueError, "hash or sequence"):
                        self.book.snapshot()
                    connection.execute("UPDATE events SET payload=? WHERE sequence=1", (original,))
                    connection.commit()
                finally:
                    if external:
                        connection.close()

    def test_failed_append_does_not_cache_uncommitted_order_or_identity(self):
        self.book.snapshot()
        append = self.book._append
        def fail(state, event):
            append(state, event)
            raise RuntimeError("injected failure after insert")
        with patch.object(self.book, "_append", side_effect=fail):
            with self.assertRaisesRegex(RuntimeError, "after insert"):
                self.order()
        self.assertEqual(self.book.snapshot()["sequence"], 1)
        self.assertEqual(self.book.snapshot()["orders"], {})
        self.order()
        self.assertEqual(self.book.snapshot()["sequence"], 2)

    def test_manual_transaction_read_is_not_published_after_rollback(self):
        self.book.snapshot()
        self.book._db.execute("BEGIN IMMEDIATE")
        self.book._append(self.book._read(), _event("KILL_SWITCH", {"enabled": True}))
        self.assertTrue(self.book.snapshot()["paused"])
        self.book._db.rollback()
        self.assertFalse(self.book.snapshot()["paused"])
        self.assertEqual(self.book.snapshot()["sequence"], 1)

    def test_builder_mutation_is_not_durable_without_an_event(self):
        def mutate(state):
            state["cash"] = Decimal("999999")
            state["faults"].add("invented")
            return None
        self.book._run(mutate)
        self.assertEqual(Decimal(self.book.snapshot()["cash"]), 3000)
        self.assertFalse(self.book.snapshot()["paused"])

    def test_builder_mutation_is_not_included_in_committed_event_projection(self):
        def mutate(state):
            state["cash"] = Decimal("999999")
            return _event("KILL_SWITCH", {"enabled": True})
        self.book._run(mutate)
        self.assertEqual(Decimal(self.book.snapshot()["cash"]), 3000)
        self.assertTrue(self.book.snapshot()["paused"])

    def test_external_commit_between_replay_and_return_is_seen_on_next_read(self):
        with OfflineOrderJournal(self.path) as other:
            original = self.book._read
            # Trigger the external commit while the SELECT is being replayed.
            apply = offline_journal.apply_event
            fired = False
            def interleave(state, event):
                nonlocal fired
                apply(state, event)
                if not fired:
                    fired = True
                    other.set_kill_switch(True, reason="interleaved stop")
            with patch.object(offline_journal, "apply_event", side_effect=interleave):
                first = original()
            self.assertFalse(first["kill_switch"])
            self.assertTrue(self.book.snapshot()["paused"])

    def test_external_commit_after_local_commit_cannot_be_tagged_as_cached_state(self):
        with OfflineOrderJournal(self.path) as other:
            connection = self.book._db
            class CommitHook:
                def __getattr__(self, name):
                    return getattr(connection, name)
                def commit(self):
                    connection.commit()
                    other.set_kill_switch(False, reason="newer external state")
            self.book._db = CommitHook()
            try:
                self.book.set_kill_switch(True, reason="local state")
            finally:
                self.book._db = connection
            actual = self.book.snapshot()
            self.assertEqual(actual["sequence"], 3)
            self.assertFalse(actual["paused"])

    def test_commit_failure_does_not_publish_inserted_state(self):
        self.book.snapshot()
        connection = self.book._db
        class FailedCommit:
            def __getattr__(self, name):
                return getattr(connection, name)
            def commit(self):
                raise sqlite3.OperationalError("injected commit failure")
        self.book._db = FailedCommit()
        try:
            with self.assertRaisesRegex(sqlite3.OperationalError, "commit failure"):
                self.order()
        finally:
            self.book._db = connection
        self.assertEqual(self.book.snapshot()["sequence"], 1)
        self.assertEqual(self.book.snapshot()["orders"], {})
        self.order()

    def test_restart_replays_history_and_quarantines_open_orders(self):
        self.order()
        self.book.snapshot()
        with patch.object(offline_journal, "apply_event", wraps=offline_journal.apply_event) as apply:
            with OfflineOrderJournal(self.path) as reopened:
                self.assertGreaterEqual(apply.call_count, 2)
                self.assertEqual(reopened.snapshot()["orders"]["one"]["status"], "UNKNOWN")
        self.assertTrue(self.book.snapshot()["paused"])

    def test_invalid_external_tail_is_not_hidden_by_projection(self):
        self.book.snapshot()
        with closing(sqlite3.connect(self.path)) as connection:
            connection.execute("INSERT INTO events VALUES (2, 'invalid', '{}', 'invalid', 'invalid')")
            connection.commit()
        with self.assertRaisesRegex(ValueError, "hash or sequence"):
            self.book.snapshot()


if __name__ == "__main__":
    unittest.main()
