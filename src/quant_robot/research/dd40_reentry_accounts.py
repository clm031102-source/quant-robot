"""One prospective risk-policy sensitivity on all twelve original frozen cases.

No factor recomputation or reselection. Capital and peak remain continuous.
"""
import gzip
import json
from pathlib import Path
import numpy as np

from quant_robot.paper.comparative_allocation import run_comparison
from quant_robot.research.indicator_combinations import ASSETS, daily_pnl, uncertainty
from quant_robot.research.full_position_accounts import audit_terminal_rights
from quant_robot.research.monthly_diagnostic_registration import canonical, sha256, write_exclusive_json


def calculate(snapshots, *, output_dir, progress=None):
    proposal = json.loads(snapshots['proposal'])
    bars = json.loads(snapshots['bars']); sessions = json.loads(snapshots['sessions'])
    actions = json.loads(snapshots['actions'])['events']
    policy = json.loads(snapshots['comparison_policy'])
    plan = json.loads(snapshots['strategy_cycles'])
    cases = plan['cases']
    if (tuple(proposal['assets']) != ASSETS or len(cases) != 12
            or policy['schema_version'] != 5 or len(sessions) != 2454 or len(bars) != 4908
            or sessions[0] != '2013-12-05' or sessions[-1] != '2024-01-02'):
        raise ValueError('Exact retained cases, sources and recovery policy required')
    directory = Path(output_dir)
    findings = []; archives = []
    planned_count = len(cases)
    selection_hash = plan['prior_frozen_selection_sha256']
    for item in cases:
        asset = item['asset']; cadence = item['cadence']; choice = item['training']
        case_id = item['case_id']; cycles = item['cycles']
        source = sorted([r for r in bars if r['asset_id'] == asset],key=lambda r:r['date'])
        action_source = [a for a in actions if a['asset_id'] == asset]
        if [r['date'] for r in source] != sessions:
            raise ValueError('Exact source calendar required')
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
            no_risk_breaches=not summary['risk_breaches'], drawdown=summary['maximum_drawdown'] <= .40,
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
            daily_pause_count=sum(e['kind']=='daily_loss_pause' for e in accounts['strategy']['daily_recovery_journal']),
            drawdown_pause_count=sum(e['kind']=='global_drawdown_pause' for e in accounts['strategy']['daily_recovery_journal']),
            recovery_count=sum(e['kind']=='eligible_after_five_complete_flat_sessions' for e in accounts['strategy']['daily_recovery_journal']),
            permanent_halt=accounts['strategy']['risk']['new_entries_halted']))
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
        indicator_count=24, training_combination_count=0, reused_training_combination_count=4648,
        frozen_selection_sha256=selection_hash, account_candidate_count=planned_count,
        account_count=planned_count*27, conditional_pass_count=sum(f['conditional_screen_passed'] for f in findings),
        qualified_strategies=0, fresh_out_of_sample=False, net_positive_EV_verified=False,
        paper_promotion_allowed=False, live_boundary_allowed=False, final_holdout_allowed=False,
        new_forward_days=0, source_limitations=proposal['limitations'])
