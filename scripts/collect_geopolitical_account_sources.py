"""Retain a fixed source packet; never run the gold account."""
from pathlib import Path
import argparse
import json
import sys
import subprocess

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.data.sources.geopolitical_account_sources import BRANCH, execute, preflight
from quant_robot.research.pm_startup_gate import build_quant_pm_startup_gate, write_quant_pm_startup_gate


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    if subprocess.check_output(['git','status','--porcelain'], cwd=root, text=True).strip():
        raise ValueError('Commit reviewed source preparation before real requests')
    branch = subprocess.check_output(['git','branch','--show-current'], cwd=root, text=True).strip()
    gate = build_quant_pm_startup_gate(
        gate_config=json.loads((root/'configs/quant_pm_startup_gate_cn_etf.json').read_bytes()),
        workstations_config=json.loads((root/'configs/workstations.json').read_bytes()),
        repo_root=root, machine='office_desktop', task='factor_review', branch=BRANCH,
        current_branch=branch,
        family_config=json.loads((root/'configs/research_family_scheduler_cn_etf.json').read_bytes()))
    write_quant_pm_startup_gate(root/'data/reports/geopolitical_account_20261104/source/pm_gate', gate)
    if args.execute:
        print(json.dumps(execute(root, gate), ensure_ascii=False, indent=2))
    else:
        scope, _, plan = preflight(root, gate)
        print(json.dumps(dict(status='source_only_preflight_passed', max_requests=scope['max_requests'],
                              sessions=len(plan['sessions']), account_execution_allowed=False)))
    return 0


if __name__ == '__main__':
    sys.exit(main())
