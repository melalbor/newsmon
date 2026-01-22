#!/usr/bin/env python3
"""Test rate limiting and backoff logic"""

import pytest
import time
from unittest.mock import patch, MagicMock
from src.telegram_msg import send_message_with_backoff
import requests


class TestRateLimitingBackoff:
    """Tests for rate limiting and backoff logic"""

    def test_rate_limit_backoff(self):
        """Test that rate limit error triggers retry with backoff"""
        # Create a mock response that fails twice with rate limit (429), then succeeds
        attempt = [0]
        
        def mock_post(*args, **kwargs):
            attempt[0] += 1
            response = MagicMock()
            if attempt[0] <= 2:
                response.status_code = 429  # Rate limit error
                response.ok = False
                response.headers = {"Retry-After": "1"}
                return response
            else:
                response.status_code = 200  # Success
                response.ok = True
                return response
        
        with patch('src.telegram_msg.requests.post', side_effect=mock_post):
            with patch('src.telegram_msg.time.sleep') as mock_sleep:
                send_message_with_backoff("token", "123", "Test", max_retries=3)
                
                # Verify retries happened
                assert attempt[0] == 3, f"Expected 3 attempts, got {attempt[0]}"
                
                # Verify sleep was called (backoff delays)
                assert mock_sleep.call_count >= 2, "Expected sleep to be called for backoff"

    def test_rate_limit_max_retries_exceeded(self):
        """Test that max retries gives up gracefully"""
        
        def mock_post(*args, **kwargs):
            response = MagicMock()
            response.status_code = 429  # Rate limit error
            response.ok = False
            response.headers = {}
            return response
        
        with patch('src.telegram_msg.requests.post', side_effect=mock_post):
            with patch('src.telegram_msg.time.sleep'):
                with pytest.raises(RuntimeError, match="Failed to send message after 2 retries"):
                    send_message_with_backoff("token", "123", "Test", max_retries=2)

    def test_normal_error_not_retried(self):
        """Test that non-rate-limit errors (419, 500) are not retried"""
        
        def mock_post(*args, **kwargs):
            response = MagicMock()
            response.status_code = 419  # Client error (not rate limit)
            response.ok = False
            response.text = "Some error"
            return response
        
        with patch('src.telegram_msg.requests.post', side_effect=mock_post):
            with patch('src.telegram_msg.time.sleep') as mock_sleep:
                with pytest.raises(RuntimeError, match="Failed to send message"):
                    send_message_with_backoff("token", "123", "Test", max_retries=2)
                
                # Should not retry on non-rate-limit errors
                assert mock_sleep.call_count == 0, "Should not retry on non-rate-limit errors"

    def test_network_error_not_retried(self):
        """Test that network errors are not retried"""
        
        with patch('src.telegram_msg.requests.post', side_effect=requests.exceptions.ConnectionError("Network error")):
            with patch('src.telegram_msg.time.sleep') as mock_sleep:
                with pytest.raises(RuntimeError, match="Failed to send message"):
                    send_message_with_backoff("token", "123", "Test", max_retries=2)
                
                # Should not retry on network errors
                assert mock_sleep.call_count == 0, "Should not retry on network errors"
