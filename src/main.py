"""
Main loop. Polls price, social/figure, news, and calendar signals on their
own cadences, runs anything new through the Claude analyzer, and dispatches
notifications for noteworthy insights.

Run with: python src/main.py
Deploy as a systemd service or `nohup python src/main.py &` on your server
for true always-on behavior. See README for a systemd unit example.
"""
import time
import traceback
from datetime import datetime

from settings import load_config
import price_monitor
import social_monitor
import calendar_monitor
import analyzer
import notifier

# Track last-run timestamps so each signal type polls on its own cadence
_last_run = {"price": 0, "social": 0, "calendar": 0}


def _due(key: str, interval_minutes: int) -> bool:
    return (time.time() - _last_run[key]) >= interval_minutes * 60


def run_cycle(cfg: dict):
    price_spikes = []
    figure_hits = []
    calendar_alerts = []

    if _due("price", cfg["polling"]["price_check_minutes"]):
        price_spikes = price_monitor.run_price_checks(cfg)
        _last_run["price"] = time.time()
        if price_spikes:
            print(f"[{datetime.now()}] price spikes: {price_spikes}")

    if _due("social", cfg["polling"]["social_check_minutes"]):
        figure_hits = social_monitor.check_figures(cfg)
        _last_run["social"] = time.time()
        if figure_hits:
            print(f"[{datetime.now()}] figure statements: {figure_hits}")

    if _due("calendar", cfg["polling"]["calendar_check_minutes"]):
        calendar_alerts = calendar_monitor.upcoming_alerts(cfg)
        _last_run["calendar"] = time.time()
        if calendar_alerts:
            print(f"[{datetime.now()}] calendar alerts: {calendar_alerts}")

    if not (price_spikes or figure_hits or calendar_alerts):
        return  # nothing new, skip the analyzer call to save API spend

    insight = analyzer.analyze_signals(price_spikes, figure_hits, calendar_alerts)
    if insight and insight.get("is_noteworthy"):
        print(f"[{datetime.now()}] NOTEWORTHY INSIGHT: {insight}")
        notifier.dispatch(insight, cfg)
    elif insight:
        print(f"[{datetime.now()}] insight generated but not noteworthy, skipping alert")


def main():
    cfg = load_config()
    print("Market monitor starting. Press Ctrl+C to stop.")
    while True:
        try:
            run_cycle(cfg)
        except Exception:
            print("[main] unhandled error in cycle:")
            traceback.print_exc()
        time.sleep(30)  # base tick -- individual signals still respect their own cadence


if __name__ == "__main__":
    main()
