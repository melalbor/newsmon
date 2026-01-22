# src/parse.py

from datetime import datetime, timezone
from typing import List, Dict, Any


def _parse_datetime(entry) -> datetime | None:
    """
    Convert feedparser time structs to datetime (UTC).
    """
    if hasattr(entry, "published_parsed") and entry.published_parsed:
        return datetime.fromtimestamp(
            int(datetime(*entry.published_parsed[:6]).timestamp()),
            tz=timezone.utc,
        )
    if hasattr(entry, "updated_parsed") and entry.updated_parsed:
        return datetime.fromtimestamp(
            int(datetime(*entry.updated_parsed[:6]).timestamp()),
            tz=timezone.utc,
        )
    return None


def normalize_feed(parsed_feed, feed_url: str) -> List[Dict[str, Any]]:
    feed_title = parsed_feed.feed.get("title", feed_url)

    items = []

    for entry in parsed_feed.entries:
        link = entry.get("link")
        title = entry.get("title")

        # Hard requirements
        if not link or not title:
            continue

        item = {
            "feed_url": feed_url,
            "feed_title": feed_title,
            "id": entry.get("id") or entry.get("guid"),
            "link": link,
            "title": title.strip(),
            "published": _parse_datetime(entry),
            "summary": entry.get("summary"),
        }

        items.append(item)

    return items