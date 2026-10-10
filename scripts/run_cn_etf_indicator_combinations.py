"""Execute only the exact registered finite indicator-comparison experiment."""
import json
from pathlib import Path
try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:
    from bootstrap import ensure_workspace_imports
ensure_workspace_imports()

from scripts.run_quant_pm_startup_gate import run_quant_pm_startup_gate
from quant_robot.research.indicator_combination_study import execute, DIRECTORY


def main():
    scheduler = json.loads(Path('configs/research_family_scheduler_cn_etf.json').read_text(encoding='utf-8'))
    def gate():
        return run_quant_pm_startup_gate(machine='office_desktop',task='factor_batch',
            branch='codex/factor-batch-indicator-combinations-20261010',output_dir=DIRECTORY+'/execution_gate')
    result = execute(Path('.'),scheduler,gate,progress=lambda row:print(json.dumps(row),flush=True))
    print(json.dumps(dict(status='completed',hypotheses=result['hypotheses'],conditional_pass_count=result['conditional_pass_count'],net_positive_EV_verified=False)))


if __name__ == '__main__':main()
