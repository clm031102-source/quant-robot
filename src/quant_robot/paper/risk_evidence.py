"""Check supplied daily account marks against explicit fixed-currency limits."""
from __future__ import annotations

from dataclasses import asdict, dataclass
import json
import math

from quant_robot.paper.account_comparison import _account, calendar_date


@dataclass(frozen=True)
class AccountRiskLimits:
    initial_cash: float = 10000
    max_position_cny: float = 1000
    max_daily_loss_cny: float = 60
    max_drawdown: float = .08


def audit_cash_account_risk(result: dict, limits=AccountRiskLimits()) -> dict:
    """This observes supplied daily marks; it does not change orders or certify data."""
    for key,value in asdict(limits).items():
        if isinstance(value,bool) or not isinstance(value,(int,float)) or not math.isfinite(value) or value <= 0:
            raise ValueError('Risk limits must be explicit finite positive numbers')
    if limits.max_drawdown >= 1 or limits.max_position_cny > limits.initial_cash:
        raise ValueError('Invalid fixed-currency risk limits')
    curve,costs=_account(result)
    issues,breaches=[],[]
    if costs['initial_cash'] != limits.initial_cash:
        breaches.append({'reason':'initial_capital_mismatch'})
    peak=float(curve.iloc[0]['equity'])
    previous=peak
    max_loss,max_drawdown,max_position=0.0,0.0,0.0
    for row in curve.to_dict(orient='records'):
        date=str(row['date'])
        equity=float(row['equity'])
        peak=max(peak,equity)
        loss=max(0.0,previous-equity)
        drawdown=max(0.0,1-equity/peak)
        max_loss,max_drawdown=max(max_loss,loss),max(max_drawdown,drawdown)
        if loss >= limits.max_daily_loss_cny:
            breaches.append({'date':date,'reason':'daily_loss_limit','loss_cny':loss})
        if drawdown >= limits.max_drawdown-1e-12:
            breaches.append({'date':date,'reason':'drawdown_limit','drawdown':drawdown})
        previous=equity
        positions=row.get('position_values')
        if isinstance(positions,str):
            try:
                positions=json.loads(positions)
            except (ValueError,TypeError):
                positions=None
        if not isinstance(positions,dict):
            issues.append({'date':date,'reason':'daily_position_evidence_missing'})
            continue
        total=0.0
        for asset,position in positions.items():
            try:
                if not isinstance(asset,str) or not asset or not isinstance(position,dict):
                    raise ValueError('invalid position identity')
                values=[position[key] for key in ('quantity','price','market_value')]
                if any(isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x) or x<=0 for x in values):
                    raise ValueError('invalid position amount')
                quantity,price,declared=values
                value=quantity*price
                if not math.isfinite(value) or not math.isclose(value,declared,rel_tol=0,abs_tol=1e-8):
                    raise ValueError('position amount differs from quantity times price')
                total+=value
                max_position=max(max_position,value)
                if calendar_date(position.get('price_date')) != row['date']:
                    issues.append({'date':date,'asset_id':asset,'reason':'position_mark_not_current'})
                if value > limits.max_position_cny+1e-8:
                    breaches.append({'date':date,'asset_id':asset,'reason':'position_limit','market_value':value})
            except (ValueError,KeyError,TypeError) as exc:
                issues.append({'date':date,'asset_id':str(asset),'reason':'invalid_position_evidence','detail':str(exc)})
        if not math.isclose(total+row['cash']+row['dividend_receivable'],equity,rel_tol=0,abs_tol=1e-8):
            issues.append({'date':date,'reason':'position_cash_equity_mismatch'})
    return {'audit_type':'daily_marked_account_risk_v1','limits':asdict(limits),
        'within_limits_on_supplied_marks':not issues and not breaches,
        'evidence_complete_on_supplied_calendar':not issues,'issues':issues,'breaches':breaches,
        'max_position_cny':max_position if not issues else None,'max_daily_loss_cny':max_loss,'max_drawdown':max_drawdown,
        'sessions':len(curve),'first_date':str(curve.iloc[0]['date']),'last_date':str(curve.iloc[-1]['date']),
        'execution_enforcement_verified':False,'complete_exchange_calendar_verified':False,
        'source_quality_verified':False,'research_admission_verified':False,'executable':False}
