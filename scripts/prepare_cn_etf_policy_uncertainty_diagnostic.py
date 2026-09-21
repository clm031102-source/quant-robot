"""Prepare a source-bound registration; does not issue an execution permission."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:
    from bootstrap import ensure_workspace_imports
ensure_workspace_imports()

from quant_robot.research.monthly_diagnostic_registration import (
    DIRECTORY, IMPLEMENTATION_FILES, build_registration, canonical, resolve_path,
    runtime_environment, sha256, verified_input_bytes, write_exclusive_json,
)
from quant_robot.research.monthly_diagnostic_inputs import check_source_links


def prepare(root):
    root = Path(root).resolve()
    proposal_path = 'configs/cn_etf_policy_uncertainty_historical_diagnostic_proposal_20260914.json'
    proposal = json.loads((root / proposal_path).read_bytes())
    paths = {'proposal': proposal_path, 'source_review': proposal['source_use']['use_specific_review_evidence'],
        'source_join': proposal['source_use']['source_join_evidence']}
    base = 'data/reports/etf_monetization_20260911/policy_uncertainty_mechanism_20260913/anchor_source_audit/'
    paths.update(policy_audit=base + 'result.json', policy_scope=base + 'scope.json',
        policy_1=base + 'batch_1_source.csv', policy_2=base + 'batch_2_source.csv',
        calendar='data/processed/trading_calendars/cn_tushare_2015_2025/cn_trading_calendar.csv',
        actions='data/reports/etf_monetization_20260911/research_price_basis_20260913/notice_source_contract/510300_notice_gross_observations_v3.json')
    for year in range(2020, 2025):
        paths['bars_' + str(year)] = 'data/processed/tushare_etf_wide_history_2023_2026/processed/bars/frequency=1d/market=CN_ETF/year=' + str(year) + '/part-00000.parquet'
    inputs = {role: {'path': path, 'sha256': sha256(resolve_path(root, path).read_bytes())} for role, path in paths.items()}
    code = {path: sha256(resolve_path(root, path).read_bytes()) for path in IMPLEMENTATION_FILES}
    branch = subprocess.check_output(['git', 'branch', '--show-current'], cwd=root, text=True).strip()
    registration = build_registration(inputs=inputs, code_files=code, environment=runtime_environment(),
        source_origin='retained_research_sources', branch=branch)
    snapshots = verified_input_bytes(root, registration, environment=runtime_environment())
    check_source_links(registration, snapshots)
    destination = resolve_path(root, DIRECTORY + '/registration.json')
    write_exclusive_json(destination, registration)
    return {'status': 'prepared_not_authorized', 'registration_id': registration['registration_id'],
        'registration_path': destination.relative_to(root).as_posix(), 'registration_sha256': sha256(canonical(registration)),
        'input_files': len(inputs), 'code_files': len(code), 'prices_decoded': False,
        'factor_generated': False, 'research_admission_granted': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', default='.')
    args = parser.parse_args()
    print(json.dumps(prepare(args.root), indent=2))


if __name__ == '__main__': main()
