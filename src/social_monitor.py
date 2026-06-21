"""
Monitors statements from market-moving public figures (Trump, and anyone
else added to config.yaml). Merges two free sources:

1. Truth Social mirror site (no API key, polls a public feed/RSS-like JSON)
2. NewsAPI mentions (fallback/cross-check -- works for any figure, not just
   people who post on Truth Social)

Posts/mentions are deduped and filtered by relevance_keywords before being
passed downstream to the analyzer.
"""
import requests
import feedparser
from settings import env

_seen_ids = set()  # dedup across polling cycles (resets on process restart)


def _is_relevant(text: str, keywords: list[str]) -> bool:
    text_lower = text.lower()
    return any(kw.lower() in text_lower for kw in keywords)


def fetch_truth_social_mirror(url: str) -> list[dict]:
    """Polls a free Truth Social mirror feed (RSS-style). These mirror sites
    can go down or change format -- wrap in try/except upstream and treat
    failures as non-fatal; news_mentions fallback still covers you."""
    posts = []
    try:
        feed = feedparser.parse(url)
        for entry in feed.entries[:20]:
            posts.append({
                "id": entry.get("id", entry.get("link")),
                "text": entry.get("title", "") + " " + entry.get("summary", ""),
                "url": entry.get("link"),
                "published": entry.get("published", None),
            })
    except Exception as e:
        print(f"[social_monitor] truth_social_mirror error: {e}")
    return posts


def fetch_news_mentions(query: str) -> list[dict]:
    """NewsAPI fallback -- catches statements reported on by the press even
    if the direct source feed is down or the figure doesn't use Truth Social."""
    posts = []
    try:
        api_key = env("NEWSAPI_KEY")
        url = "https://newsapi.org/v2/everything"
        params = {
            "q": query,
            "sortBy": "publishedAt",
            "pageSize": 15,
            "apiKey": api_key,
        }
        resp = requests.get(url, params=params, timeout=10)
        resp.raise_for_status()
        for article in resp.json().get("articles", []):
            posts.append({
                "id": article.get("url"),
                "text": (article.get("title") or "") + " " + (article.get("description") or ""),
                "url": article.get("url"),
                "published": article.get("publishedAt"),
            })
    except Exception as e:
        print(f"[social_monitor] news_mentions error: {e}")
    return posts


def check_figures(cfg: dict) -> list[dict]:
    """Returns new, relevant, deduped posts/mentions for all configured figures."""
    relevant_hits = []

    for figure in cfg.get("figures", []):
        if figure.get("enabled", True) is False:
            continue
        name = figure["name"]
        keywords = figure.get("relevance_keywords", [])
        merged_posts = []

        for source in figure.get("sources", []):
            if source["type"] == "truth_social_mirror":
                merged_posts.extend(fetch_truth_social_mirror(source["url"]))
            elif source["type"] == "news_mentions":
                merged_posts.extend(fetch_news_mentions(source["query"]))

        for post in merged_posts:
            post_id = post.get("id")
            if not post_id or post_id in _seen_ids:
                continue
            _seen_ids.add(post_id)

            if not keywords or _is_relevant(post["text"], keywords):
                relevant_hits.append({
                    "figure": name,
                    "text": post["text"].strip(),
                    "url": post.get("url"),
                    "published": post.get("published"),
                })

    return relevant_hits


if __name__ == "__main__":
    from settings import load_config
    cfg = load_config()
    print(check_figures(cfg))
