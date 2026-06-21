#!/usr/bin/env bash
# Interactive setup for market-monitor's .env file.
# Run from the project root: ./setup.sh

set -euo pipefail

ENV_FILE=".env"
EXAMPLE_FILE=".env.example"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

run_check() {
    if ! command -v python3 &>/dev/null; then
        echo "python3 not found -- can't run the credential check. Install python3 and try: python3 check_env.py"
        exit 1
    fi
    python3 "$SCRIPT_DIR/check_env.py"
}

# --check / --check-only: skip the interactive prompts, just validate
# whatever is currently in .env.
if [[ "${1:-}" == "--check" || "${1:-}" == "--check-only" ]]; then
    run_check
    exit $?
fi

if [[ ! -f "$EXAMPLE_FILE" ]]; then
    echo "Error: $EXAMPLE_FILE not found. Run this from the market-monitor project root."
    exit 1
fi

if [[ -f "$ENV_FILE" ]]; then
    read -rp "$ENV_FILE already exists. Overwrite? [y/N] " confirm
    if [[ ! "$confirm" =~ ^[Yy]$ ]]; then
        echo "Aborted. Existing .env left untouched."
        exit 0
    fi
fi

echo "== Market Monitor setup =="
echo "Press Enter to skip any optional value (leave blank)."
echo

# Helper: prompt, hide input for secrets if desired (keeping it simple/visible here)
prompt() {
    local var_name="$1" label="$2" default="$3" required="$4"
    local input
    while true; do
        if [[ -n "$default" ]]; then
            read -rp "$label [$default]: " input
            input="${input:-$default}"
        else
            read -rp "$label: " input
        fi
        if [[ -z "$input" && "$required" == "yes" ]]; then
            echo "  -> required, please enter a value."
            continue
        fi
        break
    done
    printf -v "$var_name" '%s' "$input"
}

echo "--- Anthropic / AgentRouter (analysis brain) ---"
prompt ANTHROPIC_API_KEY "API key (Anthropic or AgentRouter)" "" "yes"
prompt ANTHROPIC_BASE_URL "Base URL (blank = official Anthropic API, or e.g. https://agentrouter.org)" "" "no"

echo
echo "--- Market data ---"
prompt ALPHA_VANTAGE_API_KEY "Alpha Vantage API key" "" "yes"
prompt NEWSAPI_KEY "NewsAPI key" "" "yes"
echo "(CoinGecko free tier needs no key, skipping)"

echo
echo "--- Telegram alerts ---"
read -rp "Enable Telegram alerts? [y/N] " use_telegram
if [[ "$use_telegram" =~ ^[Yy]$ ]]; then
    prompt TELEGRAM_BOT_TOKEN "Telegram bot token (from @BotFather)" "" "yes"
    prompt TELEGRAM_CHAT_ID "Telegram chat ID" "" "yes"
else
    TELEGRAM_BOT_TOKEN=""
    TELEGRAM_CHAT_ID=""
fi

echo
echo "--- Email alerts ---"
read -rp "Enable email alerts? [y/N] " use_email
if [[ "$use_email" =~ ^[Yy]$ ]]; then
    prompt SMTP_HOST "SMTP host" "smtp.gmail.com" "no"
    prompt SMTP_PORT "SMTP port" "587" "no"
    prompt SMTP_USER "SMTP username (email)" "" "yes"
    prompt SMTP_PASS "SMTP app password" "" "yes"
    prompt ALERT_EMAIL_TO "Send alerts to" "$SMTP_USER" "no"
else
    SMTP_HOST=""
    SMTP_PORT=""
    SMTP_USER=""
    SMTP_PASS=""
    ALERT_EMAIL_TO=""
fi

echo
echo "--- SMS alerts (Twilio, high-confidence only) ---"
read -rp "Enable SMS alerts? [y/N] " use_sms
if [[ "$use_sms" =~ ^[Yy]$ ]]; then
    prompt TWILIO_ACCOUNT_SID "Twilio Account SID" "" "yes"
    prompt TWILIO_AUTH_TOKEN "Twilio Auth Token" "" "yes"
    prompt TWILIO_FROM_NUMBER "Twilio from number (e.g. +1xxxxxxxxxx)" "" "yes"
    prompt TWILIO_TO_NUMBER "Your number (e.g. +233xxxxxxxxx)" "" "yes"
else
    TWILIO_ACCOUNT_SID=""
    TWILIO_AUTH_TOKEN=""
    TWILIO_FROM_NUMBER=""
    TWILIO_TO_NUMBER=""
fi

cat > "$ENV_FILE" <<EOF
# Local secrets. Do not commit this file.

# Anthropic / AgentRouter (analysis brain)
ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
EOF

if [[ -n "${ANTHROPIC_BASE_URL:-}" ]]; then
    echo "ANTHROPIC_BASE_URL=${ANTHROPIC_BASE_URL}" >> "$ENV_FILE"
fi

cat >> "$ENV_FILE" <<EOF

# Market data
ALPHA_VANTAGE_API_KEY=${ALPHA_VANTAGE_API_KEY}
NEWSAPI_KEY=${NEWSAPI_KEY}

# Telegram
TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
TELEGRAM_CHAT_ID=${TELEGRAM_CHAT_ID}

# Email
SMTP_HOST=${SMTP_HOST}
SMTP_PORT=${SMTP_PORT}
SMTP_USER=${SMTP_USER}
SMTP_PASS=${SMTP_PASS}
ALERT_EMAIL_TO=${ALERT_EMAIL_TO}

# SMS
TWILIO_ACCOUNT_SID=${TWILIO_ACCOUNT_SID}
TWILIO_AUTH_TOKEN=${TWILIO_AUTH_TOKEN}
TWILIO_FROM_NUMBER=${TWILIO_FROM_NUMBER}
TWILIO_TO_NUMBER=${TWILIO_TO_NUMBER}
EOF

chmod 600 "$ENV_FILE"
echo
echo "== Done. Wrote $ENV_FILE (permissions set to 600) =="
echo "Run 'pip install -r requirements.txt --break-system-packages' if you haven't already."

echo
read -rp "Run a live check on these credentials now? [Y/n] " do_check
if [[ ! "$do_check" =~ ^[Nn]$ ]]; then
    echo
    run_check
fi
