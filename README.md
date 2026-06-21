# Market Monitor

Always-on market monitoring tool. Watches price/volume spikes (stocks,
crypto, forex), statements from market-moving public figures and officials
(Trump, Fed Chair Kevin Warsh, Treasury Secretary Scott Bessent, ECB
President Christine Lagarde -- expandable to anyone else), and high-impact
economic calendar events ("red folder" news). Feeds everything to Claude
for synthesis into a structured insight, then alerts you via Telegram
(free) and email (free), with SMS available but off by default since it
costs money per message.

## How it works

```
price_monitor.py    -> spike detection (CoinGecko, Alpha Vantage)
social_monitor.py   -> figure statements (Truth Social mirror + NewsAPI)
calendar_monitor.py -> red/orange folder events (ForexFactory JSON feed)
        |
        v
   analyzer.py  -> Claude synthesizes signals into one structured insight
        |
        v
  notifier.py   -> Telegram / Email / SMS (SMS gated to high-confidence)
        |
        v
   main.py      -> orchestrates polling cadence, runs forever
```

## Setup

1. **Get your API keys / accounts:**
   - Anthropic API key, or an Anthropic-compatible provider/API gateway:
     https://console.anthropic.com
   - Alpha Vantage (free): https://www.alphavantage.co/support/#api-key
   - NewsAPI (free tier): https://newsapi.org/register
   - Telegram bot: message @BotFather on Telegram, `/newbot`, get the token.
     Get your chat ID by messaging your bot then visiting
     `https://api.telegram.org/bot<TOKEN>/getUpdates`
   - SMTP: reuse your existing email/SMTP setup, or use a Gmail App Password
   - Twilio (SMS, paid per message): https://www.twilio.com

2. **Copy and fill in the env file:**
   ```bash
   cp .env.example .env
   nano .env   # fill in all your real keys
   ```
   Or run the interactive helper:
   ```bash
   ./setup.sh
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Customize `config/config.yaml`:**
   - Add/remove tickers under `assets`
   - Add more public figures under `figures` (just needs a name + at least
     one source + relevant keywords)
   - Tune `spike_thresholds` to be more/less sensitive
   - Adjust polling cadence under `polling`

5. **Test individual modules first** (each has a `__main__` block):
   ```bash
   cd src
   python3 price_monitor.py
   python3 social_monitor.py
   python3 calendar_monitor.py
   python3 analyzer.py
   ```

6. **Run the full loop:**
   ```bash
   python3 src/main.py
   ```

## Deploying for true 24/7 uptime (Oracle Cloud / any VPS)

Since you've already got an Oracle Cloud Always Free instance, this is the
easiest path. Upload this folder, then set it up as a systemd service so it
survives reboots and restarts automatically if it crashes:

```ini
# /etc/systemd/system/market-monitor.service
[Unit]
Description=Market Monitor
After=network.target

[Service]
Type=simple
WorkingDirectory=/home/youruser/market-monitor/src
ExecStart=/usr/bin/python3 /home/youruser/market-monitor/src/main.py
Restart=always
RestartSec=10
EnvironmentFile=/home/youruser/market-monitor/.env

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable market-monitor
sudo systemctl start market-monitor
sudo journalctl -u market-monitor -f   # watch logs live
```

## Notes & caveats

- **Truth Social mirror sites** are unofficial and can change format or go
  down. The NewsAPI fallback covers you if that happens, but check
  `social_monitor.py` periodically if figure alerts seem to dry up.
- **Alpha Vantage free tier** is rate-limited (~5 calls/min, 500/day). The
  code sleeps between calls to respect this. If you add many more tickers,
  consider a paid tier or spacing out polling further.
- **SMS costs money** (Twilio, per message) and is **disabled by default** in
  config. Telegram is free and just as instant on your phone, so start there.
  Flip `notifications.sms.enabled` to `true` in config.yaml if you decide you
  want it -- it's still gated to `high` confidence either way.
- **This tool does not place trades or give financial advice.** It
  surfaces correlations between news/statements/price action for you to
  evaluate. Treat every alert as a prompt to do your own research, not a
  signal to act on automatically.
- I haven't been able to live-test the external API calls (CoinGecko, Alpha
  Vantage, Telegram, Twilio) from this build environment due to network
  restrictions here. Logic and spike-detection math are verified with mock
  data, but test each module against the real APIs once you have your keys
  in place, before trusting it unattended.

## Expanding to more figures

Just add to `config.yaml`:

```yaml
  - name: "Jerome Powell"
    sources:
      - type: "news_mentions"
        query: "Powell Federal Reserve rate"
    relevance_keywords:
      - "rate cut"
      - "rate hike"
```

No code changes needed -- the social_monitor module reads this generically.
