# CN Stock Round529 External Feed Family Review

Date: 2026-07-05

Machine: office_desktop

Branch: `codex/factor-batch-cn-stock-profit-mining-20260704`

Scope: continuous-work loop round 26 after the Round504 review-agent baseline. This round did not call Tushare, did not run analyst-report cache or prescreen, did not run external-feed IC tests, did not run portfolio grids, and did not touch final holdout. It reviewed prior external-feed evidence and converted the Round528 source audit into a clear family boundary.

## Round Objective

Round528 found that local HK-hold coverage had improved, while LPR coverage remained blocked. The Round529 objective was to decide whether that source-quality change is enough to reopen any old external-feed factor family.

The answer is no.

HK-hold coverage improvement is a useful source fact, but it is not a new alpha mechanism. Old northbound and margin-credit families remain hibernated unless a future candidate plan proves a genuinely new, preregistered hypothesis before testing.

No review agents were created in this round because the next required review-agent checkpoint is round 30 after the Round504 baseline, due in Round533.

## Startup Evidence

Fresh 2026-07-05 checks:

- Local time: 2026-07-05 04:43 +08:00.
- Branch: `codex/factor-batch-cn-stock-profit-mining-20260704`.
- Git status before work: clean and synchronized with origin.
- Remote branches: `origin/main` and `origin/codex/factor-batch-cn-stock-profit-mining-20260704`.
- Startup context: clear, branch matched, upstream `0 ahead / 0 behind`.
- Quant PM startup gate: `status=ready`, blockers `[]`.
- Primary market: `CN_ETF`.
- CN stock factor-mining startup gate: `status=cleared`, blockers `[]`.
- CN stock data manifest: blockers `[]`, status `review_required`.

Data manifest warnings retained:

- `extreme_return_rows_present`
- `moneyflow_symbol_coverage_below_bars`

## Required Reading

The family review used these prior records:

- `docs/research/cn_stock_round190_192_three_round_review_2026-06-23.md`
- `docs/research/cn_stock_external_margin_credit_prescreen_round192_2026-06-23.md`
- `docs/research/cn_stock_external_margin_credit_neutral_dedup_round193_2026-06-23.md`
- `docs/research/cn_stock_round213_external_northbound_crowding_reversal_prescreen_2026-06-24.md`
- `docs/research/cn_stock_three_round_review_round213_215_2026-06-24.md`
- `docs/research/cn_stock_round217_219_three_round_review_2026-06-24.md`
- `docs/research/cn_stock_round450_452_three_round_audit_2026-06-27.md`
- `docs/research/cn_stock_round528_external_feed_rotation_source_audit_2026-07-05.md`
- `configs/factor_mining_candidate_plan_round213_external_northbound_crowding_reversal_20260624.json`

## Evidence Summary

| Family or source | Prior result | Round529 decision |
| --- | --- | --- |
| `external_northbound_positive_accumulation` | Round191 found 0 leads. Best direct-rank variants had negative mean IC direction and weak monotonicity. | Keep hibernated. Do not rerun as a direct rank. |
| `external_margin_credit` | Round192 raw IC looked positive, but Round193 style-residual and dedup review collapsed materiality. | Keep hibernated. Raw signal cannot be reused without a new independent mechanism and residual proof. |
| `external_northbound_crowding_reversal` | Round213 found weak IC, wrong or unstable quantile direction, 0 leads, and 0 promotions. | Keep hibernated. Do not revive crowding/reversal under a new label. |
| `external_macro_lpr` | Round528 source audit found LPR 1Y and 5Y non-null rows equal to 0. | Keep blocked until LPR non-missing coverage is repaired. |
| SHIBOR-only macro source | Round528 found complete SHIBOR rows, but macro-rate audit still blocked due to LPR. | Allow only as a possible regime-control review after long-cycle validation, not as a standalone stock rank. |
| HK-hold source quality | Round528 found HK-hold coverage passing with 134,461 rows, 40 observation dates, 3,980 symbols, and 1.0 median gap days. | Accept as source-quality evidence only. It does not reopen old northbound factor tests by itself. |

## Interpretation

Data-quality proof is a necessary condition for reopening a source family, but it is not sufficient. The Round528 HK-hold improvement satisfies only the data-quality side of the Round450-452 warning. It does not supply a new mechanism, a frozen formula direction, residualization plan, or multiple-testing control plan.

Therefore:

- Do not run external-feed IC tests from Round528 source audit alone.
- Do not run external-feed portfolio grids or promotion gates.
- Do not rerun old positive northbound accumulation.
- Do not rerun old northbound crowding/reversal.
- Do not use margin-credit as a continuation path unless a future review explains why Round193 residual collapse no longer applies.
- Do not use LPR-dependent macro factors until LPR coverage clears.

## Future Reopen Gate

A future HK-hold idea can be considered only if it passes a new candidate-plan gate before testing.

Minimum requirements:

- Use a new family identifier that is not `external_northbound`, `external_northbound_regime_interaction`, or `external_northbound_crowding_reversal`.
- State the new behavioral mechanism and why it is not old accumulation or crowding/reversal.
- Freeze factor direction, lookback, lag, winsorization, neutralization, and admissible universe before IC testing.
- Include the Round528 HK-hold source-quality evidence.
- Include a residualization or dedup plan against price-volume, moneyflow, and style references.
- State that LPR-dependent logic is excluded until LPR non-missing coverage is repaired.
- Exclude final holdout.
- Require multiple-testing control before any research-lead language.

If these conditions are not met, the family remains hibernated.

## Decision

Round529 does not reopen external-feed factor mining.

Primary path remains analyst-report revision:

1. Collect required quota-pack evidence from `office_desktop`, `highspec_desktop`, and `laptop`, or wait for a new local quota date.
2. Run exactly one actual-date April analyst-report cache preflight with required-machine constraints.
3. Cache April only if the preflight exits `0`.
4. Run the frozen January-April analyst-report prescreen only after April cache succeeds.

If analyst cache remains blocked and no new quota evidence is available, the next non-provider external-feed work should be source repair or source tooling, not factor testing:

- LPR backfill feasibility and schema repair plan.
- Long-window external-feed join-smoke performance optimization.
- A written SHIBOR regime-control review boundary after long-cycle validation.

## Safety Boundary

- Research-to-paper only.
- No broker connection.
- No live account reads.
- No order placement.
- No automatic live trading.
- Do not touch 2026 final holdout.
- Do not tune analyst formulas to recover March results.
- Do not run external-feed portfolio grids or promotion gates from coverage audit or join smoke.
- Do not commit `data/raw/`, `data/processed/`, `data/reports/`, Parquet/CSV outputs, logs, tokens, broker credentials, account data, or order data.
