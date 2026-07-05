Status: recorded
Created: 2026-07-05
Updated: 2026-07-05
Relates-To: .10x/tickets/done/2026-07-05-uv-migration-quality-optimization.md

# Docs dependency remediation verification

## What was observed

The docs stack was upgraded from Docusaurus 2.3.1 to Docusaurus 3.10.1, the stale Yarn lockfile was removed, and the npm lockfile was regenerated with targeted transitive overrides for vulnerable packages.

## Procedure

- `npm audit --prefix docs --omit=dev --json`
- `npm outdated --prefix docs --json`
- `npm install --prefix docs --package-lock-only`
- `npm audit fix --prefix docs --package-lock-only`
- `npm ci --prefix docs`
- `npm run build --prefix docs`
- `npm audit --prefix docs --omit=dev`
- `osv-scanner scan source -r .`
- `uv run --all-extras --with semgrep semgrep scan --config auto --error .`
- `gitleaks dir --no-banner --redact --report-format json --report-path /tmp/alto-ai-quality/gitleaks-dir-docs-final.json .`
- `npx --yes jscpd . --ignore '**/.venv/**,**/.git/**,**/__pycache__/**,**/.mypy_cache/**,**/.ruff_cache/**,**/reports/**,**/dist/**,**/node_modules/**,**/build/**' --reporters console,json --output /tmp/alto-ai-quality/jscpd-docs-final`
- `codeql database create /tmp/alto-ai-quality/codeql-db --language=python --source-root .`
- `codeql database analyze /tmp/alto-ai-quality/codeql-db python-security-and-quality.qls --format=sarif-latest --output=/tmp/alto-ai-quality/codeql.sarif`

## Results

- npm audit before remediation: 70 vulnerabilities in the docs lock graph: 7 low, 37 moderate, 24 high, 2 critical.
- npm audit after remediation: 0 vulnerabilities.
- OSV after remediation: 0 issues; scanned `uv.lock` and `docs/package-lock.json`.
- Docs build: passed cleanly after Docusaurus 3 migration fixes.
- Semgrep: passed; 0 findings.
- Gitleaks directory scan: passed; no leaks.
- jscpd: 85 clones and 6.62% duplicated lines overall. This increased because the regenerated npm lockfile is larger and mechanically repetitive.
- CodeQL: 36 SARIF results, down from the earlier 38-result snapshot. Residual results are quality/diagnostic findings such as import cycles, empty except blocks, and binary fixture extraction warnings.

## What this supports or challenges

This supports the claim that the docs lockfile vulnerabilities were remediated without breaking the static docs build. It also supports removing `docs/yarn.lock` because npm is now the verified lockfile and workflow for the docs app.

## Limits

The npm overrides force fixed transitive versions for `serialize-javascript` and `uuid`; the Docusaurus build passed with those overrides, but future Docusaurus upgrades should re-check whether the overrides are still needed. jscpd remains noisy on generated lockfile structure.
