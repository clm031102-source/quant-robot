import errno
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from quant_robot.storage.atomic import atomic_write_json


class AtomicReplaceContentionTests(unittest.TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory(); self.addCleanup(directory.cleanup)
        self.path = Path(directory.name) / 'health.json'
        atomic_write_json(self.path, {'generation':1})

    @staticmethod
    def sharing_error():
        error = PermissionError(errno.EACCES, 'synthetic Windows file contention')
        error.winerror = 5
        return error

    def test_temporary_windows_contention_reuses_the_same_fsynced_file(self):
        original = os.replace; attempts = []
        def replace(source, target):
            attempts.append(Path(source))
            if len(attempts) < 3:
                self.assertEqual(json.loads(self.path.read_text()), {'generation':1})
                raise self.sharing_error()
            return original(source, target)
        with patch('quant_robot.storage.atomic.os.replace', side_effect=replace), patch('quant_robot.storage.atomic.time.sleep') as sleep:
            atomic_write_json(self.path, {'generation':2})
        self.assertEqual(len(attempts), 3)
        self.assertEqual(len(set(attempts)), 1)
        self.assertEqual(sleep.call_count, 2)
        self.assertEqual(json.loads(self.path.read_text()), {'generation':2})

    def test_persistent_windows_failure_is_bounded_and_preserves_previous_file(self):
        with patch('quant_robot.storage.atomic.os.replace', side_effect=self.sharing_error()) as replace, patch('quant_robot.storage.atomic.time.sleep') as sleep:
            with self.assertRaises(PermissionError): atomic_write_json(self.path, {'generation':2})
        self.assertEqual(replace.call_count, 6)
        self.assertEqual(sleep.call_count, 5)
        self.assertEqual(json.loads(self.path.read_text()), {'generation':1})
        self.assertEqual(list(self.path.parent.iterdir()), [self.path])

    def test_other_io_errors_are_not_retried_or_hidden(self):
        error = OSError(errno.ENOSPC, 'synthetic disk full')
        with patch('quant_robot.storage.atomic.os.replace', side_effect=error) as replace, patch('quant_robot.storage.atomic.time.sleep') as sleep:
            with self.assertRaises(OSError) as caught: atomic_write_json(self.path, {'generation':2})
        self.assertIs(caught.exception, error)
        self.assertEqual(replace.call_count, 1)
        sleep.assert_not_called()
        self.assertEqual(json.loads(self.path.read_text()), {'generation':1})

    @unittest.skipUnless(os.name == 'nt', 'Windows sharing semantics')
    def test_real_windows_reader_closure_allows_pending_atomic_publication(self):
        attempted = threading.Event(); released = threading.Event(); failures=[]; original=os.replace
        reader=self.path.open('rb')
        def replace(source, target):
            try: return original(source, target)
            except PermissionError:
                attempted.set()
                # Coordinate the test reader explicitly. A busy CI scheduler may
                # otherwise keep the parent asleep beyond the publisher's 50 ms
                # wait budget; that is covered by the persistent-failure test.
                if not released.wait(2): raise RuntimeError('test reader did not close')
                raise
        def write():
            try: atomic_write_json(self.path, {'generation':2})
            except BaseException as exc: failures.append(exc)
        worker=threading.Thread(target=write)
        with patch('quant_robot.storage.atomic.os.replace', side_effect=replace):
            try:
                worker.start()
                self.assertTrue(attempted.wait(2))
                self.assertEqual(json.loads(reader.read()), {'generation':1})
            finally:
                reader.close()
                released.set()
                worker.join(timeout=2)
        self.assertFalse(worker.is_alive())
        self.assertEqual(failures, [])
        self.assertEqual(json.loads(self.path.read_text()), {'generation':2})


if __name__ == '__main__': unittest.main()
