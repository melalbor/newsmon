# src/dedupe.py

import hashlib
from typing import Dict, List, Any
from datetime import datetime, timezone, timedelta

def is_recent(item: Dict[str, Any], days: int = 7) -> bool:
    """
    Check if an item was published within the last N days.
    Items without a published date are considered recent.
    """
    if not item.get("published"):
        return True  # Include items with no date
    
    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=days)
    return item["published"] >= cutoff

def filter_recent_items(
    items: List[Dict[str, Any]],
    max_age_days: int = 7,
) -> List[Dict[str, Any]]:
    """
    Filter out items older than max_age_days.
    Returns list of recent items.
    """
    return [item for item in items if is_recent(item, max_age_days)]

def fingerprint(item: Dict[str, Any]) -> str:
    """
    Generate a stable fingerprint for an item.
    Priority:
    1. item['id']
    2. item['link']
    3. title + link
    """
    raw = (
        item.get("id")
        or item.get("link")
        or f"{item.get('title')}|{item.get('link')}"
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

def select_new_items(
    items: List[Dict[str, Any]],
    state: Dict[str, Any],
    max_items: int = 10,
) -> List[Dict[str, Any]]:
    """
    Returns a list of new items to send (capped).
    Since state is ephemeral (in-memory only), this function primarily
    applies per-run deduplication within the same fetch cycle.
    """

    feeds_state = state.setdefault("feeds", {})
    selected = []
    seen_fingerprints = set()  # Track within this run

    # Group items by feed
    items_by_feed: Dict[str, List[Dict[str, Any]]] = {}
    for item in items:
        items_by_feed.setdefault(item["feed_url"], []).append(item)

    for feed_url, feed_items in items_by_feed.items():
        feed_state = feeds_state.setdefault(
            feed_url,
            {"seen": []},
        )

        # Sort oldest → newest
        feed_items.sort(
            key=lambda x: x["published"] or 0
        )

        for item in feed_items:
            if len(selected) >= max_items:
                break

            fp = fingerprint(item)
            if fp in seen_fingerprints:
                continue

            # Mark as selected for this run
            item["_fingerprint"] = fp
            selected.append(item)
            seen_fingerprints.add(fp)

        if len(selected) >= max_items:
            break

    return selected
