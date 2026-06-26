# CN Stock Three-Round Review Round213-215

- Date: 2026-06-24
- Machine/task: office_desktop / factor_validation
- Branch: codex/factor-validation-cn-stock-long-cycle-20260618
- Scope: CN A-share stock factor mining and data-readiness workflow, not ETF rotation

## Rounds Reviewed

| Round | Work type | Output | Factor candidates | Research leads | Promotion candidates |
|---:|---|---|---:|---:|---:|
| 213 | External northbound crowding/reversal prescreen | Failed factor family screen | 3 | 0 | 0 |
| 214 | Financial data sampling optimization | Stratified `fina_indicator` shard plan | 0 | 0 | 0 |
| 215 | Real Tushare financial data smoke | Stratified shard1 first10 PIT-ready data | 0 | 0 | 0 |

## Evidence

Round213:

- 3 preregistered northbound crowding/reversal candidates.
- 3,144,495 factor rows and 2,949,852 aligned label rows.
- 2 FDR-significant tests, but weak effect and broken quantile shape:
  - `northbound_hold_crowding_reversal_20`: IC 0.0098, ICIR 0.171, Q5-Q1 -0.8193, monotonicity -0.300.
  - `northbound_hold_crowding_exhaustion_reversal_20`: IC 0.0092, ICIR 0.174, Q5-Q1 -0.7152, monotonicity 0.200.
- Decision: 0 leads; hibernate external northbound crowding/reversal.

Round214:

- Added optional stratified financial shard ordering.
- Old Round93 plan was code-ordered; shard 1 ran from `000001.SZ` to `000516.SZ`.
- New stratified plan uses industry, exchange, and list_year.
- Plan passed with 5,208 non-BJ symbols, 44 quarters, 53 shards, and 229,152 total planned requests.
- Stratified shard 1 covers 100 symbols, 100 industries, 2 exchanges, and 19 listing years.

Round215:

- Ran real Tushare smoke on stratified shard 1 first10.
- 440 requests, 440 processed rows, 0 empty requests, 0 skipped requests.
- Duplicate rows: 0.
- Missing asset_id rows: 0.
- PIT readiness: 452/452 financial-like datasets passed.

## Audit

The work did not produce a deployable or paper-ready alpha. That is the correct conclusion.

It did avoid the previous failure mode of staying inside a dead family. Round213 tested a new northbound hypothesis once, found weak IC plus wrong quantile shape, and stopped. It did not expand TopN, costs, windows, or portfolio grids.

Round214-215 were not factor discovery rounds; they were method repair. This is justified because the most economically meaningful remaining direction is true PIT profitability-quality data, but the prior test used only a code-ordered 100-symbol shard and failed. Before spending more Tushare budget on profitability formulas, the data sample needed to become representative.

## Decision

- Promotable factors from these three rounds: 0.
- Useful factor candidates: 0.
- Useful infrastructure artifacts: 2.
- Useful data-readiness result: 1.
- Direction: rotate away from northbound and external margin-credit; proceed only through stratified PIT financial data if continuing profitability-quality research.

## Next Action

Run one controlled expansion:

1. Backfill stratified shard1 full100 only if the request budget and runtime are acceptable.
2. Run PIT readiness and financial field coverage.
3. Only if coverage passes, rerun profitability-quality preregistration or matrix/IC screening on the stratified sample.
4. If the stratified full100 still produces 0 FDR leads, keep profitability-quality hibernated and rotate to a non-financial family.

No portfolio grid, TopN conversion, or promotion is allowed from Round213-215 evidence.
