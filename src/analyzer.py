"""
Sends merged signals (price spikes, figure statements, news, calendar
events) to Claude for synthesis into a structured, human-readable insight
with a confidence rating. Confidence rating drives which notification
channels fire (e.g. SMS reserved for high-confidence only).
"""
import json
import requests
from settings import env

MODEL = "claude-sonnet-4-6"


def _get_base_url() -> str:
    """Defaults to the official Anthropic API. Set ANTHROPIC_BASE_URL in .env
    to point at a different endpoint (e.g. AgentRouter) instead."""
    import os
    return os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com").rstrip("/")

SYSTEM_PROMPT = """You are a market-monitoring analyst assistant. You will be \
given raw signals: price/volume spikes, statements from market-moving public \
figures, news headlines, and upcoming high-impact economic calendar events.

Your job: identify whether there is a plausible, explainable connection \
between these signals, and give ONE clear bottom-line take. The person reading \
this does not want a pile of data to sift through -- they want your honest \
read, stated plainly, so they can decide for themselves whether to act.

You are not a licensed financial advisor and this is not formal financial \
advice -- give your honest analytical take anyway, the way an experienced \
trader would size up a setup for a colleague: direct, no hedging filler, but \
not falsely certain either. If the setup is weak or unclear, say so plainly \
instead of dressing it up.

Respond ONLY with valid JSON, no preamble, no markdown fences, matching this \
schema exactly:
{
  "pair": "the affected forex pair, e.g. USDJPY",
  "take": "your honest bottom-line read in 1-2 plain sentences -- worth a look, \
not worth it, too early to tell, etc. -- and why, in everyday language",
  "direction": "up" | "down" | "unclear",
  "worth_a_look": true | false,
  "confidence": "low" | "medium" | "high",
  "is_noteworthy": true | false
}

Set is_noteworthy to false if the signals are too weak, unrelated, or routine \
to be worth alerting a person about. Be conservative -- false positives waste \
the user's attention and erode trust in the tool. Do not invent connections \
that aren't supported by the data given.
"""


def analyze_signals(price_spikes: list[dict], figure_hits: list[dict],
                     calendar_events: list[dict]) -> dict | None:
    if not price_spikes and not figure_hits and not calendar_events:
        return None

    payload = {
        "price_spikes": price_spikes,
        "figure_statements": figure_hits,
        "upcoming_calendar_events": [
            {**e, "time": e["time"].isoformat()} for e in calendar_events
        ],
    }

    api_key = env("ANTHROPIC_API_KEY")
    url = f"{_get_base_url()}/v1/messages"
    resp = requests.post(
        url,
        headers={
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json",
        },
        json={
            "model": MODEL,
            "max_tokens": 500,
            "system": SYSTEM_PROMPT,
            "messages": [
                {"role": "user", "content": json.dumps(payload, default=str)}
            ],
        },
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()

    text_blocks = [b["text"] for b in data.get("content", []) if b.get("type") == "text"]
    raw_text = "".join(text_blocks).strip()
    raw_text = raw_text.removeprefix("```json").removeprefix("```").removesuffix("```").strip()

    try:
        result = json.loads(raw_text)
    except json.JSONDecodeError:
        print(f"[analyzer] failed to parse model output: {raw_text}")
        return None

    return result


if __name__ == "__main__":
    # quick manual test with fake data
    fake_spike = [{"symbol": "bitcoin", "pct_change": 4.2, "direction": "up"}]
    fake_statement = [{"figure": "Donald Trump", "text": "Announcing new tariffs on China tomorrow."}]
    print(analyze_signals(fake_spike, fake_statement, []))
