# Project Audit Remediation Design

## Context

The repository is a mature research-to-paper platform, but its current controls can still admit ambiguous data, stale cached results, self-declared evidence, survivorship bias, and incomplete promotion packets. The remediation must improve research correctness without enabling broker connectivity, account access, order placement, or live trading.

## Chosen Approach

Use layered hardening around the existing architecture.

1. Preserve stable public APIs where their semantics are sound.
2. Make ambiguous or unsafe behavior fail closed by default.
3. Keep legacy behavior only behind an explicit compatibility option.
4. Add machine-verifiable evidence and deterministic fingerprints at data, experiment, and promotion boundaries.
5. Use focused regression tests for every corrected behavior before implementation.

This is preferred over a big-bang rewrite because the repository has more than 2,000 tests and many operational entrypoints. It is also preferred over isolated patches because the audit findings share the same root cause: policy decisions are represented as prose or loosely coupled booleans instead of enforceable contracts.

## Workstreams

### 1. Authoritative Data And Provenance

- `load_processed_bars` discovers only an explicitly addressed store by default. Recursive discovery becomes opt-in and rejects multiple roots instead of concatenating them.
- Processed-bar uniqueness is keyed by instrument, timestamp, and frequency, independent of source labels.
- Market-data order validation checks the supplied order instead of sorting before validation.
- CN stock manifests include schema version, deterministic frame fingerprints, source-file inventory, and a source-tree fingerprint.
- Dataset writes and JSON manifests use same-directory temporary files followed by atomic replacement. A partition may contain one storage format only.
- Gap audits require an explicit trading calendar for clearance, count all gaps separately from truncated examples, and report whole-market missing sessions.

### 2. Research And Promotion Contracts

- Every gate consumer names the permission it needs. Portfolio grids require `portfolio_grid_allowed`; a merely ready research screen is insufficient.
- Promotion configuration rejects unknown keys and loads every declared evidence path.
- Required evidence packets are evaluated as machine-readable reports, not accepted because a prose field is non-empty.
- Paper evidence identity includes case, factor source, cost, rebalance interval, universe, data fingerprint, and research window when strict provenance is enabled.
- Missing quality evidence and non-positive paper returns become configurable hard blockers, enabled in strict production configurations.
- Final holdout access requires a frozen candidate packet and a read-once ledger receipt. A boolean command-line flag alone cannot open the holdout.

### 3. Quantitative Correctness

- Delisted instruments remain historically eligible before their delisting date; a current inactive flag is not applied backward without an effective status date.
- Financial events become tradable only on the first session strictly after announcement.
- IC, quantile, and long-short outputs preserve `horizon` and `execution_lag` dimensions.
- IC aggregate significance uses a minimum sample threshold and Newey-West standard errors.
- Walk-forward correction uses a durable cumulative hypothesis ledger, not only the rows in the current grid.
- CPCV evidence contains split-level realized return metrics and a distribution summary; a split plan alone cannot satisfy the control.

### 4. Execution Realism And Reproducibility

- Capacity-constrained backtests require positive traded amount. Missing liquidity or participation above the configured limit rejects the trade and is surfaced in downstream rejection reasons.
- Market impact continues increasing above the participation threshold instead of being capped at the threshold cost.
- Turnover is computed from changes in portfolio target weights, including cash, rather than the sum of target weights.
- Experiment resume requires a fingerprint over effective configuration, input bars, relevant source code, and runtime versions.
- Manifests record those fingerprints and refuse stale or legacy caches.

### 5. Engineering Governance

- Git attributes make repository text line endings deterministic; tests normalize HTTP text where transport line endings are irrelevant.
- CI runs a supported OS/Python matrix, installs from bounded dependency ranges plus a tracked constraints file, checks the wheel, runs tests, compile checks, and the project audit.
- Safe sync scans file type, size, path escape, and high-confidence credential patterns in addition to path policy.
- Project audit uses syntax-aware, case-insensitive implementation scanning and meaningful fixture/mock-boundary checks.
- The former `project_completion_gate` is reframed as a pre-alpha research-readiness gate. It cannot claim that the entire project is 98-100% complete.
- Large-module and test-topology debt is reported by a maintainability audit and guarded against growth. A wholesale split of the 14,000-line advisory module is a separate refactor because mixing it with research-correctness changes would increase regression risk.

## External Evidence Boundaries

The remediation cannot manufacture provider quota, missing historical feeds, a successful final holdout, or 20 paper-observation runs. These remain explicit blockers. Code may validate and report them, but must never mark them complete without real artifacts.

## Compatibility And Migration

- New strict options are the default on active CN stock entrypoints.
- Legacy packets without fingerprints or structured evidence produce an actionable validation error.
- Low-level helpers may expose an explicit compatibility mode for historical diagnostics, but compatibility mode can never grant portfolio or promotion permissions.
- Existing generated data and reports stay outside Git.

## Acceptance Criteria

1. Each audit defect has either a regression test and implementation or an explicit external/deferred blocker with a machine-enforced gate.
2. Focused unit tests for every changed subsystem pass.
3. The complete unit suite is run; any remaining failures are identified as pre-existing or fixed.
4. Project audit, compile checks, and diff checks pass.
5. No live-trading capability is introduced.
6. Changes are committed in reviewable groups and are not pushed from the office desktop.

