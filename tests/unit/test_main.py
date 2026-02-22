"""Unit tests for main.py module"""

import pytest
import tempfile
import os
from unittest.mock import Mock, patch
from src.main import load_feeds, main, FEEDS_FILE_DEFAULT


class TestLoadFeeds:
    """Test load_feeds function"""

    def test_load_valid_feeds_yaml(self):
        """Test loading valid feeds from YAML using new topics structure; channel_id is treated as env var name"""
        cfg = {
            "topics": {
                "test": {
                    "channel_id": "CHAN",
                    "feeds": [
                        "https://example.com/feed1",
                        {"url": "https://example.com/feed2"},
                    ],
                }
            }
        }
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            import yaml
            yaml.safe_dump(cfg, f)
            f.flush()

            try:
                feeds = load_feeds(f.name)
                assert len(feeds) == 2
                assert feeds[0]["feed_url"] == "https://example.com/feed1"
                assert feeds[0]["channel_id"] == "CHAN"
                assert feeds[1]["feed_url"] == "https://example.com/feed2"
            finally:
                os.unlink(f.name)

    def test_load_feeds_invalid_format(self):
        """Test that YAML missing topics key raises error"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("url: https://example.com/feed\n")
            f.flush()
            
            try:
                with pytest.raises(ValueError) as exc_info:
                    load_feeds(f.name)
                assert "topics" in str(exc_info.value)
            finally:
                os.unlink(f.name)

    def test_load_feeds_empty_list(self):
        """Test loading configuration with empty topics mapping"""
        cfg = {"topics": {}}
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            import yaml
            yaml.safe_dump(cfg, f)
            f.flush()
            
            try:
                with pytest.raises(ValueError):
                    load_feeds(f.name)
            finally:
                os.unlink(f.name)

    def test_load_feeds_nonexistent_file(self):
        """Test loading from nonexistent file raises error"""
        with pytest.raises(FileNotFoundError):
            load_feeds("/nonexistent/feeds.yaml")

    def test_load_feeds_with_comments(self):
        """Test loading YAML with comments within new structure"""
        cfg = {
            "topics": {
                "a": {
                    "channel_id": "X",
                    "feeds": [
                        "https://example.com/feed1",  # comment
                        "https://example.com/feed2",  # another comment
                    ],
                }
            }
        }
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            import yaml
            yaml.safe_dump(cfg, f)
            f.flush()
            try:
                feeds = load_feeds(f.name)
                assert len(feeds) == 2
                assert feeds[0]["feed_url"] == "https://example.com/feed1"
                assert feeds[1]["feed_url"] == "https://example.com/feed2"
            finally:
                os.unlink(f.name)

    def test_load_feeds_preserves_url_order(self):
        """Test that feeds maintain their order per topic"""
        urls = [
            "https://example1.com/feed",
            "https://example2.com/feed",
            "https://example3.com/feed",
        ]
        cfg = {"topics": {"t": {"channel_id": "C", "feeds": urls}}}
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            import yaml
            yaml.safe_dump(cfg, f)
            f.flush()
            try:
                feeds = load_feeds(f.name)
                assert [f["feed_url"] for f in feeds] == urls
            finally:
                os.unlink(f.name)

    def test_load_feeds_with_various_protocols(self):
        """Test loading feeds with different protocols (http, https)"""
        urls = [
            "http://example.com/feed",
            "https://example.com/feed",
            "https://example.com/feed.atom",
        ]
        cfg = {"topics": {"t": {"channel_id": "C", "feeds": urls}}}
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            import yaml
            yaml.safe_dump(cfg, f)
            f.flush()
            try:
                feeds = load_feeds(f.name)
                assert len(feeds) == 3
                assert all(f["feed_url"].startswith('http') for f in feeds)
            finally:
                os.unlink(f.name)

    def test_load_feeds_with_trailing_whitespace(self):
        """Test loading YAML with trailing whitespace"""
        urls = ["https://example.com/feed1   ", "https://example.com/feed2  "]
        cfg = {"topics": {"t": {"channel_id": "C", "feeds": urls}}}
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            import yaml
            yaml.safe_dump(cfg, f)
            f.flush()
            try:
                feeds = load_feeds(f.name)
                assert feeds[0]["feed_url"] == "https://example.com/feed1"
                assert feeds[1]["feed_url"] == "https://example.com/feed2"
            finally:
                os.unlink(f.name)

    def test_load_feeds_rss_format(self):
        """Test loading feeds with RSS extension"""
        urls = ["https://example.com/feed.rss", "https://example.com/feed.xml"]
        cfg = {"topics": {"t": {"channel_id": "C", "feeds": urls}}}
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            import yaml
            yaml.safe_dump(cfg, f)
            f.flush()
            try:
                feeds = load_feeds(f.name)
                assert len(feeds) == 2
                assert any('.rss' in f["feed_url"] for f in feeds)
                assert any('.xml' in f["feed_url"] for f in feeds)
            finally:
                os.unlink(f.name)

    def test_load_feeds_atom_format(self):
        """Test loading feeds with Atom extension"""
        urls = ["https://example.com/feed.atom", "https://example.com/atom.xml"]
        cfg = {"topics": {"t": {"channel_id": "C", "feeds": urls}}}
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            import yaml
            yaml.safe_dump(cfg, f)
            f.flush()
            try:
                feeds = load_feeds(f.name)
                assert len(feeds) == 2
                assert any('.atom' in f["feed_url"] for f in feeds)
            finally:
                os.unlink(f.name)

    def test_load_feeds_with_query_parameters(self):
        """Test loading feeds with query parameters in URL"""
        urls = ["https://example.com/feed?format=rss", "https://example.com/feed?id=123&type=atom"]
        cfg = {"topics": {"t": {"channel_id": "C", "feeds": urls}}}
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            import yaml
            yaml.safe_dump(cfg, f)
            f.flush()
            try:
                feeds = load_feeds(f.name)
                assert len(feeds) == 2
                assert "format=rss" in feeds[0]["feed_url"]
                assert "id=123" in feeds[1]["feed_url"]
            finally:
                os.unlink(f.name)

    def test_load_feeds_rejects_dict_format(self):
        """Test that random dict without topics is rejected"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("feeds:\n  - https://example.com/feed1\n")
            f.flush()
            
            try:
                with pytest.raises(ValueError):
                    load_feeds(f.name)
            finally:
                os.unlink(f.name)

    def test_load_feeds_rejects_string_format(self):
        """Test that single string is rejected"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            f.write("https://example.com/feed\n")
            f.flush()
            
            try:
                with pytest.raises(ValueError):
                    load_feeds(f.name)
            finally:
                os.unlink(f.name)

    def test_load_feeds_with_urls_containing_slashes(self):
        """Test loading feeds with complex URLs containing multiple slashes"""
        urls = [
            "https://example.com/path/to/feed.rss",
            "https://subdomain.example.com/blog/feed/rss",
        ]
        cfg = {"topics": {"t": {"channel_id": "C", "feeds": urls}}}
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            import yaml
            yaml.safe_dump(cfg, f)
            f.flush()
            try:
                feeds = load_feeds(f.name)
                assert len(feeds) == 2
                assert "/path/to/" in feeds[0]["feed_url"]
                assert "/blog/feed/" in feeds[1]["feed_url"]
            finally:
                os.unlink(f.name)

    def test_load_feeds_channel_id_type(self):
        """Channel id must be a string or else ValueError is raised"""
        cfg = {"topics": {"t": {"channel_id": 123, "feeds": ["https://e.com"]}}}
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            import yaml
            yaml.safe_dump(cfg, f)
            f.flush()
            try:
                with pytest.raises(ValueError):
                    load_feeds(f.name)
            finally:
                os.unlink(f.name)

    def test_load_feeds_actual_feeds_yaml(self):
        """Test loading from actual feeds.yaml if it exists"""
        feeds_path = "feeds.yaml"
        if os.path.exists(feeds_path):
            feeds = load_feeds(feeds_path)
            assert isinstance(feeds, list)
            assert len(feeds) > 0
            for f in feeds:
                assert "feed_url" in f and isinstance(f["feed_url"], str)
                assert f["feed_url"].startswith(('http://', 'https://'))

    def test_load_feeds_multiline_yaml_array(self):
        """Test loading YAML with inline array format using topics"""
        # YAML inline array should still be interpreted as a list by safe_load
        cfg = {"topics": {"t": {"channel_id": "C",
                                   "feeds": [
                                       "https://example.com/feed1",
                                       "https://example.com/feed2",
                                       "https://example.com/feed3",
                                   ]}}}
        with tempfile.NamedTemporaryFile(mode='w', suffix='.yaml', delete=False) as f:
            import yaml
            yaml.safe_dump(cfg, f)
            f.flush()
            try:
                feeds = load_feeds(f.name)
                assert len(feeds) == 3
                assert feeds[0]["feed_url"] == "https://example.com/feed1"
                assert feeds[1]["feed_url"] == "https://example.com/feed2"
                assert feeds[2]["feed_url"] == "https://example.com/feed3"
            finally:
                os.unlink(f.name)


class TestRules:
    """Tests for the allow/deny rule filtering logic"""

    def test_apply_rules_no_rules(self):
        """Items lacking rules should be returned unchanged"""
        items = [
            {"title": "foo", "summary": "bar"},
            {"title": "baz", "summary": "qux", "rules": {}},
        ]
        from src.main import apply_rules
        assert apply_rules(items) == items

    def test_apply_rules_allow(self):
        items = [
            {"title": "hello ios world", "summary": "", "rules": {"allow": ["ios"]}},
            {"title": "android news", "summary": "", "rules": {"allow": ["ios"]}},
        ]
        from src.main import apply_rules
        filtered = apply_rules(items)
        assert len(filtered) == 1
        assert "ios" in filtered[0]["title"]

    def test_apply_rules_deny(self):
        items = [
            {"title": "bad windows exploit", "summary": "", "rules": {"deny": ["windows"]}},
            {"title": "good linux tool", "summary": "", "rules": {"deny": ["windows"]}},
        ]
        from src.main import apply_rules
        filtered = apply_rules(items)
        assert len(filtered) == 1
        assert "linux" in filtered[0]["title"]

    def test_apply_rules_allow_and_deny(self):
        items = [
            {"title": "ios windows report", "summary": "", "rules": {"allow": ["ios"], "deny": ["windows"]}},
        ]
        from src.main import apply_rules
        filtered = apply_rules(items)
        assert filtered == []


class TestMain:
    """Test main function"""

    @patch.dict(os.environ, {
        "TELEGRAM_BOT_TOKEN": "test_token",
        "TELEGRAM_CHANNEL_ID": "123",            # fallback id
        "TELEGRAM_ADMIN_CHANNEL_ID": "456",
        "CHAN_ENV": "123",                     # per-topic env var
        "STATE_GIST_ID": "gid",
        "GH_GIST_UPDATE_TOKEN": "gtok",
    }, clear=True)
    @patch('src.main.update_state_gist')
    @patch('src.main.get_past_items', return_value=("file", {}))
    @patch('src.main.send_admin')
    @patch('src.main.send_items')
    @patch('src.main.select_new_items')
    @patch('src.main.normalize_feed')
    @patch('src.main.fetch_all')
    @patch('src.main.load_feeds')
    def test_main_success_flow(self, mock_load_feeds, mock_fetch, mock_normalize, mock_select,
                               mock_send_items, mock_send_admin, mock_get_past, mock_update_gist):
        """Test successful main flow (channel lookup via env var)"""
        # Setup mocks
        mock_load_feeds.return_value = [{
            "feed_url": "https://example.com/feed",
            "channel_id": "CHAN_ENV",   # this is the env var name
            "rules": {},
            "topic": "t",
        }]
        mock_fetch.return_value = {"https://example.com/feed": Mock()}
        mock_normalize.return_value = [
            {"title": "Article", "link": "https://example.com/1", "feed_url": "url", "feed_title": "Feed"}
        ]
        mock_select.return_value = [
            {"title": "Article", "link": "https://example.com/1", "feed_url": "url", 
             "feed_title": "Feed", "_fingerprint": "abc", "channel_id": "CHAN_ENV"}
        ]
        
        main()
        
        # Verify calls
        mock_send_items.assert_called_once()
        sent_args, sent_kwargs = mock_send_items.call_args
        # second positional argument is chat_id; resolved from CHAN_ENV
        assert sent_args[1] == "123", "expected channel id from environment"

    @patch.dict(os.environ, {
        "TELEGRAM_BOT_TOKEN": "test_token",
        "TELEGRAM_CHANNEL_ID": "999",            # only fallback available
        "TELEGRAM_ADMIN_CHANNEL_ID": "456",
        "STATE_GIST_ID": "gid",
        "GH_GIST_UPDATE_TOKEN": "gtok",
        # CHAN_ENV intentionally absent
    }, clear=True)
    @patch('src.main.update_state_gist')
    @patch('src.main.get_past_items', return_value=("file", {}))
    @patch('src.main.send_admin')
    @patch('src.main.send_items')
    @patch('src.main.select_new_items')
    @patch('src.main.normalize_feed')
    @patch('src.main.fetch_all')
    @patch('src.main.load_feeds')
    def test_main_envvar_missing_uses_fallback(self, mock_load_feeds, mock_fetch, mock_normalize, mock_select,
                                               mock_send_items, mock_send_admin, mock_get_past, mock_update_gist):
        """If the named channel env var isn't set we fall back to TELEGRAM_CHANNEL_ID"""
        mock_load_feeds.return_value = [{
            "feed_url": "https://example.com/feed",
            "channel_id": "CHAN_ENV",
            "rules": {},
            "topic": "t",
        }]
        mock_fetch.return_value = {"https://example.com/feed": Mock()}
        mock_normalize.return_value = [
            {"title": "Article", "link": "https://example.com/1", "feed_url": "url", "feed_title": "Feed"}
        ]
        mock_select.return_value = [
            {"title": "Article", "link": "https://example.com/1", "feed_url": "url", 
             "feed_title": "Feed", "_fingerprint": "abc", "channel_id": "CHAN_ENV"}
        ]

        main()
        mock_send_items.assert_called_once()
        sent_args, _ = mock_send_items.call_args
        assert sent_args[1] == "999", "fallback id should be used"
    @patch.dict(os.environ, {
        "TELEGRAM_BOT_TOKEN": "test_token",
        "TELEGRAM_CHANNEL_ID": "123",
        "TELEGRAM_ADMIN_CHANNEL_ID": "456",
        "CHAN_ENV": "123",
    }, clear=True)
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
        "TELEGRAM_ADMIN_CHANNEL_ID": "456",
        "CHAN_ENV": "123",
    })
    @patch('src.main.load_feeds')
    @patch('src.main.fetch_all')
    @patch('src.main.send_admin')
    def test_main_no_items_fetched(self, mock_send_admin, mock_fetch, mock_load_feeds):
        """Test main when no items are fetched"""
        mock_load_feeds.return_value = [{
            "feed_url": "https://example.com/feed",
            "channel_id": "CHAN_ENV",
            "rules": {},
            "topic": "t",
        }]
        mock_fetch.return_value = {"https://example.com/feed": Mock(entries=[])}
        
        with patch('builtins.print') as mock_print:
            main()
            mock_print.assert_called_with("No items fetched.")

    @patch.dict(os.environ, {
        "TELEGRAM_BOT_TOKEN": "test_token",
        "TELEGRAM_CHANNEL_ID": "123",
        "TELEGRAM_ADMIN_CHANNEL_ID": "456",
        "CHAN_ENV": "123",
    })
    @patch('src.main.load_feeds')
    @patch('src.main.fetch_all')
    @patch('src.main.normalize_feed')
    @patch('src.main.select_new_items')
    @patch('src.main.send_admin')
    def test_main_send_failure(self, mock_send_admin, mock_select, mock_normalize,
                               mock_fetch, mock_load_feeds):
        """Test main when send_items fails"""
        # mimic normal flow then inject send_items failure
        mock_load_feeds.return_value = [{
            "feed_url": "https://example.com/feed",
            "channel_id": "CHAN_ENV",
            "rules": {},
            "topic": "t",
        }]
        mock_fetch.return_value = {"https://example.com/feed": Mock()}
        mock_normalize.return_value = [
            {"title": "Article", "link": "https://example.com/1", "feed_url": "url", "feed_title": "Feed"}
        ]
        mock_select.return_value = [
            {"title": "Article", "link": "https://example.com/1", "feed_url": "url", 
             "feed_title": "Feed", "_fingerprint": "abc", "channel_id": "CHAN_ENV"}
        ]
        
        with patch('src.main.send_items', side_effect=Exception("Send failed")):
            with patch('builtins.print') as mock_print:
                main()
                mock_print.assert_called_with("Failed to send items. Exiting without marking as seen.")

    @patch.dict(os.environ, {
        "TELEGRAM_BOT_TOKEN": "test_token",
        "TELEGRAM_CHANNEL_ID": "123",
        "TELEGRAM_ADMIN_CHANNEL_ID": "456",
        "CHAN_ENV": "123",
    }, clear=True)
    @patch('src.main.send_admin')
    @patch('src.main.load_feeds')
    def test_main_missing_state_gist(self, mock_load_feeds, mock_send_admin):
        """Missing STATE_GIST_ID/ token short-circuits with admin notification"""
        with patch('builtins.print') as mock_print:
            main()
            mock_print.assert_any_call("✗ STATE_GIST_ID and GH_GIST_UPDATE_TOKEN must be set.")
            mock_send_admin.assert_called_once()
