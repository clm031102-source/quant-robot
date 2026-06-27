# CN Stock Round397 - Projection Unmatched Contribution Diagnostic

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-review only. No broker, account, order, or live-trading access. 2026 final holdout remains sealed.

## Purpose

Round397 audited the `unmatched_flagged_contribution_above_limit` blocker seen in the PS-on-Dragon selected-entry filter.

The first hypothesis was that unmatched contribution might come from late-2025 entries exiting in sealed 2026 data. That hypothesis was false. The trade source had no exits after 2025-12-31, and the unmatched rows were scattered across normal 2015-2025 dates.

## Code Change

The shared official-template projection now reports:

- `unmatched_nonzero_date_count`;
- `unmatched_zero_date_count`;
- `unmatched_abs_contribution_by_year`.

This flows into `shortlist_public_factor_entry_filter` because that tool uses the same projection helper.

Test-first verification:

- added a failing unit test in `tests/unit/test_shortlist_official_template_cash_filter.py`;
- watched it fail on missing `unmatched_nonzero_date_count`;
- implemented the minimal projection summary fields;
- reran the official-template and public-factor filter tests.

## Diagnostic Result

For `cash_public_ps_top20` in Round396:

| Metric | Value |
|---|---:|
| Unmatched absolute contribution | 0.0120 |
| Nonzero unmatched dates | 8 |
| Zero-contribution unmatched dates | 34 |
| 2016 unmatched abs contribution | 0.0023 |
| 2018 unmatched abs contribution | 0.0084 |
| 2019 unmatched abs contribution | 0.0014 |

The blocker remains valid. It is not a final-holdout issue and should not be waived blindly.

## Decision

Keep PS-on-Dragon lanes observation-only.

Use the improved unmatched diagnostics in all future selected-entry projection reviews. Promotion still requires either:

- template/projection calendar repair; or
- an explicitly documented tolerance policy that is validated across OOS/block/beta checks.
