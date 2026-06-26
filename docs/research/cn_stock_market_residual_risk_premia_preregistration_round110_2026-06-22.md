# CN Stock Market Residual Risk Premia Preregistration Round110

## Command

```powershell
python scripts\run_market_residual_risk_premia_preregistration.py --output-dir data\reports\market_residual_risk_premia_preregistration_round110_20260622 --min-candidates 8
```

## Source Evidence

- Source audit: `docs/research/cn_stock_round107_109_three_round_review_2026-06-22.md`
- Source rounds: Round107 negative-IC prescreen, Round108 lead dedup, Round109 overnight/intraday gap prescreen
- Evidence status: family rotation required, not promotion evidence
- Main blockers addressed:
  - Round108 hard redundancy with price-volume cluster
  - Round109 zero research leads after gap prescreen
  - FDR-significant but weak ICIR evidence must not be promoted

## Headline Result

- Stage: `market_residual_risk_premia_preregistration`
- Candidates: 10
- Unique candidate names: 10
- Portfolio backtest allowed candidates: 0
- Promotion allowed candidates: 0
- Blockers: none
- Next required gate: `alphalens_style_ic_quantile_turnover_prescreen`
- Next direction: `round111_market_residual_risk_premia_prescreen`

## Factor Model Policy

Round110 explicitly changes the source of information. Instead of extending raw price-volume, anti-overheat, or OHLC gap formulas, the next family must first build an equal-weight CN stock market proxy from signal-date-available data, then estimate rolling market beta, downside beta, correlation, residual return, and residual volatility.

The goal is to separate possible alpha from hidden market beta before any portfolio grid. No candidate is allowed to claim profitability from preregistration.

## Candidates

| Candidate | Family | Windows | Interpretation |
|---|---|---:|---|
| `low_beta_120` | market beta low | 120 | Test low market exposure directly. |
| `downside_beta_low_120` | downside beta low | 60,120 | Penalize market sensitivity on negative market days. |
| `idio_vol_low_60` | idiosyncratic volatility low | 20,60 | Test low stock-specific volatility after market residualization. |
| `residual_reversal_5_60` | market residual reversal | 5,60 | Test short reversal after removing market beta. |
| `residual_momentum_quality_20_120` | market residual momentum | 20,120 | Test skip-style residual momentum with path quality. |
| `low_market_corr_60` | market correlation low | 60 | Prefer lower broad-market correlation before capacity tests. |
| `crash_resilience_60` | crash resilience | 60 | Penalize co-crash behavior and downside residual volatility. |
| `beta_adjusted_range_contraction_60` | beta-adjusted range contraction | 60 | Re-test range contraction after market adjustment. |
| `downside_residual_vol_low_60` | downside residual volatility low | 60 | Test low downside stock-specific noise. |
| `positive_residual_skew_60` | positive residual skew | 60 | Test favorable stock-specific upside-tail shape. |

## Promotion And Portfolio Gate

No candidate is paper-ready. No candidate may enter a top-N portfolio grid before Round111 computes:

- same-parameter 2015-2025 residual factor matrix,
- signal-date-only equal-weight market proxy,
- IC, ICIR, t-stat, IC>0 rate,
- quintile spread and monotonicity,
- factor turnover and date coverage,
- capacity participation diagnostics,
- redundancy versus existing price-volume and low-vol families,
- multiple-testing accounting.

## Audit Judgment

Round110 is a useful direction change, not a profitability result. It directly attacks the likely failure mode from recent rounds: raw technical signals can be statistically visible but redundant or mostly hidden beta. The efficient next action is Round111 residual prescreen, not parameter tuning or portfolio backtest.
