"""Unit tests for fetch.py module"""

import pytest
from unittest.mock import Mock, patch, MagicMock
import requests
from src.fetch import fetch_feed, fetch_all, FeedFetchError, DEFAULT_TIMEOUT


class TestFetchFeed:
    """Test fetch_feed function"""

    @patch('src.fetch.requests.get')
    @patch('src.fetch.feedparser.parse')
    def test_fetch_feed_success(self, mock_parse, mock_get):
        """Test successful feed fetch"""
        # Setup mock response
        mock_response = Mock()
        mock_response.content = b"<rss>...</rss>"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        # Setup mock feedparser
        mock_parsed = Mock()
        mock_parsed.bozo = False
        mock_parse.return_value = mock_parsed
        
        result = fetch_feed("https://example.com/feed.rss")
        
        assert result == mock_parsed
        mock_get.assert_called_once()
        assert "User-Agent" in mock_get.call_args[1]["headers"]

    @patch('src.fetch.requests.get')
    def test_fetch_feed_http_error(self, mock_get):
        """Test fetch_feed with HTTP error"""
        mock_get.side_effect = requests.RequestException("HTTP Error")
        
        with pytest.raises(FeedFetchError) as exc_info:
            fetch_feed("https://example.com/feed.rss")
        
        assert "HTTP error" in str(exc_info.value)

    @patch('src.fetch.requests.get')
    @patch('src.fetch.feedparser.parse')
    def test_fetch_feed_parse_error(self, mock_parse, mock_get):
        """Test fetch_feed with parsing error"""
        mock_response = Mock()
        mock_response.content = b"invalid"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        mock_parsed = Mock()
        mock_parsed.bozo = True
        mock_parsed.bozo_exception = Exception("Parse failed")
        mock_parse.return_value = mock_parsed
        
        with pytest.raises(FeedFetchError) as exc_info:
            fetch_feed("https://example.com/feed.rss")
        
        assert "Failed to parse" in str(exc_info.value)

    @patch('src.fetch.requests.get')
    def test_fetch_feed_timeout(self, mock_get):
        """Test fetch_feed respects timeout"""
        mock_get.side_effect = requests.Timeout()
        
        with pytest.raises(FeedFetchError):
            fetch_feed("https://example.com/feed.rss")

    @patch('src.fetch.requests.get')
    @patch('src.fetch.feedparser.parse')
    def test_fetch_feed_custom_timeout(self, mock_parse, mock_get):
        """Test fetch_feed with custom timeout"""
        mock_response = Mock()
        mock_response.content = b"<rss>...</rss>"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        mock_parsed = Mock()
        mock_parsed.bozo = False
        mock_parse.return_value = mock_parsed
        
        fetch_feed("https://example.com/feed.rss", timeout=30)
        
        assert mock_get.call_args[1]["timeout"] == 30

    @patch('src.fetch.requests.get')
    @patch('src.fetch.feedparser.parse')
    def test_fetch_feed_default_timeout(self, mock_parse, mock_get):
        """Test fetch_feed uses default timeout"""
        mock_response = Mock()
        mock_response.content = b"<rss>...</rss>"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        mock_parsed = Mock()
        mock_parsed.bozo = False
        mock_parse.return_value = mock_parsed
        
        fetch_feed("https://example.com/feed.rss")
        
        assert mock_get.call_args[1]["timeout"] == DEFAULT_TIMEOUT

    @patch('src.fetch.requests.get')
    @patch('src.fetch.feedparser.parse')
    def test_fetch_feed_user_agent_header(self, mock_parse, mock_get):
        """Test fetch_feed sets correct User-Agent"""
        mock_response = Mock()
        mock_response.content = b"<rss>...</rss>"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response
        
        mock_parsed = Mock()
        mock_parsed.bozo = False
        mock_parse.return_value = mock_parsed
        
        fetch_feed("https://example.com/feed.rss")
        
        headers = mock_get.call_args[1]["headers"]
        assert "rss-telegram-bot" in headers["User-Agent"]


class TestFetchAll:
    """Test fetch_all function"""

    @patch('src.fetch.fetch_feed')
    def test_fetch_all_single_feed(self, mock_fetch_feed):
        """Test fetch_all with single feed"""
        mock_parsed = Mock()
        mock_fetch_feed.return_value = mock_parsed
        
        result = fetch_all(["https://example.com/feed.rss"])
        
        assert len(result) == 1
        assert "https://example.com/feed.rss" in result
        assert result["https://example.com/feed.rss"] == mock_parsed

    @patch('src.fetch.fetch_feed')
    def test_fetch_all_multiple_feeds(self, mock_fetch_feed):
        """Test fetch_all with multiple feeds"""
        mock_parsed1 = Mock()
        mock_parsed2 = Mock()
        mock_fetch_feed.side_effect = [mock_parsed1, mock_parsed2]
        
        urls = ["https://example.com/feed1.rss", "https://example.com/feed2.rss"]
        result = fetch_all(urls)
        
        assert len(result) == 2
        assert result[urls[0]] == mock_parsed1
        assert result[urls[1]] == mock_parsed2

    @patch('src.fetch.fetch_feed')
    def test_fetch_all_empty_list(self, mock_fetch_feed):
        """Test fetch_all with empty list"""
        result = fetch_all([])
        
        assert len(result) == 0
        assert result == {}

    @patch('src.fetch.fetch_feed')
    def test_fetch_all_preserves_urls_as_keys(self, mock_fetch_feed):
        """Test that fetch_all uses URLs as dictionary keys"""
        mock_parsed = Mock()
        mock_fetch_feed.return_value = mock_parsed
        
        urls = [
            "https://example1.com/feed.rss",
            "https://example2.com/feed.rss",
            "https://example3.com/feed.rss"
        ]
        result = fetch_all(urls)
        
        assert set(result.keys()) == set(urls)

    @patch('src.fetch.fetch_feed')
    def test_fetch_all_handles_partial_failure(self, mock_fetch_feed):
        """Test that fetch_all propagates exceptions"""
        mock_fetch_feed.side_effect = FeedFetchError("Feed fetch failed")
        
        with pytest.raises(FeedFetchError):
            fetch_all(["https://example.com/feed.rss"])


class TestFeedFetchError:
    """Test FeedFetchError exception"""

    def test_feed_fetch_error_is_exception(self):
        """Test that FeedFetchError is an Exception"""
        error = FeedFetchError("Test error")
        assert isinstance(error, Exception)

    def test_feed_fetch_error_message(self):
        """Test FeedFetchError preserves message"""
        message = "Custom error message"
        error = FeedFetchError(message)
        assert str(error) == message
