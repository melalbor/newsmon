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
    
    # Check type is list
    assert isinstance(data, list), f"feeds.yaml root element must be a list, got {type(data).__name__}"
    
    # Check not empty
    assert len(data) > 0, "feeds.yaml list cannot be empty"
    
    # Validate each item is a string URL
    for i, item in enumerate(data, 1):
        assert isinstance(item, str), f"Feed #{i} must be a string, got {type(item).__name__}"
        assert item.startswith(('http://', 'https://')), f"Feed #{i} must start with http:// or https://"
        assert len(item.strip()) > len('http://'), f"Feed #{i} URL appears empty or too short"
