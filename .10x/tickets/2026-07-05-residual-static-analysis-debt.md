Status: open
Created: 2026-07-05
Updated: 2026-07-05
Parent: .10x/tickets/done/2026-07-05-uv-migration-quality-optimization.md
Depends-On: None

# Residual static analysis debt

## Scope

Reduce the remaining static-analysis debt that was not reasonable to repair during the uv migration, dependency security, and docs-remediation slices.

Initial residual areas:

- `ty` reports 74 diagnostics after the hardening slice.
- `mypy` reports 93 errors after the hardening slice.
- Radon max cyclomatic complexity remains `alto/catalog.py:apply_selected` at E/37.
- Complexipy still flags legacy cognitive-complexity hotspots in catalog, engine, main, repl, ui, and dlt helper paths.
- pydoclint still reports DOC301 constructor-docstring findings.
- CodeQL still reports 36 quality/diagnostic findings, primarily import cycles, empty except blocks, binary fixture extraction warnings, and initialization-hook warnings.
- jscpd remains noisy, especially on generated lockfiles and intentionally duplicated examples.

## Acceptance criteria

- Each selected analyzer family has a current baseline recorded before changes.
- Any reduction work preserves existing functional behavior and tests.
- Security findings must not increase.
- Broad suppressions, broad `Any`, and blanket ignores are not accepted as completion unless a targeted tool limitation is documented with evidence.
- Any changed public behavior is governed by an explicit spec or a focused ticket before implementation.

## Evidence expectations

- Updated analyzer outputs for every touched tool family.
- Functional test results for affected paths.
- Review record if code is materially refactored.

## Explicit exclusions

- Do not remove CLI/doit/Docusaurus hook methods merely because low-confidence unused-code scanners cannot see dynamic dispatch.
- Do not remove package locks to reduce duplication metrics.
- Do not change product semantics without a governing spec or explicit user ratification.

## Blockers

None for investigation. Implementation slices must be split before broad refactors.

## Progress and notes

- 2026-07-05: Opened from residual analyzer findings recorded in `.10x/evidence/2026-07-05-quality-hardening-verification.md` and `.10x/evidence/2026-07-05-docs-dependency-remediation-verification.md`.
