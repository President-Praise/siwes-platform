# Secrets & keys for `siwes-platform`

Where to re-provision each environment variable if you've lost the original values.
Generated automatically from a scan of the codebase — verify against the actual code before trusting.

| Variable | Service | Where to get it |
|---|---|---|
| `ANTHROPIC_API_KEY` | Anthropic | console.anthropic.com/settings/keys |
| `CLAUDE_MODEL` | Anthropic (Claude) | console.anthropic.com/settings/keys |
| `COOKIE_SECURE` | unknown | unclear — grep the codebase for `COOKIE_SECURE` to see how it's used |
| `LMU_ADMIN_INITIAL_PIN` | self-set admin cred | you choose — pick a strong password |
| `PAYSTACK_PUBLIC_KEY` | Paystack | dashboard.paystack.com/#/settings/developers |
| `PAYSTACK_SECRET_KEY` | Paystack | dashboard.paystack.com/#/settings/developers |
| `PLATFORM_CUT_PCT` | unknown | unclear — grep the codebase for `PLATFORM_CUT_PCT` to see how it's used |
| `PLATFORM_NAME` | unknown | unclear — grep the codebase for `PLATFORM_NAME` to see how it's used |
| `PUBLIC_BASE_URL` | your site URL | e.g. http://localhost:3000 in dev, prod URL in prod |
| `REPORT_USE_CLAUDE` | Anthropic (Claude) | console.anthropic.com/settings/keys |
| `SECRET_KEY` | self-generated | generate with `openssl rand -base64 32` |
| `SOFFICE_BIN` | unknown | unclear — grep the codebase for `SOFFICE_BIN` to see how it's used |
| `SUPER_ADMIN_INITIAL_PIN` | self-set admin cred | you choose — pick a strong password |

## Recovery workflow

1. Copy `.env.example` to `.env`
2. For each row above, visit the linked dashboard and either find the existing key or create a new one
3. Paste values into `.env` (never commit)
4. `npm install` / `pip install -r requirements.txt` then run
