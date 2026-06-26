# Round97 Profitability Quality Factor Matrix Smoke Plan

## Steps

1. Add failing tests for factor-matrix and label-alignment smoke.
2. Implement factor value generation for the 14 Round96 pre-registered candidates.
3. Load local CN stock bars for the 100-symbol financial shard.
4. Map financial `ann_date` to next available bar `signal_date`.
5. Generate forward-return labels with execution lag 1.
6. Check label coverage and leakage violations.
7. Run on real Round95 financial data, Round96 preregistration output, and local CN bars.
8. Write Round97 research report and update startup gate.
9. Run verification commands.

## Stop Conditions

- Stop if label coverage is below 80%.
- Stop if any alignment violation exists.
- Stop if bars do not cover all 100 shard assets.
- Stop if factor values do not preserve the Round96 candidate definitions.
- Stop promotion regardless of smoke results.
