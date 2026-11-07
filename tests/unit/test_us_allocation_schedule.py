from datetime import datetime, timedelta
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import xml.etree.ElementTree as ET

from quant_robot.ops.us_allocation_schedule import NS, build_task_files


class FiniteUSScheduleTests(unittest.TestCase):
    def build(self, **change):
        inputs = dict(checkout='F:/example code/source', python='F:/example code/python.exe',
                      scope_path='F:/example data/capture_scope.json', scope_sha='a'*64,
                      preparation_dir='F:/example data/schedule', user_sid='S-1-5-21-123-500')
        return build_task_files(**dict(inputs, **change))

    def test_exact_twenty_utc_sessions_and_early_close(self):
        built = self.build()
        self.assertTrue(built['xml'].startswith('<Task '))
        self.assertNotIn('<?xml', built['xml'])  # Register-ScheduledTask receives a Unicode string.
        root = ET.fromstring(built['xml']); ns = {'t': NS}
        triggers = root.findall('t:Triggers/t:TimeTrigger', ns)
        self.assertEqual(len(triggers), 20)
        self.assertEqual(built['dates'][0], '2026-11-09')
        self.assertEqual(built['dates'][-1], '2026-12-07')
        self.assertNotIn('2026-11-26', built['dates'])
        for node, day in zip(triggers, built['dates']):
            start = node.find('t:StartBoundary', ns).text
            end = node.find('t:EndBoundary', ns).text
            self.assertEqual(start, day + ('T18:15:00Z' if day == '2026-11-27' else 'T21:15:00Z'))
            self.assertEqual(datetime.fromisoformat(end.replace('Z','+00:00')) - datetime.fromisoformat(start.replace('Z','+00:00')), timedelta(minutes=5))
        self.assertEqual(root.find('t:Settings/t:StartWhenAvailable',ns).text, 'false')
        self.assertEqual(root.find('t:Settings/t:AllowStartOnDemand',ns).text, 'false')
        self.assertEqual(root.find('t:Settings/t:ExecutionTimeLimit',ns).text, 'PT5M')
        self.assertIsNone(root.find('t:Settings/t:RestartOnFailure',ns))
        self.assertFalse(built['registration_performed'])

    def test_launch_is_hidden_exact_scope_and_no_warmup_command(self):
        built = self.build()
        self.assertIn('-WindowStyle Hidden -PassThru', built['launcher'])
        self.assertIn('WaitForExit(270000)', built['launcher'])
        self.assertIn('observe --scope "F:\\example data\\capture_scope.json" --scope-sha ' + 'a'*64, built['launcher'])
        self.assertIn('$env:PYTHONPATH', built['launcher'])
        self.assertNotIn(' warmup ', built['launcher'])
        self.assertIn(".stdout.log", built['launcher'])
        with self.assertRaises(ValueError): self.build(scope_sha='not-a-hash')
        with self.assertRaises(ValueError): self.build(checkout='relative')
        with self.assertRaises(ValueError): self.build(user_sid='administrator')


    @unittest.skipUnless(sys.platform == 'win32', 'Requires native Windows PowerShell')
    def test_native_launcher_propagates_success_and_failure(self):
        with tempfile.TemporaryDirectory(prefix='quant exit probe ') as temporary:
            root = Path(temporary)
            (root / 'scripts').mkdir()
            (root / 'scripts/run_us_allocation_daily_model_observer.py').write_text(
                'import json,sys\nfrom pathlib import Path\nscope=Path(sys.argv[sys.argv.index("--scope")+1])\n'
                'raise SystemExit(json.loads(scope.read_bytes())["exit"])\n', encoding='utf-8')
            environment = {key: value for key, value in os.environ.items() if key.casefold() != 'psmodulepath'}
            shell = Path(os.environ['WINDIR']) / 'System32/WindowsPowerShell/v1.0/powershell.exe'
            for expected in (0, 7):
                with self.subTest(exit_code=expected):
                    raw = json.dumps({'exit': expected}).encode()
                    scope = root / 'scope.json'
                    scope.write_bytes(raw)
                    built = build_task_files(checkout=str(root), python=sys.executable,
                        scope_path=str(scope), scope_sha=hashlib.sha256(raw).hexdigest(),
                        preparation_dir=str(root / 'schedule'), user_sid='S-1-5-21-123-500')
                    launcher = root / 'launcher.ps1'
                    launcher.write_text(built['launcher'], encoding='utf-8')
                    outcome = subprocess.run([str(shell), '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass', '-File', str(launcher)],
                        capture_output=True, text=True, timeout=25, env=environment, creationflags=subprocess.CREATE_NO_WINDOW)
                    self.assertEqual(outcome.returncode, expected, outcome.stderr)


if __name__ == '__main__': unittest.main()
