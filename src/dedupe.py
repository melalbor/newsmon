# src/dedupe.py

import hashlib
import requests
import json
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

def select_new_items(
    items: List[Dict[str, Any]],
    past_items: Dict[str, List[str]],
    max_items: int = 10,
) -> List[Dict[str, Any]]:
    """
    Returns a list of new items to send (capped).
    Items are considered new if their title is not in past_items for their feed.
    """

    selected = []

    # Group items by feed
    items_by_feed: Dict[str, List[Dict[str, Any]]] = {}
    for item in items:
        items_by_feed.setdefault(item["feed_url"], []).append(item)

    for feed_url, feed_items in items_by_feed.items():

        # Sort oldest → newest
        feed_items.sort(
            key=lambda x: x["published"] or 0
        )

        for item in feed_items:
            if len(selected) >= max_items:
                break

            if item.get("title") in past_items.get(feed_url, []):
                continue

            # Mark as selected for this run
            selected.append(item)

        if len(selected) >= max_items:
            break

    return selected

def get_past_items(gist_id: str, gh_token: str) -> tuple[str, Dict[str, List[str]]]:
    """
    Returns past item titles from state gist.
    """
    headers = {
        "Authorization": f"token {gh_token}",
        "Accept": "application/vnd.github+json"
    }

    url = f"https://api.github.com/gists/{gist_id}"
    resp = requests.get(url, headers=headers)
    resp.raise_for_status()

    gist = resp.json()

    filename = next(iter(gist["files"]))
    content = gist["files"][filename]["content"]
    data = json.loads(content)
    return filename, data

def update_state_gist(gist_id: str, gh_token: str, filename: str, updated_data: Dict[str, List[str]]):
    """"
    Update state gist with new data.
    """
    headers = {
        "Authorization": f"token {gh_token}",
        "Accept": "application/vnd.github+json"
    }
    url = f"https://api.github.com/gists/{gist_id}"
    if not updated_data:
        return  # Nothing to update
    
    payload = {
        "files": {
            filename: {
                "content": json.dumps(updated_data, indent=2)
            }
        }
    }
    try:
        response = requests.patch(url, headers=headers, json=payload)
        response.raise_for_status()
    except requests.RequestException as e:
        raise RuntimeError(f"Failed to update gist: {e}")