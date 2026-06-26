# Round96 Profitability Quality Preregistration Plan

## Steps

1. Add failing tests for profitability-quality preregistration:
   - clean PIT financial inputs produce pre-registered candidates;
   - PIT or field coverage failures block preregistration;
   - CLI writes JSON, Markdown, and CSV outputs.
2. Implement a reusable ops module:
   - load processed `fina_indicator_inputs`;
   - audit duplicate keys, missing asset ids, PIT dates, and `ann_date >= end_date`;
   - define candidate specs and economic rationales;
   - compute row, asset, and history coverage per candidate.
3. Add a CLI entrypoint for repeatable runs.
4. Run the CLI on Round95 shard 1 full100 data.
5. Write Round96 research report and Round94-96 three-round review.
6. Update startup gate to Round97 factor-matrix and label-alignment smoke.
7. Run verification commands.

## Stop Conditions

- Stop if duplicate financial keys are above 0.
- Stop if missing asset ids are above 0.
- Stop if any `ann_date` is earlier than `end_date`.
- Stop if fewer than 10 candidates pass coverage on the 100-symbol shard.
- Stop promotion regardless of coverage, because this is still one shard and no returns were tested.
