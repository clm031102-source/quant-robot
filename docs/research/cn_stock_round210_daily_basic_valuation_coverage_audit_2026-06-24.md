# CN Stock Round210 Daily-Basic Valuation Coverage Audit

- Date: 2026-06-24
- Machine: office_desktop
- Branch: codex/factor-validation-cn-stock-long-cycle-20260618
- Scope: CN stock daily-basic valuation factor mining
- Safety: research-to-review only; no broker, no account reads, no orders, no live trading

## Objective

Round210 fixes a workflow problem exposed by Round132: a factor can show strong raw IC but still be unusable if the required daily-basic fields are not consistently available.

This audit asks:

- whether the strong Round132 valuation reversal signal was blocked by one identifiable field;
- whether a public daily-basic replacement field is clean enough to justify a separately preregistered repaired factor;
- whether any valuation line should be stopped before portfolio grids.

## New Project Capability

Added a repeatable daily-basic valuation coverage audit:

- `src/quant_robot/ops/daily_basic_valuation_coverage_audit.py`
- `scripts/run_daily_basic_valuation_coverage_audit.py`
- `tests/unit/test_daily_basic_valuation_coverage_audit.py`
- `tests/unit/test_daily_basic_valuation_coverage_audit_cli.py`

The tool reports factor-level full coverage, field-level non-null coverage, date pass ratios, monthly weak points, replacement candidates, and a strict promotion policy.

Policy: this audit can only permit a repaired factor to be preregistered. It cannot permit portfolio grid search, promotion, or live use.

## Command

```powershell
python scripts\run_daily_basic_valuation_coverage_audit.py --daily-basic-root data\processed\office_desktop_20260617_daily_basic_factor_inputs --output-dir data\reports\round210_daily_basic_valuation_coverage_audit_20260624 --analysis-start-date 2023-07-03 --analysis-end-date 2025-12-31 --min-full-coverage-ratio 0.80 --min-field-non-null-ratio 0.80 --min-date-pass-ratio 0.80
```

## Result

- Data window: 2023-07-03 to 2025-12-31
- Rows: 3,262,000
- Assets: 5,567
- Target factors: 2
- Coverage-pass factors: 0
- Repair-ready factors: 1
- Blocked factors: 1
- Gate status: `mixed_repair_ready_with_blocked_factors`
- Portfolio grid allowed: false
- Promotion allowed: false

## Factor Decisions

| Factor | Raw Round132 h20 IC | Raw ICIR | Required fields | Full coverage | Date pass | Low field | Replacement | Decision |
|---|---:|---:|---|---:|---:|---|---|---|
| `daily_basic_valuation_reversion_quality_60` | 0.0701 | 0.5276 | `pb|ps_ttm|dv_ttm` | 0.6886 | 0.0000 | `dv_ttm` | `dv_ratio` passes | repair-ready for preregistration |
| `daily_basic_valuation_dispersion_compression_60` | 0.0151 | 0.1417 | `pb|pe_ttm|dv_ratio` | 0.7038 | 0.0000 | `pe_ttm` | `pe` fails | blocked |

## Field Coverage Details

- `dv_ttm`: non-null ratio 0.6887, date pass 0.0000, worst month 2024-06 at 0.6200.
- `dv_ratio`: non-null ratio 0.9287, date pass 1.0000, worst month 2023-12 at 0.8818.
- `pe_ttm`: non-null ratio 0.7507, date pass 0.0000, worst month 2025-11 at 0.7177.
- `pe`: non-null ratio 0.7868, date pass 0.3300, worst month 2025-05 at 0.7471.

## Interpretation

The strongest Round132 daily-basic valuation result was not clean enough for direct use, but it was also not a dead end.

The actionable path is narrow:

- do not reuse `daily_basic_valuation_reversion_quality_60` as-is because `dv_ttm` fails coverage;
- do not move to portfolio grids from the old Round132 result;
- preregister a new repaired candidate that replaces `dv_ttm` with `dv_ratio`;
- rerun IC, quintile, turnover, cost/capacity, and later walk-forward validation from scratch;
- block the valuation dispersion compression candidate until PE coverage is backfilled or a different economic hypothesis is preregistered.

## Process Change

Future mining must apply this rule:

```text
Strong raw IC + weak required-field coverage is not a discovery.
It is a repair audit candidate.
Only coverage-clean repaired variants may enter a fresh preregistered screen.
```

## Decision

- Promotable factors: 0
- Paper-ready factors: 0
- Repair-ready research direction: 1
- Blocked valuation direction: 1
- Useful reusable artifact: yes, daily-basic valuation coverage audit and replacement-field gate

Next valid work:

```text
round211_preregister_daily_basic_valuation_reversion_coverage_repaired_candidate
```
