# CN Stock Round565 HK-Hold Residual IC Prescreen

Date: 2026-07-05

Branch: `codex/factor-batch-cn-stock-round565-pit-source-plan-20260705`

Scope: run a research-only residual IC prescreen for the three Round565 HK-hold low-frequency state candidates after available-date join-smoke, construction smoke, and reference-dedup preparation. This uses 20-day forward returns with execution lag 1, same-day cross-sectional rank residualization, and multiple-testing accounting across the three preregistered candidates.

This is not portfolio evidence. No portfolio grid, promotion gate, provider download, broker/account access, order placement, live trading, or 2026 final-holdout read was run.

Generated report:

```text
data\reports\round565_hk_hold_residual_ic_prescreen_20260705
```

## Data Window

| Metric | Value |
| --- | ---: |
| Signal window | 2024-07-03 to 2025-12-02 |
| Horizon | 20 |
| Execution lag | 1 |
| Joined rows with labels | 1,166,584 |
| Signal dates | 343 |
| Symbols | 3,561 |
| Max entry date | 2025-12-03 |
| Max exit date | 2025-12-31 |
| Max raw HK-hold date used | 2025-09-30 |
| Max available date used | 2025-10-09 |
| PIT violations | 0 |
| Exit dates after 2025-12-31 | 0 |
| 2025-12-31 raw rows used before 2026 availability | 0 |

Controls used for residualization:

```text
liquidity_rank, log_adv20_amount, momentum_20, volatility_20,
net_mf_amount, large_net_mf_amount, net_mf_amount_20, large_net_mf_amount_20
```

Thresholds:

| Threshold | Value |
| --- | ---: |
| Minimum cross-section | 100 |
| Minimum IC observations | 20 |
| Minimum residual mean IC | 0.0200 |
| Minimum residual ICIR | 0.300 |
| Minimum residual t-stat | 2.0 |
| Minimum positive residual IC rate | 55% |
| Multiple-testing alpha | 0.05 |

## Result

| Factor | Raw mean IC | Residual mean IC | Residual ICIR | t-stat | Bonferroni p | FDR q | Positive IC rate | Status |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | --- |
| `hk_hold_sponsorship_state_change_63` | -0.0012 | 0.0052 | 0.132 | 2.21 | 0.0822 | 0.0274 | 52.3% | rejected |
| `hk_hold_sponsorship_persistence_126` | -0.0133 | 0.0099 | 0.136 | 2.27 | 0.0697 | 0.0274 | 52.9% | rejected |
| `hk_hold_sponsorship_state_liquidity_interaction_63` | -0.0001 | 0.0053 | 0.137 | 2.29 | 0.0665 | 0.0274 | 53.8% | rejected |

All three candidates are rejected as research leads. The same rejection pattern applies to each:

- residual mean IC below 0.0200;
- residual ICIR below 0.300;
- positive residual IC rate below 55%;
- Bonferroni-adjusted IC significance does not pass 0.05.

The FDR q-values are nominally below 0.05, but the project gate requires stricter multiple-testing discipline and the effect sizes are too small. Treat this as a full rejection, not as a watchlist promotion.

## Decision

Do not promote, tune, portfolio-test, or read the 2026 final holdout for the Round565 HK-hold low-frequency state candidates. The most reasonable next step is a short closeout/rejection package, then rotate away from HK-hold sponsorship unless a genuinely new mechanism is preregistered with different source information and controls.
