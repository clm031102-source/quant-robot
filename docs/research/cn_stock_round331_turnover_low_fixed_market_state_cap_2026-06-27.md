# CN Stock Round331 Fixed Market-State Cap

Date: 2026-06-27

Scope: 24h profit-factor sprint, office desktop, CN stock low-turnover research lead.

Safety boundary: research-to-review only. No broker connection, account reads, orders, or live trading.

## Objective

Round330 showed that realized strategy volatility targeting reacts too late in 2017-2018. Round331 tests a simple ex-ante market-state cap known by decision date.

The 2026 window is intentionally not used.

## Inputs

- Base return: `entry_cash_proxy_return`
- Decision date: `signal_date`
- Market return: clean-universe median daily market return
- Market cap alignment: lagged and forward-filled by decision date
- Date window: 2015-2025 only

Fixed market-state rule:

- lookbacks: 60 and 120 trading days
- stress if market momentum <= 0 or rolling market drawdown <= -10%
- exposure caps: 50% and 25%
- also tested the same cap with `dd15_cut25` strategy drawdown overlay

Output directory:

`data/reports/round331_24h_profit_sprint_turnover_low_fixed_market_state_cap_20260627`

## Full-Sample Diagnostics

| Policy | Total | Annual | Sharpe | Overlap Sharpe | Max DD | Avg Exposure | Capped Decisions |
|---|---:|---:|---:|---:|---:|---:|---:|
| `market_lb60_mom0_dd10_cap25` | +126.45% | +5.06% | 1.147 | 0.548 | -9.65% | 31.57% | 92.84% |
| `market_lb60_mom0_dd10_cap50` | +120.83% | +4.90% | 0.964 | 0.486 | -19.15% | 54.38% | 92.84% |
| `market_lb120_mom0_dd10_cap25` | +77.29% | +3.52% | 0.920 | 0.421 | -11.11% | 27.81% | 97.42% |
| `market_lb120_mom0_dd10_cap50` | +87.67% | +3.88% | 0.828 | 0.412 | -20.02% | 51.87% | 97.42% |
| `entry_cash_no_overlay` | +107.64% | +4.51% | 0.644 | 0.355 | -35.63% | 100.00% | 0.00% |

The drawdown overlay variants were effectively identical to the plain market-state cap in the top rows, because the market cap dominated exposure.

## Cross-Split Robustness

| Policy | Mean OOS Ann | Min OOS Ann | Mean OOS Overlap | Min OOS Overlap | Worst OOS DD | Mean Strict Pass |
|---|---:|---:|---:|---:|---:|---:|
| `entry_cash_no_overlay` | +5.94% | +3.69% | 0.562 | 0.245 | -19.97% | 90.18% |
| `market_lb120_mom0_dd10_cap50` | +2.69% | +1.58% | 0.516 | 0.205 | -10.50% | 90.18% |
| `market_lb60_mom0_dd10_cap50` | +2.78% | +1.65% | 0.515 | 0.201 | -10.50% | 74.32% |
| `market_lb60_mom0_dd10_cap25` | +1.24% | +0.66% | 0.440 | 0.133 | -8.57% | 63.45% |
| `market_lb120_mom0_dd10_cap25` | +1.10% | +0.57% | 0.425 | 0.126 | -5.39% | 79.32% |

## Interpretation

Market-state caps do reduce the exact failure regime:

- 2018 annualized loss improves from about -10.86% to -5.55% at cap50 and -2.81% at cap25.
- 2017-2018 max drawdown improves from about -26.8% to -14.4% at cap50 and -7.5% at cap25.

But the tested rule is too broad:

- 60-day cap triggers on 92.84% of decisions.
- 120-day cap triggers on 97.42% of decisions.
- This behaves like a low-exposure portfolio, not a selective market-regime filter.
- Cross-split OOS return and overlap Sharpe do not beat the no-overlay benchmark.

## Decision

Status:

- Simulation-ready: no
- Paper-ready: no
- Useful finding: market-state risk control is directionally useful, but the rule is over-blocking.

Next action:

Test a stricter, less-always-on ex-ante market stress rule:

- drawdown-only cap;
- momentum-and-drawdown cap;
- fewer fixed candidates;
- reject any rule with excessive capped-decision rate unless it clearly improves OOS return and drawdown together.
