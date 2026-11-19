# Contributing to Market Monitor

Thanks for helping out! Market Monitor polls market data, news, and economic
calendars, feeds signals to Claude for synthesis, and sends alerts via
Telegram/email/SMS.

## Setup

```bash
cp .env.example .env      # fill in API keys etc.
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python check_env.py       # verify your .env is complete
python src/main.py
```

Or use `./setup.sh`.

## Layout

| Path | Purpose |
|------|---------|
| `src/main.py` | scheduler / entry point |
| `src/price_monitor.py` | price & volume spike detection |
| `src/social_monitor.py` | public-figure statement monitoring |
| `src/calendar_monitor.py` | economic calendar (red-folder) events |
| `src/analyzer.py` | Claude synthesis into a structured insight |
| `src/notifier.py` | Telegram / email / SMS delivery |
| `config/config.yaml` | figures, assets, thresholds, cadence |

## Rules

- **Never commit secrets.** Use `.env` (git-ignored) and `.env.example`.
- Add new figures/assets in `config/config.yaml`, not hardcoded in `src/`.
- Keep providers pluggable; don't couple `src/` to one vendor's response shape.
- Match the existing logging and error-handling style.

## License

Contributions are licensed under the MIT License (see [LICENSE](LICENSE)).
