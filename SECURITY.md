# Security

## Reporting vulnerabilities

Please report security issues privately to the repository maintainer rather than opening a public issue.

## Credential rotation (required if secrets were ever committed)

If Meta, Cloudinary, or app tokens were exposed in git history, rotate them **before** relying on a cleaned repository:

1. **Meta Developer Console** — Reset Instagram app secret; revoke long-lived WhatsApp/Instagram user tokens; remove stale OAuth redirect and webhook URLs (e.g. old ngrok endpoints).
2. **Cloudinary** — Rotate API key/secret for any cloud that appeared in commits.
3. **This service** — Generate new `MCPKEY` in `.env` and matching `MCPKEY` in Node appcore; update VPS `~/apps/mitexlabaipythonmcp/shared/.env` and reload PM2.
4. **Optional keys** — Rotate `OPENAI_API_KEY` and `MITEX_APPCORESRV_MCP_SECRET_KEY` if they may have been used alongside compromised integrations.

## Local development

- Copy [`.env.example`](.env.example) to `.env`; never commit `.env`.
- Do not add scratch files under `packages/**/_*.txt` with real API responses or tokens.

## Authentication

The HTTP MCP endpoint expects `Authorization: Bearer <MCPKEY>` (see README). `/health` is unauthenticated for load checks.
