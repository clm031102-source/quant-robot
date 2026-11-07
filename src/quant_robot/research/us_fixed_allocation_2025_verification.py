"""Saved-only three-role arithmetic; no engine, raw source or strategy execution."""
from __future__ import annotations
from decimal import localcontext
from pathlib import Path
import json

from . import us_monthly_rotation_verification as ledger

METHOD = 'c46de5d2ea527be77aea806cb6ab42c331b6e4b29070f4e89f840845ab7f74a1'
ROLES = {'primary':('fixed_quarters','1.00',10),'stress':('fixed_quarters','2.50',30),'cash':('cash','0.35',0)}
STATISTICS = dict(status='not_applicable_single_selected_year',bootstrap_computed=False,
                  statistical_significance_claimed=False,qualified=False)
require,same = ledger.require,ledger.same


def verify_fixed_signals(fixture, actual):
    dates=[r['date'] for r in fixture['days']]
    require(dates==sorted(set(dates)) and dates[-1]==fixture['terminal_date'],'calendar')
    first=dates.index(fixture['first_decision_date']);terminal=len(dates)-1
    require(first>=19 and first+4<terminal,'prior20_and_execution')
    require(all(d[:7]==dates[first][:7] for d in dates[:first+1]),'one_month_warmup')
    ends=[i for i in range(first,terminal) if dates[i][:7]!=dates[i+1][:7]]
    require(ends and ends[0]==first,'first_month_end')
    months=[int(dates[i][:4])*12+int(dates[i][5:7]) for i in ends]
    require(all(b-a==1 for a,b in zip(months,months[1:])),'consecutive_month_ends')
    if fixture['evidence_kind']!='artificial':
        require(dates[first]=='2024-12-31' and dates[-1]=='2025-12-31'
                and all(d[:4]=='2025' for d in dates[first+1:]) and len(ends)==12
                and dates[ends[-1]][:7]=='2025-11','fixed_2025_window')
    else:require(all(2000<=int(d[:4])<=2004 for d in dates),'artificial_years')
    expected=[dict(index=i,date=dates[i],signal_kind='fixed_calendar_weights_no_momentum',intended_gross=ledger.D(1),
        weights={'fixed_quarters':dict.fromkeys(ledger.ASSETS,ledger.D('.25'))},ordinary_execution_possible=i+4<terminal) for i in ends]
    same(expected,actual,'fixed_signals');return expected


def verify_account(fixture, account):
    same('us_fixed_allocation_2025_fixture_v1',fixture['schema'],'fixture_schema')
    same('us_fixed_allocation_2025_account_v1',account['schema'],'account_schema')
    role=account['role'];require(role in ROLES,'role')
    for key,value in zip(('policy','minimum_commission','slippage_bps'),ROLES[role]):same(value,account[key],'role_'+key)
    p=fixture['provenance']
    require(p.get('split_policy_verified') is True and p.get('capital_gains_present') is False
            and p.get('holding_window_splits_absent') is True,'action_policy')
    require(all(x['ex_date']>fixture['first_decision_date'] for x in fixture['dividends']),'no_inherited_rights')
    with localcontext(ledger.CONTEXT):
        result=ledger._verify_account(fixture,account,expected_method=METHOD,signal_verifier=verify_fixed_signals)
    zero_target=[dict(decision_index=e['decision_index'],date=e['date'],asset=a,target_quantity=0)
                 for e in account['monthly_events'] for a in ledger.ASSETS if a in e['targets'] and e['targets'][a]==0]
    zero_buys=[o for e in account['monthly_events'] for o in e['buy_orders'] if o['quantity']==0]
    unheld={a:sum(d['after']['quantities'][a]==0 for d in account['days']) for a in ledger.ASSETS}
    same(zero_target,account['zero_share_target_legs'],'zero_targets');same(zero_buys,account['zero_share_buy_legs'],'zero_buys')
    same(unheld,account['unheld_asset_sessions'],'unheld_sessions');same(STATISTICS,account['statistics'],'no_bootstrap')
    result.update(role=role,zero_share_target_legs=len(zero_target),zero_share_buy_legs=len(zero_buys),unheld_asset_sessions=unheld)
    return result


def verify_recorded_accounts(root, decoded_ref, accounts, statistics_ref, registration_sha256):
    root=Path(root).resolve();refs=[decoded_ref]
    decoded=json.loads(ledger._bound(root,decoded_ref)[0]);fixture=decoded.get('fixture',decoded)
    if 'fixture' in decoded:
        same({'fixture','provenance'},set(decoded),'decoded_wrapper');same(fixture['provenance'],decoded['provenance'],'wrapper_provenance')
    kind=fixture['evidence_kind'];require(kind in ('artificial','artificial_values_true_calendar','known_history_conditional'),'kind')
    historical=kind=='known_history_conditional'
    if kind=='artificial':same(None,registration_sha256,'artificial_registration')
    else:require(type(registration_sha256) is str and len(registration_sha256)==64 and all(c in '0123456789abcdef' for c in registration_sha256),'registration')
    if historical:same(registration_sha256,fixture['provenance']['registration_sha256'],'provenance_registration')
    same(set(ROLES),set(accounts),'three_account_roles');results={};paths=[]
    for role in ROLES:
        wrapper=accounts[role];ref=wrapper['artifact'];refs.append(ref)
        if historical:require('completion' in wrapper,'completion_required')
        if 'completion' in wrapper:
            refs.append(wrapper['completion']);marker=json.loads(ledger._bound(root,wrapper['completion'])[0])
            same('complete',marker['status'],'completion_status');same(role,marker['account_id'],'completion_role')
            same(registration_sha256,marker['registration_sha256'],'completion_registration');same(ref,marker['artifact'],'completion_raw')
        raw,path=ledger._bound(root,ref);paths.append(str(path));account=json.loads(raw)
        same(role,account['role'],'indexed_role');same(registration_sha256,account['registration_sha256'],'registration')
        same(account['summary'],wrapper['summary'],'indexed_summary');results[role]=verify_account(fixture,account)
    require(len(set(paths))==3,'unique_account_paths')
    refs.append(statistics_ref)
    descriptive=dict(status='one_year_descriptive_no_bootstrap',annual_contributions={k:v['annual'] for k,v in results.items()},
                     statistical_significance_claimed=False,qualified=False)
    same(descriptive,json.loads(ledger._bound(root,statistics_ref)[0]),'statistics')
    for ref in refs:ledger._bound(root,ref)
    primary,stress=results['primary']['summary'],results['stress']['summary']
    checks={'primary_cash_profit_positive':ledger.decimal(primary['terminal_cash_only_net_profit'])>0,
            'stress_cash_profit_positive':ledger.decimal(stress['terminal_cash_only_net_profit'])>0,
            'primary_DD_below40':ledger.decimal(primary['observed_maxDD'])<ledger.D('.40'),
            'stress_DD_below40':ledger.decimal(stress['observed_maxDD'])<ledger.D('.40'),
            'all_terminal_inventory_closed':all(r['summary']['terminal_inventory_closed'] for r in results.values())}
    return dict(status='recorded_accounting_consistent',evidence_kind=kind,historical_returns_computed=historical,
        registration_sha256=registration_sha256,accounts_checked=3,counts={key:sum(x[key] for x in results.values()) for key in ('days','fills','actions','risk_observations')},
        accounts=results,fixed_economic_checks=checks,all_fixed_economic_conditions_passed=all(checks.values()),
        statistics=descriptive,strategy_intent_replayed=False,qualified=False,real_forward=0,
        limits=['Saved arithmetic and fixed-calendar weights; order-selection completeness not replayed',
                'Selected one-year conditional allocation; no alpha, statistical significance, broker fee, personal tax or execution certification',
                'Cash profit includes locked proceeds and excludes unpaid dividends; not immediately withdrawable'])
