Status: recorded
Created: 2026-07-05
Updated: 2026-07-05
Relates-To: .10x/tickets/done/2026-07-05-uv-migration-quality-optimization.md

# UV Migration Verification

## What Was Observed

The Poetry-to-uv migration resolved, built, and passed the repository functional test suite after two Dynaconf compatibility fixes and an `alto init` project-root artifact fix.

## Procedure

- `uv lock`
  - Exit code: 0
  - Result: created `uv.lock` using CPython 3.11.15.
- `uv lock --locked`
  - Exit code: 0
  - Result: lockfile remained current after edits.
- `uv build`
  - Exit code: 0
  - Result: built `dist/singer_alto-0.2.21.tar.gz` and `dist/singer_alto-0.2.21-py3-none-any.whl`.
- `uv run --frozen python -m unittest discover -s tests -p 'test_*.py'`
  - Initial exit code: 1
  - Initial finding: Dynaconf 3.3 passed a tuple of keys to the hyphen-case lookup and later returned a `DataDict` in config merge, exposing compatibility assumptions.
  - Final exit code: 0
  - Final result: 3 tests passed, including the end-to-end `tap-carbon-intensity:target-jsonl` pipeline.
- `uv run --frozen ruff check --fix .`
  - Exit code: 0
  - Result: no lint findings after safe fixes.
- `uv run --frozen ruff format .`
  - Exit code: 0
  - Result: 17 files reformatted.
- `uv run --frozen ruff check .`
  - Exit code: 0
  - Result: all checks passed.
- `uv run --frozen ruff format --check .`
  - Exit code: 0
  - Result: 28 files already formatted.

## What This Supports

- The project metadata no longer requires Poetry for lock, install, or build.
- The uv lock resolves the existing dependency intent against current compatible releases.
- The migrated dependency graph works with Dynaconf 3.3 for the covered functional paths.
- `alto init` now writes generated sample files into the requested project root.

## Limits

- This evidence covers local Python 3.11 execution. GitHub Actions still needs remote confirmation across the configured 3.8-3.11 matrix.
- The end-to-end test depends on external network availability for the carbon intensity API and Singer plugin installs.
