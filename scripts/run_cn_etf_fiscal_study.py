"""Prepare, preflight or execute the one separately admitted fiscal account study."""
import argparse
import json
from pathlib import Path
import subprocess

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:
    from bootstrap import ensure_workspace_imports
ensure_workspace_imports()

from quant_robot.research.fiscal_study_registration import (
    DIRECTORY, REVIEW_PATH, IMPLEMENTATION_FILES, build_registration, verified_input_bytes,
)
from quant_robot.research.fiscal_study_execution import preflight_registration, execute_registration
from quant_robot.research.monthly_diagnostic_registration import resolve_path, runtime_environment, sha256, canonical, write_exclusive_json
from quant_robot.research.pm_startup_gate import build_quant_pm_startup_gate, write_quant_pm_startup_gate


def run(root, *, action):
    root = Path(root).resolve()
    branch = subprocess.check_output(['git', 'branch', '--show-current'], cwd=root, text=True).strip()
    if action == 'prepare':
        review_bytes = resolve_path(root, REVIEW_PATH).read_bytes()
        review = json.loads(review_bytes)
        inputs = {**review['source_fingerprints'], REVIEW_PATH: sha256(review_bytes)}
        code = {path: sha256(resolve_path(root, path).read_bytes()) for path in IMPLEMENTATION_FILES}
        packet = build_registration(inputs=inputs, code_files=code, environment=runtime_environment(),
            source_origin='retained_research_sources', branch=branch)
        verified_input_bytes(root, packet, environment=runtime_environment())
        write_exclusive_json(resolve_path(root, DIRECTORY+'/registration.json'), packet)
        return {'status': 'prepared_not_authorized', 'registration_id': packet['registration_id'],
            'registration_sha256': sha256(canonical(packet)), 'input_files': len(inputs),
            'implementation_files': len(code), 'real_factor_or_price_decoded': False}
    if action not in ('preflight', 'execute'):
        raise ValueError('Explicit prepare, preflight or execute action required')
    packet = json.loads(resolve_path(root, DIRECTORY+'/registration.json').read_bytes())
    if packet.get('source_origin') != 'retained_research_sources':
        raise ValueError('Real CLI requires exact reviewed retained research sources')
    if subprocess.check_output(['git', 'status', '--porcelain'], cwd=root, text=True).strip():
        raise ValueError('Commit reviewed code and exact admission before real-source execution')
    scheduler_path = root/'configs/research_family_scheduler_cn_etf.json'
    scheduler = json.loads(scheduler_path.read_bytes())
    def gate_supplier():
        gate = build_quant_pm_startup_gate(
            gate_config=json.loads((root/'configs/quant_pm_startup_gate_cn_etf.json').read_bytes()),
            workstations_config=json.loads((root/'configs/workstations.json').read_bytes()),
            repo_root=root, machine='office_desktop', task='factor_batch', branch=packet['branch'],
            current_branch=branch, family_config=json.loads(scheduler_path.read_bytes()))
        write_quant_pm_startup_gate(root/DIRECTORY/'pm_gate', gate)
        return gate
    arguments = dict(root=root, scheduler=scheduler, gate_supplier=gate_supplier, environment=runtime_environment())
    if action == 'preflight':
        preflight_registration(**arguments)
        return {'status': 'ready_unconsumed', 'registration_id': packet['registration_id'],
            'real_factor_or_price_decoded': False, 'execution_claim_recorded': False}
    result = execute_registration(**arguments)
    return {'status': 'completed', 'registration_id': packet['registration_id'],
        'eligible_periods': result['eligible_periods'], 'selected_signal_periods': result['selected_signal_periods'],
        'primary_decision': result['primary_decision'], 'result_path': DIRECTORY+'/result.json'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', default='.')
    parser.add_argument('--action', choices=('prepare', 'preflight', 'execute'), required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.root, action=args.action), indent=2))


if __name__ == '__main__': main()
