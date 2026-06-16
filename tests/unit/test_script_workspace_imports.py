import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path


class ScriptWorkspaceImportTests(unittest.TestCase):
    def test_bare_python_from_repo_root_prefers_workspace_src_over_legacy_package(self):
        repo_root = Path(__file__).resolve().parents[2]
        with tempfile.TemporaryDirectory() as tmp:
            legacy = Path(tmp) / "legacy"
            _write_legacy_quant_robot_package(legacy)
            env = dict(os.environ)
            env["PYTHONPATH"] = str(legacy)

            result = subprocess.run(
                [
                    sys.executable,
                    "-c",
                    "import quant_robot.audit.project_audit as audit; print(audit.__file__)",
                ],
                cwd=repo_root,
                env=env,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0, msg=result.stderr)
            self.assertTrue(
                Path(result.stdout.strip()).resolve().is_relative_to((repo_root / "src").resolve()),
                msg=result.stdout,
            )

    def test_paper_simulation_cli_prefers_workspace_src_over_legacy_installed_package(self):
        repo_root = Path(__file__).resolve().parents[2]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            legacy = root / "legacy"
            _write_legacy_quant_robot_package(legacy)
            output_dir = root / "paper"
            env = dict(os.environ)
            env["PYTHONPATH"] = str(legacy)

            result = subprocess.run(
                [
                    sys.executable,
                    "scripts/run_paper_simulation.py",
                    "--source",
                    "fixture",
                    "--output-dir",
                    str(output_dir),
                ],
                cwd=repo_root,
                env=env,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0, msg=result.stderr)
            self.assertTrue((output_dir / "manifest.json").exists())

    def test_phase5_cli_scripts_import_workspace_src_over_legacy_installed_package(self):
        repo_root = Path(__file__).resolve().parents[2]
        with tempfile.TemporaryDirectory() as tmp:
            legacy = Path(tmp) / "legacy"
            _write_legacy_quant_robot_package(legacy)
            env = dict(os.environ)
            env["PYTHONPATH"] = str(legacy)

            for script in [
                "scripts/run_daily_ops.py",
                "scripts/run_profile_observation.py",
                "scripts/run_recent_data_refresh.py",
                "scripts/run_post_refresh_replay.py",
            ]:
                with self.subTest(script=script):
                    result = subprocess.run(
                        [
                            sys.executable,
                            "-c",
                            f"import runpy; runpy.run_path({script!r}, run_name='workspace_import_probe')",
                        ],
                        cwd=repo_root,
                        env=env,
                        capture_output=True,
                        text=True,
                    )

                    self.assertEqual(result.returncode, 0, msg=result.stderr)

    def test_direct_scripts_use_workspace_src_via_explicit_bootstrap(self):
        repo_root = Path(__file__).resolve().parents[2]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            legacy = root / "legacy"
            _write_legacy_quant_robot_package(legacy)
            audit_path = root / "data_quality_gap_audit.json"
            output_dir = root / "data_gap_resolution"
            audit_path.write_text(
                '{"stage": "phase_3_1_data_quality_gap_audit", "missing_dates": []}',
                encoding="utf-8",
            )
            env = dict(os.environ)
            env["PYTHONPATH"] = str(legacy)

            result = subprocess.run(
                [
                    sys.executable,
                    "scripts/run_data_gap_resolution.py",
                    "--data-quality-audit",
                    str(audit_path),
                    "--output-dir",
                    str(output_dir),
                ],
                cwd=repo_root,
                env=env,
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0, msg=result.stderr)
            self.assertTrue((output_dir / "data_gap_resolution_ledger.json").exists())

    def test_quant_robot_entry_scripts_bootstrap_before_workspace_imports(self):
        repo_root = Path(__file__).resolve().parents[2]
        offenders = []
        for path in sorted((repo_root / "scripts").glob("*.py")):
            if path.name in {"bootstrap.py"}:
                continue
            text = path.read_text(encoding="utf-8")
            if "from quant_robot" not in text and "import quant_robot" not in text:
                continue
            first_import = min(
                index for index in [text.find("from quant_robot"), text.find("import quant_robot")] if index >= 0
            )
            prefix = text[:first_import]
            has_bootstrap = "ensure_workspace_imports()" in prefix
            has_legacy_path_insert = "sys.path.insert" in prefix and '"src"' in prefix
            if not (has_bootstrap or has_legacy_path_insert):
                offenders.append(str(path.relative_to(repo_root)))

        self.assertEqual(offenders, [])


def _write_legacy_quant_robot_package(root: Path) -> None:
    package_root = root / "quant_robot"
    (package_root / "data").mkdir(parents=True)
    (package_root / "paper").mkdir(parents=True)
    (package_root / "storage").mkdir(parents=True)
    for path in [
        package_root / "__init__.py",
        package_root / "data" / "__init__.py",
        package_root / "paper" / "__init__.py",
        package_root / "storage" / "__init__.py",
    ]:
        path.write_text("", encoding="utf-8")
    (package_root / "data" / "fixtures.py").write_text(
        textwrap.dedent(
            """
            import pandas as pd


            def load_demo_market_bars():
                return pd.DataFrame()
            """
        ).lstrip(),
        encoding="utf-8",
    )
    (package_root / "storage" / "processed_bars.py").write_text(
        textwrap.dedent(
            """
            def load_processed_bars(*_, **__):
                raise RuntimeError("legacy processed bars should not be imported")
            """
        ).lstrip(),
        encoding="utf-8",
    )
    (package_root / "paper" / "simulator.py").write_text(
        textwrap.dedent(
            """
            from dataclasses import dataclass


            @dataclass(frozen=True)
            class PaperSimulationConfig:
                market: str = "ALL"


            def run_paper_simulation(*_, **__):
                raise RuntimeError("legacy simulator should not be imported")


            def write_paper_simulation_artifacts(*_, **__):
                raise RuntimeError("legacy simulator should not be imported")
            """
        ).lstrip(),
        encoding="utf-8",
    )


if __name__ == "__main__":
    unittest.main()
