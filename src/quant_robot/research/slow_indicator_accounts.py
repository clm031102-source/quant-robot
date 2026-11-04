"""Four prospective slow rules, full nine-cost accounts and frozen controls.

No input acquisition or admission. Called only after the distinct exclusive claim.
"""
import json
from quant_robot.paper.comparative_allocation import run_comparison
from quant_robot.research.indicator_combinations import ASSETS, daily_pnl, uncertainty
from quant_robot.research.slow_indicator_combinations import RULES, slow_features, separated_cycles


def calculate(snapshots, *, progress=None):
    proposal = json.loads(snapshots['proposal'])
    bars = json.loads(snapshots['bars'])
    sessions = json.loads(snapshots['sessions'])
    actions = json.loads(snapshots['actions'])['events']
    policy = json.loads(snapshots['comparison_policy'])
    if (tuple(proposal['assets']) != ASSETS or tuple(proposal['rules']) != RULES
            or proposal['hypothesis_count'] != 4 or policy.get('schema_version') != 2
            or sessions[0] != '2013-12-05' or sessions[-1] != '2024-01-02'
            or len(sessions) != 2454 or len(bars) != 4908):
        raise ValueError('Exact retained universe, calendar and finite experiment required')
    findings, full_accounts, signals = [], {}, {}
    for asset in ASSETS:
        asset_bars = sorted([r for r in bars if r['asset_id'] == asset], key=lambda r:r['date'])
        if [r['date'] for r in asset_bars] != sessions:
            raise ValueError('Missing or duplicate source sessions')
        source_actions = [a for a in actions if a['asset_id'] == asset]
        frame = slow_features(asset_bars, source_actions)
        # JSON nulls preserve unknown states rather than silently labeling them false.
        signals[asset] = json.loads(frame.to_json(orient='records'))
        for rule in RULES:
            case = f'{asset}__{rule}__every5_buffered'
            cycles = separated_cycles(sessions, frame[rule].tolist(), frame['trend_exit'].tolist(), first=proposal['first_session'])
            result = run_comparison(asset_bars, sessions=sessions, asset=asset, strategy_cycles=cycles, actions=source_actions, policy=policy)
            full_accounts[case] = dict(result, strategy_cycles=cycles)
            primary = result['comparisons']['min5_slip10']
            summary = primary['accounts']['strategy']
            accounts = result['accounts']['min5_slip10']
            pnls = {role:daily_pnl(account) for role,account in accounts.items()}
            evaluation = {role:values.loc[proposal['evaluation_first']:] for role,values in pnls.items()}
            interval = uncertainty(evaluation['strategy'].to_numpy(), evaluation['holding'].to_numpy(), hypotheses=4, seed=20261011)
            annual = {str(year):float(pnls['strategy'][[d.startswith(str(year)) for d in pnls['strategy'].index]].sum()) for year in range(2015, 2024)}
            folds = []
            for year in proposal['evaluation_years']:
                mask = [d.startswith(str(year)) for d in pnls['strategy'].index]
                folds.append(dict(year=year,strategy_PnL_CNY=float(pnls['strategy'][mask].sum()),holding_PnL_CNY=float(pnls['holding'][mask].sum()),selection='fixed_no_fit_no_overlapping_folds',capital_reset=False))
            stress = daily_pnl(result['accounts']['min10_slip30']['strategy']).loc[proposal['evaluation_first']:].sum()
            checks = dict(full_net_positive=summary['net_PnL_CNY'] > 0,
                evaluation_net_positive=float(evaluation['strategy'].sum()) > 0,
                later_net_positive=summary['later_net_contribution_CNY'] > 0,
                beat_holding_evaluation=float((evaluation['strategy']-evaluation['holding']).sum()) > 0,
                profitable_evaluation_years=sum(f['strategy_PnL_CNY'] > 0 for f in folds) >= 3,
                completed_episodes=summary['completed_episode_count'] >= 30,
                drawdown=summary['maximum_drawdown'] <= .08,
                no_risk_breaches=not summary['risk_breaches'],terminal_settled=summary['terminal_settled'],
                corrected_net_lower_positive=interval['corrected_one_sided_net_lower_CNY'] > 0,
                corrected_difference_lower_positive=interval['corrected_one_sided_difference_lower_CNY'] > 0,
                high_cost_evaluation_positive=float(stress) > 0)
            findings.append(dict(case_id=case,asset=asset,rule=rule,cadence=5,
                prospectively_registered=True,
                summary=summary,comparison=primary,annual_PnL_CNY=annual,evaluation_folds=folds,
                development_PnL_CNY=float(pnls['strategy'].loc[proposal['first_session']:proposal['development_last']].sum()),
                evaluation_PnL_CNY=float(evaluation['strategy'].sum()),evaluation_holding_PnL_CNY=float(evaluation['holding'].sum()),
                high_cost_evaluation_PnL_CNY=float(stress),uncertainty=interval,checks=checks,
                conditional_screen_passed=all(checks.values()),
                cost_summaries=result['comparisons'],unknown_signal_sessions=int(frame.loc[frame['date']>=proposal['first_session'],rule].isna().sum())))
            if progress:
                progress(dict(completed=len(findings),total=4,case_id=case,primary_net_PnL_CNY=summary['net_PnL_CNY']))
    return dict(study_id=proposal['study_id'],findings=findings,accounts=full_accounts,signals=signals,
        conditional_pass_count=sum(r['conditional_screen_passed'] for r in findings),hypotheses=4,
        fresh_out_of_sample=False,net_positive_EV_verified=False,paper_promotion_allowed=False,
        final_holdout_allowed=False,live_boundary_allowed=False,new_forward_days=0,
        source_limitations=proposal['limitations'])
