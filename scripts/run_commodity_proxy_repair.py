"""Preview or consume the single separately reviewed lifecycle-wrapper repair."""
import argparse
import json
from pathlib import Path

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

from quant_robot.research import commodity_proxy_repair_admission as admission
from scripts.run_commodity_proxy_accounts import load_inputs, calculate


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['preview', 'execute'])
    parser.add_argument('--registration-sha256')
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[1]
    packet, _ = admission.admitted_packet(root)
    if args.command == 'preview':
        print(json.dumps(dict(status='frozen_lifecycle_repair_ready_not_executed',
            registration_sha256=packet['registration_sha256'],
            predecessor_registration_sha256=admission.PREDECESSOR_REGISTRATION_SHA256,
            financial_values_decoded=False, predecessor_financial_fields_decoded=True,
            policy=admission.POLICY)))
        return
    from scripts.run_quant_pm_startup_gate import run_quant_pm_startup_gate
    result = admission.execute(root, expected_registration_sha256=args.registration_sha256,
        gate_supplier=lambda: run_quant_pm_startup_gate(machine='office_desktop', task='factor_review',
            branch=admission.BRANCH, output_dir=root/admission.DIRECTORY/'startup_gate'),
        load_inputs=load_inputs, calculate=calculate)
    print(json.dumps(result))


if __name__ == '__main__':
    main()
