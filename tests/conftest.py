"""
Pytest configuration and fixtures for newsmon tests.

This conftest.py file is automatically loaded by pytest and provides:
- Validation of feeds.yaml configuration before tests run
- Shared fixtures across all test modules
"""

import pytest
import yaml
from pathlib import Path


@pytest.fixture(scope="session", autouse=True)
def validate_feeds_yaml_on_startup():
    """
    Validate feeds.yaml configuration before any tests run.
    
    This fixture runs automatically at the start of the test session
    and ensures the feeds.yaml file is valid before proceeding with tests.
    """
    feeds_path = Path("feeds.yaml")
    
    # Check file exists
    assert feeds_path.exists(), "feeds.yaml file must exist in project root"
    
    # Load and parse YAML
    try:
        with open(feeds_path, 'r') as f:
            data = yaml.safe_load(f)
    except yaml.YAMLError as e:
        pytest.fail(f"feeds.yaml contains invalid YAML: {e}")
    
    # New format: root must be a dict containing 'topics'
    assert isinstance(data, dict), f"feeds.yaml root element must be a mapping, got {type(data).__name__}"
    assert 'topics' in data, "feeds.yaml must contain a 'topics' key"
    assert isinstance(data['topics'], dict), "'topics' value must be a mapping"
    assert data['topics'], "'topics' mapping cannot be empty"

    # validate each topic configuration
    for topic_name, topic_cfg in data['topics'].items():
        assert isinstance(topic_cfg, dict), f"Topic '{topic_name}' must be a mapping"
        assert 'channel_id' in topic_cfg and isinstance(topic_cfg['channel_id'], str), \
            f"Topic '{topic_name}' must declare a string channel_id"
        assert 'feeds' in topic_cfg and isinstance(topic_cfg['feeds'], list), \
            f"Topic '{topic_name}' must declare a list of feeds"
        assert topic_cfg['feeds'], f"Topic '{topic_name}' feeds list cannot be empty"

        for i, feed in enumerate(topic_cfg['feeds'], 1):
            if isinstance(feed, str):
                feed_url = feed
            elif isinstance(feed, dict):
                assert 'url' in feed and isinstance(feed['url'], str), \
                    f"Feed #{i} in topic '{topic_name}' must have a 'url' string"
                feed_url = feed['url']
                if 'rules' in feed:
                    assert isinstance(feed['rules'], dict), \
                        f"Rules for feed '{feed_url}' must be a mapping"
                    for key in feed['rules']:
                        assert key in ('allow', 'deny'), \
                            f"Unknown rule '{key}' in feed '{feed_url}'"
                        assert isinstance(feed['rules'][key], list), \
                            f"Rule '{key}' in feed '{feed_url}' must be a list"
            else:
                pytest.fail(f"Feed entry in topic '{topic_name}' must be string or mapping")
            assert feed_url.startswith(('http://', 'https://')), \
                f"Feed URL must start with http:// or https://: {feed_url}"
            assert len(feed_url.strip()) > len('http://'), f"Feed URL appears empty: {feed_url}"
