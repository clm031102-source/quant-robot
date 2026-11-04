"""Preflight or consume the one fixed GPRT full-account admission."""
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
from quant_robot.research.pm_startup_gate import build_quant_pm_startup_gate, write_quant_pm_startup_gate


def run(root,*,execute=False):
    root=Path(root).resolve()
    if subprocess.check_output(['git','status','--porcelain'],cwd=root,text=True).strip():
        raise ValueError('Commit reviewed implementation and admission before real accounts')
    scheduler_path=root/'configs/research_family_scheduler_cn_etf.json'
    scheduler=json.loads(scheduler_path.read_bytes())
    packet=json.loads((root/study.REGISTRATION).read_bytes())
    def gate_supplier():
        branch=subprocess.check_output(['git','branch','--show-current'],cwd=root,text=True).strip()
        gate=build_quant_pm_startup_gate(
            gate_config=json.loads((root/'configs/quant_pm_startup_gate_cn_etf.json').read_bytes()),
            workstations_config=json.loads((root/'configs/workstations.json').read_bytes()),
            repo_root=root,machine='office_desktop',task='factor_batch',branch=packet['branch'],
            current_branch=branch,family_config=json.loads(scheduler_path.read_bytes()))
        write_quant_pm_startup_gate(root/study.DIRECTORY/'pm_gate',gate)
        return gate
    if not execute:
        registration,snapshots,_=study.preflight(root,scheduler,gate_supplier)
        return dict(status='ready_unconsumed',registration_id=registration['registration_id'],
            inputs=len(snapshots),market_outcomes_computed=False,account_executed=False)
    result=study.execute(root,scheduler,gate_supplier)
    summary={k:result[k] for k in ('study_id','conditional_screen_passed','checks',
                                  'completed_full_episodes','completed_new_later_episodes','uncertainty')}
    summary['primary_summary']={k:v for k,v in result['primary_summary'].items() if k!='risk_breaches'}
    summary['primary_summary']['risk_breach_count']=len(result['primary_summary']['risk_breaches'])
    return summary


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',default='.');parser.add_argument('--execute',action='store_true')
    args=parser.parse_args();print(json.dumps(run(args.root,execute=args.execute),indent=2))
