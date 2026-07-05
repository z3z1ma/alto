Status: recorded
Created: 2026-07-05
Updated: 2026-07-05
Relates-To: .10x/tickets/done/2026-07-05-residual-static-analysis-debt.md

# Zero quality gates verification

## What was observed

The residual static-analysis debt ticket was completed with all selected tool exit codes at zero and the tracked metrics hill climbed from the prior residual baselines.

## Procedure

- `uv run --no-sync --with ruff ruff format .`
- `uv run --no-sync --with ruff ruff check .`
- `uv run --no-sync --with ty ty check`
- `uv run --all-extras --with mypy mypy .`
- `uv run --no-sync --with pydoclint pydoclint alto`
- `uv run --no-sync --with deptry deptry .`
- `uv run --no-sync --with vulture vulture alto tests example_proj --min-confidence 80`
- `uv run --no-sync --with complexipy complexipy .`
- `uv run --no-sync --with radon radon cc alto tests example_proj -s -a`
- `uv run --no-sync --with pytest --with pytest-randomly --with pytest-timeout --with pytest-xdist pytest -n auto --randomly-seed=20260705 --timeout=60`
- `uv run --no-sync --with pytest --with pytest-cov pytest --cov=alto --cov-report=term-missing`
- `uv audit`
- `osv-scanner scan --lockfile=uv.lock --lockfile=docs/package-lock.json`
- `gitleaks detect --no-banner --redact --source .`
- `uv run --no-sync --with semgrep semgrep --config auto --error --exclude .venv --exclude .git --exclude docs/node_modules .`
- `npx --yes jscpd --reporters console --min-lines 5 --min-tokens 50 --ignore "**/.venv/**,**/node_modules/**,**/.git/**,**/uv.lock,**/package-lock.json,**/docs/build/**,docs/**,README.md,alto/incl/**,example_proj/**" .`
- `codeql database create /tmp/alto-codeql-db --language=python --source-root . --overwrite`
- `codeql database analyze /tmp/alto-codeql-db python-security-and-quality.qls --format=sarif-latest --output=/tmp/alto-codeql.sarif`
- SARIF parse of `/tmp/alto-codeql.sarif` for result count.

## Results

- Ruff format: passed; 29 files left unchanged.
- Ruff lint: passed; all checks passed.
- ty: passed; 0 diagnostics, down from 74.
- mypy: passed; 0 errors, down from 93. Remaining messages are non-failing notes about unchecked untyped function bodies.
- pydoclint: passed; no violations, down from residual DOC301 findings.
- Deptry: passed; no dependency issues.
- Vulture: passed at `--min-confidence 80`; no findings.
- Complexipy: passed; all functions within allowed complexity.
- Radon: passed; average complexity A/2.479. The prior E/37 catalog hotspot is now B/7, and no C-grade blocks remain in the final output.
- Randomized xdist pytest: passed, 23 tests, seed `20260705`, timeout 60 seconds.
- Coverage pytest: passed, 23 tests; total line coverage 54%. This is up from the earlier hardening evidence at 45% and the residual-pass pre-hill-climb observation at 50%.
- `uv audit`: passed; no known vulnerabilities or adverse project statuses.
- OSV scanner: passed for `uv.lock` and `docs/package-lock.json`; no issues found.
- Gitleaks: passed; no leaks found.
- Semgrep: passed; 0 findings.
- jscpd source-relevant scan: passed; 0 clones and 0 duplicated lines/tokens across 30 analyzed source/config files. Generated/vendor/lock/template/example surfaces were excluded by explicit command.
- CodeQL database creation: passed. The extractor still reports warnings for existing emoji literals, but the command exits zero.
- CodeQL analysis: passed. Parsed SARIF result count is 0, down from 36 residual findings.

## What this supports or challenges

This supports closure of the residual static-analysis debt ticket: all selected gates now exit zero, security findings did not increase, and the previously recorded type, docstring, complexity, duplication, and CodeQL findings were reduced to clean gates.

## Limits

The coverage percentage is still modest because large engine, extension, and optional dlt surfaces remain expensive to exercise without broader integration fixtures. No separate follow-up is opened for that in this closure because the user requested metric hill climbing for this pass, not a new coverage threshold or integration-test program, and the reasonable low-risk coverage additions were completed here.
