from datetime import datetime, timedelta
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


if __name__ == '__main__': unittest.main()
