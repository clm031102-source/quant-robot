"""Preview or consume the single reviewed commodity proxy account batch."""
import argparse
import csv
import io
import json
from pathlib import Path

try:
    from scripts.bootstrap import ensure_workspace_imports
except ModuleNotFoundError:
    from bootstrap import ensure_workspace_imports

ensure_workspace_imports()

import pandas as pd
from quant_robot.research import commodity_proxy_admission as admission
from quant_robot.research.commodity_proxy_accounts import ASSET, calculate
from quant_robot.research.commodity_curve_proxy import select_contract_pairs


def lifecycle_records(raw, sessions):
    """Unwrap the retained metadata document before passing rows to the selector."""
    document = admission._json(raw)
    if (not isinstance(document, dict) or set(document) != {
            'source_sha256', 'records', 'delist_date_semantics', 'historical_vintage_verified'}
            or document['source_sha256'] != 'f6d5c671061d18a1c131716122f3e6444f2d7f7ec546940224d91252a4e5745c'
            or document['delist_date_semantics'] != 'provider_documented_last_trade_date'
            or document['historical_vintage_verified'] is not False):
        raise ValueError('Exact retained lifecycle wrapper and source binding required')
    records = document['records']
    # Metadata-only validation precedes all ETF/settlement financial decoding.
    select_contract_pairs(records, sessions)
    return records


def load_inputs(snapshots):
    """Called only after the durable one-use claim; bytes already hash-checked."""
    rows = list(csv.DictReader(io.StringIO(snapshots['calendar'].decode('utf-8-sig'))))
    sessions = [row['date'] for row in rows if row['market'] == 'CN' and row['is_open'] == '1'
                and '2019-12-30' <= row['date'] <= '2024-06-28']
    lifecycle = lifecycle_records(snapshots['lifecycle'], sessions)
    authority = admission._json(snapshots['etf_authority'])
    if (authority.get('asset_id') != ASSET or authority['target_metadata']['adjusted'] is not False
            or authority['units']['stored_volume'] != 'fund units/shares'
            or authority['units']['stored_amount'] != 'CNY'
            or authority['units']['do_not_apply_multipliers_again'] is not True):
        raise ValueError('Exact unadjusted ETF unit authority required')
    columns = ['asset_id', 'symbol', 'date', 'open', 'high', 'low', 'close', 'adj_close',
               'volume', 'currency', 'source', 'adjusted', 'exchange', 'asset_type']
    bars = []
    for year in range(2020, 2025):
        raw = snapshots['bars_'+str(year)]
        declared = next(row for row in authority['partitions'] if row['year'] == year)
        if admission.digest(raw) != declared['sha256']:
            raise ValueError('ETF authority partition bytes changed')
        frame = pd.read_parquet(io.BytesIO(raw), columns=columns,
            filters=[('asset_id', '==', ASSET)], engine='pyarrow')
        if (len(frame) != declared['target_rows'] or not frame['asset_id'].eq(ASSET).all()
                or not frame['symbol'].eq('159985.SZ').all() or not frame['currency'].eq('CNY').all()
                or not frame['source'].eq('tushare').all() or not frame['exchange'].eq('XSHE').all()
                or not frame['asset_type'].eq('etf').all() or not frame['adjusted'].eq(False).all()
                or not frame['adj_close'].eq(frame['close']).all()):
            raise ValueError('Frozen raw ETF identity or price basis changed')
        for row in frame.to_dict('records'):
            day = row['date'].isoformat()
            if not day.startswith(str(year)+'-'):
                raise ValueError('ETF year partition mismatch')
            bars.append(dict(asset_id=ASSET, date=day,
                **{key: row[key] for key in ('open', 'high', 'low', 'close', 'volume')},
                suspended=None, limit_up=None, limit_down=None))
    expected_dates = [day for day in sessions if day >= '2020-01-02']
    if sorted(row['date'] for row in bars) != expected_dates or len(bars) != 1087:
        raise ValueError('Exact1087 ETF dates required; no missing/duplicate/extra marks')
    structure = admission._json(snapshots['settlement_structure'])
    source_scope = admission._json(snapshots['settlement_scope'])
    if (structure.get('POST_started_count') != 38 or structure.get('retries') != 0
            or len(structure['receipts']) != 38 or len(source_scope['requests']) != 38
            or admission.digest(snapshots['settlement_scope']) != structure['scope_sha256']):
        raise ValueError('Frozen38-source structure required')
    settlements = []
    for number, receipt in enumerate(structure['receipts'], 1):
        request = source_scope['requests'][number-1]
        raw = snapshots['settlement_'+str(number).zfill(2)]
        if (admission.digest(raw) != receipt['raw_sha256']
                or receipt['status'] != 'format_complete_for_selected_dates'
                or receipt['missing_selected_dates'] or receipt['additional_in_range_dates']):
            raise ValueError('Exact selected settlement originals required')
        body = admission._json(raw, decimal_numbers=True)
        if body.get('code') != 0 or body['data']['fields'] != ['ts_code', 'trade_date', 'settle']:
            raise ValueError('Settlement response field contract changed')
        items = body['data']['items']
        if (request['request_id'] != receipt['request_id']
                or request['params']['ts_code'] != receipt['ts_code']
                or len(items) != receipt['row_count']
                or any(len(row) != 3 or row[0] != receipt['ts_code'] for row in items)
                or sorted(row[1] for row in items) != [day.replace('-', '') for day in request['required_selected_dates']]
                or any(not '20191230' <= row[1] <= '20240626' for row in items)):
            raise ValueError('Selected settlement rows changed')
        settlements.extend(dict(zip(body['data']['fields'], row, strict=True)) for row in items)
    if len(settlements) != 2174:
        raise ValueError('Exact2174 selected contract/date records required')
    actions = admission._json(snapshots['actions'])
    review = admission._json(snapshots['actions_review'])
    if (actions.get('asset_id') != ASSET or actions.get('coverage_start') != '2020-01-02'
            or actions.get('coverage_end') != '2024-06-28'
            or actions.get('share_conversions_supported') is not False
            or review.get('actions_sha256') != admission.digest(snapshots['actions'])
            or review.get('status') != 'accepted_for_conditional_account'
            or review.get('qualified') is not False):
        raise ValueError('Explicit reviewed corporate-action input required')
    return dict(sessions=sessions, bars=bars, settlements=settlements, actions=actions['actions'],
                lifecycle=lifecycle)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['preview', 'execute'])
    parser.add_argument('--registration-sha256')
    args = parser.parse_args(argv)
    root = Path(__file__).resolve().parents[1]
    packet, _ = admission.admitted_packet(root)
    if args.command == 'preview':
        print(json.dumps(dict(status='frozen_batch_ready_not_executed',
            registration_sha256=packet['registration_sha256'], financial_values_decoded=False,
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
