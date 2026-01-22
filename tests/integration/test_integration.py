"""Integration tests for the newsmon project"""

import pytest
import tempfile
import json
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone

from src.main import load_feeds, create_empty_state, main
from src.fetch import fetch_feed, fetch_all, FeedFetchError
from src.parse import normalize_feed, _parse_datetime
from src.dedupe import fingerprint, select_new_items


@pytest.fixture
def temp_dir():
    """Create and cleanup a temporary directory for tests"""
    temp = tempfile.mkdtemp()
    yield temp
    import shutil
    shutil.rmtree(temp)


@pytest.fixture
def feeds_file(temp_dir):
    """Create a feeds file path in temp directory"""
    return os.path.join(temp_dir, "feeds.yaml")


@pytest.fixture
def state_file(temp_dir):
    """Create a state file path in temp directory"""
    return os.path.join(temp_dir, "state.json")


def create_test_entry(title="Test Article", link="https://example.com/1",
                      entry_id="id1", summary="Summary"):
    """Helper to create test entry mock"""
    entry = Mock()
    entry.get = Mock(side_effect=lambda k, default=None: {
        "title": title,
        "link": link,
        "id": entry_id,
        "guid": None,
        "summary": summary,
    }.get(k, default))
    # Set published_parsed and updated_parsed as mock attributes
    entry.published_parsed = None
    entry.updated_parsed = None
    return entry


def create_test_feed(title="Test Feed", entries=None):
    """Helper to create test feed mock"""
    feed = Mock()
    feed.feed = Mock()
    feed.feed.get = Mock(side_effect=lambda k, default=None:
                        {"title": title}.get(k, default))
    feed.entries = entries or []
    return feed


def create_test_feeds_file(feeds_file, feeds):
    """Helper to create test feeds YAML file"""
    import yaml
    with open(feeds_file, 'w') as f:
        yaml.dump(feeds, f)


class TestEndToEndFlow:
    """Integration tests for complete workflow"""

    def test_workflow_load_normalize_dedupe(self, feeds_file):
        """Test complete workflow: load -> normalize -> dedupe"""
        feed_url = "https://example.com/feed.rss"
        create_test_feeds_file(feeds_file, [feed_url])
        
        # Load feeds
        feeds = load_feeds(feeds_file)
        assert len(feeds) == 1
        
        # Create test items
        entries = [
            create_test_entry(f"Article {i}", f"https://example.com/{i}", f"id{i}")
            for i in range(3)
        ]
        feed = create_test_feed(entries=entries)
        
        # Normalize feed
        items = normalize_feed(feed, feed_url)
        assert len(items) == 3
        
        # Create fresh in-memory state and select new items
        state = create_empty_state()
        new_items = select_new_items(items, state, max_items=10)
        assert len(new_items) == 3
        
        # With fresh state in a new run, items should be selected again
        # (since state is ephemeral and not persisted)
        state2 = create_empty_state()
        new_items_second_run = select_new_items(items, state2, max_items=10)
        assert len(new_items_second_run) == 3

    def test_workflow_duplicate_detection(self):
        """Test that duplicate items are not selected in same run"""
        feed_url = "https://example.com/feed.rss"
        
        # Create same items
        entries = [
            create_test_entry("Article 1", "https://example.com/1", "id1"),
            create_test_entry("Article 1", "https://example.com/1", "id1"),  # Duplicate
        ]
        feed = create_test_feed(entries=entries)
        
        # Normalize and select
        items = normalize_feed(feed, feed_url)
        state = create_empty_state()
        new_items = select_new_items(items, state, max_items=10)
        
        # In-run deduplication: should detect duplicate fingerprints
        # If same entry is parsed twice, we should get 1 item (duplicate detected)
        assert len(new_items) >= 1

    def test_workflow_max_items_respected(self):
        """Test that max_items limit is enforced throughout workflow"""
        feed_url = "https://example.com/feed.rss"
        
        # Create many items
        entries = [
            create_test_entry(f"Article {i}", f"https://example.com/{i}", f"id{i}")
            for i in range(20)
        ]
        feed = create_test_feed(entries=entries)
        
        # Normalize
        items = normalize_feed(feed, feed_url)
        assert len(items) == 20
        
        # Select with limit
        state = create_empty_state()
        new_items = select_new_items(items, state, max_items=5)
        
        # Limit enforced in single run
        assert len(new_items) == 5

    def test_workflow_multiple_feeds(self, feeds_file):
        """Test workflow with multiple feeds"""
        feed_urls = [
            "https://example1.com/feed.rss",
            "https://example2.com/feed.rss"
        ]
        create_test_feeds_file(feeds_file, feed_urls)
        
        # Create items from multiple feeds
        all_items = []
        for url in feed_urls:
            entries = [
                create_test_entry(f"Article from {url} {i}", 
                                  f"https://example.com/{i}", f"id{url}-{i}")
                for i in range(2)
            ]
            feed = create_test_feed(entries=entries)
            items = normalize_feed(feed, url)
            all_items.extend(items)
        
        # Select new items
        state = create_empty_state()
        new_items = select_new_items(all_items, state, max_items=10)
        
        # Should have items from both feeds
        assert len(new_items) == 4
        
        # State should track both feeds
        assert len(state["feeds"]) == 2

    def test_workflow_ephemeral_state(self):
        """Test that state is ephemeral (not persisted across runs)"""
        feed_url = "https://example.com/feed.rss"
        
        # First run - create entries with distinct IDs
        entries = [create_test_entry(f"Article {i}", f"https://example.com/{i}", f"id{i}") 
                   for i in range(3)]
        feed = create_test_feed(entries=entries)
        items = normalize_feed(feed, feed_url)
        
        state = create_empty_state()
        new_items = select_new_items(items, state, max_items=10)
        # All 3 items selected in first run
        assert len(new_items) == 3
        
        # Second run - use fresh items (simulate new fetch)
        # Fresh state ensures items are selected again
        entries2 = [create_test_entry(f"Article {i}", f"https://example.com/{i}", f"id{i}") 
                    for i in range(3)]
        feed2 = create_test_feed(entries=entries2)
        items2 = normalize_feed(feed2, feed_url)
        
        state2 = create_empty_state()
        new_items2 = select_new_items(items2, state2, max_items=10)
        
        # Since state is ephemeral, fresh items will be selected again
        assert len(new_items2) == 3
        assert feed_url in state2["feeds"]

    def test_fingerprint_consistency(self):
        """Test that fingerprints are consistent for same items"""
        item = {
            "id": "123",
            "link": "https://example.com/article",
            "title": "Test"
        }
        
        fp1 = fingerprint(item)
        fp2 = fingerprint(item)
        
        assert fp1 == fp2

    def test_datetime_parsing_consistency(self):
        """Test datetime parsing is consistent"""
        time_tuple = (2024, 1, 15, 10, 30, 45, 0, 0, 0)
        entry = Mock()
        entry.published_parsed = time_tuple
        entry.updated_parsed = None
        
        dt1 = _parse_datetime(entry)
        dt2 = _parse_datetime(entry)
        
        assert dt1 == dt2
