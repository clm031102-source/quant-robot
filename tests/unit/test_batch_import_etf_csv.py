import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from quant_robot.storage.processed_bars import load_processed_bars
from scripts.batch_import_etf_csv import batch_import_etf_csv, infer_symbol_from_filename


class BatchEtfCsvImportTests(unittest.TestCase):
    def test_infers_symbol_from_tradingview_filename(self):
        self.assertEqual(infer_symbol_from_filename(Path("SSE_DLY_510300, 1D_abc.csv")), "510300.SH")
        self.assertEqual(infer_symbol_from_filename(Path("SZSE_DLY_159915, 1D_abc.csv")), "159915.SZ")

    def test_batch_import_moves_raw_files_and_writes_processed_bars(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            incoming = root / "incoming"
            incoming.mkdir()
            output = root / "processed"
            raw_dir = root / "raw"
            first = incoming / "SSE_DLY_510300, 1D_abc.csv"
            second = incoming / "SZSE_DLY_159915, 1D_def.csv"
            _write_csv(first, close="3.05")
            _write_csv(second, close="3.05")

            result = batch_import_etf_csv(incoming, output, raw_dir=raw_dir, move_raw=True)
            bars = load_processed_bars(output, "CN_ETF")

            self.assertEqual(result["symbols"], ["510300.SH", "159915.SZ"])
            self.assertEqual(result["files"], 2)
            self.assertTrue((raw_dir / "510300_SH_1d.csv").exists())
            self.assertTrue((raw_dir / "159915_SZ_1d.csv").exists())
            self.assertFalse(first.exists())
            self.assertFalse(second.exists())
            self.assertTrue((output / "batch_import_manifest.json").exists())
            self.assertEqual(set(bars["symbol"]), {"510300.SH", "159915.SZ"})

    def test_cli_can_start_when_executed_as_script(self):
        repo_root = Path(__file__).resolve().parents[2]
        env = {**os.environ, "PYTHONPATH": "src"}

        result = subprocess.run(
            [sys.executable, "scripts/batch_import_etf_csv.py", "--help"],
            cwd=repo_root,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )

        self.assertEqual(result.returncode, 0, result.stderr)


def _write_csv(path: Path, close: str) -> None:
    path.write_text(
        "time,open,high,low,close,Volume\n"
        f"2024-01-02,3,3.1,2.9,{close},100\n"
        f"2024-01-03,3.1,3.2,3.0,{close},120\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    unittest.main()
