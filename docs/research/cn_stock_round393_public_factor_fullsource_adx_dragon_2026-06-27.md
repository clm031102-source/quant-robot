# CN Stock Round393 - Full-Market Public Factor Source For ADX Dragon-Hot

Date: 2026-06-27

Branch: `codex/factor-validation-cn-stock-24h-profit-sprint-20260627`

Scope: CN stock factor validation, research-to-review only. No broker, account, order, or live-trading access. 2026 final holdout remains unused.

## Purpose

Round391 used a public-factor parquet generated around an older turnover-low subset, creating a coverage blocker. Round393 rebuilt the public indicator source from full CN stock bars, then re-ran the ADX-on-Dragon projection and risk overlays.

## New Tooling

- `src/quant_robot/ops/shortlist_public_factor_source.py`
- `scripts/run_shortlist_public_factor_source.py`
- `tests/unit/test_shortlist_public_factor_source.py`

The tool computes public indicators on the full market cross-section, then clips the output to the selected trade signal-date and asset pairs. This avoids computing ADX ranks on only the already-selected trades.

## Output

- Factor source: `data/reports/round393_24h_profit_sprint_public_factor_source_for_dragon_hot_20260627`
- Projection: `data/reports/round393_24h_profit_sprint_public_factor_on_dragon_hot_projection_20260627`
- Wrapped events: `data/reports/round393_24h_profit_sprint_adx_fullsource_on_dragon_hot_vt6_zz500_projection_20260627`
- Self-risk: `data/reports/round393_24h_profit_sprint_adx_fullsource_self_risk_20260627`
- OOS: `data/reports/round393_24h_profit_sprint_adx_fullsource_self_risk_oos_20260627`
- Block audit: `data/reports/round393_24h_profit_sprint_adx_fullsource_self_risk_block_audit_20260627`
- Beta audit: `data/reports/round393_24h_profit_sprint_adx_fullsource_self_risk_beta_audit_20260627`

## Coverage

Full-market source coverage on 26,450 target pairs:

| Factor | Matched | Missing Share |
|---|---:|---:|
| ADX exhaustion reversal | 17,517 | 33.77% |
| ADX choppiness quality | 17,557 | 33.62% |
| KAMA efficiency decay | 17,395 | 34.23% |
| Anti-SuperTrend | 4,370 | 83.48% |
| Smart-money trend | 4,484 | 83.05% |
| SuperTrend capacity strict | 1,798 | 93.20% |

The old source was not clean, but full-market rebuild did not fully solve coverage. ADX still has a missing-factor blocker and therefore remains an observation lane.

## Projection Result

Official-template projection with the full-market source:

| Candidate | Ann | Total | Overlap Sharpe | Max DD | Missing Share | Blockers |
|---|---:|---:|---:|---:|---:|---|
| Dragon-Hot base | 5.94% | 1.5979 | 0.4541 | -32.87% | n/a | none |
| ADX bottom20 | 6.09% | 1.6581 | 0.5198 | -25.17% | 34.04% | missing coverage |
| Anti-SuperTrend top20 | 6.11% | 1.6692 | 0.4850 | -30.23% | 83.60% | missing coverage |

Anti-SuperTrend is not continued because the apparent improvement is carried by a tiny available subset.

## Wrapped And Risk-Budget Result

| Candidate | Ann | Total | Sharpe | Overlap Sharpe | Max DD | OOS Ann | OOS Overlap | Worst OOS DD |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Dragon-Hot 100 | 6.45% | 1.8120 | 0.987 | 0.5324 | -28.57% | 8.02% | 0.8693 | -23.68% |
| Dragon-Hot roll21 neg half | 6.71% | 1.9310 | 1.173 | 0.6172 | -15.46% | 7.20% | 0.8536 | -12.75% |
| ADX full-source 100 | 6.44% | 1.8069 | 1.093 | 0.5950 | -24.45% | 7.80% | 0.9326 | -19.63% |
| ADX full-source roll42 -3% half | 6.51% | 1.8400 | 1.174 | 0.6386 | -17.41% | 7.70% | 0.9295 | -13.86% |
| ADX full-source roll21 neg half | 6.48% | 1.8261 | 1.252 | 0.6613 | -13.78% | 6.92% | 0.8899 | -11.42% |

ZZ500 beta audit:

| Candidate | Beta | R2 | Hedged Ann | Hedged Overlap | Hedged DD |
|---|---:|---:|---:|---:|---:|
| Dragon-Hot roll21 neg half | 0.0333 | 0.2348 | 6.68% | 0.9786 | -9.49% |
| ADX full-source roll42 -3% half | 0.0325 | 0.2377 | 6.48% | 1.0027 | -11.23% |
| ADX full-source roll21 neg half | 0.0297 | 0.2294 | 6.44% | 1.0341 | -8.96% |

## Decision

Add `primary_high_return_dragon_hot_chase_adx_fullsource_roll42` as a simulation observation lane, not as a promotable factor.

The lane is useful because it keeps OOS return near the raw Dragon-Hot lane while materially reducing drawdown and improving overlap Sharpe. It remains blocked from promotion by ADX coverage quality.

## Process Lesson

The correct pipeline is:

1. Generate public indicator values from full-market bars.
2. Project only onto the frozen official event calendar.
3. Reuse reference vol-target exposure when comparing against prior wrapped lanes.
4. Run block, OOS, and beta audits before adding a lane to the shortlist config.

This prevents the previous mistake of reusing a local subset factor source.
