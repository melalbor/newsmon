"""Unit tests for telegram_msg.py module"""

import pytest
from unittest.mock import patch, MagicMock
from src.telegram_msg import send_message, send_items, send_admin


class TestTelegramMessage:
    """Test send_message function"""

    def test_send_message_calls_requests(self):
        """Test that send_message makes POST request to Telegram API"""
        with patch('src.telegram_msg.requests.post') as mock_post:
            mock_response = MagicMock()
            mock_response.ok = True
            mock_post.return_value = mock_response
            
            send_message("test_token", "12345", "Test message")
            
            mock_post.assert_called_once()
            call_args = mock_post.call_args
            assert "api.telegram.org" in call_args[0][0]
            assert call_args[1]["json"]["chat_id"] == "12345"
            assert call_args[1]["json"]["text"] == "Test message"

    def test_send_message_correct_url_format(self):
        """Test that send_message uses correct Telegram API URL"""
        with patch('src.telegram_msg.requests.post') as mock_post:
            mock_response = MagicMock()
            mock_response.ok = True
            mock_post.return_value = mock_response
            
            send_message("test_token_123", "chat_456", "Test")
            
            url = mock_post.call_args[0][0]
            assert "test_token_123" in url
            assert "sendMessage" in url

    def test_send_message_correct_parameters(self):
        """Test that send_message passes correct chat_id and text"""
        with patch('src.telegram_msg.requests.post') as mock_post:
            mock_response = MagicMock()
            mock_response.ok = True
            mock_post.return_value = mock_response
            
            send_message("token", "chat_123", "Hello Telegram")
            
            json_payload = mock_post.call_args[1]["json"]
            assert json_payload["chat_id"] == "chat_123"
            assert json_payload["text"] == "Hello Telegram"

    def test_send_message_exception_handling(self):
        """Test that send_message raises RuntimeError on failure"""
        with patch('src.telegram_msg.requests.post') as mock_post:
            mock_response = MagicMock()
            mock_response.ok = False
            mock_response.status_code = 400
            mock_response.text = "Bad Request"
            mock_post.return_value = mock_response
            
            with pytest.raises(RuntimeError) as exc_info:
                send_message("token", "123", "Message")
            
            assert "Failed to send message" in str(exc_info.value)

    def test_send_message_handles_419_error(self):
        """Test that send_message handles 419 errors"""
        with patch('src.telegram_msg.requests.post') as mock_post:
            mock_response = MagicMock()
            mock_response.ok = False
            mock_response.status_code = 419
            mock_response.text = "Telegram error"
            mock_post.return_value = mock_response
            
            with pytest.raises(RuntimeError) as exc_info:
                send_message("token", "123", "Message")
            
            assert "419" in str(exc_info.value)


class TestTelegramItems:
    """Test send_items function"""

    def test_send_items_single_item(self):
        """Test sending a single item"""
        with patch('src.telegram_msg.send_message_with_backoff') as mock_send:
            items = [
                {"title": "Article", "feed_title": "Feed", "link": "http://example.com"}
            ]
            send_items("token", "123", items, pause_sec=0.01)
            
            mock_send.assert_called_once()

    def test_send_items_multiple_items(self):
        """Test sending multiple items"""
        with patch('src.telegram_msg.send_message_with_backoff') as mock_send:
            items = [
                {"title": "Article 1", "feed_title": "Feed A", "link": "http://example.com/1"},
                {"title": "Article 2", "feed_title": "Feed B", "link": "http://example.com/2"},
                {"title": "Article 3", "feed_title": "Feed C", "link": "http://example.com/3"},
            ]
            send_items("token", "123", items, pause_sec=0.01)
            
            assert mock_send.call_count == 3

    def test_send_items_message_format(self):
        """Test that items are formatted correctly"""
        with patch('src.telegram_msg.send_message_with_backoff') as mock_send:
            items = [
                {"title": "Breaking News", "feed_title": "News Feed", "link": "http://news.com/1"}
            ]
            send_items("token", "123", items, pause_sec=0.01)
            
            call_args = mock_send.call_args[0]
            message = call_args[2]
            
            # Check message format
            assert "📰" in message
            assert "Breaking News" in message
            assert "News Feed" in message
            assert "http://news.com/1" in message

    def test_send_items_empty_list(self):
        """Test sending empty items list"""
        with patch('src.telegram_msg.send_message_with_backoff') as mock_send:
            send_items("token", "123", [], pause_sec=0.01)
            
            mock_send.assert_not_called()

    def test_send_items_pause_between_messages(self):
        """Test that pause_sec is respected (at least has sleep call)"""
        with patch('src.telegram_msg.send_message_with_backoff'):
            with patch('src.telegram_msg.time.sleep') as mock_sleep:
                items = [
                    {"title": "A", "feed_title": "F", "link": "http://example.com/1"},
                    {"title": "B", "feed_title": "F", "link": "http://example.com/2"},
                ]
                send_items("token", "123", items, pause_sec=0.5)
                
                # sleep should be called once per item
                assert mock_sleep.call_count == 2
                # Check it was called with correct pause value
                for call_obj in mock_sleep.call_args_list:
                    assert call_obj[0][0] == 0.5


class TestTelegramAdmin:
    """Test send_admin function"""

    def test_send_admin_format(self):
        """Test that admin messages have warning emoji"""
        with patch('src.telegram_msg.send_message') as mock_send:
            send_admin("token", "admin_id", "Error occurred")
            
            call_args = mock_send.call_args[0]
            message = call_args[2]
            
            assert "⚠️" in message
            assert "Error occurred" in message

    def test_send_admin_calls_send_message(self):
        """Test that send_admin calls send_message"""
        with patch('src.telegram_msg.send_message') as mock_send:
            send_admin("token", "admin_id", "Test")
            
            mock_send.assert_called_once()
            call_args = mock_send.call_args[0]
            
            assert call_args[0] == "token"
            assert call_args[1] == "admin_id"

    def test_send_admin_error_propagates(self):
        """Test that send_admin handles errors gracefully (doesn't crash)"""
        with patch('src.telegram_msg.send_message') as mock_send:
            mock_send.side_effect = RuntimeError("Send failed")
            
            # Should not raise, just print error
            with patch('builtins.print') as mock_print:
                send_admin("token", "admin_id", "Message")
                # Verify error was logged
                mock_print.assert_called()
                assert "Failed to send admin notification" in str(mock_print.call_args)


class TestTelegramRateLimiting:
    """Test rate limiting and backoff logic"""

    def test_rate_limit_429_triggers_backoff(self):
        """Test that 429 rate limit error triggers retry with backoff"""
        from src.telegram_msg import send_message_with_backoff
        
        with patch('src.telegram_msg.requests.post') as mock_post:
            # First two calls fail with 429, third succeeds
            mock_response_fail = MagicMock()
            mock_response_fail.status_code = 429
            mock_response_fail.ok = False
            
            mock_response_success = MagicMock()
            mock_response_success.ok = True
            
            mock_post.side_effect = [mock_response_fail, mock_response_fail, mock_response_success]
            
            with patch('src.telegram_msg.time.sleep') as mock_sleep:
                # Should succeed after retries
                send_message_with_backoff("token", "123", "Test")
                
                # Verify retries happened
                assert mock_post.call_count == 3
                # Verify sleep was called for backoff
                assert mock_sleep.call_count == 2

    def test_rate_limit_max_retries_exceeded(self):
        """Test that max retries gives up gracefully"""
        from src.telegram_msg import send_message_with_backoff
        
        with patch('src.telegram_msg.requests.post') as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 429
            mock_response.ok = False
            mock_post.return_value = mock_response
            
            with patch('src.telegram_msg.time.sleep'):
                with pytest.raises(RuntimeError) as exc_info:
                    send_message_with_backoff("token", "123", "Test", max_retries=2)
                
                assert "Failed to send message after 2 retries" in str(exc_info.value)

    def test_other_errors_not_retried(self):
        """Test that non-429 errors are not retried"""
        from src.telegram_msg import send_message_with_backoff
        
        with patch('src.telegram_msg.requests.post') as mock_post:
            mock_response = MagicMock()
            mock_response.status_code = 400
            mock_response.ok = False
            mock_response.text = "Bad Request"
            mock_post.return_value = mock_response
            
            with patch('src.telegram_msg.time.sleep') as mock_sleep:
                with pytest.raises(RuntimeError):
                    send_message_with_backoff("token", "123", "Test", max_retries=2)
                
                # Should fail immediately, no retries
                assert mock_post.call_count == 1
                assert mock_sleep.call_count == 0

    def test_rate_limit_with_retry_after_header(self):
        """Test that Retry-After header is respected"""
        from src.telegram_msg import send_message_with_backoff
        
        with patch('src.telegram_msg.requests.post') as mock_post:
            mock_response_fail = MagicMock()
            mock_response_fail.status_code = 429
            mock_response_fail.ok = False
            mock_response_fail.headers = {"Retry-After": "30"}
            
            mock_response_success = MagicMock()
            mock_response_success.ok = True
            
            mock_post.side_effect = [mock_response_fail, mock_response_success]
            
            with patch('src.telegram_msg.time.sleep') as mock_sleep:
                send_message_with_backoff("token", "123", "Test")
                
                # Verify sleep was called with Retry-After value
                mock_sleep.assert_called_once_with(30)


class TestTelegramIntegration:
    """Integration tests for Telegram functionality"""

    def test_full_workflow_single_item(self):
        """Test complete workflow sending single item"""
        with patch('src.telegram_msg.requests.post') as mock_post:
            mock_response = MagicMock()
            mock_response.ok = True
            mock_post.return_value = mock_response
            
            item = {"title": "Test", "feed_title": "Feed", "link": "http://example.com"}
            send_items("token", "123", [item], pause_sec=0.01)
            
            # Verify POST was called
            mock_post.assert_called()
            # Verify correct URL and payload
            url = mock_post.call_args[0][0]
            json_payload = mock_post.call_args[1]["json"]
            assert "sendMessage" in url
            assert json_payload["chat_id"] == "123"
