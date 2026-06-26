# CN Stock External Feed Ten-Round Package - Rounds173-182

Date: 2026-06-23

Scope: Ten controlled monthly external-feed backfill shards for CN stock factor mining.

## Rounds Covered

| Round | Shard | Main result |
| --- | --- | --- |
| 173 | 2025-12 | First monthly shard; all external-feed seeds still short-history. |
| 174 | 2025-11 | Margin seeds became history-ready. |
| 175 | 2025-10 | Three seeds remained history-ready. |
| 176 | 2025-09 | SHIBOR seed became history-ready. |
| 177 | 2025-08 | Four seeds remained matrix-ready. |
| 178 | 2025-07 | Four seeds remained matrix-ready; HK hold still sparse. |
| 179 | 2025-06 | HK hold primary coverage improved to 3 observation dates. |
| 180 | 2025-05 | Formal canonical HK hold output empty for this shard; four seeds still ready. |
| 181 | 2025-04 | Formal canonical HK hold output empty for this shard; four seeds still ready. |
| 182 | 2025-03 | HK hold primary coverage improved to 4 observation dates; four seeds still ready. |

## Current Cumulative State

Latest join smoke:

- `data/reports/round182_external_feed_ten_month_join_smoke_20260623/external_feed_factor_matrix_join_smoke.json`

Summary:

- Seed count: 6
- Pass: 4
- Insufficient history: 2
- Fail: 0
- Warn: 0
- Joined rows: 2448110
- `available_date` violations: 0
- Raw same-day/future-date violations: 0

Matrix-ready seeds:

| Seed | Observation dates | Joined rows | Unique symbols |
| --- | ---: | ---: | ---: |
| `index_location_value_liquidity_regime_20` | 207 | 207 | n/a |
| `margin_balance_crowding_reversal_20` | 207 | 889830 | 4636 |
| `margin_financing_acceleration_exhaustion_20` | 207 | 889830 | 4636 |
| `shibor_liquidity_tightening_regime_20` | 205 | 205 | n/a |

Blocked seeds:

- `northbound_hold_ratio_accumulation_20`: only 4 primary HK hold observation dates.
- `northbound_hold_accumulation_flow_regime_20`: secondary `north_money` has 198 observation dates, but primary HK hold has only 4.

## Audit

The ten-round objective improved data readiness, not profitability:

- No factor IC, RankIC, quantile return, long-short return, Sharpe, win-rate, drawdown, or cost/capacity walk-forward was claimed from these shards.
- Join smoke remains a schema, coverage, and point-in-time alignment check only.
- The strict blockers are still correct: no portfolio grid, no promotion, and no northbound-hold daily ranking until primary feed frequency is repaired or explicitly redesigned.

## GitHub Sync Status

This is the lightweight ten-round package required by the continuing mining protocol.

GitHub push is not executed here because the current startup gate has `pushes_allowed=false` for this task context. Data outputs under `data/raw`, `data/processed`, `data/reports`, logs, and credentials remain excluded from Git.

Next safe action:

- Continue Round183 with the `2025-02` shard.
- After Round183, run the Round181-183 three-round review before additional mining or external-feed portfolio work.
