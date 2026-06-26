# CN Stock Profitability Quality Controlled IC Screen Round98 - 2026-06-22

## Executive Summary

Round98 tested the 14 pre-registered profitability-quality factors from Round96 on the clean 100-symbol Tushare `fina_indicator` shard built in Round95. The screen used the Round97 point-in-time factor matrix and label-alignment path.

Result: the family produced no usable alpha evidence on this shard.

- Candidates tested: 14
- Horizons: 5d and 20d
- Total factor-horizon tests: 28
- IC observations: 1,204
- Label-aligned rows: 117,394
- Bonferroni significant: 0
- FDR significant: 0
- Research leads after multiple testing: 0
- Promotion allowed: false
- Portfolio backtest allowed: false

## Best Raw Results

These are the strongest raw IC rows by absolute t-statistic. None pass multiple testing.

| Factor | Horizon | IC Mean | ICIR | t-stat | p-value | Positive IC Rate | Decision |
|---|---:|---:|---:|---:|---:|---:|---|
| `fina_ocfps_improvement_yoy` | 20 | -0.0274 | -0.233 | -1.47 | 0.1413 | 35.0% | rejected |
| `fina_revenue_yoy_growth` | 5 | 0.0197 | 0.190 | 1.26 | 0.2066 | 56.8% | rejected |
| `fina_cash_earnings_quality_ratio` | 20 | -0.0165 | -0.173 | -1.15 | 0.2522 | 45.5% | rejected |
| `fina_gross_margin_level` | 20 | 0.0197 | 0.154 | 1.02 | 0.3067 | 52.3% | rejected |
| `fina_profitability_quality_blend` | 20 | 0.0213 | 0.150 | 0.99 | 0.3200 | 54.5% | rejected |

## Interpretation

The result is a useful negative result. It says the current profitability-quality family should not proceed to portfolio backtesting, parameter expansion, or promotion from this 100-symbol shard.

The best raw IC is small, statistically weak, and unstable in sign. The best p-value is 0.1413, while the Bonferroni threshold across 28 tests is 0.001786. The gap is too large to treat as a near miss.

## Why This Matters

Previous weak work suffered from short-window evidence, same-family lock-in, and premature portfolio translation. Round98 prevents a repeat of that mistake:

- The candidates were pre-registered before testing.
- The screen used announcement-date availability and execution lag.
- Cross-sectional IC required minimum breadth.
- Multiple testing was accounted for explicitly.
- A zero-lead outcome blocks promotion instead of inviting parameter tuning.

## Decision

Do not continue this exact profitability-quality family with more knobs.

Next direction:

```text
round99_profitability_quality_family_rejection_and_next_family_rotation_audit
```

Round99 should close the Round97-99 block by auditing why the clean PIT profitability-quality family failed and deciding whether to rotate to a different family or expand only after a data/universe rationale is documented.
