#!/usr/bin/env python3
"""Real Telegram integration test - sends actual test messages"""

import pytest
import os
from datetime import datetime
from unittest.mock import patch, MagicMock
from src.telegram_msg import send_message, send_items, send_admin
import requests


@pytest.fixture
def telegram_credentials():
    """Fixture for Telegram credentials from environment"""
    return {
        "bot_token": os.environ.get("TELEGRAM_BOT_TOKEN"),
        "admin_channel_id": os.environ.get("TELEGRAM_ADMIN_CHANNEL_ID"),
        # TELEGRAM_CHANNEL_ID is a convenient fallback for quick tests; in
        # production you would normally specify channel IDs in feeds.yaml instead.
        "test_channel_id": os.environ.get("TELEGRAM_CHANNEL_ID"),
    }


class TestTelegramRealIntegration:
    """Real Telegram integration tests - require valid credentials"""

    @pytest.mark.skipif(not os.environ.get("TELEGRAM_BOT_TOKEN"), 
                        reason="TELEGRAM_BOT_TOKEN not set")
    @pytest.mark.skipif(not os.environ.get("TELEGRAM_ADMIN_CHANNEL_ID"),
                        reason="TELEGRAM_ADMIN_CHANNEL_ID not set")
    def test_send_admin_message(self, telegram_credentials):
        """Test sending message to admin channel"""
        bot_token = telegram_credentials["bot_token"]
        admin_channel_id = telegram_credentials["admin_channel_id"]
        
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        test_message = f"🤖 Test message from newsmon integration test\nTime: {timestamp}"
        
        # Should not raise exception
        send_admin(bot_token, admin_channel_id, test_message)

    @pytest.mark.skipif(not os.environ.get("TELEGRAM_BOT_TOKEN"),
                        reason="TELEGRAM_BOT_TOKEN not set")
    @pytest.mark.skipif(not os.environ.get("TELEGRAM_CHANNEL_ID"),
                        reason="TELEGRAM_CHANNEL_ID not set (fallback for real tests)")
    def test_send_message_to_channel(self, telegram_credentials):
        """Test sending message to test channel"""
        bot_token = telegram_credentials["bot_token"]
        test_channel_id = telegram_credentials["test_channel_id"]
        
        sample_message = "📰 Test Article - Telegram Integration\nhttps://example.com/helloworld"
        
        # Should not raise exception
        send_message(bot_token, test_channel_id, sample_message)

    @pytest.mark.skipif(not os.environ.get("TELEGRAM_BOT_TOKEN"),
                        reason="TELEGRAM_BOT_TOKEN not set")
    @pytest.mark.skipif(not os.environ.get("TELEGRAM_CHANNEL_ID"),
                        reason="TELEGRAM_CHANNEL_ID not set (fallback for real tests)")
    def test_send_multiple_items(self, telegram_credentials):
        """Test sending multiple items to channel"""
        bot_token = telegram_credentials["bot_token"]
        test_channel_id = telegram_credentials["test_channel_id"]
        
        test_items = [
            {
                "title": "Test Item 1 - Age Filter Check",
                "feed_title": "Debug Feed",
                "link": "https://example.com/1",
                "published": "2024-01-21"
            },
            {
                "title": "Test Item 2 - Dedup Check",
                "feed_title": "Debug Feed",
                "link": "https://example.com/2",
                "published": "2024-01-20"
            }
        ]
        
        # Should not raise exception
        send_items(bot_token, test_channel_id, test_items, pause_sec=0.5)


class TestTelegramMessageFormatting:
    """Test Telegram message formatting and parameters"""

    def test_send_message_works_with_requests(self):
        """Test that send_message uses requests properly"""
        def mock_post(*args, **kwargs):
            response = MagicMock()
            response.status_code = 200
            response.ok = True
            return response
        
        with patch('src.telegram_msg.requests.post', side_effect=mock_post) as mock_post_fn:
            send_message("test_token", "12345", "Test message")
            
            # Verify requests.post was called
            assert mock_post_fn.call_count == 1
            call_args = mock_post_fn.call_args
            
            # Verify URL is correct
            assert "sendMessage" in call_args[0][0]
            # Verify payload
            assert call_args[1]['json']['chat_id'] == "12345"
            assert call_args[1]['json']['text'] == "Test message"

    def test_send_message_error_handling(self):
        """Test that send_message handles errors properly"""
        def mock_post(*args, **kwargs):
            response = MagicMock()
            response.status_code = 400
            response.ok = False
            response.text = "Bad Request"
            return response
        
        with patch('src.telegram_msg.requests.post', side_effect=mock_post):
            with pytest.raises(RuntimeError, match="Failed to send message"):
                send_message("test_token", "12345", "Test message")

    def test_send_items_batch(self):
        """Test that send_items sends multiple items"""
        call_count = [0]
        
        def mock_post(*args, **kwargs):
            call_count[0] += 1
            response = MagicMock()
            response.status_code = 200
            response.ok = True
            return response
        
        with patch('src.telegram_msg.requests.post', side_effect=mock_post):
            with patch('src.telegram_msg.time.sleep'):
                items = [
                    {"title": "Item 1", "feed_title": "Feed A", "link": "http://example.com/1"},
                    {"title": "Item 2", "feed_title": "Feed B", "link": "http://example.com/2"},
                ]
                send_items("token", "123", items, pause_sec=0.01)
                
                # Should send 2 messages
                assert call_count[0] == 2
