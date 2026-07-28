# CN ETF Margin-Positioning Source Readiness Plan

**Goal:** Build and audit a resumable point-in-time CN ETF margin-positioning
dataset before any alpha test.

1. Add a pure readiness operation for ETF-bar intersection, exact next-session
   availability, uniqueness, numeric integrity, cross-sectional breadth, and
   final-holdout exclusion.
2. Add a strict config and resumable CLI that fetches only `margin_detail`,
   caches one deterministic date shard per validated session, and writes a
   canonical yearly dataset plus content hashes.
3. Run the full frozen 2020-01-02 through 2024-06-28 ingest and repeat the
   readiness audit from cached shards.
4. If ready, update the scheduler and preregister exactly one compact
   ETF-specific margin-positioning prescreen; otherwise record the blocker and
   rotate.
5. Verify, commit, integrate, push, and clean the completed branch.

