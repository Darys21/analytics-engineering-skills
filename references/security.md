# Reference: Security

## When to use
- Always, for any code or pipeline that connects to a real system or handles real data.
- Before deployment to any shared or production environment.
- When externalizing artifacts (reports, exports, sample datasets, dashboards shared outside team).

## When NOT to use
There is no case for skipping security thinking. Level of rigor scales with sensitivity.

## Common mistakes
- Secrets in source control (git), hardcoded, in notebooks, in command-line arguments.
- Broad "sysadmin" or "db_owner" credentials used everywhere (no least privilege).
- PII exported to CSV, included in screenshots, logged in plaintext, or committed.
- Logging full request/response bodies that contain secrets or PII.
- No row-level or column-level security for sensitive datasets.
- Public blob storage / open report workspaces.
- Unpinned dependencies, accidental PyPI typo-squat installs, no dependency scan.

## Trade-offs
- Convenience vs. security: a .env file is more secure than hardcoded but less convenient. A secret manager is more secure than .env. Choose the level matching the data sensitivity.
- Usability vs. access control: strict RLS can make reports slow; mitigate with semantic design, not by removing RLS.

## What to inspect first
1. **Secrets.** Is there any secret hardcoded? Check: source files, notebooks, git history, CI logs.
2. **Data access.** Can the user/role read anything other than exactly what they need?
3. **Sensitive data.** What PII or commercially sensitive data exists? Where is it used, logged, exported?
4. **Dependencies.** Do we lock versions? Are we pulling known CVEs?
5. **Sharing settings.** Workspaces, reports, storage accounts — who has access? Who can share further?

## Good implementation

### 1. Secrets management (from least to most mature)
- Never commit secrets. Ever.
- Local: `.env` file in `.gitignore`. Load with `python-dotenv` or equivalent.
- CI: repository/organization secrets. Never `echo` them into logs; most systems mask them, but don't rely on that.
- Cloud / production: native secret stores (Azure Key Vault, AWS Secrets Manager, GCP Secret Manager, HashiCorp Vault).
- Rotate: periodic rotation, revocation on suspected exposure, scoped service principals per environment.

### 2. Least privilege
- Each user, service principal, connection gets the minimum permissions needed for its role.
- Separate accounts for ingestion vs. transformation vs. serving vs. BI.
- BI tools: use the tool's semantic layer RLS/OLS and workspace access instead of broad db-level permissions if feasible.

### 3. Credentials and access control in practice
- Service principals / managed identities over user accounts for services.
- Short-lived credentials (temporary SAS tokens, OIDC, short TTL service account tokens) preferred over static keys.
- Connection strings: store in secret store, pull at runtime, never print to logs.
- RLS and OLS (object-level security, column-level): apply at the semantic/dataset layer, not only in the app.
- Share workspaces/apps via AAD groups, not per-user, to enable offboarding hygiene.

### 4. PII and sensitive data
- **Know what you have.** Inventory PII columns: name, email, phone, national ID, IP (when treated as PII), address, salary, health data, etc.
- **Minimize.** Don't ingest or expose PII unless required.
- **Mask / pseudonymize / hash** where possible for analytics purposes. Use a stable keyed hash with salt stored securely, never plain SHA-256 alone.
- **Differential privacy or k-anonymity** before sharing aggregated datasets externally.
- **Exports:** every export/report must be reviewed for PII if it crosses a team boundary.
- **Logs:** scrub PII. Do not log full request payloads if they contain user data. Log IDs instead.

### 5. Logging hygiene
- Never log: tokens, API keys, passwords, connection strings, full credit card fields, free-form PII fields.
- If you must log IDs: use surrogate / opaque IDs, not natural keys that are PII.
- Structured logs with explicit allowlist of logged keys = far safer than string formatting.

### 6. Dependency security
- Pin versions in `requirements.txt` / `package.json` / `packages.lock.json` / lock files.
- Enable automated dependency scans (Dependabot, Renovate, Snyk, GitHub/GitLab dependency graph, OWASP dependency-check).
- Review any new dependency before adding; is it maintained? Is the scope tiny or a huge transitive tree?
- If install scripts run on install, that's a huge red flag; avoid, or pin + audit.

### 7. Secure deployment
- Infrastructure as code (Bicep, Terraform, ARM) checked in, reviewed, not manually-clicked in portals.
- Deployment identities with scoped permissions; not global admin.
- Rollback path documented; no manual edits in prod.
- Secrets in deployment rotated on personnel change or suspected breach.

### 8. Dashboards and reports
- Row-level and column-level security scoped to users/groups.
- Export restrictions (PDF/CSV) if content sensitive.
- Tenant settings: disable "export to PowerPoint with live data" if not needed.
- Do not embed connection strings or secrets in PBIX / template files that will be shared.

## How to test
- **Secrets scan:** run gitleaks / trufflehog / GitHub secret scanning on the repo and on CI logs. Fix every finding; force-push to re-write history if a secret leaked + rotate the secret.
- **Access review:** quarterly: list all users/service principals with access. Remove what's not needed.
- **RLS smoke tests:** as a low-privileged user, can I see data for other regions/tenants?
- **Dependency scan:** automated, in CI. Fail the build for known-critical CVEs.
- **PII hunt:** grep for PII patterns in committed code / sample data / example outputs. Fail PRs that add PII.

## Pitfalls
- "We are not a target." You are.
- "It's only internal." Most breaches start inside.
- "We can't do that much." Start small: .env + .gitignore + service principal with narrow grants.
- Hiding security behind a VPN only; no application-level RLS.
- Default credentials in PoCs never rotated when it reaches prod.

---
*See also:* `references/ci-cd.md`, `workflows/delivery.md`, `workflows/review.md` (security dimension), `references/power-bi.md` (RLS/OLS).
