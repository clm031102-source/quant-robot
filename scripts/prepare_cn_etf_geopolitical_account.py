"""Freeze exact reviewed inputs and one historical account admission; no returns."""
import argparse
import json
from pathlib import Path
import subprocess

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:
    from bootstrap import ensure_workspace_imports
ensure_workspace_imports()

from quant_robot.research import geopolitical_account_study as study
from quant_robot.research.monthly_diagnostic_registration import (
    resolve_path, runtime_environment, sha256, write_exclusive_json,
)


def prepare(root):
    root=Path(root).resolve();study.require_unused(root)
    registration_path=resolve_path(root,study.REGISTRATION)
    if registration_path.exists():
        raise ValueError('Existing registration must not be overwritten')
    scheduler_path=root/'configs/research_family_scheduler_cn_etf.json'
    scheduler=json.loads(scheduler_path.read_bytes())
    if study.DECISION in scheduler:
        raise ValueError('Existing account decision must not be overwritten')
    review=json.loads(resolve_path(root,study.FROZEN['input_review']['path']).read_bytes())
    inputs={'review_'+role:pin for role,pin in review['inputs'].items()}
    plan=json.loads(resolve_path(root,inputs['review_account_plan']['path']).read_bytes())
    cycle_path=resolve_path(root,study.EXTRA_PATHS['strategy_cycles'])
    write_exclusive_json(cycle_path,plan['strategy_cycles'])
    cycle_pin=dict(path=study.EXTRA_PATHS['strategy_cycles'],sha256=sha256(cycle_path.read_bytes()))
    write_exclusive_json(resolve_path(root,study.EXTRA_PATHS['comparison_policy']),
                         dict(plan['comparison_policy'],strategy_cycles=cycle_pin))
    for role,path in study.EXTRA_PATHS.items():
        inputs[role]=dict(path=path,sha256=sha256(resolve_path(root,path).read_bytes()))
    code={path:dict(path=path,sha256=sha256(resolve_path(root,path).read_bytes())) for path in study.IMPLEMENTATION}
    branch=subprocess.check_output(['git','branch','--show-current'],cwd=root,text=True).strip()
    packet=study.build_registration(inputs=inputs,code_files=code,branch=branch,environment=runtime_environment())
    study.source_chain(packet,{role:resolve_path(root,pin['path']).read_bytes() for role,pin in inputs.items()})
    registration_path.parent.mkdir(parents=True,exist_ok=True)
    write_exclusive_json(registration_path,packet)
    scheduler[study.DECISION]=study.admission(packet,registration_path.read_bytes())
    scheduler_path.write_text(json.dumps(scheduler,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='\n')
    return dict(registration_id=packet['registration_id'],input_files=len(inputs),code_files=len(code),
                market_outcomes_computed=False,account_executed=False)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--root',default='.')
    args=parser.parse_args();print(json.dumps(prepare(args.root),indent=2))
