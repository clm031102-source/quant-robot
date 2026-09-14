"""Prepare the reviewed month_start source registration without granting execution."""
import argparse
import json
from pathlib import Path
import subprocess

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:
    from bootstrap import ensure_workspace_imports
ensure_workspace_imports()

from quant_robot.research.month_start_diagnostic_registration import (
    DIRECTORY, IMPLEMENTATION_FILES, build_registration, expected_input_paths, verified_input_bytes,
)
from quant_robot.research.monthly_diagnostic_registration import (
    canonical, resolve_path, runtime_environment, sha256, write_exclusive_json,
)
from quant_robot.research.month_start_diagnostic_inputs import check_source_links


def prepare(root):
    root = Path(root).resolve()
    inputs = {role: {'path': path, 'sha256': sha256(resolve_path(root, path).read_bytes())}
        for role, path in expected_input_paths().items()}
    code = {path: sha256(resolve_path(root, path).read_bytes()) for path in IMPLEMENTATION_FILES}
    branch = subprocess.check_output(['git', 'branch', '--show-current'], cwd=root, text=True).strip()
    packet = build_registration(inputs=inputs, code_files=code, environment=runtime_environment(),
        source_origin='retained_research_sources', branch=branch)
    snapshots = verified_input_bytes(root, packet, environment=runtime_environment())
    check_source_links(packet, snapshots)
    destination = resolve_path(root, DIRECTORY+'/registration.json')
    write_exclusive_json(destination, packet)
    return {'status': 'prepared_not_authorized', 'registration_id': packet['registration_id'],
        'registration_path': destination.relative_to(root).as_posix(),
        'registration_sha256': sha256(canonical(packet)), 'input_files': len(inputs),
        'code_files': len(code), 'prices_decoded': False, 'factor_generated': False,
        'research_admission_granted': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', default='.')
    args = parser.parse_args()
    print(json.dumps(prepare(args.root), indent=2))


if __name__ == '__main__': main()
