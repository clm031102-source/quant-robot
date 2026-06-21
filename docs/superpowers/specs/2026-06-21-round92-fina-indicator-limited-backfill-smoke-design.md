# Round92 Fina Indicator Limited Backfill Smoke Design

## Goal

Run a limited-symbol 2015-2025 Tushare `fina_indicator` backfill smoke safely, without treating missing historical quarters as fatal and without making factor profitability claims.

## Context

Round91 produced a planning-only backfill package. The plan showed that two symbols across 44 quarters requires 88 requests, while a full current-symbol universe could exceed 240,000 requests. The next safe step is not full backfill. It is a limited smoke that verifies real long-history behavior, resume semantics, and PIT readiness on processed output.

## Selected Approach

Add an explicit empty-response policy to the existing `run_tushare_fina_indicator_ingest` path:

- Default policy remains `fail`, preserving existing behavior for ordinary ingests.
- New policy `record` writes the empty raw response, marks the request completed with zero rows, records the request in `empty_requests`, and continues.
- Resume must skip completed zero-row raw partitions, not repeatedly download them.
- A new limited-smoke CLI wraps the existing ingest path, checks the Round91-style request budget before downloading, and writes a lightweight smoke report.

## Rejected Approaches

- Treat all empty Tushare responses as errors: too brittle for pre-listing or no-disclosure quarters.
- Treat empty responses as silent success without reporting: hides data coverage problems.
- Full-universe backfill now: request count is too large before limited smoke and PIT readiness audit.

## Success Criteria

- Mixed empty/non-empty fixture backfill completes.
- Default empty-response behavior still fails.
- Resume skips recorded zero-row completed requests.
- Limited-smoke CLI enforces request budget and writes a report.
- Real smoke is run only with explicit small symbols and no final-holdout factor testing.
