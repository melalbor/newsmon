#!/usr/bin/env python3
"""
Comprehensive test for validating actual feeds.yaml URL parsing and structure.
This tests the exact feeds present in the production feeds.yaml file.
"""

import pytest
import yaml
from pathlib import Path


@pytest.fixture(scope="session")
def feeds_data():
    """Load the actual feeds.yaml file once for all tests"""
    feeds_path = Path("feeds.yaml")
    if feeds_path.exists():
        with open(feeds_path, 'r') as f:
            return yaml.safe_load(f)
    return None


class TestActualFeedsYaml:
    """Test actual feeds.yaml file parsing and validation"""

    def test_feeds_yaml_exists(self):
        """Verify feeds.yaml file exists"""
        assert Path("feeds.yaml").exists(), "feeds.yaml file must exist"

    def test_feeds_data_is_list(self, feeds_data):
        """Verify feeds data is a list"""
        assert feeds_data is not None, "feeds.yaml must be readable"
        assert isinstance(feeds_data, list), "feeds.yaml must contain a list"

    def test_feeds_list_not_empty(self, feeds_data):
        """Verify feeds list is not empty"""
        assert len(feeds_data) > 0, "feeds list must not be empty"

    def test_feeds_count(self, feeds_data):
        """Verify expected number of feeds (currently 5)"""
        assert len(feeds_data) == 5, f"Expected 5 feeds, got {len(feeds_data)}"

    def test_all_feeds_are_strings(self, feeds_data):
        """Verify all feed URLs are strings"""
        for i, feed in enumerate(feeds_data):
            assert isinstance(feed, str), f"Feed #{i+1} must be a string, got {type(feed).__name__}"

    def test_all_feeds_start_with_https_or_http(self, feeds_data):
        """Verify all feeds start with http:// or https://"""
        for i, feed in enumerate(feeds_data):
            assert feed.startswith(('http://', 'https://')), \
                f"Feed #{i+1} must start with http:// or https://: {feed}"

    def test_no_duplicate_feeds(self, feeds_data):
        """Verify there are no duplicate feed URLs"""
        assert len(feeds_data) == len(set(feeds_data)), \
            "Feed list contains duplicates"

    def test_feed_urls_not_empty_strings(self, feeds_data):
        """Verify no feed URL is an empty string"""
        for i, feed in enumerate(feeds_data):
            assert len(feed.strip()) > 0, f"Feed #{i+1} cannot be empty"

    def test_feed_urls_have_domain(self, feeds_data):
        """Verify each feed has a domain (at least one dot)"""
        for i, feed in enumerate(feeds_data):
            # Remove protocol
            domain_part = feed.split('://', 1)[1] if '://' in feed else feed
            # Should have at least one dot (domain separator)
            assert '.' in domain_part, \
                f"Feed #{i+1} must have a domain with dot: {feed}"

    def test_specific_apple_feed(self, feeds_data):
        """Verify Apple releases feed is present and correct"""
        expected = "https://developer.apple.com/news/releases/rss/releases.rss"
        assert expected in feeds_data, \
            f"Apple releases feed not found. Expected: {expected}"

    def test_specific_grapheneos_feed(self, feeds_data):
        """Verify GrapheneOS releases feed is present and correct"""
        expected = "https://grapheneos.org/releases.atom"
        assert expected in feeds_data, \
            f"GrapheneOS feed not found. Expected: {expected}"

    def test_specific_securelist_feed(self, feeds_data):
        """Verify Securelist feed is present and correct"""
        expected = "https://securelist.com/threat-category/mobile-threats/feed/"
        assert expected in feeds_data, \
            f"Securelist feed not found. Expected: {expected}"

    def test_specific_citizenlab_feed(self, feeds_data):
        """Verify CitizenLab feed is present and correct"""
        expected = "https://citizenlab.ca/feed/"
        assert expected in feeds_data, \
            f"CitizenLab feed not found. Expected: {expected}"

    def test_specific_amnesty_feed(self, feeds_data):
        """Verify Amnesty security lab feed is present and correct"""
        expected = "https://securitylab.amnesty.org/feed/"
        assert expected in feeds_data, \
            f"Amnesty security lab feed not found. Expected: {expected}"

    def test_feed_order_preserved(self, feeds_data):
        """Verify feeds are in expected order"""
        expected_order = [
            "https://developer.apple.com/news/releases/rss/releases.rss",
            "https://grapheneos.org/releases.atom",
            "https://securelist.com/threat-category/mobile-threats/feed/",
            "https://citizenlab.ca/feed/",
            "https://securitylab.amnesty.org/feed/"
        ]
        assert feeds_data == expected_order, \
            "Feed order does not match expected order"

    def test_no_rss_feeds_have_malformed_urls(self, feeds_data):
        """Verify RSS feeds have proper .rss extension"""
        rss_feeds = [f for f in feeds_data if 'rss' in f.lower()]
        for feed in rss_feeds:
            # Either has .rss or /feed/ or /feed suffix
            has_rss_format = (feed.endswith('.rss') or 
                            '/rss' in feed or 
                            feed.endswith('/feed/') or
                            feed.endswith('/feed') or
                            'feed' in feed.lower())
            assert has_rss_format, f"RSS feed may be malformed: {feed}"

    def test_atom_feeds_format(self, feeds_data):
        """Verify Atom feeds are properly formatted"""
        atom_feeds = [f for f in feeds_data if '.atom' in f.lower()]
        for feed in atom_feeds:
            assert feed.endswith('.atom'), f"Atom feed should end with .atom: {feed}"

    def test_feeds_have_valid_schemes(self, feeds_data):
        """Verify all feeds use secure HTTPS where possible"""
        # Most modern feeds should use HTTPS
        http_feeds = [f for f in feeds_data if f.startswith('http://')]
        https_feeds = [f for f in feeds_data if f.startswith('https://')]
        
        assert len(https_feeds) > 0, "At least some feeds should use HTTPS"
        # Note: We don't fail if some use HTTP, just report

    def test_feeds_uniqueness_by_domain(self, feeds_data):
        """Verify feeds are from different sources (different domains)"""
        domains = set()
        for feed in feeds_data:
            # Extract domain from URL
            domain = feed.split('://')[1].split('/')[0] if '://' in feed else feed
            domains.add(domain)
        
        # Should have at least as many domains as feeds (typically more)
        # Unless multiple feeds from same source
        assert len(domains) >= 4, f"Expected at least 4 different domains, got {len(domains)}"

    def test_feed_urls_accessible_format(self, feeds_data):
        """Verify feed URLs have reasonable accessibility paths"""
        required_path_indicators = ['feed', 'rss', 'atom', 'releases']
        for i, feed in enumerate(feeds_data):
            # Check if URL contains feed/rss/atom/releases indicator
            url_lower = feed.lower()
            has_indicator = any(indicator in url_lower for indicator in required_path_indicators)
            assert has_indicator, \
                f"Feed #{i+1} should contain feed/rss/atom/releases indicator: {feed}"

    def test_yaml_file_valid_format(self):
        """Verify the YAML file itself is valid and correctly formatted"""
        # This is already tested by feeds_data fixture loading without error
        # but we add explicit assertion
        with open('feeds.yaml', 'r') as f:
            content = f.read()
        
        assert content.startswith('-'), \
            "feeds.yaml should be a YAML list (start with -)"
        
        # Each line should start with - or be empty/comment
        for i, line in enumerate(content.split('\n'), 1):
            if line.strip() and not line.strip().startswith('#'):
                assert line.strip().startswith('-'), \
                    f"Line {i} should start with '-': {line}"


class TestFeedsYamlComparison:
    """Test feeds.yaml against expected structure"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Load feeds for comparison tests"""
        with open('feeds.yaml', 'r') as f:
            self.feeds = yaml.safe_load(f)

    def test_feeds_list_integrity(self):
        """Comprehensive test of feeds list integrity"""
        # All items should be strings
        assert all(isinstance(f, str) for f in self.feeds), \
            "All feeds must be strings"
        # All should be URLs
        assert all(f.startswith(('http://', 'https://')) for f in self.feeds), \
            "All feeds must be URLs"
        # Should have expected count
        assert len(self.feeds) == 5, f"Expected 5 feeds, got {len(self.feeds)}"

    def test_print_feeds_for_inspection(self, capsys):
        """Print feed details for manual inspection"""
        output_lines = [
            "\n" + "=" * 70,
            "FEEDS YAML CONTENT INSPECTION",
            "=" * 70,
        ]
        
        for i, feed in enumerate(self.feeds, 1):
            output_lines.append(f"\n  Feed #{i}:")
            output_lines.append(f"    Type: {type(feed).__name__}")
            output_lines.append(f"    Length: {len(feed)} characters")
            output_lines.append(f"    URL: {feed}")
            
            # Parse URL components
            if '://' in feed:
                protocol, rest = feed.split('://', 1)
                if '/' in rest:
                    domain, path = rest.split('/', 1)
                    output_lines.append(f"    Protocol: {protocol}")
                    output_lines.append(f"    Domain: {domain}")
                    output_lines.append(f"    Path: /{path}")
        
        output_lines.append("\n" + "=" * 70)
        
        # In pytest, we can still use print which gets captured
        for line in output_lines:
            print(line)
