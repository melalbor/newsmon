# src/fetch.py

import requests
import feedparser

DEFAULT_TIMEOUT = 10


class FeedFetchError(Exception):
    pass


def fetch_feed(url: str, timeout: int = DEFAULT_TIMEOUT):
    try:
        resp = requests.get(
            url,
            timeout=timeout,
            headers={
                "User-Agent": "rss-telegram-bot/0.1"
            },
        )
        resp.raise_for_status()
    except requests.RequestException as e:
        raise FeedFetchError(f"HTTP error fetching {url}: {e}") from e

    parsed = feedparser.parse(resp.content)

    # feedparser sets bozo flag if parsing failed
    if parsed.bozo:
        raise FeedFetchError(
            f"Failed to parse feed {url}: {parsed.bozo_exception}"
        )

    return parsed


def fetch_all(feed_urls: list[str]) -> dict[str, object]:
    results = {}

    for url in feed_urls:
        results[url] = fetch_feed(url)

    return results