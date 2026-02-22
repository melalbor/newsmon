#!/usr/bin/env python3
"""
Validation tests for the current feeds.yaml configuration.

The repository moved from a flat list of URLs to a more structured "topics"
mapping, where each topic has a channel_id and a list of feeds (optionally with
allow/deny rules).  These tests reflect the new shape and still perform basic
sanity checks on the data contained in the file.
"""

import pytest
import yaml
from pathlib import Path


@pytest.fixture(scope="session")
def feeds_data():
    """Load and return the raw YAML mapping from feeds.yaml."""
    feeds_path = Path("feeds.yaml")
    if feeds_path.exists():
        with open(feeds_path, 'r') as f:
            return yaml.safe_load(f)
    return None


class TestActualFeedsYaml:
    """Tests that exercise the real feeds.yaml contents."""

    def test_file_exists(self):
        assert Path("feeds.yaml").exists(), "feeds.yaml file must exist"

    def test_root_structure(self, feeds_data):
        assert isinstance(feeds_data, dict), "root must be a mapping"
        assert "topics" in feeds_data, "must define 'topics'"
        assert isinstance(feeds_data["topics"], dict), "'topics' must be a mapping"
        assert feeds_data["topics"], "there must be at least one topic"

    def test_each_topic_valid(self, feeds_data):
        for topic, cfg in feeds_data["topics"].items():
            assert isinstance(cfg, dict)
            assert "channel_id" in cfg and isinstance(cfg["channel_id"], str)
            assert "feeds" in cfg and isinstance(cfg["feeds"], list)
            assert cfg["feeds"], f"topic '{topic}' cannot have an empty feed list"
            for feed in cfg["feeds"]:
                if isinstance(feed, str):
                    url = feed
                else:
                    assert "url" in feed and isinstance(feed["url"], str)
                    url = feed["url"]
                assert url.startswith(("http://", "https://")), f"bad url: {url}"

    def test_no_duplicate_urls(self, feeds_data):
        seen = set()
        for cfg in feeds_data["topics"].values():
            for feed in cfg["feeds"]:
                url = feed if isinstance(feed, str) else feed.get("url")
                assert url not in seen, f"duplicate url {url}"
                seen.add(url)

    def test_rule_keys_are_valid(self, feeds_data):
        for cfg in feeds_data["topics"].values():
            for feed in cfg["feeds"]:
                if isinstance(feed, dict) and "rules" in feed:
                    rules = feed["rules"]
                    assert isinstance(rules, dict)
                    for key in rules:
                        assert key in ("allow", "deny"), f"unknown rule {key}"
                        assert isinstance(rules[key], list), f"rule {key} must be a list"

    def test_simple_url_checks(self, feeds_data):
        # flatten urls for convenience
        urls = []
        for cfg in feeds_data["topics"].values():
            for feed in cfg["feeds"]:
                urls.append(feed if isinstance(feed, str) else feed.get("url"))

        assert urls, "we must have at least one url"
        assert all(url.startswith(("http://", "https://")) for url in urls)
        assert len(urls) == len(set(urls)), "no duplicates allowed"

        domains = {url.split('://',1)[1].split('/')[0] for url in urls}
        assert len(domains) >= 1


class TestFeedsYamlComparison:
    """Additional generic sanity checks used during development."""

    @pytest.fixture(autouse=True)
    def setup(self):
        with open('feeds.yaml', 'r') as f:
            self.data = yaml.safe_load(f)

    def test_topics_listed(self):
        assert isinstance(self.data.get("topics"), dict)
        assert self.data["topics"], "topics mapping empty"

    def test_print_for_debug(self, capsys):
        print(yaml.dump(self.data))
