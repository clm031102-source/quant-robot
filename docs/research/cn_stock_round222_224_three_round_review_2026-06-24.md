# CN Stock Round222-224 Three-Round Review

- Review date: 2026-06-24
- Scope: financial PIT post-announcement drift and repaired gap reversal
- Machine/task: office_desktop / factor_validation
- Promotion result: 0 promotable factors

## Round Summary

| Round | Direction | Main Output | Result |
|---|---|---|---|
| Round222 | Financial PIT post-announcement drift | Preregistered PEAD-style continuation and underreaction candidates, then ran matrix/label smoke and residual prescreen | Original underreaction sign failed; best diagnostic was meaningfully negative, implying overreaction reversal rather than drift |
| Round223 | Financial PIT post-announcement gap reversal | Repaired sign, preregistered 5 gap-reversal candidates, ran PIT matrix/label smoke and residual neutral prescreen | 5 residual research leads, 0 promotable factors |
| Round224 | Reference-dedup walk-forward preflight | Recomputed candidate-cluster correlations, froze only non-duplicate candidates | 3 frozen walk-forward candidates, 2 high-correlation duplicates, 0 promotable factors |

## What Improved

- The process did rotate direction after evidence showed the original sign was wrong.
- Same-day event trading remains blocked; factor dates use the first tradable date after event reaction.
- Candidate counting is now cluster-aware: highly correlated variants are not counted as independent discoveries.
- Startup now points to Round225 walk-forward, cost/capacity, and regime validation instead of more residual IC mining.

## Frozen Candidates

| Candidate | Residual IC | t | Reason To Keep |
|---|---:|---:|---|
| `pead_gap_overreaction_reversal_low_liquidity_penalized_1_5` | 0.1383 | 4.01 | strongest IC and neutral retention; cluster representative |
| `pead_gap_overreaction_reversal_volume_confirmed_1_5` | 0.1069 | 2.79 | not above high-correlation duplicate threshold after representative freeze |
| `pead_gap_overreaction_reversal_quality_conditioned_1_5` | 0.0654 | 2.28 | lower raw IC, but most orthogonal candidate correlation profile |

## Rejected Counting

- `pead_gap_overreaction_reversal_1_5` is a duplicate of the low-liquidity-penalized representative at candidate correlation 0.972.
- `pead_gap_overreaction_reversal_size_neutral_candidate_1_5` is also a duplicate of the same representative at candidate correlation 0.971.

## Audit Conclusion

This sequence is useful research progress, but not a tradable edge yet. The correct interpretation is:

- 0 paper-ready factors
- 0 promotable factors
- 3 walk-forward candidates
- 2 duplicate variants removed from independent factor counts

Round225 must test whether the 3 frozen candidates survive rolling OOS folds, cost/capacity stress, regime coverage, and drawdown/turnover controls. If Round225 fails, the gap-reversal family should be hibernated or repaired rather than expanded.
