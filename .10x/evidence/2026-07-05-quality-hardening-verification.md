Status: recorded
Created: 2026-07-05
Updated: 2026-07-05
Relates-To: .10x/tickets/2026-07-05-uv-migration-quality-optimization.md

# Quality hardening verification

## What was observed

After the uv migration commit, a focused hardening slice improved dependency health, security findings, task metadata typing, and several low-risk correctness issues while preserving the functional test suite.

## Procedure

- `uv lock --locked`
- `uv build`
- `uv run --frozen --python 3.10 python -m unittest discover -s tests -p 'test_*.py'`
- `uv run --frozen --python 3.11 python -m unittest discover -s tests -p 'test_*.py'`
- `uv run --no-sync --with pytest --with pytest-randomly --with pytest-timeout --with pytest-xdist pytest -q -n auto --timeout=300`
- `uv run --all-extras --with pytest --with pytest-timeout --with coverage coverage run --branch -m pytest -q --timeout=300`
- `uv run --all-extras --with coverage coverage report --show-missing`
- `uv run --no-sync ruff check .`
- `uv run --no-sync ruff format --check .`
- `uv run --no-sync --with ty ty check`
- `uv run --all-extras --with mypy mypy .`
- `uv audit --frozen`
- `uv run --all-extras --with deptry deptry .`
- `uv run --all-extras --with vulture vulture alto tests example_proj --min-confidence 80`
- `uv run --all-extras --with pydoclint pydoclint alto`
- `uv run --all-extras --with radon radon cc alto tests -s -a`
- `uv run --all-extras --with complexipy complexipy .`
- `uv run --all-extras --with semgrep semgrep scan --config auto --error .`
- `gitleaks git --no-banner --redact --report-format json --report-path /tmp/alto-ai-quality/gitleaks-git-final.json .`
- `gitleaks dir --no-banner --redact --report-format json --report-path /tmp/alto-ai-quality/gitleaks-dir-final.json .`
- `npx --yes jscpd . --ignore '**/.venv/**,**/.git/**,**/__pycache__/**,**/.mypy_cache/**,**/.ruff_cache/**,**/reports/**,**/dist/**' --reporters console,json --output /tmp/alto-ai-quality/jscpd-final`

## Results

- uv lock: passed.
- Build: passed; source distribution and wheel built.
- Python 3.10 unittest suite: passed, 3 tests.
- Python 3.11 unittest suite: passed, 3 tests.
- Pytest xdist suite: passed, 3 tests.
- Coverage: total 45% line coverage with branch measurement enabled.
- Ruff lint and format checks: passed.
- ty diagnostics: improved from 142 baseline diagnostics to 74 diagnostics.
- mypy errors: improved from 164 baseline errors to 93 errors.
- uv audit: passed; no known vulnerabilities across 45 packages.
- Deptry: passed; no dependency issues.
- Vulture gate: passed at the specified `--min-confidence 80` threshold.
- pydoclint: unchanged residual DOC301 constructor-docstring findings.
- Radon: max cyclomatic complexity remains `alto/catalog.py:apply_selected` at E/37; average complexity is A/3.214.
- Complexipy: residual legacy cognitive-complexity failures remain; the local `AltoRichUI.complete_run` regression was reduced back to 21.
- Semgrep: passed; 0 findings.
- Gitleaks git and directory scans: passed; no leaks.
- jscpd: 21 clones, 1.96% duplicated lines overall; docs lockfiles and intentional examples account for much of the residual duplication.

## What this supports or challenges

This supports the claim that the Python/package hardening slice preserved runtime behavior while materially improving security and type-safety metrics. It also confirms remaining type, complexity, docstring, and duplication findings are legacy or docs-stack work rather than regressions from this slice.

## Limits

The test suite is small and coverage remains low. The functional pipeline tests depend on external network behavior. OSV source scanning still needs a separate docs dependency remediation slice because the Docusaurus lockfiles contain vulnerable transitive dependencies.
