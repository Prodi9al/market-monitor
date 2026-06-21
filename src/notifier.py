"""
Sends alerts through Telegram, email, and SMS. Each channel fails
independently and non-fatally -- if one breaks, the others still fire.

SMS is reserved for high-confidence insights only (configurable) since
Twilio charges per message.
"""
import smtplib
import requests
from email.mime.text import MIMEText
from settings import env

CONFIDENCE_RANK = {"low": 1, "medium": 2, "high": 3}


def format_message(insight: dict) -> str:
    verdict = "👀 Worth a look" if insight.get("worth_a_look") else "⏭️ Skip this one"
    return (
        f"{verdict} — {insight.get('pair', 'N/A')}\n\n"
        f"{insight['take']}\n\n"
        f"Direction: {insight.get('direction', 'unclear')} | "
        f"Confidence: {insight.get('confidence', 'unknown')}"
    )


def send_telegram(message: str) -> bool:
    try:
        token = env("TELEGRAM_BOT_TOKEN")
        chat_id = env("TELEGRAM_CHAT_ID")
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        resp = requests.post(url, json={"chat_id": chat_id, "text": message}, timeout=10)
        resp.raise_for_status()
        return True
    except Exception as e:
        print(f"[notifier] telegram error: {e}")
        return False


def send_email(subject: str, message: str) -> bool:
    try:
        host = env("SMTP_HOST")
        port = int(env("SMTP_PORT"))
        user = env("SMTP_USER")
        password = env("SMTP_PASS")
        to_addr = env("ALERT_EMAIL_TO")

        msg = MIMEText(message)
        msg["Subject"] = subject
        msg["From"] = user
        msg["To"] = to_addr

        with smtplib.SMTP(host, port) as server:
            server.starttls()
            server.login(user, password)
            server.send_message(msg)
        return True
    except Exception as e:
        print(f"[notifier] email error: {e}")
        return False


def send_sms(message: str) -> bool:
    try:
        sid = env("TWILIO_ACCOUNT_SID")
        token = env("TWILIO_AUTH_TOKEN")
        from_number = env("TWILIO_FROM_NUMBER")
        to_number = env("TWILIO_TO_NUMBER")

        url = f"https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"
        # Twilio SMS has a ~1600 char limit; truncate to be safe
        resp = requests.post(
            url,
            auth=(sid, token),
            data={"From": from_number, "To": to_number, "Body": message[:1500]},
            timeout=10,
        )
        resp.raise_for_status()
        return True
    except Exception as e:
        print(f"[notifier] sms error: {e}")
        return False


def dispatch(insight: dict, cfg: dict):
    """Sends the insight through all enabled channels, respecting the
    min_confidence gate on SMS."""
    message = format_message(insight)
    notif_cfg = cfg["notifications"]

    if notif_cfg["telegram"]["enabled"]:
        send_telegram(message)

    if notif_cfg["email"]["enabled"]:
        send_email(subject=f"Market Alert: {insight.get('pair', 'Trade idea')}", message=message)

    if notif_cfg["sms"]["enabled"]:
        min_conf = CONFIDENCE_RANK[notif_cfg["sms"].get("min_confidence", "high")]
        actual_conf = CONFIDENCE_RANK.get(insight.get("confidence", "low"), 1)
        if actual_conf >= min_conf:
            send_sms(message)
