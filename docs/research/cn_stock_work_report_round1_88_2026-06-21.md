# CN Stock Factor Mining Work Report Rounds 1-88 - 2026-06-21

## Executive Summary

Current context:

- Machine: `office_desktop`
- Task: `factor_validation`
- Branch: `codex/factor-validation-cn-stock-long-cycle-20260618`
- Mandate: CN A-share stock cross-sectional alpha research, not ETF rotation
- Safety: research-to-review only; no broker, account, order, or live-trading actions

Headline status through Round88:

- Promotable profitable factors: 0
- Paper-ready factors: 0
- Manual/live usable factors: 0
- Current research leads: 0 active promotion leads
- Current next direction: `round89_tushare_financial_ingestion_design_and_smoke`

The project has found multiple statistically interesting signals, but none has survived the full promotion stack: long-cycle replay, walk-forward validation, costs, capacity, calendar holding realism, overlap-aware statistics, drawdown, benchmark-relative checks, and multiple-testing discipline.

## Rounds 87-88 Completed In This Work Session

### Round87 - Public QVM Bottom-Exclusion Walk-Forward

Round87 froze the two Round86 public QVM leads and tested them as bottom-tail exclusion filters:

- `public_qvm_value_reversal_quality_20`
- `public_qvm_lowbeta_value_momentum_20`

Settings:

- Rolling train days: 756
- Rolling test days: 252
- Folds: 7
- Bottom exclusion quantile: 20%
- Holding period: 20 bars
- Rebalance interval: 10 bars
- Cost: 10 bps
- Market impact: 20 bps
- Max participation: 1% ADV
- Min entry amount: 10,000,000
- Portfolio value: 1,000,000
- Target gross exposure: 0.6

Result:

| Factor | Accepted Folds | Mean Test Total | Mean Test Relative | Mean Test Overlap Sharpe | Worst Test DD | Mean Test Win Rate | Capacity-Limited | Decision |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| `public_qvm_value_reversal_quality_20` | 0/7 | +0.50% | +1.07% | -0.0734 | -18.67% | 46.44% | 0 | rejected |
| `public_qvm_lowbeta_value_momentum_20` | 0/7 | +0.13% | +0.69% | -0.0807 | -18.96% | 46.55% | 0 | rejected |

Interpretation:

- QVM had weak loser-avoidance information.
- It stayed capacity-clean.
- It did not create a robust costed risk-filter portfolio.
- Accepted folds were 0/7 for both candidates, so QVM was hibernated as a promotion path.

### Round88 - Tushare Financial Profitability PIT Readiness

Round88 audited whether local Tushare data can support true profitability and quality factors.

Result:

| Check | Result |
|---|---:|
| Files scanned | 6,939 |
| Financial-like datasets found | 0 |
| PIT-ready financial datasets found | 0 |
| Readiness pass | false |
| Blocker | `missing_financial_statement_or_indicator_dataset` |

Decision:

- No profitability factors were pre-registered.
- Daily-basic valuation and liquidity data must not be relabeled as profitability.
- The next step must be financial statement / indicator ingestion with PIT publication-date discipline.

## Bright Data Found Across Prior Rounds

These are the strongest pieces of evidence found so far, with their final status.

| Area | Bright Data | Why It Did Not Promote |
|---|---|---|
| Technical baselines | RSI/Bollinger RankIC around 0.047-0.049 | drawdown, tail, and capacity weakness |
| Data repair | false +91.71x return collapsed to +2.36x after adjusted-ratio repair | fake alpha correctly killed |
| Public price-volume formulas | `formula_pv_corr_reversal_20` RankIC about 0.076, t=10.88 | portfolio translation failed |
| Industry-neutral public formulas | neutral RankIC about 0.088-0.091, t near 49 | strong IC but weak long-only portfolio |
| Bottom-exclusion overlays | overlay t up to 8.46, positive rate about 70% | costed portfolios failed Sharpe/drawdown gates |
| Daily-basic residuals | neutral RankIC 0.042-0.056 | long-only conversion failed |
| Benchmark beta diagnostics | residual alpha t=4.39-5.42 | beta dominance remained too high |
| RSRS public indicator | `rsrs_reversal_18_60` total +72.07%, t=4.77 | walk-forward accepted folds 0/7 |
| SuperTrend public indicator | anti-SuperTrend neutral RankIC 0.0888, t=46.29 | walk-forward accepted folds 0/7 |
| Daily-basic low-turnover raw | `turnover_rate_low` +5127.61%, Sharpe 1.983; `turnover_rate_f_low` +5318.72%, Sharpe 1.872 | contaminated by capacity/calendar tradeability problems |
| Capacity-clean low-turnover | clean return +177.86% and +130.86% | overlap Sharpe only 0.410/0.294, relative return deeply negative |
| Public QVM direct | best RankIC 0.0724, t=9.43, capacity-limited trades 0 | overlap Sharpe 0.226, max DD -47.71%, relative return -2282.54% |
| Public QVM exclusion | positive mean relative return +1.07% / +0.69%, capacity-limited trades 0 | accepted folds 0/7, mean test overlap Sharpe negative |

## Recent Round Progression

| Round | Direction | Key Result | Decision |
|---:|---|---|---|
| 81 | Public SuperTrend/ATR signal audit | anti-SuperTrend neutral RankIC 0.0888, t=46.29; direct portfolios failed | no promotion; only bottom-exclusion lead |
| 82 | Anti-SuperTrend costed walk-forward exclusion | accepted folds 0/7; mean test overlap Sharpe -0.3693 | SuperTrend hibernated |
| 83 | Tushare daily-basic core alpha factory | `turnover_rate_low` +5127.61%, Sharpe 1.983; `turnover_rate_f_low` +5318.72%, Sharpe 1.872 | bright but contaminated; diagnostics required |
| 84 | Low-turnover capacity/extreme/calendar diagnostic | capacity breaches 1,437/1,641; max calendar holding 787 days | raw low-turnover promotion killed |
| 85 | Capacity-clean low-turnover replay | clean returns fell to +177.86%/+130.86%; overlap Sharpe 0.410/0.294 | low-turnover direct line hibernated |
| 86 | Public QVM capacity-safe replay | best +91.21%, Sharpe 0.419, RankIC 0.0724, but relative return -2282.54% | no promotion; 2 diagnostic leads |
| 87 | QVM bottom-exclusion walk-forward | 0/7 accepted folds for both frozen leads | QVM hibernated |
| 88 | Tushare financial PIT readiness | 6,939 files scanned, 0 financial-like datasets | profitability mining blocked until financial ingest exists |

## Reusable Work Products Built Or Hardened

Code and process now support:

- CN stock startup gate for every factor-mining round.
- Three-round review cadence.
- Ten-round safe-sync cadence.
- Long-cycle 2015-2025 replay discipline.
- Same-parameter full-sample diagnostics.
- Rolling walk-forward train/test validation.
- Cost and market-impact modeling.
- Capacity and signal-date liquidity gates.
- Calendar holding drift detection.
- Overlap-adjusted return statistics.
- Data quality and adjusted-ratio repair audits.
- Industry-neutral IC audits.
- IC-to-portfolio gap audits.
- Benchmark beta exposure diagnostics.
- Bottom-exclusion translation-layer testing.
- Public RSRS and SuperTrend indicator audits.
- Daily-basic alpha factory and QVM composite source.
- Project audit registration for new factor sources.
- Tushare financial PIT readiness audit module and CLI.

## Why The Results Are So Poor

The poor headline is a feature of stricter validation, not only bad luck.

Main causes:

- IC did not reliably convert into a tradable long-only portfolio.
- Raw high-return factors often depended on illiquidity, sparse trading, or calendar-holding artifacts.
- Public technical indicators were more useful as loser-avoidance diagnostics than as buy signals.
- QVM and daily-basic proxies had ranking information but not enough return engine after costs.
- Benchmark-relative checks exposed that many absolute-positive strategies still underperformed broad CN stock exposure.
- The project lacks true Tushare financial statement PIT inputs, so it cannot yet test real profitability-quality factors.
- Many earlier candidate searches were too broad relative to the amount of independent evidence, so multiple-testing discipline correctly forced rejection.

## Current Conclusion

As of Round88, the project has no deployable profitable CN stock factor.

The most valuable outcome is the failure map:

1. Stop rescuing failed families with more parameter tuning.
2. Stop treating daily-basic valuation/liquidity proxies as true profitability.
3. Require PIT financial inputs before mining ROE, ROA, margin, profit-growth, accruals, or cash-flow quality factors.
4. Keep long-cycle, costed, capacity-aware, walk-forward gates as mandatory.

## Next Action

Round89 should build or smoke-test the missing Tushare financial input layer:

`round89_tushare_financial_ingestion_design_and_smoke`

Do not run new profitability factor backtests until the Round88 readiness audit passes on actual financial statement or indicator data.
