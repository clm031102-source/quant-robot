"""Only a root-frozen once package can enter the historical source loader."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:
    from bootstrap import ensure_workspace_imports
ensure_workspace_imports()

from quant_robot.research import spot_macd_transfer_admission as admission


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command",choices=("preview","execute"))
    parser.add_argument("--registration-sha256")
    args=parser.parse_args(argv)
    root=Path(__file__).resolve().parents[1]
    if args.command=="preview":
        print(json.dumps(admission.build_registration(root),indent=2))
        return 0
    if not args.registration_sha256: parser.error("--registration-sha256 is required for one exact package")
    def gate():
        from scripts.run_quant_pm_startup_gate import run_quant_pm_startup_gate
        return run_quant_pm_startup_gate(machine="office_desktop",task="factor_review",branch=admission.BRANCH,
                                        output_dir=root/admission.DIRECTORY/"startup_gate")
    os.chdir(root)
    result=admission.execute_once(root,expected_registration_sha256=args.registration_sha256,gate_supplier=gate)
    print(json.dumps(result,indent=2))
    return 0


if __name__=="__main__":
    sys.exit(main())
