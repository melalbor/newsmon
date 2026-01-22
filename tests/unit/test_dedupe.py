"""Unit tests for dedupe.py module"""

import pytest
from datetime import datetime, timezone, timedelta
from src.dedupe import fingerprint, select_new_items, is_recent, filter_recent_items


class TestFingerprint:
    """Test fingerprint function"""

    def test_fingerprint_with_id(self):
        """Test fingerprint using item id"""
        item = {
            "id": "article-123",
            "link": "https://example.com/article",
            "title": "Test Article"
        }
        
        fp = fingerprint(item)
        
        assert isinstance(fp, str)
        assert len(fp) == 64  # SHA256 hex digest length

    def test_fingerprint_consistency(self):
        """Test that same item produces same fingerprint"""
        item = {
            "id": "article-123",
            "link": "https://example.com/article",
            "title": "Test Article"
        }
        
        fp1 = fingerprint(item)
        fp2 = fingerprint(item)
        
        assert fp1 == fp2

    def test_fingerprint_with_link_fallback(self):
        """Test fingerprint falls back to link when id is None"""
        item = {
            "id": None,
            "link": "https://example.com/article",
            "title": "Test Article"
        }
        
        fp = fingerprint(item)
        
        assert isinstance(fp, str)
        assert len(fp) == 64

    def test_fingerprint_with_title_link_fallback(self):
        """Test fingerprint falls back to title+link when both id and link missing"""
        item = {
            "id": None,
            "link": None,
            "title": "Test Article"
        }
        
        fp = fingerprint(item)
        
        assert isinstance(fp, str)
        assert len(fp) == 64

    def test_fingerprint_different_for_different_items(self):
        """Test that different items produce different fingerprints"""
        item1 = {"id": "123", "link": None, "title": None}
        item2 = {"id": "456", "link": None, "title": None}
        
        fp1 = fingerprint(item1)
        fp2 = fingerprint(item2)
        
        assert fp1 != fp2


class TestSelectNewItems:
    """Test select_new_items function"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test fixtures"""
        self.feed_url = "https://example.com/feed"
        self.state = {"version": 1, "feeds": {}}

    def _create_item(self, title="Article", feed_url=None, item_id="id1", 
                    published=None):
        """Helper to create an item"""
        return {
            "title": title,
            "link": f"https://example.com/{item_id}",
            "feed_url": feed_url or self.feed_url,
            "feed_title": "Test Feed",
            "id": item_id,
            "published": published,
            "summary": "Summary"
        }

    def test_select_new_items_basic(self):
        """Test selecting new items from state"""
        items = [self._create_item(item_id=str(i)) for i in range(3)]
        
        result = select_new_items(items, self.state, max_items=10)
        
        assert len(result) == 3

    def test_select_new_items_respects_max(self):
        """Test that max_items limit is respected"""
        items = [self._create_item(item_id=str(i)) for i in range(20)]
        
        result = select_new_items(items, self.state, max_items=5)
        
        assert len(result) == 5

    def test_select_new_items_deduplicates_within_run(self):
        """Test that duplicate items within same run are deduped"""
        # Create items with same fingerprint (same ID)
        items = [
            self._create_item(item_id="same-id", title="Item 1"),
            self._create_item(item_id="same-id", title="Item 1 duplicate"),
        ]
        
        # First pass - both have same fingerprint
        result1 = select_new_items(items, self.state, max_items=10)
        # Only one should be selected (in-run dedup)
        assert len(result1) == 1
        
        # Fresh state (ephemeral) - items would be selected again if same items provided
        fresh_state = {"version": 1, "feeds": {}}
        result2 = select_new_items(items, fresh_state, max_items=10)
        # With fresh state, same items selected again (no cross-run memory)
        assert len(result2) == 1

    def test_select_new_items_fingerprint_added(self):
        """Test that _fingerprint is added to selected items"""
        items = [self._create_item()]
        
        result = select_new_items(items, self.state, max_items=10)
        
        assert "_fingerprint" in result[0]
        assert len(result[0]["_fingerprint"]) == 64

    def test_select_new_items_initializes_feed_state(self):
        """Test that feed state is initialized"""
        items = [self._create_item()]
        initial_state = {"version": 1, "feeds": {}}
        
        select_new_items(items, initial_state, max_items=10)
        
        assert self.feed_url in initial_state["feeds"]
        assert "seen" in initial_state["feeds"][self.feed_url]

    def test_select_new_items_multiple_feeds(self):
        """Test selecting items from multiple feeds"""
        items = [
            self._create_item(feed_url="feed1", item_id="1"),
            self._create_item(feed_url="feed2", item_id="2"),
            self._create_item(feed_url="feed1", item_id="3"),
        ]
        
        result = select_new_items(items, self.state, max_items=10)
        
        assert len(result) == 3
        assert len(self.state["feeds"]) == 2

    def test_select_new_items_mixed_new_and_old(self):
        """Test selecting from mix of items (in-run dedup only)"""
        items = [self._create_item(item_id=str(i)) for i in range(5)]
        
        # Since state is ephemeral, persisted "seen" list doesn't affect selection
        # All fresh items will be selected on fresh state
        self.state["feeds"][self.feed_url] = {
            "seen": []  # Empty in-memory state
        }
        
        result = select_new_items(items, self.state, max_items=10)
        
        # All items should be selected (no persistent state to compare against)
        assert len(result) == 5


class TestIsRecent:
    """Test is_recent function for age filtering"""

    def test_recent_item_today(self):
        """Test that today's item is recent"""
        item = {
            "title": "Today's News",
            "published": datetime.now(timezone.utc)
        }
        assert is_recent(item, days=7)

    def test_recent_item_few_days_ago(self):
        """Test that item from 3 days ago is recent"""
        item = {
            "title": "Recent News",
            "published": datetime.now(timezone.utc) - timedelta(days=3)
        }
        assert is_recent(item, days=7)

    def test_old_item_beyond_threshold(self):
        """Test that item from 10 days ago is old"""
        item = {
            "title": "Old News",
            "published": datetime.now(timezone.utc) - timedelta(days=10)
        }
        assert not is_recent(item, days=7)

    def test_item_at_boundary_just_old(self):
        """Test item at exact boundary (8 days old, threshold 7)"""
        item = {
            "title": "Boundary News",
            "published": datetime.now(timezone.utc) - timedelta(days=8)
        }
        assert not is_recent(item, days=7)

    def test_item_at_boundary_just_recent(self):
        """Test item just within boundary (6.9 days old, threshold 7)"""
        item = {
            "title": "Just Recent",
            "published": datetime.now(timezone.utc) - timedelta(days=6, hours=23)
        }
        assert is_recent(item, days=7)

    def test_item_without_published_date(self):
        """Test that items without published date are considered recent"""
        item = {
            "title": "Unknown Date News",
            "published": None
        }
        assert is_recent(item, days=7)

    def test_item_with_missing_published_key(self):
        """Test that items with missing published key are considered recent"""
        item = {
            "title": "No Date News"
        }
        assert is_recent(item, days=7)

    def test_custom_age_threshold(self):
        """Test with custom age threshold"""
        item = {
            "title": "News",
            "published": datetime.now(timezone.utc) - timedelta(days=14)
        }
        assert not is_recent(item, days=7)
        assert is_recent(item, days=21)


class TestFilterRecentItems:
    """Test filter_recent_items function"""

    def test_filter_all_recent(self):
        """Test filtering when all items are recent"""
        items = [
            {
                "title": "Today",
                "published": datetime.now(timezone.utc)
            },
            {
                "title": "Yesterday",
                "published": datetime.now(timezone.utc) - timedelta(days=1)
            },
            {
                "title": "Last week",
                "published": datetime.now(timezone.utc) - timedelta(days=6)
            },
        ]
        filtered = filter_recent_items(items, max_age_days=7)
        assert len(filtered) == 3

    def test_filter_some_old(self):
        """Test filtering when some items are old"""
        items = [
            {
                "title": "Today",
                "published": datetime.now(timezone.utc)
            },
            {
                "title": "Old News",
                "published": datetime.now(timezone.utc) - timedelta(days=10)
            },
            {
                "title": "Ancient History",
                "published": datetime.now(timezone.utc) - timedelta(days=30)
            },
        ]
        filtered = filter_recent_items(items, max_age_days=7)
        assert len(filtered) == 1
        assert filtered[0]["title"] == "Today"

    def test_filter_all_old(self):
        """Test filtering when all items are old"""
        items = [
            {
                "title": "Ancient 1",
                "published": datetime.now(timezone.utc) - timedelta(days=30)
            },
            {
                "title": "Ancient 2",
                "published": datetime.now(timezone.utc) - timedelta(days=45)
            },
        ]
        filtered = filter_recent_items(items, max_age_days=7)
        assert len(filtered) == 0

    def test_filter_empty_list(self):
        """Test filtering empty list"""
        filtered = filter_recent_items([], max_age_days=7)
        assert len(filtered) == 0

    def test_filter_no_dates(self):
        """Test filtering items without dates"""
        items = [
            {"title": "No date 1"},
            {"title": "No date 2", "published": None},
        ]
        filtered = filter_recent_items(items, max_age_days=7)
        assert len(filtered) == 2

    def test_filter_mixed_with_no_dates(self):
        """Test filtering mix of dated and undated items"""
        items = [
            {
                "title": "Today",
                "published": datetime.now(timezone.utc)
            },
            {
                "title": "No date",
            },
            {
                "title": "Old News",
                "published": datetime.now(timezone.utc) - timedelta(days=10)
            },
        ]
        filtered = filter_recent_items(items, max_age_days=7)
        # Should have today's and no-date items
        assert len(filtered) == 2
        titles = [item["title"] for item in filtered]
        assert "Today" in titles
        assert "No date" in titles

    def test_filter_preserves_order(self):
        """Test that filtering preserves item order"""
        now = datetime.now(timezone.utc)
        items = [
            {"title": "First", "published": now},
            {"title": "Second", "published": now - timedelta(days=1)},
            {"title": "Third", "published": now - timedelta(days=3)},
        ]
        filtered = filter_recent_items(items, max_age_days=7)
        assert len(filtered) == 3
        assert [item["title"] for item in filtered] == ["First", "Second", "Third"]
