# CN ETF Fund-Structure Crowding Prescreen Implementation Plan

**Goal:** Preregister and execute exactly one cost-stressed, point-in-time CN
ETF residual share-creation crowding prescreen.

## 1. Implement the frozen factor

- Add a pure factor builder with exact-session share lag, `known_from`
  enforcement, frozen controls, cross-sectional winsorization/standardization,
  rank checks, factor output, direct exposures, and ADV20.
- Add unit tests for sign, lag, eligibility, missing history, and invariance.

## 2. Freeze preregistration

- Add a fund-structure preregistration operation, strict CLI, and frozen config.
- Hash-bind the source-readiness evidence and all five canonical yearly
  partitions.
- Extend the reusable single-prescreen authorization without changing the
  existing dynamic-peer packet contract.
- Prove preregistration artifacts are deterministic.

## 3. Open one scoped batch

- Update the scheduler with exact preregistration and authorization hashes.
- Extend the Quant PM gate for only the new candidate, branch, stage, and
  one-use authorization.
- Run the startup gate and prescreen preflight before labels are read.

## 4. Execute and close

- Claim the authorization once, compute labels, and run the existing
  statistical, correlation, capacity, and 5/10 bps cost gates.
- Write a hash manifest and terminal execution outcome.
- Update the scheduler and research index based only on the frozen primary
  result: either close at zero budget or authorize the next preregistration.

## 5. Verify and publish

- Run focused tests, project audit, and relevant integration checks.
- Commit and push the review/preregistration state, then the batch/closeout
  state on task branches.
