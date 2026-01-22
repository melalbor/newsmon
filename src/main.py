# src/main.py

import os
import yaml
import time
from src.fetch import fetch_all, FeedFetchError
from src.parse import normalize_feed
from src.dedupe import select_new_items, filter_recent_items
from src.telegram_msg import send_items, send_admin

FEEDS_FILE_DEFAULT = "feeds.yaml"

MAX_ITEMS_PER_RUN = 10
PAUSE_BETWEEN_MESSAGES = 0.3  # seconds
# Allow override via TEST_MODE_RELAXED_AGE env var for testing purposes
MAX_ITEM_AGE_DAYS = int(os.environ.get("TEST_MODE_RELAXED_AGE", "1"))  # Default 24h, can be 3+ for testing


def load_feeds(feeds_file=FEEDS_FILE_DEFAULT):
    with open(feeds_file, "r", encoding="utf-8") as f:
        feeds_config = yaml.safe_load(f)
    # Expecting list of URLs
    if not isinstance(feeds_config, list):
        raise ValueError("feeds.yaml must be a list of feed URLs")
    return feeds_config


def create_empty_state():
    """Create an empty in-memory state object for deduplication."""
    return {"version": 1, "feeds": {}}


def main():
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    channel_id = os.environ.get("TELEGRAM_CHANNEL_ID")
    admin_channel_id = os.environ.get("TELEGRAM_ADMIN_CHANNEL_ID")

    # Allow running without Telegram by making it optional
    has_telegram = bool(bot_token and channel_id and admin_channel_id)
    if not has_telegram:
        print("⚠️  Telegram not configured (missing env vars). Running in dry-run mode.")

    feeds = load_feeds()
    state = create_empty_state()  # Fresh in-memory state for this run
    all_items = []

    # Step 1: Fetch and parse feeds
    for feed_url in feeds:
        try:
            parsed = fetch_all([feed_url])[feed_url]
            items = normalize_feed(parsed, feed_url)
            all_items.extend(items)
            print(f"✓ Fetched {len(items)} items from {feed_url}")
        except FeedFetchError as e:
            error_msg = f"Failed to fetch {feed_url}: {e}"
            print(f"✗ {error_msg}")
            if has_telegram:
                send_admin(bot_token, admin_channel_id, error_msg)
            continue
        except Exception as e:
            error_msg = f"Unexpected error {feed_url}: {e}"
            print(f"✗ {error_msg}")
            if has_telegram:
                send_admin(bot_token, admin_channel_id, error_msg)
            continue

    if not all_items:
        print("No items fetched.")
        return

    print(f"Total items fetched: {len(all_items)}")

    # Step 1.5: Filter out items older than MAX_ITEM_AGE_DAYS
    recent_items = filter_recent_items(all_items, max_age_days=MAX_ITEM_AGE_DAYS)
    print(f"Items after age filter (< {MAX_ITEM_AGE_DAYS} days): {len(recent_items)}")
    if len(recent_items) < len(all_items):
        print(f"  (Dropped {len(all_items) - len(recent_items)} old items)")

    if not recent_items:
        print("No recent items to process.")
        return

    # Step 2: Dedupe and enforce cap
    new_items = select_new_items(recent_items, state, max_items=MAX_ITEMS_PER_RUN)

    if not new_items:
        print("No new items to send.")
        return

    print(f"New items after dedup: {len(new_items)}")

    # Optional overflow warning
    if len(new_items) >= MAX_ITEMS_PER_RUN:
        overflow_msg = f"Overflow: {len(all_items)} new items, posting {MAX_ITEMS_PER_RUN} now."
        print(f"⚠️  {overflow_msg}")
        if has_telegram:
            send_admin(bot_token, admin_channel_id, overflow_msg)

    # Step 3: Send items to Telegram (if configured)
    if has_telegram:
        try:
            send_items(bot_token, channel_id, new_items, pause_sec=PAUSE_BETWEEN_MESSAGES)
            print(f"✓ Sent {len(new_items)} items to Telegram")
        except Exception as e:
            error_msg = f"Telegram send failure: {e}"
            print(f"✗ {error_msg}")
            send_admin(bot_token, admin_channel_id, error_msg)
            print("Failed to send items. Exiting without marking as seen.")
            return
    else:
        print(f"[DRY RUN] Would send {len(new_items)} items to Telegram")

    # Note: State is not persisted (in-memory only for this run)
    # This ensures fresh deduplication on each run and avoids state file management
    status = "Successfully sent" if has_telegram else "Successfully processed (dry-run)"
    print(f"{status} {len(new_items)} items.")


if __name__ == "__main__":
    main()