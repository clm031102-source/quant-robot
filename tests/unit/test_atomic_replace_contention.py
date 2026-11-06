import errno
from contextlib import ExitStack
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

from quant_robot.storage.atomic import atomic_write, atomic_write_json, open_atomic_read, _replace_atomic, _replace_open_windows_file, _open_windows_file


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
        original = _replace_atomic; attempts = []; writes = []
        def writer(path):
            writes.append(path)
            path.write_text(json.dumps({'generation':2}), encoding='utf-8')
        def replace(source, target):
            attempts.append(Path(source))
            self.assertEqual(fsync.call_count, 1)
            self.assertEqual(json.loads(Path(source).read_text()), {'generation':2})
            if len(attempts) < 3:
                self.assertEqual(json.loads(self.path.read_text()), {'generation':1})
                raise self.sharing_error()
            return original(source, target)
        with patch('quant_robot.storage.atomic._replace_atomic', side_effect=replace), \
                patch('quant_robot.storage.atomic.time.sleep') as sleep, \
                patch('quant_robot.storage.atomic.os.fsync', wraps=os.fsync) as fsync:
            atomic_write(self.path, writer)
        self.assertEqual(len(attempts), 3)
        self.assertEqual(len(set(attempts)), 1)
        self.assertEqual(writes, [attempts[0]])
        fsync.assert_called_once()
        self.assertEqual(sleep.call_count, 2)
        self.assertEqual(json.loads(self.path.read_text()), {'generation':2})

    def test_persistent_windows_failure_is_bounded_and_preserves_previous_file(self):
        with patch('quant_robot.storage.atomic._replace_atomic', side_effect=self.sharing_error()) as replace, patch('quant_robot.storage.atomic.time.sleep') as sleep:
            with self.assertRaises(PermissionError): atomic_write_json(self.path, {'generation':2})
        self.assertEqual(replace.call_count, 6)
        self.assertEqual(sleep.call_count, 5)
        self.assertEqual(json.loads(self.path.read_text()), {'generation':1})
        self.assertEqual(list(self.path.parent.iterdir()), [self.path])

    def test_other_io_errors_are_not_retried_or_hidden(self):
        errors = (OSError(errno.ENOSPC, 'synthetic disk full'),
                  PermissionError(errno.EACCES, 'permission denied without a Windows contention code'))
        for error in errors:
            with self.subTest(errno=error.errno):
                with patch('quant_robot.storage.atomic._replace_atomic', side_effect=error) as replace, \
                        patch('quant_robot.storage.atomic.time.sleep') as sleep:
                    with self.assertRaises(OSError) as caught:
                        atomic_write_json(self.path, {'generation':2})
                self.assertIs(caught.exception, error)
                self.assertEqual(replace.call_count, 1)
                sleep.assert_not_called()
                self.assertEqual(json.loads(self.path.read_text()), {'generation':1})

    @unittest.skipUnless(os.name == 'nt', 'Windows sharing semantics')
    def test_real_persistent_reader_lock_preserves_target_and_only_removes_own_temporary(self):
        unrelated = self.path.parent / '.health.unrelated.json'
        unrelated.write_text('preserve unrelated file', encoding='utf-8')
        original = _replace_atomic
        with self.path.open('rb') as reader, \
                patch('quant_robot.storage.atomic._replace_atomic', wraps=original) as replace:
            with self.assertRaises(PermissionError) as caught:
                atomic_write_json(self.path, {'generation':2})
            self.assertIn(caught.exception.winerror, {5, 32, 33})
            self.assertEqual(replace.call_count, 6)
            self.assertEqual(json.loads(reader.read()), {'generation':1})
        self.assertEqual(json.loads(self.path.read_text()), {'generation':1})
        self.assertEqual(set(self.path.parent.iterdir()), {self.path, unrelated})
        self.assertEqual(unrelated.read_text(), 'preserve unrelated file')

    @unittest.skipUnless(os.name == 'nt', 'Windows sharing semantics')
    def test_real_windows_reader_closure_allows_pending_atomic_publication(self):
        attempted = threading.Event(); released = threading.Event(); failures=[]; original=_replace_atomic
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
        with patch('quant_robot.storage.atomic._replace_atomic', side_effect=replace):
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

    def test_atomic_reader_is_readonly_and_closes_and_preserves_missing_file_error(self):
        with open_atomic_read(self.path) as reader:
            self.assertEqual(json.load(reader), {'generation':1})
            self.assertFalse(reader.writable())
            with self.assertRaises(OSError):
                reader.write(b'forbidden')
        self.assertTrue(reader.closed)
        with self.assertRaises(FileNotFoundError):
            open_atomic_read(self.path.parent / 'missing.json')
        with self.assertRaises(ValueError):
            open_atomic_read(str(self.path) + '\x00ignored')

    @unittest.skipUnless(os.name == 'nt', 'Windows sharing semantics')
    def test_native_replacement_supports_unicode_and_retains_open_snapshot(self):
        path = self.path.parent / '\u5065\u5eb7\U0001f9ea.json'
        atomic_write_json(path, {'generation':1})
        with open_atomic_read(path) as reader:
            atomic_write_json(path, {'generation':2})
            self.assertEqual(json.load(reader), {'generation':1})
            with open_atomic_read(path) as current:
                self.assertEqual(json.load(current), {'generation':2})

    @unittest.skipUnless(os.name == 'nt', 'Windows native filename contract')
    def test_native_filename_buffer_contains_explicit_utf16_terminator(self):
        import ctypes
        from ctypes import wintypes

        class Header(ctypes.Structure):
            _fields_ = [('Flags', wintypes.DWORD), ('RootDirectory', wintypes.HANDLE),
                        ('FileNameLength', wintypes.DWORD), ('FileName', wintypes.WCHAR * 1)]

        checked = []
        expected = [None]
        def open_file(path, access):
            kernel, handle = _open_windows_file(path, access)
            class KernelProxy:
                CloseHandle = kernel.CloseHandle
            def rename(native_handle, info_class, buffer, size):
                header = ctypes.cast(buffer, ctypes.POINTER(Header)).contents
                offset = Header.FileName.offset
                content = ctypes.string_at(buffer, size)
                encoded = str(expected[0].absolute()).encode('utf-16-le')
                self.assertEqual(header.FileNameLength, len(encoded))
                self.assertEqual(content[offset:offset + header.FileNameLength], encoded)
                # Win32 FILE_RENAME_INFO.FileName is NUL-terminated, even though
                # FileNameLength excludes that terminator. Do not rely on padding.
                self.assertGreaterEqual(size, offset + header.FileNameLength + 2)
                self.assertEqual(content[offset + header.FileNameLength:offset + header.FileNameLength + 2], b'\x00\x00')
                checked.append(header.FileNameLength % 8)
                kernel.SetFileInformationByHandle.argtypes = [wintypes.HANDLE, ctypes.c_int, ctypes.c_void_p, wintypes.DWORD]
                kernel.SetFileInformationByHandle.restype = wintypes.BOOL
                return kernel.SetFileInformationByHandle(native_handle, info_class, buffer, size)
            proxy = KernelProxy()
            proxy.SetFileInformationByHandle = rename
            return proxy, handle

        for width in range(8):
            path = self.path.parent / ('x' * width + 'health.json')
            expected[0] = path
            atomic_write_json(path, {'generation':0})
            with self.subTest(width=width), open_atomic_read(path) as old, \
                    patch('quant_robot.storage.atomic._open_windows_file', side_effect=open_file):
                atomic_write_json(path, {'generation':1})
                self.assertEqual(json.load(old), {'generation':0})
                self.assertEqual(json.loads(path.read_text()), {'generation':1})
        self.assertEqual(set(checked), {0, 2, 4, 6})

    @unittest.skipUnless(os.name == 'nt', 'Windows repeated native publication')
    def test_twenty_replacements_preserve_every_snapshot_and_exact_target_for_path_lengths(self):
        for prefix in ('ascii', '\u5065\u5eb7\U0001f9ea'):
            for width in range(8):
                with self.subTest(prefix=prefix, width=width):
                    directory = self.path.parent / (prefix + '_' + str(width))
                    directory.mkdir()
                    path = directory / ('x' * width + 'health.json')
                    def payload(generation):
                        return {'generation':generation, 'complete':[generation, '\u5b8c\u6574\U0001f9ea', list(range(32))]}
                    atomic_write_json(path, payload(0))
                    with ExitStack() as readers:
                        held = []
                        for generation in range(1, 21):
                            # Hold every generation, so every replacement must
                            # handle an open current target, not just the first.
                            held.append(readers.enter_context(open_atomic_read(path)))
                            self.assertEqual(atomic_write_json(path, payload(generation)), path)
                            with open_atomic_read(path) as current:
                                self.assertEqual(json.load(current), payload(generation))
                            self.assertEqual(set(directory.iterdir()), {path})
                        for generation, reader in enumerate(held):
                            self.assertEqual(json.load(reader), payload(generation))
                    self.assertEqual(set(directory.iterdir()), {path})

    @unittest.skipUnless(os.name == 'nt', 'Windows fallback semantics')
    def test_only_known_contention_errors_enter_native_fallback(self):
        for code in (5, 32, 33):
            error = self.sharing_error(); error.winerror = code
            with self.subTest(winerror=code), \
                    patch('quant_robot.storage.atomic.os.replace', side_effect=error), \
                    patch('quant_robot.storage.atomic._replace_open_windows_file', wraps=_replace_open_windows_file) as native:
                atomic_write_json(self.path, {'generation':code})
                native.assert_called_once()
            self.assertEqual(json.loads(self.path.read_text()), {'generation':code})
        for error in (PermissionError(errno.EACCES, 'no Windows code'), OSError(errno.EIO, 'device failure')):
            with self.subTest(error=error), \
                    patch('quant_robot.storage.atomic.os.replace', side_effect=error), \
                    patch('quant_robot.storage.atomic._replace_open_windows_file') as native:
                with self.assertRaises(OSError) as caught:
                    atomic_write_json(self.path, {'generation':4})
                self.assertIs(caught.exception, error)
                native.assert_not_called()

    @unittest.skipUnless(os.name == 'nt', 'Windows fallback semantics')
    def test_unsupported_native_rename_retains_original_bounded_failure(self):
        original = self.sharing_error()
        for code in (1, 50, 87, 120):
            native_error = OSError('unsupported native rename'); native_error.winerror = code
            with self.subTest(winerror=code), \
                    patch('quant_robot.storage.atomic.os.replace', side_effect=original) as replace, \
                    patch('quant_robot.storage.atomic._replace_open_windows_file', side_effect=native_error) as native, \
                    patch('quant_robot.storage.atomic.time.sleep') as sleep:
                with self.assertRaises(PermissionError) as caught:
                    atomic_write_json(self.path, {'generation':2})
                self.assertIs(caught.exception, original)
                self.assertEqual((replace.call_count, native.call_count, sleep.call_count), (6, 6, 5))
            self.assertEqual(json.loads(self.path.read_text()), {'generation':1})
            self.assertEqual(list(self.path.parent.iterdir()), [self.path])

    @unittest.skipUnless(os.name == 'nt', 'Windows fallback semantics')
    def test_unknown_native_error_is_not_swallowed_or_retried(self):
        error = OSError('native device error'); error.winerror = 1117
        with patch('quant_robot.storage.atomic.os.replace', side_effect=self.sharing_error()), \
                patch('quant_robot.storage.atomic._replace_open_windows_file', side_effect=error) as native, \
                patch('quant_robot.storage.atomic.time.sleep') as sleep:
            with self.assertRaises(OSError) as caught:
                atomic_write_json(self.path, {'generation':2})
            self.assertIs(caught.exception, error)
            native.assert_called_once(); sleep.assert_not_called()
        self.assertEqual(json.loads(self.path.read_text()), {'generation':1})
        self.assertEqual(list(self.path.parent.iterdir()), [self.path])

    def assert_native_handle_closed(self, handle):
        import ctypes
        from ctypes import wintypes
        kernel = ctypes.WinDLL('kernel32', use_last_error=True)
        kernel.GetHandleInformation.argtypes = [wintypes.HANDLE, ctypes.POINTER(wintypes.DWORD)]
        kernel.GetHandleInformation.restype = wintypes.BOOL
        flags = wintypes.DWORD()
        self.assertFalse(kernel.GetHandleInformation(handle, ctypes.byref(flags)))
        self.assertEqual(ctypes.get_last_error(), 6)  # ERROR_INVALID_HANDLE.

    @unittest.skipUnless(os.name == 'nt', 'Windows handle ownership')
    def test_native_reader_handle_closes_on_normal_and_failed_crt_transfer(self):
        import msvcrt
        with open_atomic_read(self.path) as reader:
            handle = msvcrt.get_osfhandle(reader.fileno())
        self.assert_native_handle_closed(handle)
        handles = []
        error = OSError('CRT transfer failed')
        def fail(handle, flags):
            handles.append(handle)
            raise error
        with patch('msvcrt.open_osfhandle', side_effect=fail):
            with self.assertRaises(OSError) as caught:
                open_atomic_read(self.path)
        self.assertIs(caught.exception, error)
        self.assertEqual(len(handles), 1)
        self.assert_native_handle_closed(handles[0])

    @unittest.skipUnless(os.name == 'nt', 'Windows handle ownership')
    def test_reader_closes_crt_descriptor_when_file_object_creation_fails(self):
        descriptors = []
        error = OSError('file object creation failed')
        def fail(descriptor, mode):
            descriptors.append(descriptor)
            raise error
        with patch('quant_robot.storage.atomic.os.fdopen', side_effect=fail):
            with self.assertRaises(OSError) as caught:
                open_atomic_read(self.path)
        self.assertIs(caught.exception, error)
        self.assertEqual(len(descriptors), 1)
        with self.assertRaises(OSError) as closed:
            os.fstat(descriptors[0])
        self.assertEqual(closed.exception.errno, errno.EBADF)

    @unittest.skipUnless(os.name == 'nt', 'Windows handle ownership')
    def test_native_rename_failure_closes_source_handle_and_preserves_both_files(self):
        source = self.path.parent / 'candidate.json'
        source.write_text('{"generation":2}', encoding='utf-8')
        handles = []
        def open_file(path, access):
            kernel, handle = _open_windows_file(path, access)
            handles.append(handle)
            return kernel, handle
        with self.path.open('rb') as reader, \
                patch('quant_robot.storage.atomic._open_windows_file', side_effect=open_file):
            with self.assertRaises(PermissionError):
                _replace_open_windows_file(source, self.path)
            self.assertEqual(json.load(reader), {'generation':1})
        self.assertEqual(json.loads(source.read_text()), {'generation':2})
        self.assertEqual(json.loads(self.path.read_text()), {'generation':1})
        self.assertEqual(len(handles), 1)
        self.assert_native_handle_closed(handles[0])


if __name__ == '__main__': unittest.main()
