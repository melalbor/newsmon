"""Integration tests for the newsmon project"""

import pytest
import tempfile
import json
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timezone

from src.main import load_feeds, main
from src.fetch import fetch_feed, fetch_all, FeedFetchError
from src.parse import normalize_feed, _parse_datetime
from src.dedupe import select_new_items


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
        
        # Select new items
        new_items = select_new_items(items, {}, max_items=10)
        assert len(new_items) == 3

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
        new_items = select_new_items(items, {}, max_items=5)
        
        # Limit enforced in single run
        assert len(new_items) == 5

    def test_datetime_parsing_consistency(self):
        """Test datetime parsing is consistent"""
        time_tuple = (2024, 1, 15, 10, 30, 45, 0, 0, 0)
        entry = Mock()
        entry.published_parsed = time_tuple
        entry.updated_parsed = None
        
        dt1 = _parse_datetime(entry)
        dt2 = _parse_datetime(entry)
        
        assert dt1 == dt2
