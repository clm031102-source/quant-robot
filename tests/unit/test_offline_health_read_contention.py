import errno
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from quant_robot.execution.offline_runtime_health import read_health, SupervisorPermit, health_record, journal_identity
from quant_robot.execution.offline_runtime import OfflineRuntime
from tests.unit.test_offline_runtime import create_book, observation
from tests.unit.test_offline_order_admission import NOW, intent


class OfflineHealthReadContentionTests(unittest.TestCase):
    def setUp(self):
        temporary=tempfile.TemporaryDirectory();self.addCleanup(temporary.cleanup)
        self.root=Path(temporary.name);self.health=self.root/'health.json'
        self.health.write_text('{"generation":1}',encoding='utf-8')

    @staticmethod
    def error():return PermissionError(errno.EACCES,'synthetic Windows read contention')

    def test_transient_windows_denial_reopens_and_reads_new_bytes(self):
        original=Path.open;attempts=[]
        def open_file(path,*args,**kwargs):
            attempts.append(path)
            if len(attempts)<3:raise self.error()
            return original(path,*args,**kwargs)
        def wait(_seconds):
            with original(self.health,'w',encoding='utf-8') as target:json.dump({'generation':2},target)
        with patch('quant_robot.execution.offline_runtime_health._WINDOWS',True,create=True),patch.object(Path,'open',open_file), \
                patch('quant_robot.execution.offline_runtime_health.time.sleep',side_effect=wait) as sleep:
            self.assertEqual(read_health(self.health),{'generation':2})
        self.assertEqual(len(attempts),3);self.assertEqual(sleep.call_count,2)

    def test_persistent_windows_denial_is_bounded_and_not_returned_as_health(self):
        error=self.error()
        with patch('quant_robot.execution.offline_runtime_health._WINDOWS',True,create=True), \
                patch.object(Path,'open',side_effect=error) as opened,patch('quant_robot.execution.offline_runtime_health.time.sleep') as sleep:
            with self.assertRaises(PermissionError) as caught:read_health(self.health)
        self.assertIs(caught.exception,error)
        self.assertEqual(opened.call_count,6);self.assertEqual(sleep.call_count,5)

    def test_non_windows_permissions_and_other_io_errors_are_not_retried(self):
        for windows,error in ((False,self.error()),(True,OSError(errno.EIO,'device error')),(True,FileNotFoundError('missing'))):
            with self.subTest(windows=windows,error=type(error).__name__), \
                    patch('quant_robot.execution.offline_runtime_health._WINDOWS',windows,create=True), \
                    patch.object(Path,'open',side_effect=error) as opened,patch('quant_robot.execution.offline_runtime_health.time.sleep') as sleep:
                with self.assertRaises(OSError):read_health(self.health)
                self.assertEqual(opened.call_count,1);sleep.assert_not_called()

    def test_malformed_or_oversized_health_is_not_retried(self):
        original=Path.open;attempts=[]
        def open_file(path,*args,**kwargs):attempts.append(path);return original(path,*args,**kwargs)
        for value in ('{','[]','x'*65537):
            self.health.write_text(value,encoding='utf-8');attempts.clear()
            with patch.object(Path,'open',open_file),patch('quant_robot.execution.offline_runtime_health.time.sleep') as sleep:
                with self.assertRaises(ValueError):read_health(self.health)
                self.assertEqual(len(attempts),1);sleep.assert_not_called()

    def test_permission_wait_does_not_refresh_an_expired_supervisor_timestamp(self):
        identity=dict(instance_id='a'*32,journal_path=str(self.root/'book.sqlite'),genesis_hash='b'*64,process_id=123)
        self.health.write_text(json.dumps(health_record('supervisor',**identity,phase='running',monotonic_ns=10_000_000_000)),encoding='utf-8')
        now=[11_995_000_000];original=Path.open;attempts=[]
        def open_file(path,*args,**kwargs):
            attempts.append(path)
            if len(attempts)==1:raise self.error()
            return original(path,*args,**kwargs)
        def wait(seconds):now[0]+=int(seconds*1_000_000_000)
        permit=SupervisorPermit(self.health,**identity,max_age_seconds=2,monotonic_ns=lambda:now[0])
        with patch('quant_robot.execution.offline_runtime_health._WINDOWS',True,create=True),patch.object(Path,'open',open_file), \
                patch('quant_robot.execution.offline_runtime_health.time.sleep',side_effect=wait):
            with self.assertRaisesRegex(ValueError,'stale'):permit()
        self.assertEqual(len(attempts),2)

    def test_persistent_read_failure_still_latches_runtime_and_blocks_new_orders(self):
        path=self.root/'runtime.sqlite';create_book(path)
        identity=dict(instance_id='a'*32,**journal_identity(path),process_id=123)
        self.health.write_text(json.dumps(health_record('supervisor',**identity,phase='running',monotonic_ns=10_000_000_000)),encoding='utf-8')
        permit=SupervisorPermit(self.health,**identity,max_age_seconds=2,monotonic_ns=lambda:11_000_000_000)
        with OfflineRuntime(path,clock=lambda:NOW,admission_guard=permit) as runtime:
            runtime.tick(observation(runtime,opening=True))
            feed=observation(runtime);feed['intents']=[intent()]
            with patch('quant_robot.execution.offline_runtime_health._WINDOWS',True,create=True), \
                    patch.object(Path,'open',side_effect=self.error()),patch('quant_robot.execution.offline_runtime_health.time.sleep'):
                runtime.tick(feed)
            snapshot=runtime.book.snapshot()
        self.assertIn('runtime_supervision_requires_review',snapshot['faults'])
        self.assertTrue(snapshot['paused']);self.assertEqual(snapshot['orders'],{})
        self.assertIsNotNone(snapshot['portfolio_valuation']['last_valid'])

    @unittest.skipUnless(os.name=='nt','Windows file sharing semantics')
    def test_real_windows_exclusive_handle_release_allows_pending_read(self):
        import ctypes
        from ctypes import wintypes
        kernel=ctypes.WinDLL('kernel32',use_last_error=True)
        kernel.CreateFileW.argtypes=[wintypes.LPCWSTR,wintypes.DWORD,wintypes.DWORD,ctypes.c_void_p,wintypes.DWORD,wintypes.DWORD,wintypes.HANDLE]
        kernel.CreateFileW.restype=wintypes.HANDLE
        kernel.CloseHandle.argtypes=[wintypes.HANDLE];kernel.CloseHandle.restype=wintypes.BOOL
        handle=kernel.CreateFileW(str(self.health),0x80000000,0,None,3,0x80,None)
        self.assertNotIn(handle,(None,ctypes.c_void_p(-1).value))
        attempted=threading.Event();released=threading.Event();result=[];failures=[];original=Path.open
        def open_file(path,*args,**kwargs):
            try:return original(path,*args,**kwargs)
            except PermissionError:
                attempted.set()
                if not released.wait(2):raise RuntimeError('test handle was not released')
                raise
        def read():
            try:result.append(read_health(self.health))
            except BaseException as exc:failures.append(exc)
        worker=threading.Thread(target=read)
        with patch.object(Path,'open',open_file):
            try:
                worker.start();self.assertTrue(attempted.wait(2))
            finally:
                kernel.CloseHandle(handle);released.set();worker.join(timeout=2)
        self.assertFalse(worker.is_alive());self.assertEqual(failures,[])
        self.assertEqual(result,[{'generation':1}])


if __name__=='__main__':unittest.main()
