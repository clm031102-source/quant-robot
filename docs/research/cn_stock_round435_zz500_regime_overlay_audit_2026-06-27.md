# CN Stock Round435 ZZ500 Regime Overlay Audit

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-paper only. No broker, account, order, or live-trading access. The 2026 final holdout remains sealed.

## Purpose

Round435 tested whether decision-date market state improves the delayed-exit handoff pack. The overlay uses only lagged `CN_ETF_XSHG_510500` data from the previous trading day, so no same-day or future market information is used.

Fixed states tested:

- 60-day ETF momentum negative;
- 120-day ETF momentum negative;
- 60-day drawdown below -10%;
- 60-day drawdown below -15%;
- momentum/drawdown composite states.

Exposure multipliers tested per state: 0.75x, 0.50x, and 0.00x.

## Output

`data/reports/round435_24h_profit_sprint_zz500_regime_overlay_audit_20260627`

## Result

No regime overlay survived the first gate. There was no variant with both non-negative annualized-return delta and positive overlap-Sharpe delta.

| Candidate | Baseline Ann. | Baseline Overlap | Baseline DD | Best Triage Variant | Variant Ann. | Variant Overlap | Variant DD |
|---|---:|---:|---:|---|---:|---:|---:|
| 10 bps | 6.663% | 0.496 | -26.21% | `mom120_or_dd10_x0p75` | 5.888% | 0.491 | -24.46% |
| 20 bps | 6.060% | 0.456 | -28.07% | `mom120_or_dd10_x0p75` | 5.366% | 0.452 | -26.07% |
| 30 bps | 5.415% | 0.416 | -29.66% | `mom120_or_dd10_x0p75` | 4.803% | 0.414 | -27.43% |

The best-looking state rule reduced drawdown by about 1.75 to 2.23 percentage points, but it also reduced annualized return by about 0.61 to 0.78 percentage points and did not improve overlap Sharpe.

## Diagnosis

The weak-market states are not reliably bad for this signal. In several fixed states, average event return was equal to or better than the outside-state return:

- 10 bps `mom60_neg`: in-state mean return 0.1255%, outside 0.0908%;
- 20 bps `dd60_lt_15`: in-state mean return 0.1476%, outside 0.0905%;
- 30 bps `mom60_neg`: in-state mean return 0.1074%, outside 0.0707%.

This makes intuitive sense for a delayed-exit Dragon/Alpha101 candidate: it may earn part of its edge during stressed or rebound-prone market states. A broad market risk-off overlay cuts both risk and signal.

## Decision

Reject ZZ500 momentum/drawdown regime overlays for the current delayed-exit candidate.

Do not tune market-regime lookbacks or thresholds around this result. If market-state logic returns later, it should be a portfolio-level risk-budget decision for simulation, not a new alpha claim or an optimized filter.
