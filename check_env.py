#!/usr/bin/env python3
"""
Validates the credentials in .env by making one lightweight real call per
service. Doesn't touch your price history, config thresholds, etc. -- just
checks "does this key work".

Usage: python3 check_env.py
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent

try:
    import requests
    from dotenv import load_dotenv
except ImportError:
    print("Missing dependencies. Run: pip install requests python-dotenv --break-system-packages")
    sys.exit(1)

load_dotenv(ROOT / ".env")

GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
RESET = "\033[0m"


def ok(msg):
    print(f"{GREEN}✔{RESET} {msg}")


def fail(msg):
    print(f"{RED}✘{RESET} {msg}")


def skip(msg):
    print(f"{YELLOW}–{RESET} {msg} (skipped, not configured)")


def check_anthropic():
    key = os.getenv("ANTHROPIC_API_KEY", "")
    if not key or key.startswith("paste_") or key.startswith("sk-ant-xxxx"):
        fail("Anthropic/AgentRouter: ANTHROPIC_API_KEY is missing or still a placeholder")
        return
    base_url = os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com").rstrip("/")
    try:
        resp = requests.post(
            f"{base_url}/v1/messages",
            headers={
                "x-api-key": key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            json={
                "model": "claude-sonnet-4-6",
                "max_tokens": 1,
                "messages": [{"role": "user", "content": "hi"}],
            },
            timeout=15,
        )
        if resp.status_code == 200:
            ok(f"Anthropic/AgentRouter ({base_url}): key works")
        elif resp.status_code == 401:
            fail(f"Anthropic/AgentRouter ({base_url}): 401 unauthorized -- key is wrong or expired")
        else:
            fail(f"Anthropic/AgentRouter ({base_url}): HTTP {resp.status_code} -- {resp.text[:150]}")
    except requests.RequestException as e:
        fail(f"Anthropic/AgentRouter ({base_url}): request failed -- {e}")


def check_alpha_vantage():
    key = os.getenv("ALPHA_VANTAGE_API_KEY", "")
    if not key or key.startswith("your_"):
        fail("Alpha Vantage: ALPHA_VANTAGE_API_KEY is missing or still a placeholder")
        return
    try:
        resp = requests.get(
            "https://www.alphavantage.co/query",
            params={"function": "GLOBAL_QUOTE", "symbol": "AAPL", "apikey": key},
            timeout=15,
        )
        data = resp.json()
        if "Global Quote" in data and data["Global Quote"]:
            ok("Alpha Vantage: key works")
        elif "Note" in data:
            fail(f"Alpha Vantage: rate-limited -- {data['Note'][:150]}")
        elif "Information" in data:
            fail(f"Alpha Vantage: {data['Information'][:150]}")
        else:
            fail(f"Alpha Vantage: unexpected response -- {str(data)[:150]}")
    except requests.RequestException as e:
        fail(f"Alpha Vantage: request failed -- {e}")


def check_newsapi():
    key = os.getenv("NEWSAPI_KEY", "")
    if not key or key.startswith("your_"):
        fail("NewsAPI: NEWSAPI_KEY is missing or still a placeholder")
        return
    try:
        resp = requests.get(
            "https://newsapi.org/v2/top-headlines",
            params={"category": "business", "pageSize": 1, "apiKey": key},
            timeout=15,
        )
        data = resp.json()
        if data.get("status") == "ok":
            ok("NewsAPI: key works")
        else:
            fail(f"NewsAPI: {data.get('message', str(data))[:150]}")
    except requests.RequestException as e:
        fail(f"NewsAPI: request failed -- {e}")


def check_telegram():
    token = os.getenv("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.getenv("TELEGRAM_CHAT_ID", "")
    if not token or token.startswith("your_"):
        skip("Telegram")
        return
    try:
        resp = requests.get(f"https://api.telegram.org/bot{token}/getMe", timeout=15)
        data = resp.json()
        if data.get("ok"):
            bot_name = data["result"].get("username", "?")
            ok(f"Telegram: bot token works (@{bot_name})")
            if not chat_id or chat_id.startswith("your_"):
                fail("Telegram: TELEGRAM_CHAT_ID is missing or still a placeholder")
        else:
            fail(f"Telegram: bot token rejected -- {data.get('description', '')[:150]}")
    except requests.RequestException as e:
        fail(f"Telegram: request failed -- {e}")


def check_smtp():
    host = os.getenv("SMTP_HOST", "")
    user = os.getenv("SMTP_USER", "")
    pwd = os.getenv("SMTP_PASS", "")
    port = os.getenv("SMTP_PORT", "587")
    if not host or not user or user.startswith("your_") or not pwd or pwd.startswith("your_"):
        skip("Email/SMTP")
        return
    import smtplib
    try:
        with smtplib.SMTP(host, int(port), timeout=15) as server:
            server.starttls()
            server.login(user, pwd)
        ok(f"Email/SMTP ({host}): login works")
    except Exception as e:
        fail(f"Email/SMTP ({host}): login failed -- {e}")


def check_twilio():
    sid = os.getenv("TWILIO_ACCOUNT_SID", "")
    token = os.getenv("TWILIO_AUTH_TOKEN", "")
    if not sid or sid.startswith("your_") or not token or token.startswith("your_"):
        skip("Twilio/SMS")
        return
    try:
        resp = requests.get(
            f"https://api.twilio.com/2010-04-01/Accounts/{sid}.json",
            auth=(sid, token),
            timeout=15,
        )
        if resp.status_code == 200:
            ok("Twilio/SMS: credentials work")
        elif resp.status_code == 401:
            fail("Twilio/SMS: 401 unauthorized -- SID or auth token is wrong")
        else:
            fail(f"Twilio/SMS: HTTP {resp.status_code} -- {resp.text[:150]}")
    except requests.RequestException as e:
        fail(f"Twilio/SMS: request failed -- {e}")


def main():
    if not (ROOT / ".env").exists():
        print("No .env found. Run ./setup.sh first.")
        sys.exit(1)

    print("== Checking market-monitor credentials ==\n")
    check_anthropic()
    check_alpha_vantage()
    check_newsapi()
    check_telegram()
    check_smtp()
    check_twilio()
    print("\nDone. Crypto (CoinGecko) needs no key, so it's not checked here.")


if __name__ == "__main__":
    main()
