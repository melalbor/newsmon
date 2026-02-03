# src/telegram_msg.py

import time
import re
import requests
import json


def send_message_with_backoff(bot_token: str, chat_id: str, text: str, max_retries: int = 3):
    """
    Send a message with exponential backoff retry logic for rate limiting.
    Handles Telegram's rate limiting errors gracefully.
    """
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    
    # Retry with exponential backoff
    retry_count = 0
    while retry_count <= max_retries:
        try:
            response = requests.post(url, json=payload, timeout=10)
            
            # Check for errors
            if response.status_code == 429:  # Rate limit error
                # Try to extract retry-after header or use exponential backoff
                retry_after = None
                if "Retry-After" in response.headers:
                    retry_after = int(response.headers["Retry-After"])
                else:
                    retry_after = 60 * (2 ** retry_count)
                
                if retry_count < max_retries:
                    print(f"⏳ Telegram rate limit hit. Waiting {retry_after}s before retry {retry_count + 1}/{max_retries}...")
                    time.sleep(retry_after)
                    retry_count += 1
                    continue
                else:
                    raise RuntimeError(f"Failed to send message after {max_retries} retries: Rate limit (429)")
            elif response.status_code == 419 or not response.ok:
                # 419 or other HTTP errors - fail immediately
                error_text = response.text[:200]  # Limit error text for logging
                raise RuntimeError(f"Failed to send message to {chat_id}: HTTP {response.status_code}: {error_text}")
            
            return  # Success
        except requests.exceptions.RequestException as e:
            # Network errors - fail immediately
            raise RuntimeError(f"Failed to send message to {chat_id}: {e}") from e
    
    raise RuntimeError(f"Failed to send message to {chat_id}")


def send_message(bot_token: str, chat_id: str, text: str):
    """Send a message via Telegram Bot API."""
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    
    try:
        response = requests.post(url, json=payload, timeout=10)
        
        if not response.ok:
            error_text = response.text[:200]
            raise RuntimeError(f"Failed to send message to {chat_id}: HTTP {response.status_code}: {error_text}")
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f"Failed to send message to {chat_id}: {e}") from e


def send_items(bot_token: str, chat_id: str, items: list, pause_sec: float = 0.3):
    """
    Send each item as a separate message.
    Pause between messages and use backoff retry for rate limiting.
    """
    for item in items:
        ts = str(item.get('published')).split()[0] if item.get('published') else ''
        text = f"📰 {item['feed_title']} / {item['title']}\n{ts}\n\n{item['link']}"
        try:
            send_message_with_backoff(bot_token, chat_id, text)
        except Exception as e:
            raise RuntimeError(f"Failed to send item: {e}") from e
        time.sleep(pause_sec)


def send_admin(bot_token: str, admin_chat_id: str, text: str):
    """
    Send admin notifications (errors, overflows, etc.)
    """
    try:
        send_message(bot_token, admin_chat_id, f"⚠️ {text}")
    except Exception as e:
        # Log but don't crash on admin notification failures
        print(f"⚠️  Failed to send admin notification: {e}")