"""
Scrapes ForexFactory's calendar for high/medium impact ("red folder" /
"orange folder") economic events. No API key needed -- public page.

ForexFactory doesn't offer a clean free API, so this parses their calendar
JSON endpoint that powers their own front-end widget. If this breaks (they
do change markup occasionally), fall back to scraping the HTML calendar
page directly -- structure noted in comments below.
"""
import requests
from datetime import datetime, timedelta

IMPACT_RANK = {"low": 1, "medium": 2, "high": 3}

# ForexFactory exposes a JSON feed used by their embeddable calendar widget.
CALENDAR_JSON_URL = "https://nfs.faireconomy.media/ff_calendar_thisweek.json"


def fetch_calendar_events() -> list[dict]:
    """Returns this week's events as parsed dicts. Falls back to an empty
    list (logged, non-fatal) if the feed is unreachable so the rest of the
    pipeline keeps running."""
    try:
        resp = requests.get(CALENDAR_JSON_URL, timeout=10)
        resp.raise_for_status()
        raw_events = resp.json()
    except Exception as e:
        print(f"[calendar_monitor] fetch error: {e}")
        return []

    events = []
    for e in raw_events:
        impact = (e.get("impact") or "").lower()
        if impact not in IMPACT_RANK:
            continue
        try:
            event_time = datetime.fromisoformat(e["date"].replace("Z", "+00:00"))
        except Exception:
            continue
        events.append({
            "title": e.get("title"),
            "country": e.get("country"),
            "impact": impact,
            "time": event_time,
            "forecast": e.get("forecast"),
            "previous": e.get("previous"),
        })
    return events


def upcoming_alerts(cfg: dict) -> list[dict]:
    """Returns events that are within pre_alert_minutes of starting and meet
    the configured minimum impact threshold."""
    min_impact = IMPACT_RANK[cfg["calendar"]["min_impact"]]
    pre_alert_minutes = cfg["calendar"]["pre_alert_minutes"]
    now = datetime.now(tz=None).astimezone()

    alerts = []
    for event in fetch_calendar_events():
        if IMPACT_RANK[event["impact"]] < min_impact:
            continue
        minutes_until = (event["time"] - now).total_seconds() / 60
        if 0 <= minutes_until <= pre_alert_minutes:
            alerts.append(event)
    return alerts


if __name__ == "__main__":
    from settings import load_config
    cfg = load_config()
    print(upcoming_alerts(cfg))
