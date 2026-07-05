Status: recorded
Created: 2026-07-05
Updated: 2026-07-05
Relates-To: .10x/tickets/done/2026-07-05-ci-production-readiness.md

# CI production readiness verification

## What was observed

GitHub Actions failures on `main` were inspected with the GitHub CLI and repaired locally. The failing Alto Tests run was `28735223236`; the failing Release run was `28735223238`.

Local verification after the fixes exited zero across the CI commands, package release path, static analysis, security scans, and workflow linting. Test count increased from 23 to 28 and coverage increased from the prior recorded 54% to 61%.

## Procedure

- `gh auth status`
- `gh repo view --json owner,name,defaultBranchRef,url`
- `gh pr list --state open --json number,title,headRefName,baseRefName,url`
- `gh workflow list --all`
- `gh run list --branch main --limit 12 --json databaseId,workflowName,status,conclusion,headSha,headBranch,displayTitle,url`
- `gh run view 28735223236 --json ...` and `gh run view 28735223236 --log-failed`
- `gh run view 28735223238 --json ...` and `gh run view 28735223238 --log-failed`
- `uv run --python 3.10 python -m unittest discover -s tests -p 'test_*.py'`
- `uv run --python 3.11 python -m unittest discover -s tests -p 'test_*.py'`
- `uv lock --check && uv sync --frozen --all-groups`
- `uv run ruff check .`
- `uv run ruff format --check .`
- `git diff --check`
- `uv run --all-extras --with ty ty check`
- `uv run --all-extras --with mypy mypy .`
- `uv run --no-sync --with pydoclint pydoclint alto`
- `uv run --no-sync --with deptry deptry .`
- `uv run --no-sync --with vulture vulture alto tests example_proj --min-confidence 80`
- `uv run --no-sync --with complexipy complexipy .`
- `uv run --no-sync --with radon radon cc alto tests example_proj -s -a`
- `uv run --no-sync --with pytest --with pytest-randomly --with pytest-timeout --with pytest-xdist pytest -n auto --randomly-seed=20260705 --timeout=300`
- `uv run --no-sync --with pytest --with pytest-cov pytest --cov=alto --cov-report=term-missing`
- `uv audit`
- `osv-scanner scan --lockfile=uv.lock --lockfile=docs/package-lock.json`
- `gitleaks detect --no-banner --redact --source .`
- `uv run --no-sync --with semgrep semgrep --config auto --error --exclude .venv --exclude .git --exclude docs/node_modules .`
- `npm audit --prefix docs --omit=dev`
- `npx --yes jscpd --reporters console --min-lines 5 --min-tokens 50 --ignore "**/.venv/**,**/node_modules/**,**/.git/**,**/uv.lock,**/package-lock.json,**/docs/build/**,docs/**,README.md,alto/incl/**,example_proj/**" .`
- `uv build --no-sources`
- wheel metadata inspection from `dist/*.whl`
- sdist forbidden-entry inspection for `.10x`, `.github`, `docs`, and `uv.lock`
- `uv run --with twine twine check dist/*`
- working-tree release-style dev replay: `uv version --bump patch --frozen`, `uv version "$version.dev.1234567890" --frozen`, `uv build --no-sources`, sdist forbidden-entry inspection, and `twine check`
- `codeql database create /tmp/alto-codeql-db --language=python --source-root . --overwrite`
- `codeql database analyze /tmp/alto-codeql-db python-security-and-quality.qls --format=sarif-latest --output=/tmp/alto-codeql.sarif`
- SARIF result count parse for `/tmp/alto-codeql.sarif`
- `go run github.com/rhysd/actionlint/cmd/actionlint@latest .github/workflows/release.yml .github/workflows/test.yml .github/workflows/labeler.yml`

## Results

- GitHub CLI auth succeeded for `github.com` as `z3z1ma`; target repo is `z3z1ma/alto`, default branch `main`; no open PRs were present.
- Alto Tests run `28735223236` failed on Python 3.10 because `patch("alto.main.main")` resolved through the package-level `alto.main` export instead of the module. The test now patches the imported module object.
- Release run `28735223238` failed because `pypa/gh-action-pypi-publish` `v1.8.3` rejected valid `Metadata-Version: 2.4` artifacts. The workflow now uses pinned `v1.14.0` and canonical `repository-url`.
- Release workflow hardening added explicit `contents: write`, robust version-tag detection, and tag creation that handles multi-commit pushes without republishing old-version main commits.
- Hatch sdist selection now excludes project-internal files; release-style dev replay reported `forbidden_sdist_entries=0`.
- Python unittest matrix: 28 tests passed on Python 3.10 and Python 3.11.
- Pytest xdist: 28 tests passed.
- Coverage: 28 tests passed; total coverage is 61%, up from the prior recorded 54%.
- Ruff, ty, mypy, pydoclint, deptry, vulture, complexipy, radon, uv audit, OSV, Gitleaks, Semgrep, npm audit, jscpd, twine, CodeQL, and actionlint all exited zero.
- jscpd final scan reported 0 clones and 0 duplicated lines/tokens.
- CodeQL SARIF result count was 0. Database creation still emitted existing extractor warnings for emoji literals, but the commands exited zero.

## What this supports or challenges

This supports the claim that the known GitHub Actions failures were root-caused and repaired, and that the broader production-readiness review fixed confirmed reservoir, target, filesystem, packaging, and release-workflow bugs without regressing the previous zero-gate baseline.

## Limits

Local release verification cannot prove PyPI/TestPyPI secret validity before a workflow run starts, only package metadata validity, workflow syntax, and publish-action compatibility. The pushed workflow later completed successfully on GitHub Actions.
