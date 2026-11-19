# Security Policy

## Reporting a vulnerability

Please **do not** open a public issue for security problems. Report privately
via [GitHub Security Advisories](https://github.com/Prodi9al/market-monitor/security/advisories/new)
or contact the maintainer (@Prodi9al).

## Secrets

This tool talks to many paid/free APIs, so it handles several credentials.
They are loaded from a local `.env` file (git-ignored):

| Variable | Service |
|----------|---------|
| `ANTHROPIC_API_KEY` | Claude analysis |
| `ALPHA_VANTAGE_API_KEY`, `NEWSAPI_KEY` | Market / news data |
| `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID` | Alerts |
| `SMTP_USER`, `SMTP_PASS` | Email alerts |
| `TWILIO_*` | Optional SMS |

**Never commit `.env`.** Copy `.env.example` and fill in real values. If a key
is ever exposed, revoke it at the provider immediately and rotate.

## Deployer checklist

- [ ] `.env` is present, git-ignored, and mode `600`.
- [ ] API keys use the least privilege available (read-only where possible).
- [ ] Use an app-specific password for SMTP (Gmail), not the account password.
- [ ] Run under a dedicated user; don't run as root.

## Out of scope

- Trading/financial losses — this tool surfaces signals, it is not advice.
