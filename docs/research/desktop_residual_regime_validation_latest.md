# Desktop Residual-Regime Validation Summary

- Generated at: 2026-07-16 02:37:52 +0800
- Scope: residualized moneyflow + liquidity/volatility/amount controls with regime-aware walk-forward.
- Boundary: research-to-paper only; no broker connection, no account reads, no order placement.
- Cases: 96
- Accepted: 0 / 96
- Rejected: 96 / 96
- Walk-forward manifest: verified

## Top Walk-Forward Rows

| Case | Status | Factor | Regime | Top N | Cost | Sharpe | Adj Sharpe | Eff N | Overlap | Relative | Drawdown | Folds | Adj IC p | Tail IC p | Tail IC status |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| CN_large_minus_liquidity_20_top5_cost20_reb1_regime252 | rejected | large_minus_liquidity_20 | regime=252 | 5 | 20.0 | 2.181023765143779 | 2.1445445214961563 | 0.0 | False | 0.1842273616873209 | -0.39128825727712535 | 0/38 | 1.0 | 1.0 | mixed |
| CN_large_resid_liquidity_20_top5_cost20_reb1_regime252 | rejected | large_resid_liquidity_20 | regime=252 | 5 | 20.0 | 2.1542962142197255 | 2.1171071227151765 | 0.0 | False | 0.18785595787674525 | -0.333923784807862 | 0/38 | 1.0 | 1.0 | mixed |
| CN_large_resid_liq_vol_amt_20_top5_cost20_reb1_regime252 | rejected | large_resid_liq_vol_amt_20 | regime=252 | 5 | 20.0 | 2.0492695751210435 | 2.0146809662468295 | 0.0 | False | 0.18784857144058495 | -0.34300600610066734 | 0/38 | 1.0 | 1.0 | mixed |
| CN_large_minus_liquidity_20_top5_cost30_reb1_regime252 | rejected | large_minus_liquidity_20 | regime=252 | 5 | 30.0 | 1.1762491195020228 | 1.1521347027532785 | 0.0 | False | 0.0825819196293213 | -0.41812938197425287 | 0/38 | 1.0 | 1.0 | mixed |
| CN_large_minus_liquidity_20_top5_cost20_reb1_regime120 | rejected | large_minus_liquidity_20 | regime=120 | 5 | 20.0 | 5.267945009270639 | 4.28780519957098 | 0.0 | False | 0.20197822767572132 | -0.40941861353573983 | 0/38 | 1.0 | 1.0 | mixed |
| CN_large_resid_liquidity_20_top5_cost20_reb1_regime120 | rejected | large_resid_liquidity_20 | regime=120 | 5 | 20.0 | 5.312903206035116 | 4.331855887226413 | 0.0 | False | 0.21238105576106486 | -0.40724620017444024 | 0/38 | 1.0 | 1.0 | mixed |
| CN_large_resid_liquidity_20_top5_cost30_reb1_regime252 | rejected | large_resid_liquidity_20 | regime=252 | 5 | 30.0 | 1.1464557594991702 | 1.1216885803546703 | 0.0 | False | 0.08608955004438491 | -0.36046757406459107 | 0/38 | 1.0 | 1.0 | mixed |
| CN_large_resid_liq_vol_amt_20_top5_cost20_reb1_regime120 | rejected | large_resid_liq_vol_amt_20 | regime=120 | 5 | 20.0 | 5.214912988512194 | 4.235063511644206 | 0.0 | False | 0.20703203572884016 | -0.3883820853642802 | 0/38 | 1.0 | 1.0 | mixed |
| CN_large_resid_liq_vol_amt_20_top5_cost30_reb1_regime252 | rejected | large_resid_liq_vol_amt_20 | regime=252 | 5 | 30.0 | 1.045069198513281 | 1.0228744983329576 | 0.0 | False | 0.08575963332479218 | -0.36555288127542196 | 0/38 | 1.0 | 1.0 | mixed |
| CN_large_resid_liquidity_20_top5_cost20_reb1_regime150 | rejected | large_resid_liquidity_20 | regime=150 | 5 | 20.0 | 1.9290977553472082 | 1.9078931048367942 | 0.0 | False | 0.2287096930761059 | -0.40724620017444024 | 0/38 | 1.0 | 1.0 | mixed |

## Promotion Gate

- Blocked: 96
- Research only: 0
- Paper ready: 0
- Manual live review: 0

### Top Blocking Reasons

- `ic_significance_below_threshold`: 96
- `positive_ic_rate_below_threshold`: 96
- `adjusted_ic_p_value_above_threshold`: 96
- `adjusted_ic_significance_not_passed`: 96
- `tail_ic_significance_below_threshold`: 96
- `insufficient_distinct_regime_lookbacks`: 96
- `walk_forward_not_accepted`: 96
- `quality_gap_audit_not_cleared`: 96
- `missing_dates_present`: 96
- `oos_drawdown_above_limit`: 90

## Data Quality

- Status: review_required
- Cleared: False
- Assets: 4726
- Missing date rows: 337904
- Duplicate bars: n/a
- Zero-volume rows: 0
- Asset gap policy: review
- Calendar manifest: data\processed\trading_calendars\cn_tushare_2015_2025\cn_trading_calendar_manifest.json
- Blockers: none
- Review reasons: asset_sessions_require_suspension_review

### Repair Actions

- `inspect_missing_dates`
- `refresh_tushare_data`
- `rebuild_promotion_ops`

## Market Regime Coverage

- Status: sufficient
- Covered regimes: 3
- Allowed rows: 13610
- Blocked rows: 10037
- Regimes: bear, bull, sideways

### Regime Blockers

- None reported.

## Review Notes

- Treat accepted rows as strict-validation evidence, not live-trading approval.
- Prefer candidates that survive more than one regime lookback and do not collapse under higher cost.
- Keep generated CSV/JSON reports out of Git; sync this lightweight Markdown only when it contains useful conclusions.
