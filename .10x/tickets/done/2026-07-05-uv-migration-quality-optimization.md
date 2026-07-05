Status: done
Created: 2026-07-05
Updated: 2026-07-05

# UV Migration and Quality Optimization

## Scope

Migrate the repository from Poetry-managed packaging to standards-based project metadata and uv-managed locking, then run the requested Python quality optimizer procedure as far as the repository and locally available tools allow.

## Acceptance Criteria

- `pyproject.toml` uses PEP 621 `[project]` metadata and no Poetry-specific package metadata.
- `poetry.lock` is removed and `uv.lock` is created.
- CI/release commands no longer depend on Poetry.
- The repository installs/builds with uv.
- Relevant fast, standard, and available deep quality tools are run and their results are recorded.
- Reasonable, evidence-backed fixes for glaring repository issues are applied without speculative rewrites.
- Changes are committed and pushed on `main` in coherent slices.

## Explicit Exclusions

- No unbounded redesign of Alto behavior.
- No deletion of public API solely from static dead-code candidates.
- No secret values copied into records or final reports.
- No broad suppressions to hide tool findings.

## Evidence Expectations

- Record command outcomes and metric deltas in `.10x/evidence/`.
- Record closure review in `.10x/reviews/`.
- Reference commits pushed to `origin/main`.

## Blockers

None. The user explicitly approved implementation, dependency metadata changes, lockfile mutation, commits, pushes, and reasonable quality fixes.

## Progress and Notes

- 2026-07-05: Inspected initial repository state, attached quality procedure, Poetry metadata, workflows, tests, and package layout. The repository has no prior `.10x/` records.
- 2026-07-05: Migrated `pyproject.toml` to PEP 621 metadata with Hatchling, removed Poetry workflow commands, removed `poetry.lock`, and generated `uv.lock`.
- 2026-07-05: Initial uv test run exposed Dynaconf 3.3 compatibility failure in `find_hyphen_key`; fixed the lookup to support both mappings and key iterables.
- 2026-07-05: Functional tests exposed `alto init` writing sample assets to the process cwd instead of the requested project root; fixed path handling and added regression assertions.
- 2026-07-05: Quality scans found vulnerable Black dev dependencies, missing optional dependency metadata, mutable GitHub Action refs, SHA-1 cache hashing, permissive PEX permissions, and small dead-code candidates; applying a focused hardening slice.
- 2026-07-05: Verified and recorded the Python/package hardening slice in `.10x/evidence/2026-07-05-quality-hardening-verification.md`; docs dependency lockfile vulnerabilities remain for a separate slice.
- 2026-07-05: Upgraded docs from Docusaurus 2.3.1 to 3.10.1, removed `docs/yarn.lock`, regenerated the npm lockfile with narrow transitive security overrides, and recorded verification in `.10x/evidence/2026-07-05-docs-dependency-remediation-verification.md`.
