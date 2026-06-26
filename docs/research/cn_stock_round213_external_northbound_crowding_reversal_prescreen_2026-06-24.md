# CN Stock Round213 External Northbound Crowding Reversal Prescreen

- Date: 2026-06-24
- Machine/task: office_desktop / factor_validation
- Branch: codex/factor-validation-cn-stock-long-cycle-20260618
- Scope: CN A-share stock cross-sectional factor mining, not ETF rotation
- Stage: preregistered IC/quantile/turnover prescreen only

## Objective

Round213 tested a new external northbound hypothesis after the daily-basic valuation-reversion repair failed Round212 shape and exposure audits.

This was not a continuation of the rejected Round191 positive northbound accumulation thesis. The plan separately preregistered a negative crowding/reversal mechanism: crowded northbound ownership may represent saturation or buyer exhaustion rather than informed incremental demand.

## Controls

- Candidate plan gate: `data/reports/round213_external_northbound_crowding_reversal_candidate_plan_gate_20260624/`
- Candidate plan status: research-ready
- Candidate blockers: none
- Active candidates: 3
- Portfolio grid allowed: false
- Promotion allowed: false
- Final holdout: excluded; 2026 remains read-once only after later gates clear

## Command

```powershell
python scripts\run_factor_mining_candidate_plan_gate.py --candidate-plan configs\factor_mining_candidate_plan_round213_external_northbound_crowding_reversal_20260624.json --quality-gate data\reports\round206_quality_gate_after_event_control_gate_20260623\factor_mining_quality_gate.json --gate-stage discovery --output-dir data\reports\round213_external_northbound_crowding_reversal_candidate_plan_gate_20260624
```

```powershell
python scripts\run_external_feed_northbound_prescreen.py --seed-config configs\factor_mining_candidate_plan_round213_external_northbound_crowding_reversal_20260624.json --output-dir data\reports\round213_external_northbound_crowding_reversal_prescreen_20260624 --analysis-start-date 2015-01-01 --analysis-end-date 2025-12-31 --horizons 20 --execution-lag 1 --lookback 20 --min-cross-section 30 --min-ic-observations 20 --min-signal-date-amount 10000000
```

## Data Window

- Bars: 10,785,537 rows, 5,707 assets, 2015-01-05 to 2025-12-31
- Northbound factor rows: 3,144,495 rows, 3,116 assets
- Label rows: 10,665,909
- Aligned rows: 2,949,852
- Signal dates: 2024-07-31 to 2025-12-31
- HK hold raw dates: 2024-07-02 to 2025-12-31
- PIT rule: external feeds join by `available_date`; raw feed date must be before signal date

## Results

| Factor | Horizon | IC obs | Mean RankIC | ICIR | t-stat | IC>0 | Q5-Q1 | Monotonicity | Top turnover | FDR | Lead |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|---|
| `northbound_hold_crowding_reversal_20` | 20 | 323 | 0.0098 | 0.171 | 3.07 | 56.7% | -0.8193 | -0.300 | 2.0% | yes | no |
| `northbound_hold_crowding_exhaustion_reversal_20` | 20 | 323 | 0.0092 | 0.174 | 3.13 | 56.7% | -0.7152 | 0.200 | 1.7% | yes | no |
| `northbound_hold_decrowding_resilience_20` | 20 | 323 | 0.0026 | 0.056 | 1.00 | 52.6% | -0.8105 | -0.200 | 1.9% | no | no |

## Interpretation

Round213 produced zero strict research leads and zero promotion candidates.

Two candidates were FDR-significant, but the effect size is too small and the quantile shape is wrong. RankIC around 0.009 is below the project gate, ICIR around 0.17 is weak, and the Q5-Q1 spreads are negative even when mean RankIC is positive. This means the cross-sectional rank has no clean tradable top-minus-bottom shape.

The result is useful because it avoided repeating the old positive northbound line and answered a distinct hypothesis quickly. It is not useful enough to justify neutral-dedup, costed portfolio grids, or TopN parameter expansion.

## Decision

- Research leads: 0
- Promotion candidates: 0
- Portfolio grid permission: 0
- Action: hibernate `external_northbound_crowding_reversal` unless a future plan introduces a genuinely different northbound structure with new data or a stronger pre-test reason.
- Next direction: rotate away from northbound and margin-credit external-feed families.

## Verification

- `python -m unittest tests.unit.test_external_feed_northbound_prescreen`
- `python -m unittest tests.unit.test_factor_mining_candidate_plan_gate tests.unit.test_factor_mining_candidate_plan_gate_cli`
- Candidate plan gate cleared with 3 active candidates and 0 blockers.
