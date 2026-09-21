import unittest
from tests.integration.test_offline_supervisor_process import wait_for_progressing_worker


class ProgressWaitTests(unittest.TestCase):
    def test_more_than_ten_seconds_of_advancing_ticks_can_complete(self):
        now = [0.0]
        class Child:
            def poll(self): return 0 if now[0] >= 12 else None
            def wait(self, timeout): return 0
        def sleep(_): now[0] += .5
        result = wait_for_progressing_worker(Child(), lambda: {'completed_ticks': int(now[0])},
            clock=lambda: now[0], sleep=sleep)
        self.assertEqual(result, 0)
        self.assertGreater(now[0], 10)

    def test_live_but_stalled_worker_still_fails_with_health_evidence(self):
        now = [0.0]
        class Child:
            def poll(self): return None
        def sleep(_): now[0] += .5
        with self.assertRaisesRegex(TimeoutError, 'last_progress_age=10.000.*completed_ticks'):
            wait_for_progressing_worker(Child(), lambda: {'completed_ticks': 2}, clock=lambda: now[0], sleep=sleep)
        self.assertEqual(now[0], 10)

    def test_progress_does_not_remove_the_total_deadline(self):
        now = [0.0]
        class Child:
            def poll(self): return None
        def sleep(_): now[0] += .5
        with self.assertRaisesRegex(TimeoutError, 'elapsed=60.000'):
            wait_for_progressing_worker(Child(), lambda: {'completed_ticks': int(now[0])}, clock=lambda: now[0], sleep=sleep)


if __name__ == '__main__': unittest.main()
