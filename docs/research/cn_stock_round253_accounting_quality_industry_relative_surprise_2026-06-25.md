# CN Stock Round253 Accounting Quality Industry-Relative Surprise

- Date: 2026-06-25
- Machine: office_desktop
- Branch: codex/factor-validation-cn-stock-long-cycle-20260618
- Scope: CN A-share stock factor mining
- Safety: research-to-review only. No broker connection, no account reads, no order placement, no live trading.

## Purpose

Round252 rejected direct public-reference and IC-only price-volume/moneyflow paths. Round253 therefore used the new allowed direction:

`round253_rotate_to_non_price_volume_expectation_revision_or_industry_relative_surprise`

The fresh hypothesis was not another public technical rule and not a rerun of the old raw accounting-quality formulas. It tested whether PIT financial statement improvements are useful only when they are surprising relative to same-industry peers reporting in the same signal-date cluster.

## Implemented Changes

- Added `industry_relative_surprise` mode to `scripts/run_accounting_quality_statement_residual_ic_shape_prescreen.py`.
- Added three new preregistered candidate names:
  - `aq_industry_relative_profitability_surprise`
  - `aq_industry_relative_asset_disciplined_surprise`
  - `aq_industry_relative_cash_conversion_surprise`
- Enforced same-signal-date, same-industry peer normalization.
- Required at least two same-industry announcers on the signal date before an industry-relative value is emitted.
- Kept PIT timing: `signal_date` is strictly after `ann_date`.
- Kept promotion and portfolio grids blocked at this prescreen stage.

## Command

```powershell
$roots = Get-ChildItem data\processed -Directory | Where-Object { $_.Name -match '^round(236|237|238|241|242|243)_financial_statement' } | Sort-Object Name
$argsList = @(
  'scripts\run_accounting_quality_statement_residual_ic_shape_prescreen.py',
  '--output-dir', 'data\reports\round253_accounting_quality_industry_relative_surprise_130_symbol_20260625',
  '--factor-mode', 'industry_relative_surprise',
  '--analysis-start-date', '2015-01-01',
  '--analysis-end-date', '2025-12-31',
  '--horizon', '5',
  '--horizon', '20',
  '--execution-lag', '1',
  '--min-cross-section', '30',
  '--min-ic-observations', '8',
  '--min-neutral-rank-ic', '0.01',
  '--min-neutral-ic-t-stat', '2.0',
  '--min-neutral-retention', '0.35',
  '--allow-not-ready'
)
foreach ($root in $roots) { $argsList += @('--statement-root', $root.FullName) }
& .venv\Scripts\python.exe @argsList
```

## Results

| Metric | Value |
|---|---:|
| Statement-derived source factor rows before context | 45,644 |
| Industry-relative factor rows | 1,910 |
| Label rows | 661,614 |
| Aligned rows | 3,820 |
| Candidates | 3 |
| Tests | 6 |
| IC observations per test | 8 |
| FDR-significant tests | 0 |
| Neutral-gate pass tests | 0 |
| Research leads | 0 |
| Promotion allowed | 0 |

Top rows:

| Factor | H | IC | ICIR | t | IC>0 | Q5-Q1 | IndNeuIC | SizeNeuIC | LiqNeuIC | Lead |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `aq_industry_relative_asset_disciplined_surprise` | 20 | -0.0478 | -0.470 | -1.33 | 25.0% | -0.0061 | -0.1622 | -0.0411 | -0.0395 | no |
| `aq_industry_relative_cash_conversion_surprise` | 5 | -0.0390 | -0.790 | -2.23 | 12.5% | -0.0056 | -0.1376 | -0.0411 | -0.0449 | no |
| `aq_industry_relative_asset_disciplined_surprise` | 5 | -0.0313 | -0.287 | -0.81 | 37.5% | -0.0019 | 0.2418 | -0.0127 | -0.0247 | no |
| `aq_industry_relative_profitability_surprise` | 5 | -0.0030 | -0.040 | -0.11 | 62.5% | -0.0012 | -0.0496 | 0.0045 | 0.0002 | no |

## Interpretation

Round253 is rejected. The fresh construction did what it was supposed to do mechanically, but the current 130-symbol PIT financial statement sample is underpowered after same-date, same-industry filtering.

The failure is not a portfolio issue and not a drawdown-tolerance issue. It fails before portfolio construction:

- Only 8 IC observations per factor-horizon test.
- Zero FDR-significant tests.
- Zero neutral-gate pass tests.
- Most raw IC and quantile spreads are negative.
- Size-neutral and liquidity-neutral IC are near zero or negative.

The one superficially interesting row is `aq_industry_relative_asset_disciplined_surprise` at 5 days with industry-neutral IC 0.2418, but it still fails raw IC, FDR, size-neutral, liquidity-neutral, quantile spread, and t-stat gates. It is not a research lead.

## Decision

- Promotable factors from Round253: 0.
- Research leads from Round253: 0.
- Portfolio backtest allowed: 0.
- This exact 130-symbol industry-relative statement-surprise sample should not be promoted or grid-searched.
- Do not flip signs after seeing negative IC. Any inverse idea needs fresh preregistration and broader data coverage.

## Next Direction

Round254 should not spend more budget on this exact small-sample financial-statement surprise grid.

Allowed next work:

- Prefer a true expectation event feed if available, such as forecast or earnings-preannouncement surprise, with PIT available dates and enough cross-sectional coverage.
- If staying with financial statements, expand coverage first; do not mine more subformulas on 130 symbols with 8 IC observations per test.
- Rotate to a different non-price-volume event or external-revision family if broad PIT coverage already exists locally.
