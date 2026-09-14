from decimal import Decimal
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from quant_robot.execution.offline_runtime import OfflineRuntime
from quant_robot.execution.offline_journal import OfflineOrderJournal
from tests.unit.test_offline_target_compiler import create_target_book, target
from tests.unit.test_offline_order_admission import NOW, SYMBOL, intent
from tests.unit.test_offline_runtime import observation


class OfflineTargetRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/'runtime.sqlite'
        with create_target_book(self.path,cash='1000'):pass
        self.runtime=OfflineRuntime(self.path,clock=lambda:NOW)
        self.addCleanup(lambda:self.runtime.close())

    def feed(self, **commands):
        return {**observation(self.runtime),**commands}

    def test_driver_compiles_then_guards_dispatch_without_inventing_fill(self):
        feed=self.feed(targets=[target(self.runtime.book)])
        report=self.runtime.tick(feed)
        self.assertEqual(report['status'],'ready')
        snap=self.runtime.book.snapshot()
        order=snap['orders']['target-one']
        self.assertEqual(order['quantity'],200)
        self.assertIn('dispatch',order)
        self.assertEqual(order['filled_quantity'],0)
        self.assertEqual(Decimal(snap['cash']),1000)
        self.assertTrue(any(s['stage']=='post_order_valuation' for s in report['steps']))
        self.assertEqual(report['counts_as_forward_paper_days'],0)
        self.assertFalse(report['qualifies_for_strategy_promotion'])
        self.assertFalse(report['executable'])
        self.runtime.tick(feed)
        self.assertEqual(self.runtime.book.snapshot()['orders'],snap['orders'])

    def test_existing_intent_group_is_admitted_first_and_targets_use_remaining_budget(self):
        feed=self.feed(intents=[intent('explicit')],targets=[target(self.runtime.book)])
        report=self.runtime.tick(feed)
        self.assertEqual(report['status'],'ready')
        self.assertEqual(self.runtime.book.snapshot()['orders']['target-one']['quantity'],100)
        self.assertEqual(Decimal(self.runtime.book.snapshot()['reserved_cash']),810)

    def test_same_identity_across_groups_is_not_reinterpreted_as_new_request(self):
        feed=self.feed(intents=[intent('target-one')],targets=[target(self.runtime.book)])
        report=self.runtime.tick(feed)
        self.assertEqual(len(self.runtime.book.snapshot()['orders']),1)
        self.assertNotIn('target_compilation',self.runtime.book.snapshot()['orders']['target-one']['admission'])
        self.assertTrue(any(s['stage']=='target' and s['status']=='already_attempted' for s in report['steps']))

    def test_rejection_remains_attempted_after_restart_and_no_signal_is_retimed(self):
        feed=self.feed(targets=[target(self.runtime.book,signal_timestamp='2026-09-14')])
        self.assertEqual(self.runtime.tick(feed)['status'],'attention')
        self.runtime.close()
        self.runtime=OfflineRuntime(self.path,clock=lambda:NOW)
        report=self.runtime.tick(self.feed(targets=[target(self.runtime.book)]))
        self.assertEqual(self.runtime.book.snapshot()['orders'],{})
        self.assertTrue(any(s['stage']=='target' and s['status']=='already_attempted' for s in report['steps']))

    def test_restart_does_not_recompile_or_resend_active_target(self):
        self.runtime.tick(self.feed(targets=[target(self.runtime.book)]))
        before=self.runtime.book.snapshot()['orders']['target-one']['admission']
        self.runtime.close()
        self.runtime=OfflineRuntime(self.path,clock=lambda:NOW)
        report=self.runtime.tick(self.feed(targets=[target(self.runtime.book,limit_price='3')]))
        row=self.runtime.book.snapshot()['orders']['target-one']
        self.assertEqual(row['status'],'UNKNOWN')
        self.assertEqual(row['admission'],before)
        self.assertEqual(Decimal(self.runtime.book.snapshot()['reserved_cash']),805)
        self.assertFalse(any(s['stage']=='dispatch' for s in report['steps']))

    def test_invalid_target_group_and_supervisor_stop_cannot_admit(self):
        report=self.runtime.tick(self.feed(targets={'quantity':100}))
        self.assertEqual(report['feed_status'],'invalid')
        self.runtime.admission_guard=lambda:'synthetic supervisor stop'
        report=self.runtime.tick(self.feed(targets=[target(self.runtime.book)]))
        self.assertEqual(report['status'],'attention')
        self.assertEqual(self.runtime.book.snapshot()['orders'],{})

    def test_existing_cli_process_accepts_explicit_targets_with_the_full_frozen_account(self):
        path=Path(self.temp.name)/'cli.sqlite'
        feed_path=path.with_suffix('.feed.json')
        report_path=path.with_suffix('.report.json')
        with create_target_book(path) as book:
            packet={**observation(type('BookView',(),{'book':book})()),'targets':[target(book)]}
        feed_path.write_text(json.dumps(packet),encoding='utf-8')
        result=subprocess.run([sys.executable,'scripts/run_offline_runtime.py','--journal',str(path),
            '--feed',str(feed_path),'--report',str(report_path),'--max-ticks','2',
            '--interval-seconds','1','--fixture-clock-start',NOW.isoformat()],
            capture_output=True,text=True,timeout=30)
        self.assertEqual(result.returncode,0,result.stdout+result.stderr)
        reports=[json.loads(line) for line in result.stdout.splitlines()]
        self.assertEqual(len(reports),2)
        # A shared runner can exceed the requested cadence without rejecting
        # the target. Keep that warning, and verify the actual execution state.
        for report in reports:
            self.assertEqual(report['feed_status'],'present',report)
            self.assertFalse(report['paused'],report)
            self.assertEqual(report['faults'],[],report)
            self.assertEqual(report['risk_stop_causes'],[],report)
            self.assertFalse(any(step['status']=='rejected' for step in report['steps']),report)
            self.assertEqual(report['cadence_overrun'],report['tick_duration_seconds'] > 1,report)
            self.assertEqual(report['status'],'attention' if report['cadence_overrun'] else 'ready',report)
            self.assertEqual(report['counts_as_forward_paper_days'],0,report)
            self.assertFalse(report['qualifies_for_strategy_promotion'],report)
            self.assertFalse(report['executable'],report)
        self.assertEqual(json.loads(report_path.read_text(encoding='utf-8')),reports[-1])
        snap=OfflineOrderJournal.inspect_snapshot(path)
        self.assertEqual(snap['risk_session']['session_date'],NOW.date().isoformat())
        self.assertEqual(Decimal(snap['cash']),10000)
        self.assertEqual(Decimal(snap['reserved_cash']),805)
        self.assertEqual(len(snap['orders']),1)
        self.assertEqual(snap['orders']['target-one']['quantity'],200)
        self.assertEqual(snap['orders']['target-one']['filled_quantity'],0)
        self.assertTrue(snap['drawdown_guard_configured'])
