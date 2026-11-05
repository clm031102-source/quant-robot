"""Training-only finite selection followed by frozen continuous evaluation.

All accounts start in cash before 2019; training is a predictive screen, not a
simulated account that is reset. Annual evaluation reports never reset capital.
"""
import gzip
import json
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
import numpy as np

from quant_robot.paper.comparative_allocation import run_comparison
from quant_robot.research.indicator_combinations import ASSETS, daily_pnl, state_cycles, uncertainty
from quant_robot.research.full_position_factors import (CATALOG, candidate_combinations,
    feature_frame, combined_state, screen_training, choose_training_candidates)
from quant_robot.research.monthly_diagnostic_registration import canonical, sha256, write_exclusive_json


def audit_terminal_rights(result, actions):
    action_map = {a['event_id']: a for a in actions}
    for case, roles in result['accounts'].items():
        for role, value in roles.items():
            paid = {e['event_id']: Decimal(str(e['amount'])) for e in value['corporate_action_journal']
                    if e['kind'] == 'cash_paid_after_fills'}
            pending = []
            for event in value['corporate_action_journal']:
                if event['kind'] != 'record_entitlement' or not event['quantity']:
                    continue
                earned = (Decimal(event['quantity']) * Decimal(str(action_map[event['event_id']]['cash_per_unit']))).quantize(Decimal('.01'), rounding=ROUND_HALF_UP)
                remaining = earned - paid.get(event['event_id'], Decimal(0))
                if remaining > 0:
                    pending.append(dict(event_id=event['event_id'], unpaid_CNY=float(remaining)))
            settled = value['risk']['terminal_settled'] and not pending
            value['terminal_entitlement_audit'] = dict(unpaid_rights=pending, terminal_settled=settled)
            result['comparisons'][case]['accounts'][role]['terminal_settled'] = settled


def calculate(snapshots, *, output_dir, progress=None):
    proposal = json.loads(snapshots['proposal'])
    bars = json.loads(snapshots['bars']); sessions = json.loads(snapshots['sessions'])
    actions = json.loads(snapshots['actions'])['events']
    policy = json.loads(snapshots['comparison_policy'])
    if (tuple(proposal['assets']) != ASSETS or proposal['indicator_names'] != list(CATALOG)
            or proposal['combination_count_per_asset'] != len(candidate_combinations())
            or sessions[0] != '2013-12-05' or sessions[-1] != '2024-01-02'
            or len(sessions) != 2454 or len(bars) != 4908 or policy['schema_version'] != 3):
        raise ValueError('Exact retained source, catalogue and full NAV policy required')
    directory = Path(output_dir)
    selected = {}; training = {}; asset_sources = {}
    # No evaluation labels or account outcomes are computed in this loop.
    for asset in ASSETS:
        source = sorted([r for r in bars if r['asset_id'] == asset], key=lambda r:r['date'])
        if [r['date'] for r in source] != sessions:
            raise ValueError('Missing source session')
        action_source = [a for a in actions if a['asset_id'] == asset]
        asset_sources[asset] = (source, action_source)
        earlier = [r for r in source if r['date'] <= proposal['training_last']]
        frame = feature_frame(earlier, action_source)
        training[asset] = screen_training(frame, first=proposal['training_first'],
            last=proposal['training_last'], horizon=5, minimum_selected=30)
        selected[asset] = choose_training_candidates(training[asset], count=3)
    write_exclusive_json(directory/'training_factor_screen.json', training)
    selection = dict(selected=selected, training_first=proposal['training_first'],
        training_last=proposal['training_last'], prediction_horizon_sessions=5,
        labels_purged_at_training_end=True, evaluation_outcomes_read=False,
        screened_combinations=2*len(candidate_combinations()), training_accounts_run=0)
    write_exclusive_json(directory/'frozen_training_selection.json', selection)
    selection_hash = sha256((directory/'frozen_training_selection.json').read_bytes())
    if progress:
        progress(dict(stage='selection_frozen', searched=selection['screened_combinations'],
                      selected=sum(map(len, selected.values())), selection_sha256=selection_hash))
    findings = []; archives = []
    planned_count = sum(map(len, selected.values())) * 2
    for asset, choices in selected.items():
        source, action_source = asset_sources[asset]
        frame = feature_frame(source, action_source)
        for choice in choices:
            state = combined_state(frame, choice['components'])
            for cadence in (1, 5):
                case_id = f"{asset}__{choice['candidate_id']}__every{cadence}"
                cycles = state_cycles(sessions, state.tolist(), first=proposal['evaluation_first'], cadence=cadence)
                result = run_comparison(source, sessions=sessions, asset=asset,
                    strategy_cycles=cycles, actions=action_source, policy=policy)
                audit_terminal_rights(result, action_source)
                primary = result['comparisons']['min5_slip10']
                summary = primary['accounts']['strategy']
                accounts = result['accounts']['min5_slip10']
                pnl = {k:daily_pnl(v).loc[proposal['evaluation_first']:] for k,v in accounts.items()}
                interval = uncertainty(pnl['strategy'].to_numpy(), pnl['holding'].to_numpy(),
                    hypotheses=12, seed=20261104)
                interval['interpretation'] = 'conditional_historical_sensitivity_only; 4648_training_searches_and_prior_data_exposure_remain_disclosed; not_certified_EV'
                annual = [dict(year=y, strategy_PnL_CNY=float(pnl['strategy'].loc[[d.startswith(str(y)) for d in pnl['strategy'].index]].sum()),
                    holding_PnL_CNY=float(pnl['holding'].loc[[d.startswith(str(y)) for d in pnl['holding'].index]].sum()),
                    capital_reset=False, candidate_reselected=False) for y in range(2019,2024)]
                high = result['comparisons']['min10_slip30']['accounts']['strategy']['net_PnL_CNY']
                checks = dict(net_positive=summary['net_PnL_CNY'] > 0,
                    later_positive=summary['later_net_contribution_CNY'] > 0,
                    beat_holding=primary['strategy_minus_holding_CNY'] > 0,
                    profitable_years=sum(a['strategy_PnL_CNY'] > 0 for a in annual) >= 3,
                    completed_episodes=summary['completed_episode_count'] >= 30,
                    no_risk_breaches=not summary['risk_breaches'], drawdown=summary['maximum_drawdown'] <= .08,
                    terminal_settled=all(a['terminal_settled'] for a in primary['accounts'].values()),
                    high_cost_positive=high > 0,
                    conditional_net_interval_positive=interval['corrected_one_sided_net_lower_CNY'] > 0,
                    conditional_difference_interval_positive=interval['corrected_one_sided_difference_lower_CNY'] > 0)
                ret = pnl['strategy'].to_numpy() / np.maximum(np.array([r['equity'] for r in accounts['strategy']['equity_curve'] if r['date'] >= proposal['evaluation_first']]) - pnl['strategy'].to_numpy(), 1e-12)
                sharpe = float(np.sqrt(252)*np.mean(ret)/np.std(ret,ddof=1)) if np.std(ret,ddof=1)>0 else None
                findings.append(dict(case_id=case_id, asset=asset, components=choice['components'],cadence=cadence,
                    training=choice, summary=summary, annual=annual, primary_comparison=primary,
                    cost_summaries=result['comparisons'], conditional_uncertainty=interval,
                    total_return=summary['net_PnL_CNY']/10000, daily_sharpe=sharpe,
                    checks=checks, conditional_screen_passed=all(checks.values()),
                    unknown_signal_sessions=int(np.isnan(state[[d>=proposal['evaluation_first'] for d in sessions]]).sum())))
                path = directory/f"accounts_{len(findings):02d}.json.gz"
                payload = canonical(dict(case_id=case_id, strategy_cycles=cycles, **result))
                with path.open('xb') as stream:
                    with gzip.GzipFile(fileobj=stream, mode='wb',mtime=0) as compressed:
                        compressed.write(payload)
                archives.append(dict(path=path.name,sha256=sha256(path.read_bytes()),uncompressed_sha256=sha256(payload)))
                if progress:
                    progress(dict(stage='account_complete', completed=len(findings), total=planned_count,
                        case_id=case_id, net_PnL_CNY=summary['net_PnL_CNY'], conditional_passed=all(checks.values())))
    return dict(study_id=proposal['study_id'], findings=findings, account_archives=archives,
        indicator_count=len(CATALOG), training_combination_count=selection['screened_combinations'],
        frozen_selection_sha256=selection_hash, account_candidate_count=planned_count,
        account_count=planned_count*27, conditional_pass_count=sum(f['conditional_screen_passed'] for f in findings),
        qualified_strategies=0, fresh_out_of_sample=False, net_positive_EV_verified=False,
        paper_promotion_allowed=False, live_boundary_allowed=False, final_holdout_allowed=False,
        new_forward_days=0, source_limitations=proposal['limitations'])
