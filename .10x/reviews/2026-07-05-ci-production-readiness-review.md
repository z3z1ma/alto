Status: recorded
Created: 2026-07-05
Updated: 2026-07-05
Target: .10x/tickets/2026-07-05-ci-production-readiness.md
Verdict: pass

# CI production readiness review

## Target

Review of the CI repair, release hardening, reservoir correctness fixes, filesystem pull fix, package artifact boundary, and added regression tests.

## Assumptions tested

- The Python 3.10 CI failure is fixed by changing the test patch target rather than changing public package exports.
- Release publishing failure is fixed by updating the stale publish action and retaining valid modern package metadata.
- Release workflow changes do not accidentally republish the old `0.2.21` release from current `main`.
- Reservoir writes persist mapped schema/record payloads, keep separate schema buffers, and do not index failed uploads as successful.
- Tap/reservoir and reservoir/target subprocess failures now raise instead of reporting success.
- The broader quality/security gates remain at zero exits after the production-readiness fixes.

## Findings

- No blocking findings.
- The test entrypoint fix is scoped to the test and preserves the package API.
- The release workflow now treats the existing `v0.2.21` tag as an old release when it does not point at `HEAD`, so current main pushes continue to publish dev builds instead of attempting a duplicate PyPI release.
- The release workflow now has explicit `contents: write`, removes a third-party version-detection action, uses full tag history, and pins the current PyPI publish action by commit SHA.
- The sdist is narrowed to package and metadata files, eliminating `.10x`, `.github`, docs build state, examples, tests, fixture outputs, and `uv.lock` from published source archives.
- The reservoir fixes are covered by focused tests for mapped bytes, schema-buffer preservation, upload failure propagation, tap failure handling, target failure handling, and current-directory `alto fs pull`.
- The final local gate suite exits zero, with coverage improved to 61% and jscpd source duplication at 0 clones.

## Verdict

Pass. The identified CI failures and production-readiness defects were repaired with targeted code and workflow changes, and the evidence record supports pushing for remote CI validation.

## Residual risk

Remote publish steps still depend on repository secrets and TestPyPI/PyPI availability. CodeQL database creation continues to emit known emoji-literal extractor warnings, but analysis exits zero and reports 0 SARIF results.
