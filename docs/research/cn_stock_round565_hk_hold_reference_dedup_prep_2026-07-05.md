# CN Stock Round565 HK-Hold Reference Dedup Prep

Date: 2026-07-05

Branch: `codex/factor-batch-cn-stock-round565-pit-source-plan-20260705`

Scope: prepare reference-overlap evidence for the Round565 HK-hold low-frequency state candidates before any residual IC screen. This uses same-day cross-sectional Spearman correlations between the constructed HK-hold features and price-volume, moneyflow, and style-proxy references. It does not use forward returns, compute IC, run a portfolio, call a provider, promote a factor, or read the 2026 final holdout.

Generated report:

```text
data\reports\round565_hk_hold_reference_dedup_prep_20260705
```

## Inputs

| Group | References |
| --- | --- |
| Price-volume and style proxies | `liquidity_rank`, `log_adv20_amount`, `momentum_20`, `reversal_20`, `volatility_20`, `low_volatility_20` |
| Moneyflow proxies | `net_mf_amount`, `large_net_mf_amount`, `net_mf_amount_20`, `large_net_mf_amount_20` |
| HK-hold features | `hk_hold_sponsorship_state_change_63`, `hk_hold_sponsorship_persistence_126`, `hk_hold_sponsorship_state_liquidity_interaction_63` |

Spearman correlation was computed as Pearson correlation of within-date ranks to avoid adding a new runtime dependency. This is equivalent for the same-day cross-sectional rank-overlap check used here.

## Result

| Metric | Value |
| --- | ---: |
| Joined rows | 1,241,443 |
| Joined signal dates | 364 |
| Joined symbols | 3,568 |
| Available-date violations | 0 |
| Same-day/future raw-date violations | 0 |
| 2025-12-31 raw rows used before 2026 availability | 0 |

Feature-level overlap:

| Feature | Max abs reference | Max abs Spearman | References >= 0.70 any date | References >= 0.50 any date |
| --- | --- | ---: | ---: | ---: |
| `hk_hold_sponsorship_state_change_63` | `volatility_20` | 0.2305 | 0 | 0 |
| `hk_hold_sponsorship_persistence_126` | `liquidity_rank` / `log_adv20_amount` | 0.5662 | 0 | 2 |
| `hk_hold_sponsorship_state_liquidity_interaction_63` | `liquidity_rank` | 0.2760 | 0 | 0 |

The persistence candidate has material but not extreme overlap with liquidity/amount proxies. It must be residualized against liquidity and size-style controls before any residual IC claim. The 63-day state-change and local-liquidity interaction variants show lower reference overlap in this prep pass, but still require the full residual/control gate before any signal claim.

## Decision

Round565 may proceed to a research-only residual IC prescreen only if the prescreen explicitly includes liquidity/amount, price-volume, moneyflow, and style residualization plus multiple-testing accounting. Promotion gates, portfolio grids, final-holdout reads, provider downloads, old northbound accumulation or crowding/reversal reruns, and margin-credit reentry remain blocked.
