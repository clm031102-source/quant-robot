import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import ExitStack
from pathlib import Path
from unittest.mock import Mock, patch

from scripts import run_constrained_candidate_search as constrained


class ConstrainedArtifactReuseTests(unittest.TestCase):
    def test_late_stage_stale_selection_is_rejected_before_any_stage_or_cache_read(self):
        with tempfile.TemporaryDirectory() as tmp, ExitStack() as stack:
            root = Path(tmp)
            risk = root / 'risk'
            risk.mkdir()
            stale = {
                'selection_status': 'risk_candidate_selected',
                'selected_candidate': {'case_id': 'old-policy-result', 'market': 'CN_ETF'},
                'policy': {'max_drawdown_limit': -0.3},
            }
            (risk / 'risk_candidate_pack.json').write_text(json.dumps(stale), encoding='utf-8')
            config = root / 'config.json'
            config.write_text(json.dumps({
                'walk_forward_output_dir': str(root / 'walk'),
                'paper_batch_output_dir': str(root / 'paper'),
                'promotion_output_dir': str(root / 'promotion'),
                'risk_candidate_output_dir': str(risk),
                'max_drawdown_limit': 0.08,
                'output_dir': str(root / 'output'),
                'reuse_existing_artifacts': True,
            }), encoding='utf-8')
            runners = [stack.enter_context(patch.object(constrained, name, return_value={})) for name in (
                'run_walk_forward', 'run_paper_batch', 'run_promotion_report', 'run_risk_candidate_selector',
            )]
            read = stack.enter_context(patch.object(constrained, '_read_json', return_value=stale))
            with self.assertRaisesRegex(ValueError, 'Unbound candidate artifact reuse'):
                constrained.run_constrained_candidate_search(config)
            read.assert_not_called()
            for runner in runners:
                runner.assert_not_called()
            self.assertFalse((root / 'output').exists())

    def test_private_stage_reuse_rejects_before_loading_or_recomputing(self):
        with tempfile.TemporaryDirectory() as tmp:
            artifact = Path(tmp) / 'stale.json'
            artifact.write_text('{"selected_candidate": {"case_id": "old"}}', encoding='utf-8')
            runner = Mock(return_value={})
            with patch.object(constrained, '_read_json') as read:
                with self.assertRaisesRegex(ValueError, 'Unbound candidate artifact reuse'):
                    constrained._reuse_or_run(True, artifact, runner)
                read.assert_not_called()
                runner.assert_not_called()

    def test_explicit_fresh_run_does_not_read_existing_artifact(self):
        with tempfile.TemporaryDirectory() as tmp:
            artifact = Path(tmp) / 'stale.json'
            artifact.write_text('not-json', encoding='utf-8')
            current = {'fixture': 'current'}
            runner = Mock(return_value=current)
            with patch.object(constrained, '_read_json') as read:
                result = constrained._reuse_or_run(False, artifact, runner)
            self.assertIs(result, current)
            read.assert_not_called()
            runner.assert_called_once_with()

    def test_actual_cli_rejects_late_cache_before_missing_stage_configs(self):
        workspace = Path(__file__).resolve().parents[2]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            risk = root / 'risk'
            risk.mkdir()
            (risk / 'risk_candidate_pack.json').write_text('not-read', encoding='utf-8')
            config = root / 'config.json'
            config.write_text(json.dumps({
                'walk_forward_config': str(root / 'missing-walk.json'),
                'walk_forward_output_dir': str(root / 'walk'),
                'paper_batch_output_dir': str(root / 'paper'),
                'promotion_output_dir': str(root / 'promotion'),
                'risk_candidate_output_dir': str(risk),
                'output_dir': str(root / 'output'),
            }), encoding='utf-8')
            result = subprocess.run(
                [sys.executable, str(workspace / 'scripts/run_constrained_candidate_search.py'),
                 '--config', str(config)], cwd=workspace, capture_output=True,
                text=True, encoding='utf-8', timeout=30,
            )
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('Unbound candidate artifact reuse', result.stderr)
            self.assertFalse((root / 'output').exists())
