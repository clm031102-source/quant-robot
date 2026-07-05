# CN Stock Round506 Analyst Report Revision Quota-Aware Review

Date: 2026-07-05

Machine: office_desktop

Branch: `codex/factor-batch-cn-stock-profit-mining-20260704`

Scope: continuous-work loop round 3 after the Round504 review-agent baseline. This round did not call Tushare or create new generated data. It reviewed the local Round504/Round505 analyst-report-revision evidence and chose the next safest action under the known `report_rc` quota risk.

## Round Objective

Round505 already made the second successful `report_rc` monthly request on 2026-07-05 after Round504 had fetched February 2024. Historical Round467 evidence showed a `2_per_day` provider limit for this endpoint. The selected objective for Round506 was therefore:

- Do not make a same-day third `report_rc` request.
- Compare Round504 and Round505 local prescreen evidence.
- Decide whether the family merits one more quota-aware monthly cache or should rotate.
- Keep final holdout, portfolio grids, promotion gates, and formula tuning blocked.

No new review agents were created in this round because the continuous-work instruction asks for the two-agent review every ten rounds; this is round 3.

## Startup Evidence

Fresh 2026-07-05 checks:

- Branch: `codex/factor-batch-cn-stock-profit-mining-20260704`.
- Upstream sync: `0 ahead / 0 behind`.
- Quant PM startup gate: `status=ready`, no blockers.
- Primary market: `CN_ETF`.
- CN stock factor-mining startup gate: `status=cleared`, no blockers.
- CN stock data manifest: no blockers, `status=review_required`.

Data manifest warnings retained:

- `extreme_return_rows_present`
- `moneyflow_symbol_coverage_below_bars`

## Local Evidence Compared

| Evidence pack | Report rows | Report assets | Factor rows | Aligned rows | Multiple-testing leads | Neutral-gate passes | Research leads | Promotion allowed |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Round504 January-February | 3,498 | 1,317 | 6,882 | 13,764 | 5 | 4 | 0 | 0 |
| Round505 January-March | 5,132 | 1,511 | 9,966 | 19,932 | 0 | 2 | 0 | 0 |

Round504 top diagnostics:

| Candidate | Horizon | Mean IC | ICIR | FDR significant | Research lead | Main blocker |
| --- | ---: | ---: | ---: | --- | --- | --- |
| `analyst_np_revision_90` | 5 | 0.10024513625752637 | 1.0607971970865206 | true | false | `ic_year_coverage_below_gate` |
| `analyst_eps_revision_90` | 5 | 0.0965548271209604 | 1.1603474324497258 | true | false | `ic_year_coverage_below_gate` |
| `analyst_eps_revision_90` | 20 | 0.08937436298092054 | 0.6501332850738102 | true | false | `ic_year_coverage_below_gate` |
| `analyst_np_revision_90` | 20 | 0.08914440572692325 | 0.6358836909723388 | true | false | `ic_year_coverage_below_gate` |

Round505 top diagnostics after adding March:

| Candidate | Horizon | Mean IC | ICIR | FDR significant | Research lead | Main blocker |
| --- | ---: | ---: | ---: | --- | --- | --- |
| `analyst_np_revision_90` | 20 | 0.07710561091491691 | 0.5640800340719271 | false | false | `not_fdr_significant_after_multiple_testing` |
| `analyst_eps_revision_90` | 20 | 0.07674041200653667 | 0.5697655240917351 | false | false | `not_fdr_significant_after_multiple_testing` |
| `analyst_np_revision_90` | 5 | 0.07007631336183154 | 0.4979692684743769 | false | false | `not_fdr_significant_after_multiple_testing` |
| `analyst_eps_revision_90` | 5 | 0.06588572318679375 | 0.5041600464441606 | false | false | `not_fdr_significant_after_multiple_testing` |

## Interpretation

Adding March increased the evidence base, but the signal weakened:

- Multiple-testing leads fell from 5 to 0.
- Neutral-gate passes fell from 4 to 2.
- The best mean IC fell from about 0.100 to about 0.077.
- Research lead count stayed 0.
- Promotion-allowed candidates stayed 0.

This is not a reason to tune formulas. It is evidence that the analyst-report-revision family is still only a source-smoke candidate, and one more month should be treated as a final quota-aware check rather than a path to promotion.

## Decision

Do not run the April 2024 `report_rc` cache on 2026-07-05 because the day already contains two successful monthly requests and Round467 documented a `2_per_day` provider limit.

Allowed next action after provider quota resets:

- Cache April 2024 once.
- Rerun the same frozen January-April prescreen.
- Stop immediately if the provider returns quota or rate-limit errors.
- If January-April still has zero research leads or zero multiple-testing leads, run a three-round family review and rotate to a new PIT source candidate plan.

Blocked actions:

- No analyst formula tuning.
- No q20/range/ps threshold tuning.
- No portfolio grid.
- No promotion gate.
- No 2026 final-holdout read.

## Safety Boundary

- No broker connection.
- No live account reads.
- No order placement.
- No automatic live trading.
- Do not commit `data/raw/`, `data/processed/`, `data/reports/`, Parquet/CSV outputs, logs, tokens, broker credentials, account data, or order data.
