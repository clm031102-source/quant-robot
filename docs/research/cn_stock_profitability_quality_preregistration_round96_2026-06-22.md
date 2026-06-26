# CN Stock Profitability Quality Preregistration Round96 - 2026-06-22

## Executive Summary

Round96 produced 14 pre-registered profitability-quality factor candidates from the clean Round95 Tushare `fina_indicator` shard. All 14 passed field/history coverage on the 100-symbol PIT shard.

This is useful factor-mining progress, but it is not a profitability result. No Sharpe ratio, profit rate, win rate, IC, or portfolio return was tested in this round.

## Scope

- Machine: `office_desktop`
- Task: `factor_validation`
- Branch: `codex/factor-validation-cn-stock-long-cycle-20260618`
- Market: CN A-share stocks, not ETF rotation
- Input root: `data/processed/tushare_fina_indicator_shard1_full100_backfill_round95_20260622`
- Output: `data/reports/profitability_quality_preregistration_round96_20260622`
- Safety: research-to-review only; no broker, account, order, or live-trading action

## Command

```powershell
python scripts\run_profitability_quality_preregistration.py --input-root data\processed\tushare_fina_indicator_shard1_full100_backfill_round95_20260622 --output-dir data\reports\profitability_quality_preregistration_round96_20260622 --min-assets 80 --min-passed-candidates 10
```

## Dataset Quality

| Metric | Value |
|---|---:|
| Rows | 4,328 |
| Assets | 100 |
| Duplicate financial keys | 0 |
| Missing asset id rows | 0 |
| Missing PIT date rows | 0 |
| `ann_date < end_date` rows | 0 |
| Ann date range | 2015-04-15 to 2026-04-30 |
| Report period range | 2015-03-31 to 2025-12-31 |

## Candidate Coverage

| Candidate | Category | Coverage | Assets | Decision |
|---|---|---:|---:|---|
| `fina_roe_level` | profitability level | 99.10% | 100 | pre-registered |
| `fina_roa_level` | profitability level | 97.99% | 98 | pre-registered |
| `fina_net_margin_level` | profitability level | 99.98% | 100 | pre-registered |
| `fina_gross_margin_level` | profitability level | 97.97% | 98 | pre-registered |
| `fina_netprofit_yoy_growth` | growth quality | 100.00% | 100 | pre-registered |
| `fina_revenue_yoy_growth` | growth quality | 100.00% | 100 | pre-registered |
| `fina_profit_growth_quality_spread` | growth quality | 100.00% | 100 | pre-registered |
| `fina_cash_earnings_quality_ratio` | cash-profit quality | 100.00% | 100 | pre-registered |
| `fina_profitability_quality_blend` | composite quality | 97.07% | 98 | pre-registered |
| `fina_growth_quality_blend` | composite quality | 100.00% | 100 | pre-registered |
| `fina_roe_persistence_4q` | profitability stability | 92.17% | 100 | pre-registered |
| `fina_roa_persistence_4q` | profitability stability | 91.20% | 98 | pre-registered |
| `fina_net_margin_improvement_yoy` | margin change | 90.73% | 100 | pre-registered |
| `fina_ocfps_improvement_yoy` | cash-profit quality | 90.76% | 100 | pre-registered |

## Research Decision

Round96 is accepted as candidate-preregistration progress.

Current factor status:

- Promotable factors: 0
- Paper-ready factors: 0
- Manual/live usable factors: 0
- New Round96 pre-registered candidates: 14
- New Round96 candidates with usable coverage for next smoke: 14

These candidates are now allowed to enter a controlled factor-matrix and label-alignment smoke. They are not allowed to enter promotion review, live use, or paper-ready status.

## Next Direction

Round97 should build factor matrices from these 14 pre-registered definitions and audit label alignment before IC or portfolio evaluation:

```text
round97_profitability_quality_factor_matrix_smoke_and_label_alignment
```

Required gates:

- factor signal date must use `ann_date`;
- future returns must start after signal availability;
- no negative-shift label leakage in factor construction;
- candidate matrix coverage must match preregistration coverage;
- no promotion from single-shard matrix smoke.
