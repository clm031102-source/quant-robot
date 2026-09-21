"""Preflight or execute the exact separately admitted month_start commission screen."""
import argparse
import json
from pathlib import Path
import subprocess

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:
    from bootstrap import ensure_workspace_imports
ensure_workspace_imports()

from quant_robot.research.month_start_diagnostic_registration import DIRECTORY
from quant_robot.research.monthly_diagnostic_registration import resolve_path, runtime_environment
from quant_robot.research.month_start_diagnostic_execution import execute_registration, preflight_registration
from quant_robot.research.pm_startup_gate import build_quant_pm_startup_gate, write_quant_pm_startup_gate


def run(root, *, execute=False):
    root = Path(root).resolve()
    registration_path = DIRECTORY+'/registration.json'
    registration = json.loads(resolve_path(root, registration_path).read_bytes())
    if registration.get('source_origin') != 'retained_research_sources':
        raise ValueError('CLI requires explicitly reviewed real sources; use isolated tests for fixtures')
    if registration.get('source_origin') == 'retained_research_sources':
        changed = subprocess.check_output(['git', 'status', '--porcelain'], cwd=root, text=True).strip()
        if changed:
            raise ValueError('commit reviewed code and admission before a real-input run')
    scheduler_path = root/'configs/research_family_scheduler_cn_etf.json'
    scheduler = json.loads(scheduler_path.read_bytes())
    def gate_supplier():
        branch = subprocess.check_output(['git', 'branch', '--show-current'], cwd=root, text=True).strip()
        gate = build_quant_pm_startup_gate(
            gate_config=json.loads((root/'configs/quant_pm_startup_gate_cn_etf.json').read_bytes()),
            workstations_config=json.loads((root/'configs/workstations.json').read_bytes()),
            repo_root=root, machine='office_desktop', task='factor_batch', branch=registration['branch'],
            current_branch=branch, family_config=json.loads(scheduler_path.read_bytes()))
        write_quant_pm_startup_gate(root/DIRECTORY/'pm_gate', gate)
        return gate
    arguments = dict(root=root, registration_path=registration_path, scheduler=scheduler,
        gate_supplier=gate_supplier, environment=runtime_environment())
    if not execute:
        prepared = preflight_registration(**arguments)
        return {'status': 'ready_unconsumed', 'registration_id': prepared.registration['registration_id'],
            'input_files': len(prepared.snapshots), 'factor_generated': False,
            'prices_decoded': False, 'execution_claim_recorded': False}
    result = execute_registration(**arguments)
    return {'status': 'completed', 'decision': result['diagnostic']['decision'],
        'source_origin': result['source_origin'], 'cycles': result['diagnostic']['cycle_count'],
        'result': DIRECTORY+'/result.json', 'outcome': DIRECTORY+'/outcome.json',
        'net_account_result': False, 'formal_positive_ev_verified': False,
        'counts_as_forward_paper_days': 0}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', default='.')
    parser.add_argument('--execute', action='store_true')
    args = parser.parse_args()
    print(json.dumps(run(args.root, execute=args.execute), indent=2))


if __name__ == '__main__': main()
