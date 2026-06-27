# CN Stock Round454 Source Efficiency And Public Projection Redundancy Audit

Date: 2026-06-27

Machine: office_desktop

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: make a fast source-efficiency decision before any new factor generation in the 24h profit-factor sprint.

## Executive Decision

Round454 produces 0 new factors and 0 usable alpha leads.

The correct action is to stop spending the 24h sprint on slow source accumulation or highly correlated public-factor projection variants. The next work should use already cached PIT sources with independent economic rationale, or harden the current simulation handoff candidates for paper simulation.

## Analyst Report Revision Source

Round453 pre-registered analyst report revision factors, but the source smoke hit the Tushare `report_rc` provider limit:

- fetched windows: 0
- failed windows: 1
- rows: 0
- assets: 0
- provider limit: 2 requests per day

Decision: analyst report revision stays hibernated during the 24h sprint unless a local PIT cache appears.

## Financial Reporting Timeliness Source

The existing financial reporting timeliness cache remains far below the candidate-generation gate:

- required unique symbol gate: 1000
- latest aggregate unique symbols: 394
- row count: 84,499
- source count: 112
- source-ready count: 0

Round302 already showed the cost of continuing this path:

- 609 endpoint requests for only 6 net-new symbols
- coverage moved from 388 to 394
- the source still stayed far below the 1000-symbol gate

The overlap previews also show diminishing practical efficiency:

- shard19 offset0 limit6: 4 net-new, 2 existing
- shard19 offset6 limit6: 4 net-new, 2 existing
- shard19 offset12 limit6: 6 net-new, already backfilled in Round302

Decision: do not continue financial-reporting-timeliness backfill inside this 24h sprint unless there is a separate coverage plan that can reach the source gate quickly. No factor matrix, portfolio grid, or promotion claim is allowed from the partial cache.

## Public Projection Redundancy

Round405 public-factor projection produced some visually attractive variants, but the unadvanced Alpha101 projections are not independent from the active Dragon-Hot and Alpha101 lanes:

- `alpha_volume_div_top_tilt_round405` correlation to `alpha_open_tilt_round405`: 0.9976
- `alpha_volume_div_top_tilt_round405` correlation to `dragon_base_round405`: 0.9991
- `alpha_gap_fade_top_tilt_round405` correlation to `dragon_base_round405`: 0.9991
- correlations to the Round406 Alpha101 open-close lane were about 0.979 to 0.980

Decision: do not expand adjacent public Alpha101 projection variants. They are mostly the same event-return stream dressed in different formulas, so the risk is false discovery and parameter hopping rather than independent alpha.

## Round454 Output

- new independent alpha factors: 0
- usable research leads: 0
- useful process improvements: 3

The useful improvements are:

- analyst report revision re-entry requires local PIT cache or a higher request budget;
- financial reporting timeliness re-entry requires a credible coverage plan, not slow endpoint accumulation;
- public Alpha101 projection re-entry requires low return-stream correlation and a new economic mechanism.

## Next Direction

Round455 should test whether current simulation-shortlist candidates can be combined into a genuinely better portfolio. If the return streams are too correlated or do not beat the best component, stop blend search and run the required three-round audit for Round453-455 before the next mining batch.
