# GEO Optimizer Backlog

Last updated: 2026-03-23

## Current Status
- No confirmed P0 runtime blockers on `main`.
- Keep this file focused on unresolved issues only.

## Recently Resolved
1. `GeoScoreAdapter` runtime import bug in `backend/services/workflow_executor.py`
- Previous issue: adapter imported a non-existent `GEOScorer` class.
- Resolution: switched to `compute_geo_score(...)` and added regression tests.
- Resolved date: 2026-03-23.

## Parking Lot
1. Add dedicated workflow executor API-level tests for full pipeline path.
2. Review pydantic deprecation warnings before V3 migration window.
3. Keep adapter error messages and readiness diagnostics aligned with runbook wording.
