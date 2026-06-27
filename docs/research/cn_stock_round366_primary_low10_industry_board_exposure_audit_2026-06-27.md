# CN Stock Round366 - Primary Low10 Industry / Board Exposure Audit

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-review only. No broker, account, order, or live-trading access.

## Why This Round

Round363-365 made replay and event-schema checks stricter, then rejected broad public-indicator sweeps as a primary source of edge. Round366 audits the current low-turnover repair line for hidden industry or board exposure before doing more mining.

The main question:

`replace_drop_turnover_f_low10` might not be a clean low-turnover alpha. It could be earning from concentrated A-share board or industry exposure, or wasting weight on names that the account cannot buy.

## Output

Signal-date exposure audit:

`data/reports/round366_24h_profit_sprint_primary_low10_industry_board_exposure_audit_20260627`

Exit-date contribution cross-check:

`data/reports/round366_24h_profit_sprint_primary_low10_industry_board_exposure_audit_exitdate_20260627`

Reusable tool added:

- `src/quant_robot/ops/shortlist_exposure_audit.py`
- `scripts/run_shortlist_exposure_audit.py`
- `tests/unit/test_shortlist_exposure_audit.py`

## Signal-Date Findings

Trade source:

`data/reports/round338_24h_profit_sprint_turnover_low_replacement_filters_quarantine_corrected_20260627/replace_drop_turnover_f_low10_trades_with_tradeability.parquet`

| Dimension | Missing Weight | Avg Top Share | P95 Top Share | Avg HHI | Top Abs Return Contribution Share | Gate |
|---|---:|---:|---:|---:|---:|---|
| industry | 13.44% | 16.77% | 36.00% | 0.070 | 6.79% | pass |
| stock_market | 13.40% | 79.33% | 94.00% | 0.686 | 98.13% | blocked |

Industry exposure is not the main problem. The basket is diversified enough across industries, and no single industry explains the return contribution.

The board exposure is the problem:

- `主板`: 79.33% of weight and 98.13% of absolute return contribution;
- `科创板`: 4.85% of weight but 0 entry-cash return contribution;
- `创业板`: 2.42% of weight but 0 entry-cash return contribution;
- `UNKNOWN`: 13.40% of weight, mostly inactive/ST/delisted metadata cases.

## Tradeability Diagnosis

By `stock_market`:

| Board | Weight | Entry Allowed Rate | Entry-Cash Return | Raw Weighted Return |
|---|---:|---:|---:|---:|
| `主板` | 104.915 | 96.25% | 0.9286 | 0.9809 |
| `UNKNOWN` | 17.725 | 5.22% | 0.0196 | 0.1743 |
| `创业板` | 3.195 | 0.00% | 0.0000 | 0.0172 |
| `科创板` | 6.415 | 0.00% | 0.0000 | 0.1077 |

Top blocked reasons confirm the issue:

- `创业板`: almost all rows are `board_permission_blocked`;
- `科创板`: almost all rows are `board_permission_blocked`;
- `UNKNOWN`: mostly `st_flag` and `delisted_or_inactive_flag`.

## Decision

Do not start with industry neutralization. Industry concentration is not the first-order risk.

The better next test is static board-permission pre-ranking:

1. keep the same `replace_drop_turnover_f_low10` idea;
2. exclude board-permission-ineligible names before ranking;
3. refill Top50 with the next eligible low-turnover names;
4. keep next-day entry cash handling for limit/suspension issues to avoid look-ahead.

No candidate is promoted from this round. This is a direction-selection audit.
