"""Preview hashes or consume one separately reviewed fixed-month financial study."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:
    from bootstrap import ensure_workspace_imports
ensure_workspace_imports()

from quant_robot.research import crypto_monthly_admission as admission


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=('preview','execute'))
    parser.add_argument('--registration-sha256')
    args=parser.parse_args(argv)
    root=Path(__file__).resolve().parents[1]
    packet,_=admission.admitted_packet(root)
    if args.command=='preview':
        print(json.dumps({'status':'frozen_month_ready_not_executed','registration_sha256':packet['registration_sha256'],
            'policy':admission.POLICY,'financial_values_decoded':False,'qualified':False,'real_forward':0}))
        return 0
    from scripts.run_quant_pm_startup_gate import run_quant_pm_startup_gate
    result=admission.execute(root,expected_registration_sha256=args.registration_sha256,
        gate_supplier=lambda:run_quant_pm_startup_gate(machine='office_desktop',task='factor_review',
            branch=admission.BRANCH,output_dir=root/admission.DIRECTORY/'startup_gate'))
    print(json.dumps(result))
    return 0


if __name__=='__main__': raise SystemExit(main())
