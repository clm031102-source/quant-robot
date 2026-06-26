import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.run_waited_desktop_factor_validation import _process_is_running, run_waited_desktop_factor_validation


class WaitedDesktopFactorValidationTests(unittest.TestCase):
    def test_daily_basic_default_uses_full_2015_2025_authority_bars_after_daily_basic_backfill(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            events = []

            def runner(**kwargs):
                events.append(("runner", kwargs))
                return {"summary": {"accepted": 0}, "leaderboard": []}

            run_waited_desktop_factor_validation(
                log_path=root / "queue.log",
                summary_path=root / "queue_summary.json",
                runner=runner,
                timestamp=lambda: "2026-06-20T16:05:00+08:00",
            )

            self.assertEqual(events[0][0], "runner")
            self.assertEqual(events[0][1]["data_root"], Path("configs/cn_stock_authority_bars_2015_2025.json"))

    def test_waits_for_blocking_pids_before_running_validation_and_writes_summary(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            log_path = root / "queue.log"
            summary_path = root / "queue_summary.json"
            events = []
            running_counts = {101: 2, 202: 1}

            def is_running(pid: int) -> bool:
                remaining = running_counts.get(pid, 0)
                if remaining <= 0:
                    return False
                running_counts[pid] = remaining - 1
                return True

            def sleep(seconds: float) -> None:
                events.append(("sleep", seconds))

            def runner(**kwargs):
                events.append(("runner", kwargs))
                return {"summary": {"accepted": 0, "rejected": 4}, "leaderboard": []}

            result = run_waited_desktop_factor_validation(
                wait_pids=[101, 202],
                config_path=Path("configs/walk_forward_demo.json"),
                data_root=Path("configs/cn_stock_authority_bars_2015_2024.json"),
                log_path=log_path,
                summary_path=summary_path,
                poll_seconds=7,
                is_running=is_running,
                sleep=sleep,
                runner=runner,
                timestamp=lambda: "2026-06-20T15:50:00+08:00",
            )

            self.assertEqual([event for event in events if event[0] == "sleep"], [("sleep", 7), ("sleep", 7), ("sleep", 7)])
            runner_event = events[-1]
            self.assertEqual(runner_event[0], "runner")
            self.assertEqual(runner_event[1]["config_path"], Path("configs/walk_forward_demo.json"))
            self.assertEqual(runner_event[1]["data_root"], Path("configs/cn_stock_authority_bars_2015_2024.json"))
            self.assertFalse(runner_event[1]["require_accepted"])
            self.assertEqual(result["summary"], {"accepted": 0, "rejected": 4})

            log_text = log_path.read_text(encoding="utf-8")
            self.assertIn("waiting_for_pid=101", log_text)
            self.assertIn("pid_finished=202", log_text)
            saved = json.loads(summary_path.read_text(encoding="utf-8"))
            self.assertEqual(saved["waited_pids"], [101, 202])
            self.assertEqual(saved["validation_summary"], {"accepted": 0, "rejected": 4})

    def test_process_probe_uses_windows_fallback_when_psutil_is_unavailable(self):
        real_import = __import__

        def import_without_psutil(name, *args, **kwargs):
            if name == "psutil":
                raise ImportError("psutil intentionally unavailable")
            return real_import(name, *args, **kwargs)

        with (
            patch("builtins.__import__", side_effect=import_without_psutil),
            patch("os.kill", side_effect=OSError("signal 0 unsupported")),
            patch("scripts.run_waited_desktop_factor_validation._windows_pid_exists", return_value=True, create=True) as fallback,
        ):
            self.assertTrue(_process_is_running(12345))

        fallback.assert_called_once_with(12345)


if __name__ == "__main__":
    unittest.main()
