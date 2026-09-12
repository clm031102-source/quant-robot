import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from quant_robot.execution.offline_journal import OfflineOrderJournal
from quant_robot.execution.offline_runtime import OfflineRuntime
from quant_robot.execution.offline_runtime_health import journal_identity, read_health
from quant_robot.execution import offline_supervisor
from quant_robot.execution.offline_supervisor import launch_owned_python, supervise_worker
from tests.unit.test_offline_runtime import create_book, observation
from tests.unit.test_offline_order_admission import NOW


class OfflineSupervisorProcessTests(unittest.TestCase):
    def setUp(self):
        directory=tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root=Path(directory.name)
        self.path=self.root/'journal.sqlite'; self.feed=self.root/'feed.json'
        self.health=self.root/'worker.json';self.permit=self.root/'permit.json';self.report=self.root/'monitor.json'
        create_book(self.path)
        with OfflineRuntime(self.path,clock=lambda:NOW) as runtime:
            self.feed.write_text(json.dumps(observation(runtime,opening=True)),encoding='utf-8')

    def snapshot(self):
        with OfflineOrderJournal(self.path) as book:return book.snapshot()

    def cli(self, *extra):
        return [sys.executable,'scripts/run_offline_supervisor.py','--journal',str(self.path),
            '--feed',str(self.feed),'--report',str(self.report),'--health',str(self.health),'--permit',str(self.permit),
            '--interval-seconds','.25','--poll-seconds','.03','--startup-seconds','5','--stall-seconds','1',
            '--max-ticks','3','--fixture-clock-start',NOW.isoformat(),*extra]

    def launch_fixture(self, body):
        children=[]
        error_paths=[]
        self.fixture_errors=lambda:'\n'.join(path.read_text(encoding='utf-8',errors='replace') for path in error_paths if path.exists())[-6000:]
        source="""
import json,sys,time,os
from quant_robot.execution.offline_runtime import OfflineRuntime
from quant_robot.execution.offline_runtime_health import WorkerHealth
from tests.unit.test_offline_order_admission import NOW,intent
from tests.unit.test_offline_runtime import observation
b=json.loads(sys.argv[1])
with OfflineRuntime(b['journal_path'],clock=lambda:NOW) as runtime:
    health=WorkerHealth(b['health_path'],**{k:b[k] for k in ('instance_id','journal_path','genesis_hash')})
    health.publish('starting')
"""+''.join('    '+line+'\n' for line in body.splitlines())
        def launch(binding):
            error_path=self.root/('fixture-child-'+str(len(children))+'.stderr')
            error_paths.append(error_path)
            with error_path.open('wb') as errors:
                child=launch_owned_python(['-c',source,json.dumps(binding)],stderr=errors)
            children.append(child)
            return child
        def cleanup():
            for child in children:
                if child.poll() is None:child.kill()
                child.wait(timeout=5)
        self.addCleanup(cleanup)
        return launch,children

    def supervise(self, launch, *, stall_seconds=.4, **options):
        return supervise_worker(self.path,health_path=self.health,permit_path=self.permit,report_path=self.report,
            launch=launch,interval_seconds=.05,poll_seconds=.02,startup_seconds=2,stall_seconds=stall_seconds,**options)

    def test_normal_bounded_cli_exits_with_stopped_health_and_no_fault(self):
        result=subprocess.run(self.cli(),capture_output=True,text=True,timeout=15)
        self.assertEqual(result.returncode,0,result.stderr)
        monitor=json.loads(result.stdout);worker=json.loads(self.health.read_text())
        self.assertEqual(monitor['phase'],'stopped');self.assertFalse(monitor['child_alive'])
        self.assertEqual(worker['phase'],'stopped');self.assertEqual(worker['last_tick_status'],'ready')
        self.assertEqual(worker['completed_ticks'],3)
        self.assertEqual(self.snapshot()['faults'],[])
        self.assertEqual(worker['instance_id'],monitor['instance_id'])
        self.assertNotEqual(worker['updated_wall_utc'],NOW.isoformat())

    def test_owned_handle_is_the_interpreter_pid_and_preserves_environment(self):
        source="import json,os,sys;import pandas;print(json.dumps(dict(pid=os.getpid(),prefix=sys.prefix)))"
        child=launch_owned_python(['-c',source],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        output,errors=child.communicate(timeout=10)
        self.assertEqual(child.returncode,0,errors)
        result=json.loads(output)
        self.assertEqual(result['pid'],child.pid)
        self.assertEqual(Path(result['prefix']).resolve(),Path(sys.prefix).resolve())

    def test_nested_owned_launches_keep_handles_on_both_interpreters(self):
        source="""
import json,os,subprocess,sys
from quant_robot.execution.offline_supervisor import launch_owned_python
child=launch_owned_python(['-c','import json,os,sys;print(json.dumps(dict(pid=os.getpid(),prefix=sys.prefix)))'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
out,err=child.communicate(timeout=10)
assert child.returncode==0,err
print(json.dumps(dict(pid=os.getpid(),nested_handle_pid=child.pid,nested=json.loads(out))))
"""
        child=launch_owned_python(['-c',source],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        out,err=child.communicate(timeout=15)
        self.assertEqual(child.returncode,0,err)
        result=json.loads(out)
        self.assertEqual(result['pid'],child.pid)
        self.assertEqual(result['nested_handle_pid'],result['nested']['pid'])
        self.assertEqual(Path(result['nested']['prefix']).resolve(),Path(sys.prefix).resolve())

    def test_blocked_child_is_terminated_and_fault_is_durable(self):
        launch,children=self.launch_fixture('time.sleep(20)')
        result=self.supervise(launch)
        self.assertEqual(result['phase'],'failed')
        self.assertEqual(result['pause_enforcement']['status'],'latched')
        self.assertIsNotNone(children[0].poll())
        self.assertIn('runtime_supervision_requires_review',self.snapshot()['faults'])

    def test_fresh_but_nonprogressing_worker_cannot_keep_monitor_green(self):
        launch,children=self.launch_fixture("for _ in range(1000):\n    health.publish('ticking')\n    time.sleep(.015)")
        result=self.supervise(launch)
        self.assertIn('completed tick progress deadline',result['failure'])
        self.assertIsNotNone(children[0].poll())
        self.assertEqual(result['pause_enforcement']['status'],'latched')

    def test_exit_after_preparing_order_recovers_unknown_and_never_restarts(self):
        # Exercise crash recovery after work, allowing scheduling/disk latency.
        # The separate stalled-worker tests retain the short watchdog deadline.
        launch,children=self.launch_fixture("time.sleep(.6)\npacket=observation(runtime,opening=True)\npacket['intents']=[intent()]\nhealth.complete_tick(runtime.tick(packet))\nos._exit(7)")
        result=self.supervise(launch,stall_seconds=5)
        state=self.snapshot()
        self.assertEqual(len(children),1)
        self.assertEqual(result['child_returncode'],7,json.dumps(result)+"\n"+self.fixture_errors())
        self.assertEqual(result['completed_ticks'],1)
        self.assertIn('worker exited without verified clean stop: 7',result['failure'])
        self.assertEqual(state['orders']['one']['status'],'UNKNOWN')
        self.assertEqual(state['orders']['one']['filled_quantity'],0)
        self.assertIn('runtime_supervision_requires_review',state['faults'])

    def test_identity_change_after_ownership_is_observed_stops_owned_child(self):
        launch,children=self.launch_fixture('time.sleep(20)')
        corrupted=False
        def corrupt(record):
            nonlocal corrupted
            if record['owner_observed'] and not corrupted:
                row=json.loads(self.health.read_text());row['instance_id']='f'*32
                self.health.write_text(json.dumps(row));corrupted=True
        result=self.supervise(launch,on_observation=corrupt)
        self.assertTrue(corrupted)
        self.assertIn('identity',result['failure'])
        self.assertEqual(result['pause_enforcement']['status'],'latched')
        self.assertIsNotNone(children[0].poll())

    def test_report_write_failure_still_stops_child_and_latches_journal(self):
        launch,children=self.launch_fixture('time.sleep(20)')
        write=offline_supervisor.atomic_write_json
        def fail(path,record):
            if Path(path)==self.report and record.get('owner_observed'):
                raise OSError('injected disk output failure')
            return write(path,record)
        with patch.object(offline_supervisor,'atomic_write_json',side_effect=fail):
            result=self.supervise(launch)
        self.assertEqual(result['status'],'attention')
        self.assertEqual(result['pause_enforcement']['status'],'latched')
        self.assertFalse(result['child_alive'])
        self.assertIn('runtime_supervision_requires_review',self.snapshot()['faults'])

    def test_journal_pause_failure_is_reported_without_claiming_enforcement(self):
        launch,children=self.launch_fixture('time.sleep(20)')
        with patch.object(offline_supervisor.OfflineOrderJournal,'__init__',side_effect=sqlite3.OperationalError('injected database failure')):
            result=self.supervise(launch)
        self.assertEqual(result['pause_enforcement']['status'],'failed')
        self.assertIn('database failure',result['pause_enforcement']['reason'])
        self.assertFalse(result['child_alive'])
        self.assertEqual(result['status'],'attention')

    def test_existing_driver_is_not_recovered_or_stopped_by_second_monitor(self):
        launch,children=self.launch_fixture('time.sleep(20)')
        with OfflineRuntime(self.path,clock=lambda:NOW) as owner:
            before=owner.book.snapshot()
            with self.assertRaisesRegex(ValueError,'driver'):
                self.supervise(launch)
            self.assertEqual(owner.book.snapshot(),before)
        self.assertEqual(children,[])

    def test_second_supervisor_is_rejected_before_launch(self):
        from quant_robot.execution.offline_runtime_lease import RuntimeLease
        launch,children=self.launch_fixture('time.sleep(20)')
        with RuntimeLease(self.path,role='supervisor'):
            with self.assertRaisesRegex(ValueError,'supervisor'):self.supervise(launch)
        self.assertEqual(children,[])

    def test_driver_racing_between_probe_and_launch_is_not_recovered(self):
        launch_child,children=self.launch_fixture('time.sleep(20)')
        owners=[]
        def launch(binding):
            owner=OfflineRuntime(self.path,clock=lambda:NOW)
            owners.append(owner)
            return launch_child(binding)
        try:
            result=self.supervise(launch)
            self.assertEqual(result['pause_enforcement']['status'],'not_attempted')
            self.assertEqual(owners[0].book.snapshot()['faults'],[])
            self.assertIsNotNone(children[0].poll())
        finally:
            for owner in owners:owner.close()

    def test_startup_timeout_without_ownership_does_not_recover_unrelated_journal(self):
        before=self.snapshot()
        children=[]
        def launch(binding):
            child=launch_owned_python(['-c','import time;time.sleep(20)'])
            children.append(child)
            return child
        try:
            result=supervise_worker(self.path,health_path=self.health,permit_path=self.permit,report_path=self.report,
                launch=launch,interval_seconds=.05,poll_seconds=.02,startup_seconds=.3,stall_seconds=.4)
            self.assertIn('startup deadline',result['failure'])
            self.assertEqual(result['pause_enforcement']['status'],'not_attempted')
            self.assertIsNotNone(children[0].poll())
            self.assertEqual(self.snapshot(),before)
        finally:
            for child in children:
                if child.poll() is None:child.kill()
                child.wait(timeout=5)

    def test_output_alias_is_rejected_before_worker_or_journal_changes(self):
        original=self.path.read_bytes()
        for extra in (['--health',str(self.path)],['--permit',str(self.feed)],
                ['--worker-report',str(self.health)],['--report',str(self.path)+'-wal']):
            with self.subTest(extra=extra):
                result=subprocess.run(self.cli(*extra),capture_output=True,text=True,timeout=10)
                self.assertEqual(result.returncode,2,result.stderr)
                self.assertEqual(self.path.read_bytes(),original)

    def test_supervisor_entrypoint_uses_workspace_with_stale_installed_package(self):
        package=self.root/'legacy'/'quant_robot';package.mkdir(parents=True)
        (package/'__init__.py').write_text("raise RuntimeError('stale package imported')")
        result=subprocess.run(self.cli(),capture_output=True,text=True,timeout=15,
            env={**os.environ,'PYTHONPATH':str(package.parent)})
        self.assertEqual(result.returncode,0,result.stderr)
        self.assertEqual(json.loads(result.stdout)['phase'],'stopped')

    def test_expired_supervisor_permit_latches_worker_without_discarding_valuation(self):
        identity=dict(instance_id='a'*32,**journal_identity(self.path))
        error_path=self.root/'permit-worker-errors.log'
        errors=error_path.open('w',encoding='utf-8');self.addCleanup(errors.close)
        def diagnostic():
            errors.flush()
            return error_path.read_text(encoding='utf-8',errors='replace')[-6000:]
        source="""
import json,sys,time
from quant_robot.execution.offline_runtime_health import health_record
from quant_robot.storage.atomic import atomic_write_json
identity=json.loads(sys.argv[2])
for _ in range(500):
    atomic_write_json(sys.argv[1],health_record('supervisor',**identity,phase='running'))
    time.sleep(.02)
"""
        producer=launch_owned_python(['-c',source,str(self.permit),json.dumps(identity)],stderr=errors)
        worker=None
        try:
            deadline=time.monotonic()+5
            while not self.permit.exists() and time.monotonic()<deadline:time.sleep(.01)
            self.assertTrue(self.permit.exists())
            command=[sys.executable,'scripts/run_offline_runtime.py','--journal',str(self.path),'--feed',str(self.feed),
                '--health',str(self.health),'--instance-id',identity['instance_id'],'--supervisor-permit',str(self.permit),
                '--supervisor-pid',str(producer.pid),'--supervisor-genesis',identity['genesis_hash'],'--supervisor-max-age','.5',
                '--interval-seconds','.05','--max-ticks','50','--fixture-clock-start',NOW.isoformat()]
            worker=launch_owned_python(command[1:],stderr=errors)
            deadline=time.monotonic()+5
            ready=False
            while time.monotonic()<deadline:
                if self.health.exists():
                    health=read_health(self.health)
                    if health.get('completed_ticks',0)>=2 and health.get('last_tick_status')=='ready':
                        ready=True
                        break
                if worker.poll() is not None:break
                time.sleep(.01)
            self.assertIsNone(worker.poll(),diagnostic())
            self.assertTrue(ready,diagnostic())
            producer.kill();producer.wait(timeout=5)
            self.assertEqual(worker.wait(timeout=10),0,diagnostic())
            state=self.snapshot()
            self.assertIn('runtime_supervision_requires_review',state['faults'])
            self.assertIsNotNone(state['portfolio_valuation']['last_valid'])
            self.assertEqual(json.loads(self.health.read_text())['last_tick_status'],'attention')
        finally:
            for child in (producer,worker):
                if child is not None:
                    if child.poll() is None:child.kill()
                    child.wait(timeout=5)


if __name__ == '__main__': unittest.main()
