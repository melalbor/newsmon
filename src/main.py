# src/main.py

import os
import yaml
import time
from src.fetch import fetch_all, FeedFetchError
from src.parse import normalize_feed
from src.dedupe import select_new_items, filter_recent_items, get_past_items, update_state_gist
from src.telegram_msg import send_items, send_admin

from typing import List, Dict, Any


def apply_rules(items: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Return the subset of ``items`` that satisfy any configured rules.

    Each item may have a ``rules`` mapping with optional ``allow`` and
    ``deny`` lists.  ``allow`` acts as a whitelist (at least one keyword must
    be present in the title or summary), while ``deny`` excludes items
    containing any of the deny keywords.  Matching is case‑insensitive
    substring search.
    """
    filtered: List[Dict[str, Any]] = []
    for item in items:
        rules = item.get("rules", {}) or {}
        title = (item.get("title") or "").lower()
        summary = (item.get("summary") or "").lower()
        text = title + " " + summary

        allow = rules.get("allow")
        deny = rules.get("deny")

        if allow:
            # require at least one keyword
            if not any(str(tok).lower() in text for tok in allow):
                continue
        if deny:
            if any(str(tok).lower() in text for tok in deny):
                continue
        filtered.append(item)
    return filtered

FEEDS_FILE_DEFAULT = "feeds.yaml"

# When iterating feeds, we limit the total number of new items posted in a
# single execution so the bot doesn't flood Telegram channels.
MAX_ITEMS_PER_RUN = 10  # avoid flooding TG
PAUSE_BETWEEN_MESSAGES = 0.3  # seconds
MAX_ITEM_AGE_DAYS = 30  # items older than this are ignored


def load_feeds(feeds_file=FEEDS_FILE_DEFAULT):
    """Parse the YAML configuration and return a flattened list of feed
    descriptors.

    The configuration changed recently and now has a structure like::

        topics:
          mobsec:
            channel_id: TG_CHANNEL_MOBSEC
            feeds:
              - url: https://example.com/feed
                rules:
                  allow: ["ios"]
                  deny: ["windows"]
              - url: https://another.example/feed
          cti:
            channel_id: TG_CHANNEL_CTI
            feeds: [ ... ]

    Each returned element is a dict with the following keys:
    ``topic`` (str), ``channel_id`` (str), ``feed_url`` (str) and ``rules``
    (dict containing optional ``allow``/``deny`` lists).

    The ``channel_id`` field holds the **name of an environment variable**
    (for example ``TG_CHANNEL_MOBSEC``) rather than the Telegram chat ID
    itself.  When the bot runs the value of that variable will be looked up
    and used; this keeps sensitive identifiers out of the YAML file.

    The previous behaviour (list of URL strings) is no longer supported.
    """
    with open(feeds_file, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not isinstance(data, dict) or "topics" not in data:
        raise ValueError("feeds.yaml must be a mapping with a top-level 'topics' key")

    topics = data["topics"]
    if not isinstance(topics, dict):
        raise ValueError("'topics' value in feeds.yaml must be a dictionary")

    result = []
    for topic_name, topic_cfg in topics.items():
        if not isinstance(topic_cfg, dict):
            raise ValueError(f"Topic '{topic_name}' definition must be a mapping")
        chan = topic_cfg.get("channel_id")
        if not isinstance(chan, str):
            raise ValueError(
                f"Topic '{topic_name}' must include a string 'channel_id'"
            )
        # ``chan`` is expected to be the *name* of an environment variable,
        # not a literal Telegram id.  We can't resolve it here because the
        # environment may change when the bot is executed.
        feeds = topic_cfg.get("feeds")
        if not isinstance(feeds, list):
            raise ValueError(f"Topic '{topic_name}' feeds must be a list")

        for feed in feeds:
            if isinstance(feed, str):
                feed_url = feed.strip()
                rules = {}
            elif isinstance(feed, dict):
                feed_url = feed.get("url")
                if not isinstance(feed_url, str):
                    raise ValueError(f"Feed in topic '{topic_name}' missing 'url'")
                feed_url = feed_url.strip()
                rules = feed.get("rules", {}) or {}
                if not isinstance(rules, dict):
                    raise ValueError(f"Rules for feed '{feed_url}' must be a mapping")
            else:
                raise ValueError(f"Feed entry in topic '{topic_name}' must be a string or mapping")

            result.append({
                "topic": topic_name,
                "channel_id": chan,
                "feed_url": feed_url,
                "rules": rules,
            })
    if not result:
        raise ValueError("feeds.yaml must define at least one feed")
    return result

def main():
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN")
    channel_id = os.environ.get("TELEGRAM_CHANNEL_ID")
    admin_channel_id = os.environ.get("TELEGRAM_ADMIN_CHANNEL_ID")
    state_gist_id = os.environ.get("STATE_GIST_ID")
    gh_gist_token = os.environ.get("GH_GIST_UPDATE_TOKEN")


    # Allow running without Telegram by making it optional
    has_telegram = bool(bot_token and channel_id and admin_channel_id)
    if not has_telegram:
        print("⚠️  Telegram not configured (missing env vars). Running in dry-run mode.")
    
    if not state_gist_id or not gh_gist_token:
        error_msg = "STATE_GIST_ID and GH_GIST_UPDATE_TOKEN must be set."
        print(f"✗ {error_msg}")
        if has_telegram:
            send_admin(bot_token, admin_channel_id, error_msg)
        return

    feeds = load_feeds()
    all_items = []

    # Step 1: Fetch and parse feeds.  We keep metadata (topic/channel/rules)
    for cfg in feeds:
        feed_url = cfg["feed_url"]
        try:
            parsed = fetch_all([feed_url])[feed_url]
            items = normalize_feed(parsed, feed_url)

            # attach metadata so later stages know which channel and rules apply
            for item in items:
                item["channel_id"] = cfg["channel_id"]
                item["rules"] = cfg.get("rules", {})
                item["topic"] = cfg.get("topic")

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

    # apply allow/deny rules before we do any further processing
    before_rules = len(all_items)
    all_items = apply_rules(all_items)
    if len(all_items) < before_rules:
        print(f"Items after rule filtering: {len(all_items)} (dropped {before_rules - len(all_items)})")

    # Step 1.5: Filter out items older than MAX_ITEM_AGE_DAYS
    recent_items = filter_recent_items(all_items, max_age_days=MAX_ITEM_AGE_DAYS)
    print(f"Items after age filter (< {MAX_ITEM_AGE_DAYS} days): {len(recent_items)}")
    if len(recent_items) < len(all_items):
        print(f"  (Dropped {len(all_items) - len(recent_items)} old items)")

    if not recent_items:
        error_msg = "No recent items to process."
        print(error_msg)
        if has_telegram:
            send_admin(bot_token, admin_channel_id, error_msg)
        return

    # Step 2: Dedupe and enforce cap
    gist_filename, past_items = get_past_items(state_gist_id, gh_gist_token)
    known_items = dict(past_items) # this will be incremented w/ new items later on.
    new_items = select_new_items(recent_items, past_items, max_items=MAX_ITEMS_PER_RUN)

    if not new_items:
        error_msg = "No new items to send."
        print(error_msg)
        if has_telegram:
            send_admin(bot_token, admin_channel_id, error_msg)
        return

    # Optional overflow warning - never happens since select_new_items caps it.
    #if len(recent_items) > MAX_ITEMS_PER_RUN:
    #    overflow_msg = f"Overflow: {len(recent_items)} new items, posting {MAX_ITEMS_PER_RUN} now."
    #    print(f"⚠️  {overflow_msg}")
    #    if has_telegram:
    #        send_admin(bot_token, admin_channel_id, overflow_msg)

    print(f"New items after dedup: {len(new_items)}")

    # Step 3: Send items to Telegram (if configured).  Items may go to
    # different channels depending on their topic.  In the feed configuration
    # the ``channel_id`` field is actually the name of an environment
    # variable holding the real chat id.  We resolve that here when grouping
    # items, falling back to the generic TELEGRAM_CHANNEL_ID if necessary.
    if has_telegram:
        # group items by actual chat id
        items_by_channel: dict[str, list] = {}
        for item in new_items:
            envname = item["channel_id"]
            # look up the variable; if it's not set use the fallback
            chat = os.environ.get(envname) or os.environ.get("TELEGRAM_CHANNEL_ID")
            if not chat:
                # We don't have a valid chat id; report and skip
                err = f"channel environment variable {envname} not set"
                print(f"✗ {err}")
                send_admin(bot_token, admin_channel_id, err)
                continue
            items_by_channel.setdefault(chat, []).append(item)

        try:
            for chat, items in items_by_channel.items():
                send_items(bot_token, chat, items, pause_sec=PAUSE_BETWEEN_MESSAGES)

            # update state once everything is successfully posted
            for item in new_items:
                if item['title'] not in known_items.get(item['feed_url'], []):
                    known_items.setdefault(item['feed_url'], []).append(item['title'])
            update_state_gist(state_gist_id, gh_gist_token, gist_filename, known_items)
            print(f"✓ Sent {len(new_items)} items to Telegram across {len(items_by_channel)} channel(s)")
        except Exception as e:
            error_msg = f"Telegram send failure: {e}"
            print(f"✗ {error_msg}")
            send_admin(bot_token, admin_channel_id, error_msg)
            print("Failed to send items. Exiting without marking as seen.")
            return
    else:
        print(f"[DRY RUN] Would send {len(new_items)} items to Telegram")

    status = "Successfully sent" if has_telegram else "Successfully processed (dry-run)"
    print(f"{status} {len(new_items)} items.")


if __name__ == "__main__":
    main()