"""Unit tests for parse.py module"""

import pytest
from datetime import datetime, timezone
from unittest.mock import Mock
from src.parse import _parse_datetime, normalize_feed


class TestParseDatetime:
    """Test _parse_datetime function"""

    def test_parse_published_datetime(self):
        """Test parsing published_parsed field"""
        entry = Mock()
        entry.published_parsed = (2024, 1, 15, 10, 30, 45, 0, 0, 0)
        entry.updated_parsed = None
        
        result = _parse_datetime(entry)
        
        assert result is not None
        assert isinstance(result, datetime)
        assert result.year == 2024
        assert result.month == 1

    def test_parse_updated_datetime(self):
        """Test parsing updated_parsed field when published is missing"""
        entry = Mock()
        entry.published_parsed = None
        entry.updated_parsed = (2024, 2, 20, 14, 15, 30, 0, 0, 0)
        
        result = _parse_datetime(entry)
        
        assert result is not None
        assert isinstance(result, datetime)
        assert result.month == 2

    def test_parse_no_datetime(self):
        """Test when neither published nor updated is present"""
        entry = Mock(spec=[])
        
        result = _parse_datetime(entry)
        
        assert result is None

    def test_parse_datetime_with_none_values(self):
        """Test when datetime fields exist but are None"""
        entry = Mock()
        entry.published_parsed = None
        entry.updated_parsed = None
        
        result = _parse_datetime(entry)
        
        assert result is None

    def test_datetime_is_utc(self):
        """Test that returned datetime is in UTC timezone"""
        entry = Mock()
        entry.published_parsed = (2024, 1, 1, 0, 0, 0, 0, 0, 0)
        entry.updated_parsed = None
        
        result = _parse_datetime(entry)
        
        assert result.tzinfo == timezone.utc


class TestNormalizeFeed:
    """Test normalize_feed function"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Set up test fixtures"""
        self.feed_url = "https://example.com/feed.rss"
        
    def _create_entry(self, title="Test Title", link="https://example.com/article",
                     entry_id="123", guid=None, published=None, summary="Summary"):
        """Helper to create mock entry"""
        entry = Mock()
        entry.get = Mock(side_effect=lambda k, default=None: {
            "title": title,
            "link": link,
            "id": entry_id,
            "guid": guid,
            "summary": summary,
        }.get(k, default))
        # Set published_parsed and updated_parsed as mock attributes
        entry.published_parsed = published
        entry.updated_parsed = None
        return entry
    
    def _create_feed(self, title="Test Feed", entries=None):
        """Helper to create mock feed"""
        feed = Mock()
        feed.feed = Mock()
        feed.feed.get = Mock(side_effect=lambda k, default=None: 
                            {"title": title}.get(k, default))
        feed.entries = entries or []
        return feed

    def test_normalize_valid_entry(self):
        """Test normalizing a valid feed entry"""
        entry = self._create_entry()
        feed = self._create_feed(entries=[entry])
        
        result = normalize_feed(feed, self.feed_url)
        
        assert len(result) == 1
        assert result[0]["title"] == "Test Title"
        assert result[0]["link"] == "https://example.com/article"
        assert result[0]["feed_url"] == self.feed_url

    def test_normalize_missing_title(self):
        """Test that entries without title are skipped"""
        entry = self._create_entry(title=None)
        feed = self._create_feed(entries=[entry])
        
        result = normalize_feed(feed, self.feed_url)
        
        assert len(result) == 0

    def test_normalize_missing_link(self):
        """Test that entries without link are skipped"""
        entry = self._create_entry(link=None)
        feed = self._create_feed(entries=[entry])
        
        result = normalize_feed(feed, self.feed_url)
        
        assert len(result) == 0

    def test_normalize_multiple_entries(self):
        """Test normalizing multiple entries"""
        entries = [
            self._create_entry(title=f"Article {i}", 
                              link=f"https://example.com/{i}")
            for i in range(3)
        ]
        feed = self._create_feed(entries=entries)
        
        result = normalize_feed(feed, self.feed_url)
        
        assert len(result) == 3

    def test_normalize_title_stripped(self):
        """Test that titles are stripped of whitespace"""
        entry = self._create_entry(title="  Title with spaces  ")
        feed = self._create_feed(entries=[entry])
        
        result = normalize_feed(feed, self.feed_url)
        
        assert result[0]["title"] == "Title with spaces"

    def test_normalize_uses_feed_title(self):
        """Test that feed title is included in normalized item"""
        feed = self._create_feed(title="Feed Title", 
                                entries=[self._create_entry()])
        
        result = normalize_feed(feed, self.feed_url)
        
        assert result[0]["feed_title"] == "Feed Title"

    def test_normalize_uses_feed_url_as_fallback_title(self):
        """Test that feed URL is used as title if feed title missing"""
        entry = self._create_entry()
        feed = Mock()
        feed.feed = Mock()
        # Create a get method that properly handles the default parameter
        feed.feed.get = Mock(side_effect=lambda k, default=None: default)
        feed.entries = [entry]
        
        result = normalize_feed(feed, self.feed_url)
        
        assert result[0]["feed_title"] == self.feed_url

    def test_normalize_preserves_optional_fields(self):
        """Test that optional fields are preserved"""
        entry = self._create_entry(entry_id="id123", summary="Test summary")
        feed = self._create_feed(entries=[entry])
        
        result = normalize_feed(feed, self.feed_url)
        
        assert result[0]["id"] == "id123"
        assert result[0]["summary"] == "Test summary"
