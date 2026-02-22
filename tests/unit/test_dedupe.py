"""Unit tests for dedupe.py module"""

import pytest
import requests
from datetime import datetime, timezone, timedelta
from src.dedupe import select_new_items, is_recent, filter_recent_items, get_past_items, update_state_gist

class TestSelectNewItems:
    """Test select_new_items function"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test fixtures"""
        self.feed_url = "https://example.com/feed"

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
        """Test selecting new items"""
        items = [self._create_item(item_id=str(i)) for i in range(3)]
        
        result = select_new_items(items, {}, max_items=10)
        
        assert len(result) == 3

    def test_select_new_items_skips_past(self):
        """Items whose titles appear in past_items should be ignored"""
        items = [
            self._create_item(title="A", item_id="1"),
            self._create_item(title="B", item_id="2"),
        ]
        past = {self.feed_url: ["A"]}
        result = select_new_items(items, past, max_items=10)
        assert len(result) == 1
        assert result[0]["title"] == "B"

    def test_select_new_items_multiple_feeds_and_cap(self):
        """Ensure items from multiple feeds are interleaved and cap respected"""
        # create items for feed1 and feed2 with distinct titles
        items = []
        for i in range(5):
            items.append(self._create_item(title=f"Article-f1-{i}", feed_url="f1", item_id=f"f1-{i}"))
            items.append(self._create_item(title=f"Article-f2-{i}", feed_url="f2", item_id=f"f2-{i}"))
        # no past items
        result = select_new_items(items, {}, max_items=3)
        # should have exactly 3 items regardless of feed
        assert len(result) == 3
        # ensure oldest-first ordering per feed by inspecting published (none -> treat as 0)
        # since all have published None they retain insertion order; ensure no duplication
        titles = [r["title"] for r in result]
        assert len(set(titles)) == 3

    def test_select_new_items_respects_max(self):
        """Test that max_items limit is respected"""
        items = [self._create_item(item_id=str(i)) for i in range(20)]
        
        result = select_new_items(items, {}, max_items=5)
        
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


def test_state_gist_roundtrip(monkeypatch):
    """Ensure get_past_items and update_state_gist work with expected format"""
    import json
    # prepare fake get response
    sample = {"https://example.com/feed": ["A","B"]}
    class DummyGet:
        status_code = 200
        def raise_for_status(self):
            pass
        def json(self):
            return {"files": {"state.json": {"content": json.dumps(sample)}}}
    monkeypatch.setattr('requests.get', lambda url, headers: DummyGet())

    filename, data = get_past_items("id", "token")
    assert filename == "state.json"
    assert data == sample

    # patch behaviour for update
    captured = {}
    def fake_patch(url, headers=None, **kwargs):
        captured['url'] = url
        # payload may be under 'json' key
        captured['payload'] = kwargs.get('json')
        class DummyPatch:
            def raise_for_status(self):
                pass
        return DummyPatch()
    monkeypatch.setattr('requests.patch', fake_patch)

    update_state_gist("id", "token", filename, {"foo": ["bar"]})
    assert 'files' in captured['payload']
    assert "foo" in captured['payload']['files'][filename]['content']


def test_update_state_gist_noop(monkeypatch):
    """Calling update_state_gist with empty data should not POST"""
    called = False
    def fake_patch(url, headers=None, **kwargs):
        nonlocal called
        called = True
        class Dummy:
            def raise_for_status(self): pass
        return Dummy()
    monkeypatch.setattr('requests.patch', fake_patch)
    update_state_gist("id", "token", "fname", {})
    assert not called


def test_update_state_gist_network_error(monkeypatch):
    """Network errors during patch should raise RuntimeError"""
    def fake_patch(url, headers=None, **kwargs):
        raise requests.RequestException("fail")
    monkeypatch.setattr('requests.patch', fake_patch)
    with pytest.raises(RuntimeError):
        update_state_gist("id", "token", "fname", {"a":["b"]})


def test_get_past_items_http_error(monkeypatch):
    """get_past_items should propagate HTTP errors"""
    class BadGet:
        status_code = 404
        def raise_for_status(self):
            raise requests.HTTPError("404")
    monkeypatch.setattr('requests.get', lambda url, headers: BadGet())
    with pytest.raises(requests.HTTPError):
        get_past_items("id", "token")


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
