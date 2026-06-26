# CN Stock Round251-253 Three-Round Review

- Date: 2026-06-25
- Machine: office_desktop
- Branch: codex/factor-validation-cn-stock-long-cycle-20260618
- Review window: Round251, Round252, Round253
- Decision: rotate away from the tested direct paths; do not run portfolio grids.
- Safety: research-to-review only. No broker connection, no account reads, no order placement, no live trading.

## What Was Tried

Round251 tested A-share event supply pressure:

- `event_share_unlock_pressure_60`
- `event_pledge_ratio_relief_1q`

Round252 replayed the frozen Round127 public-reference multi-family set across the long 2015-2025 sample:

- 20 candidates
- 9 families
- 60 factor-horizon tests
- public technical, Alpha101, qlib-style, smart-money, moneyflow, and composite candidates

Round253 implemented and tested a fresh non-price-volume family:

- `aq_industry_relative_profitability_surprise`
- `aq_industry_relative_asset_disciplined_surprise`
- `aq_industry_relative_cash_conversion_surprise`

## Results

| Round | Direction | Tests | Research leads | Promotion | Main reason rejected |
|---:|---|---:|---:|---:|---|
| 251 | Share unlock / pledge supply events | 4 | 0 | 0 | share-unlock year coverage too sparse; pledge sign and neutral gates failed |
| 252 | Public-reference multi-family full replay | 60 | 0 | 0 | IC existed but quantile shape, direction, or monotonicity failed |
| 253 | Industry-relative statement surprise | 6 | 0 | 0 | underpowered 130-symbol sample; zero FDR and zero neutral-gate passes |

Total across the review window:

- Candidates tested: 25.
- Factor-horizon tests: 70.
- Research leads: 0.
- Promotable factors: 0.
- Portfolio grids allowed: 0.

## Most Important Evidence

Round251:

- `event_share_unlock_pressure_60` at 20 days had IC 0.1443, ICIR 0.666, and Q5-Q1 0.0721, but the evidence appeared in only 3 years.
- `event_pledge_ratio_relief_1q` had broad coverage but wrong sign and size-neutral failure.

Round252:

- `alpha101_rank_pv_reversal_liquid_20` had strong long-cycle IC, for example 20-day IC 0.0468 and t-stat 24.61, but Q5-Q1 was -0.0313 and monotonicity was weak.
- `main_force_divergence_reversal_5_20` had positive IC every year at 5 days, but ICIR was only 0.239 and monotonicity was negative.
- Donchian and RSRS diagnostics were strongly negative across all years, but sign flipping is blocked without fresh preregistration.

Round253:

- Current PIT statement coverage is too small for this refined industry-relative idea: 1,910 factor rows and only 8 IC observations per test.
- Best-looking industry-neutral row still failed raw IC, FDR, size-neutral, liquidity-neutral, quantile spread, and promotion gates.

## Audit Conclusion

The work did not find a usable profitability factor. It did, however, materially improve the process:

- The project stopped treating strong IC as enough.
- The project stopped short-sample event clusters before portfolio grids.
- The project implemented a new non-price-volume industry-relative surprise mode instead of continuing moneyflow or public technical sweeps.
- The project exposed that financial-statement surprise mining needs broader PIT coverage or a different event feed before further formula mining is efficient.

## Decision

Do not continue any of these exact paths as portfolio grids:

- direct share-unlock stock ranking after sparse year coverage,
- pledge relief positive ranking after sign and neutral failure,
- direct public-reference Alpha101/moneyflow/technical rows after IC-to-portfolio shape failure,
- 130-symbol statement surprise variants after underpowered zero-lead results.

Round254 should rotate to a higher-coverage non-price-volume source. Preferred path: true expectation or event revision data with PIT available dates, such as forecast or earnings-preannouncement surprise. If such data is unavailable locally, run a coverage/readiness audit before mining, not another formula search.
