"""Fingerprint or execute one independently released USD monthly-rotation study."""
from __future__ import annotations
import argparse,json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from bootstrap import ensure_workspace_imports
ensure_workspace_imports()
from quant_robot.research import us_monthly_rotation_historical as h

def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('command',choices=('fingerprint','preview','execute'))
    p.add_argument('--study-number',type=int)
    p.add_argument('--registration-sha256')
    args=p.parse_args(argv);root=Path(__file__).resolve().parents[1]
    if args.command=='fingerprint':
        packet=h.build_registration(root,study_number=args.study_number)
        print(json.dumps(dict(status='UNREGISTERED',packet=packet,financial_values_decoded=False)))
    elif args.command=='preview':
        packet,_=h.admitted(root)
        print(json.dumps(dict(status='reviewed_not_executed',registration_sha256=packet['registration_sha256'],
            policy=packet['policy'],financial_values_decoded=False)))
    else:
        from scripts.run_quant_pm_startup_gate import run_quant_pm_startup_gate
        result=h.execute(root,expected_registration_sha256=args.registration_sha256,
            gate_supplier=lambda:run_quant_pm_startup_gate(machine='office_desktop',task='factor_review',
                branch=h.BRANCH,output_dir=root/h.DIRECTORY/'startup_gate'))
        print(json.dumps(dict(status=result['status'],registration_sha256=result['registration_sha256'],
            account_count=result['account_count'],qualified=False,real_forward=0)))
    return 0

if __name__=='__main__':raise SystemExit(main())

