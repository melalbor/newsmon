"""Unit tests for main.py module"""

import pytest
import tempfile
import os
from unittest.mock import Mock, patch
from src.main import load_feeds, main, FEEDS_FILE_DEFAULT


class TestLoadFeeds:
    """Test load_feeds function"""

    def test_load_valid_feeds_yaml(self):
        """Test loading valid feeds from YAML"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("- https://example.com/feed1\n")
            f.write("- https://example.com/feed2\n")
            f.flush()
            
            try:
                feeds = load_feeds(f.name)
                assert len(feeds) == 2
                assert feeds[0] == "https://example.com/feed1"
            finally:
                os.unlink(f.name)

    def test_load_feeds_invalid_format(self):
        """Test that non-list YAML raises error"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("url: https://example.com/feed\n")
            f.flush()
            
            try:
                with pytest.raises(ValueError) as exc_info:
                    load_feeds(f.name)
                assert "must be a list" in str(exc_info.value)
            finally:
                os.unlink(f.name)

    def test_load_feeds_empty_list(self):
        """Test loading empty feeds list"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("[]\n")
            f.flush()
            
            try:
                feeds = load_feeds(f.name)
                assert len(feeds) == 0
            finally:
                os.unlink(f.name)

    def test_load_feeds_nonexistent_file(self):
        """Test loading from nonexistent file raises error"""
        with pytest.raises(FileNotFoundError):
            load_feeds("/nonexistent/feeds.yaml")

    def test_load_feeds_with_comments(self):
        """Test loading YAML with comments"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("# List of RSS feeds\n")
            f.write("- https://example.com/feed1  # First feed\n")
            f.write("- https://example.com/feed2  # Second feed\n")
            f.flush()
            
            try:
                feeds = load_feeds(f.name)
                assert len(feeds) == 2
                assert feeds[0] == "https://example.com/feed1"
                assert feeds[1] == "https://example.com/feed2"
            finally:
                os.unlink(f.name)

    def test_load_feeds_preserves_url_order(self):
        """Test that feeds maintain their order"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            urls = [
                "https://example1.com/feed",
                "https://example2.com/feed",
                "https://example3.com/feed",
                "https://example4.com/feed",
            ]
            for url in urls:
                f.write(f"- {url}\n")
            f.flush()
            
            try:
                feeds = load_feeds(f.name)
                assert feeds == urls
            finally:
                os.unlink(f.name)

    def test_load_feeds_with_various_protocols(self):
        """Test loading feeds with different protocols (http, https)"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("- http://example.com/feed\n")
            f.write("- https://example.com/feed\n")
            f.write("- https://example.com/feed.atom\n")
            f.flush()
            
            try:
                feeds = load_feeds(f.name)
                assert len(feeds) == 3
                assert all(url.startswith('http') for url in feeds)
            finally:
                os.unlink(f.name)

    def test_load_feeds_with_trailing_whitespace(self):
        """Test loading YAML with trailing whitespace"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("- https://example.com/feed1   \n")
            f.write("- https://example.com/feed2  \n")
            f.flush()
            
            try:
                feeds = load_feeds(f.name)
                # YAML should strip trailing whitespace
                assert feeds[0] == "https://example.com/feed1"
                assert feeds[1] == "https://example.com/feed2"
            finally:
                os.unlink(f.name)

    def test_load_feeds_rss_format(self):
        """Test loading feeds with RSS extension"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("- https://example.com/feed.rss\n")
            f.write("- https://example.com/feed.xml\n")
            f.flush()
            
            try:
                feeds = load_feeds(f.name)
                assert len(feeds) == 2
                assert any('.rss' in url for url in feeds)
                assert any('.xml' in url for url in feeds)
            finally:
                os.unlink(f.name)

    def test_load_feeds_atom_format(self):
        """Test loading feeds with Atom extension"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("- https://example.com/feed.atom\n")
            f.write("- https://example.com/atom.xml\n")
            f.flush()
            
            try:
                feeds = load_feeds(f.name)
                assert len(feeds) == 2
                assert any('.atom' in url for url in feeds)
            finally:
                os.unlink(f.name)

    def test_load_feeds_with_query_parameters(self):
        """Test loading feeds with query parameters in URL"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("- https://example.com/feed?format=rss\n")
            f.write("- https://example.com/feed?id=123&type=atom\n")
            f.flush()
            
            try:
                feeds = load_feeds(f.name)
                assert len(feeds) == 2
                assert "format=rss" in feeds[0]
                assert "id=123" in feeds[1]
            finally:
                os.unlink(f.name)

    def test_load_feeds_rejects_dict_format(self):
        """Test that dictionary format is rejected"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("feeds:\n")
            f.write("  - https://example.com/feed1\n")
            f.write("  - https://example.com/feed2\n")
            f.flush()
            
            try:
                with pytest.raises(ValueError) as exc_info:
                    load_feeds(f.name)
                assert "must be a list" in str(exc_info.value)
            finally:
                os.unlink(f.name)

    def test_load_feeds_rejects_string_format(self):
        """Test that single string is rejected"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("https://example.com/feed\n")
            f.flush()
            
            try:
                with pytest.raises(ValueError) as exc_info:
                    load_feeds(f.name)
                assert "must be a list" in str(exc_info.value)
            finally:
                os.unlink(f.name)

    def test_load_feeds_with_urls_containing_slashes(self):
        """Test loading feeds with complex URLs containing multiple slashes"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("- https://example.com/path/to/feed.rss\n")
            f.write("- https://subdomain.example.com/blog/feed/rss\n")
            f.flush()
            
            try:
                feeds = load_feeds(f.name)
                assert len(feeds) == 2
                assert "/path/to/" in feeds[0]
                assert "/blog/feed/" in feeds[1]
            finally:
                os.unlink(f.name)

    def test_load_feeds_actual_feeds_yaml(self):
        """Test loading from actual feeds.yaml if it exists"""
        feeds_path = "feeds.yaml"
        if os.path.exists(feeds_path):
            feeds = load_feeds(feeds_path)
            # Should be a list
            assert isinstance(feeds, list)
            # Should not be empty
            assert len(feeds) > 0
            # All items should be strings (URLs)
            assert all(isinstance(url, str) for url in feeds)
            # All items should start with http or https
            assert all(url.startswith(('http://', 'https://')) for url in feeds)

    def test_load_feeds_multiline_yaml_array(self):
        """Test loading YAML with inline array format"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("[https://example.com/feed1, https://example.com/feed2, https://example.com/feed3]\n")
            f.flush()
            
            try:
                feeds = load_feeds(f.name)
                assert len(feeds) == 3
                assert feeds[0] == "https://example.com/feed1"
                assert feeds[1] == "https://example.com/feed2"
                assert feeds[2] == "https://example.com/feed3"
            finally:
                os.unlink(f.name)


class TestMain:
    """Test main function"""

    @patch.dict(os.environ, {
        "TELEGRAM_BOT_TOKEN": "test_token",
        "TELEGRAM_CHANNEL_ID": "123",
        "TELEGRAM_ADMIN_CHANNEL_ID": "456"
    })
    @patch('src.main.send_admin')
    @patch('src.main.send_items')
    @patch('src.main.select_new_items')
    @patch('src.main.normalize_feed')
    @patch('src.main.fetch_all')
    @patch('src.main.load_feeds')
    def test_main_success_flow(self, mock_load_feeds, mock_fetch, mock_normalize, mock_select,
                               mock_send_items, mock_send_admin):
        """Test successful main flow"""
        # Setup mocks
        mock_load_feeds.return_value = ["https://example.com/feed"]
        mock_fetch.return_value = {"https://example.com/feed": Mock()}
        mock_normalize.return_value = [
            {"title": "Article", "link": "https://example.com/1", "feed_url": "url", "feed_title": "Feed"}
        ]
        mock_select.return_value = [
            {"title": "Article", "link": "https://example.com/1", "feed_url": "url", 
             "feed_title": "Feed", "_fingerprint": "abc"}
        ]
        
        main()
        
        # Verify calls
        mock_send_items.assert_called_once()

    @patch.dict(os.environ, {
        "TELEGRAM_BOT_TOKEN": "test_token",
        "TELEGRAM_CHANNEL_ID": "123",
        "TELEGRAM_ADMIN_CHANNEL_ID": "456"
    })
    @patch('src.main.fetch_all')
    @patch('src.main.send_admin')
    @patch('src.main.load_feeds')
    def test_main_missing_env_vars(self, mock_load_feeds, mock_send_admin, mock_fetch):
        """Test main with missing environment variables"""
        with patch.dict(os.environ, {}, clear=True):
            # Running without telegram env vars triggers dry-run mode
            main()  # Should not raise, just run in dry-run

    @patch.dict(os.environ, {
        "TELEGRAM_BOT_TOKEN": "test_token",
        "TELEGRAM_CHANNEL_ID": "123",
        "TELEGRAM_ADMIN_CHANNEL_ID": "456"
    })
    @patch('src.main.load_feeds')
    @patch('src.main.fetch_all')
    @patch('src.main.send_admin')
    def test_main_no_items_fetched(self, mock_send_admin, mock_fetch, mock_load_feeds):
        """Test main when no items are fetched"""
        mock_load_feeds.return_value = ["https://example.com/feed"]
        mock_fetch.return_value = {"https://example.com/feed": Mock(entries=[])}
        
        with patch('builtins.print') as mock_print:
            main()
            mock_print.assert_called_with("No items fetched.")

    @patch.dict(os.environ, {
        "TELEGRAM_BOT_TOKEN": "test_token",
        "TELEGRAM_CHANNEL_ID": "123",
        "TELEGRAM_ADMIN_CHANNEL_ID": "456"
    })
    @patch('src.main.load_feeds')
    @patch('src.main.fetch_all')
    @patch('src.main.normalize_feed')
    @patch('src.main.select_new_items')
    @patch('src.main.send_admin')
    def test_main_send_failure(self, mock_send_admin, mock_select, mock_normalize,
                               mock_fetch, mock_load_feeds):
        """Test main when send_items fails"""
        mock_load_feeds.return_value = ["https://example.com/feed"]
        mock_fetch.return_value = {"https://example.com/feed": Mock()}
        mock_normalize.return_value = [
            {"title": "Article", "link": "https://example.com/1", "feed_url": "url", "feed_title": "Feed"}
        ]
        mock_select.return_value = [
            {"title": "Article", "link": "https://example.com/1", "feed_url": "url", 
             "feed_title": "Feed", "_fingerprint": "abc"}
        ]
        
        with patch('src.main.send_items', side_effect=Exception("Send failed")):
            with patch('builtins.print') as mock_print:
                main()
                mock_print.assert_called_with("Failed to send items. Exiting without marking as seen.")
