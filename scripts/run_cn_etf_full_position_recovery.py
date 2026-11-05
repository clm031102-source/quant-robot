"""Prepare or execute one hash-bound full-allocation technical search."""
import argparse
import json
import gzip
import subprocess
from pathlib import Path
try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:
    from bootstrap import ensure_workspace_imports
ensure_workspace_imports()

from scripts.run_quant_pm_startup_gate import run_quant_pm_startup_gate
from quant_robot.paper.comparative_allocation import recovery_policy_template
from quant_robot.research import full_position_recovery_study as study
from quant_robot.research.monthly_diagnostic_registration import (
    canonical, runtime_environment, sha256, write_exclusive_json)

BRANCH = 'codex/factor-batch-full-position-technicals-20261104'
SCHEDULER = Path('configs/research_family_scheduler_cn_etf.json')


def prepare():
    root = Path('.').resolve()
    actual_branch = subprocess.check_output(['git','branch','--show-current'],text=True).strip()
    if actual_branch != BRANCH:
        raise ValueError('Exact user-authorized research branch required')
    scheduler = json.loads(SCHEDULER.read_text(encoding='utf-8'))
    if study.DECISION in scheduler:
        raise ValueError('Existing study decision must not be overwritten')
    study.require_unused(root)
    directory = root/study.DIRECTORY
    directory.mkdir(parents=True,exist_ok=True)
    if (root/study.REGISTRATION).exists():
        raise ValueError('Registration already exists; do not overwrite')
    old = json.loads(Path('data/reports/slow_indicator_combinations_20261104/registration.json').read_text(encoding='utf-8'))
    inputs = {}
    for role in (*study.SOURCE_HASHES,'source_review'):
        previous = old['inputs'][role]
        data = Path(previous['path']).read_bytes()
        if sha256(data) != previous['sha256']:
            raise ValueError('Retained source changed: '+role)
        path = directory/'source'/f'{role}.json';path.parent.mkdir(exist_ok=True)
        with path.open('xb') as f:f.write(data)
        inputs[role] = dict(path=path.relative_to(root).as_posix(),sha256=sha256(data))
    inputs['proposal'] = dict(path=study.PROPOSAL,sha256=sha256(Path(study.PROPOSAL).read_bytes()))
    plan = dict(kind='prospective_decision_calendar_and_frozen_rules',
        proposal=inputs['proposal'],sessions=inputs['sessions'],
        selection='reuse all original12 frozen cases and cycles; no new selection',
        financial_account_first_session='2019-01-02',capital_reset=False)
    previous_directory = Path('data/reports/full_position_factor_search_20261104')
    proposal = json.loads(Path(study.PROPOSAL).read_bytes())
    original_bytes = (previous_directory/'result.json').read_bytes()
    if sha256(original_bytes) != proposal['prior_result_sha256']:
        raise ValueError('Exact original result required; no reselection')
    original = json.loads(original_bytes)
    if original['frozen_selection_sha256'] != proposal['prior_frozen_selection_sha256']:
        raise ValueError('Original frozen selection identity required')
    plan['prior_frozen_selection_sha256'] = original['frozen_selection_sha256']
    plan['prior_result_sha256'] = proposal['prior_result_sha256']
    plan['cases'] = []
    for finding,archive in zip(original['findings'],original['account_archives'],strict=True):
        compressed = (previous_directory/archive['path']).read_bytes()
        raw = gzip.decompress(compressed)
        if sha256(compressed) != archive['sha256'] or sha256(raw) != archive['uncompressed_sha256']:
            raise ValueError('Original cycle archive changed')
        account = json.loads(raw)
        if account['case_id'] != finding['case_id']:
            raise ValueError('Original cycle case mismatch')
        plan['cases'].append(dict(case_id=finding['case_id'],asset=finding['asset'],
            cadence=finding['cadence'],training=finding['training'],cycles=account['strategy_cycles'],
            original_archive=archive))
    if len(plan['cases']) != 12 or len({c['case_id'] for c in plan['cases']}) != 12:
        raise ValueError('All original twelve cases required')
    path = directory/'strategy_cycles.json';write_exclusive_json(path,plan)
    inputs['strategy_cycles'] = dict(path=path.relative_to(root).as_posix(),sha256=sha256(path.read_bytes()))
    policy = recovery_policy_template(study_id=study.STUDY,first_session='2019-01-02',
        terminal_session='2024-01-02',later_start='2021-01-04')
    policy['strategy_cycles'] = inputs['strategy_cycles']
    path = directory/'comparison_policy.json';write_exclusive_json(path,policy)
    inputs['comparison_policy'] = dict(path=path.relative_to(root).as_posix(),sha256=sha256(path.read_bytes()))
    code = {p:dict(path=p,sha256=sha256(Path(p).read_bytes())) for p in study.IMPLEMENTATION}
    packet = study.build_registration(inputs=inputs,code_files=code,branch=BRANCH,
        workspace=root,environment=runtime_environment())
    write_exclusive_json(root/study.REGISTRATION,packet)
    scheduler[study.DECISION] = study.admission(packet,(root/study.REGISTRATION).read_bytes())
    SCHEDULER.write_text(json.dumps(scheduler,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(stage='registered_not_executed',registration_id=packet['registration_id'],
        training_candidates=0,reused_training_candidates=4648,maximum_account_candidates=12,maximum_accounts=324)))


def main():
    parser=argparse.ArgumentParser();mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--prepare',action='store_true');mode.add_argument('--execute',action='store_true')
    args=parser.parse_args()
    if args.prepare:
        prepare();return
    scheduler=json.loads(SCHEDULER.read_text(encoding='utf-8'))
    def gate():
        return run_quant_pm_startup_gate(machine='office_desktop',task='factor_batch',
            branch=BRANCH,output_dir=study.DIRECTORY+'/execution_gate')
    result=study.execute(Path('.'),scheduler,gate,progress=lambda row:print(json.dumps(row),flush=True))
    print(json.dumps(dict(stage='completed',training_candidates=result['training_combination_count'],
        account_candidates=result['account_candidate_count'],conditional_pass_count=result['conditional_pass_count'],
        qualified_strategies=0)))


if __name__=='__main__':main()
