# newsmon - RSS to Telegram Bot

An automated RSS feed aggregator that fetches news from multiple sources and sends them to a Telegram channel. Designed for scheduled execution (e.g., daily cron jobs) with built-in deduplication, rate limiting, and error recovery.

## Features

- **Multi-Feed Support**: Monitor 35+ RSS/Atom feeds from diverse sources
- **Intelligent Deduplication**: Fingerprint-based duplicate detection across feeds
- **Automated Scheduling**: GitHub Actions integration for daily execution
- **Rate Limiting**: Exponential backoff with automatic retry on API rate limits
- **Error Handling**: Graceful error handling with proper failure reporting
- **No State Persistence**: Ephemeral in-memory operation - perfect for serverless
- **Comprehensive Testing**: 132 tests with 5.28x test/code ratio
- **Security First**: Environment variables for all sensitive data, no hardcoded secrets

## Project Structure

```
newsmon/
├── src/
│   ├── main.py              # Orchestration and main logic
│   ├── fetch.py             # RSS feed fetching with retries
│   ├── parse.py             # Feed parsing and normalization
│   ├── dedupe.py            # Deduplication and filtering
│   └── telegram_msg.py      # Telegram API integration
├── tests/
│   ├── unit/                # Unit tests (119 tests)
│   ├── integration/         # Integration tests (13 tests)
│   └── __init__.py
├── feeds.yaml               # RSS feed configuration
├── requirements.txt         # Python dependencies
├── pytest.ini               # Pytest configuration
├── .github/workflows/
│   └── rss-bot.yml         # GitHub Actions workflow
└── README.md               # This file
```

## Prerequisites

- **Python**: 3.11+ (tested with 3.12.1)
- **pip**: For package management
- **Telegram Bot Token**: From @BotFather
- **Telegram Channel ID**: Numeric channel identifier
- **Git**: For cloning and version control

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/melalbor/newsmon.git
cd newsmon
```

### 2. Create Virtual Environment

```bash
python3 -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Set Up Environment Variables

Create a `.env` file (not committed to git):

```bash
export TELEGRAM_BOT_TOKEN="your_bot_token_here"
export TELEGRAM_CHANNEL_ID="your_channel_id_here"
export TELEGRAM_ADMIN_CHANNEL_ID="your_admin_channel_id_here"
```

Or set them directly in your shell:

```bash
export TELEGRAM_BOT_TOKEN="..."
export TELEGRAM_CHANNEL_ID="..."
export TELEGRAM_ADMIN_CHANNEL_ID="..."
```

### 5. Verify Installation

```bash
python -m pytest tests/ -v
```

Expected output: `132 passed in ~1.72s`

## Configuration

### feeds.yaml

The `feeds.yaml` file contains the list of RSS/Atom feeds to monitor:

```yaml
feeds:
  - https://example.com/feed/rss
  - https://example.com/atom.xml
  - https://another-source.com/news/feed
  # Add more feed URLs here
```

**Current feeds include sources from:**
- Security organizations (Apple, GrapheneOS, Kaspersky, Citizen Lab, Amnesty International)
- Technology blogs
- News aggregators
- Industry-specific sources

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `TELEGRAM_BOT_TOKEN` | Yes | Bot token from @BotFather |
| `TELEGRAM_CHANNEL_ID` | Yes | Channel ID to post updates |
| `TELEGRAM_ADMIN_CHANNEL_ID` | Yes | Admin channel for notifications |

## Usage

### Local Testing

Run the bot locally to test configuration:

```bash
# Make sure environment variables are set
python -m src.main
```

### Running Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/unit/test_main.py -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html

# Run only fast tests
pytest tests/unit/ -v
```

## Architecture

### Data Flow

```
feeds.yaml
    ↓
[Fetch] → Fetch all feeds with retry logic (10s timeout)
    ↓
[Parse] → Normalize feeds to common format
    ↓
[Dedupe] → Fingerprint-based duplicate detection
    ↓
[Filter] → Keep recent items (configurable age threshold)
    ↓
[Telegram] → Send to channel with rate limiting
    ↓
[Admin] → Notify admin channel of execution status
```

### Key Components

#### fetch.py
- Fetches RSS/Atom feeds with proper User-Agent headers
- 10-second timeout per feed
- Graceful error handling for network issues
- Returns parsed feed objects

#### parse.py
- Normalizes different feed formats to common structure
- Extracts title, link, description, published date
- Falls back to feed-level metadata when item-level is missing
- UTC timezone normalization

#### dedupe.py
- Creates fingerprints using: ID → Link → Title+Link hierarchy
- Maintains in-memory state of seen items
- Filters items by recency (default: 7 days)
- Respects max_items limit per feed

#### telegram_msg.py
- Sends formatted messages to Telegram channel
- Exponential backoff on rate limits (429 errors)
- Admin notifications with execution status
- Message pausing to avoid rapid-fire delivery

#### main.py
- Orchestrates the full workflow
- Loads feeds from YAML configuration
- Coordinates all modules
- Comprehensive error handling and reporting

## Deployment

### GitHub Actions (Recommended)

The project includes a GitHub Actions workflow that automatically runs daily:

**Schedule:** 5 PM UTC daily (configurable via `.github/workflows/rss-bot.yml`)

**Setup Steps:**

1. **Fork/Push to GitHub** - Ensure code is on GitHub

2. **Configure Secrets** - In GitHub repository settings:
   - Go to Settings → Secrets and variables → Actions
   - Add these secrets:
     - `TELEGRAM_BOT_TOKEN`
     - `TELEGRAM_CHANNEL_ID`
     - `TELEGRAM_ADMIN_CHANNEL_ID`

3. **Enable Actions** - Ensure GitHub Actions is enabled

4. **Monitor Runs** - View executions in Actions tab

**Workflow Features:**
- Runs daily at 17:00 UTC
- Automatic retry on transient failures
- Concurrency control (prevents overlapping runs)
- Detailed logging via GitHub Actions

### Docker Deployment

To run in a container:

```dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY src/ ./src/
COPY feeds.yaml .

CMD ["python", "-m", "src.main"]
```

Build and run:

```bash
docker build -t newsmon .
docker run -e TELEGRAM_BOT_TOKEN="..." \
           -e TELEGRAM_CHANNEL_ID="..." \
           -e TELEGRAM_ADMIN_CHANNEL_ID="..." \
           newsmon
```

### Manual Cron Setup (Linux/macOS)

```bash
# Edit crontab
crontab -e

# Add this line to run daily at 5 PM:
0 17 * * * cd /path/to/newsmon && source .venv/bin/activate && python -m src.main
```

## Testing

### Test Coverage

- **Unit Tests (119)**: Individual module functionality
  - Feed fetching (13 tests)
  - Feed parsing (13 tests)
  - Deduplication (21 tests)
  - Telegram messaging (20 tests)
  - Main orchestration (19 tests)
  - Rate limiting (11 tests)
  - Configuration validation (22 tests)

- **Integration Tests (13)**: End-to-end workflows
  - Complete workflow from feed to Telegram
  - Duplicate detection across multiple feeds
  - Max items respected
  - Ephemeral state validation
  - Real Telegram message formatting

### Running Specific Tests

```bash
# Run specific test class
pytest tests/unit/test_dedupe.py::TestFingerprint -v

# Run specific test
pytest tests/unit/test_main.py::TestMain::test_main_success_flow -v

# Run with output capture disabled (for debugging)
pytest tests/ -v -s

# Run with verbose traceback
pytest tests/ -v --tb=long
```

## Performance Characteristics

| Metric | Value | Notes |
|--------|-------|-------|
| Test Execution | ~1.72s | Full test suite (132 tests) |
| Feed Timeout | 10s | Per-feed timeout |
| Telegram Timeout | 10s | Per-message timeout |
| Rate Limit Retries | 5 | With exponential backoff |
| Memory Usage | <50MB | Ephemeral state |
| Typical Run Time | 30-60s | Depends on feed count/size |

## Security

- ✅ **No Hardcoded Secrets**: All credentials via environment variables
- ✅ **Input Validation**: URL scheme and format validation
- ✅ **Error Handling**: Exceptions caught and logged appropriately
- ✅ **Timeout Protection**: All network requests have timeouts
- ✅ **Rate Limiting**: Respects Telegram API rate limits
- ✅ **.gitignore**: Properly configured to exclude sensitive files

### Best Practices

1. **Never commit `.env` files**
2. **Use GitHub Secrets** for sensitive credentials
3. **Rotate bot tokens** periodically
4. **Review admin channel logs** regularly
5. **Test feed URLs** before adding to feeds.yaml

## Troubleshooting

### Bot not sending messages

1. Verify bot token is correct: `@BotFather` → /token
2. Check channel ID format (should be negative for groups: `-123456789`)
3. Ensure bot is added to the channel with send message permissions
4. Check GitHub Actions logs for error messages

### Feeds not fetching

1. Verify feed URLs in `feeds.yaml` are valid
2. Test URL access: `curl -I https://example.com/feed`
3. Check timeout errors in logs (10s limit)
4. Verify User-Agent header acceptance

### Duplicate messages

1. Each run is independent (ephemeral state)
2. Duplicates within same run are filtered
3. Different runs may send same item if published recently
4. Adjust MAX_ITEM_AGE in `src/dedupe.py` if needed

### Rate limiting issues

1. Check Telegram API limits (30 messages/second)
2. Review message frequency configuration
3. Exponential backoff is automatic (max 5 retries)
4. Consider spreading execution across different times

## Development

### Setting Up Development Environment

```bash
# Install dev dependencies
pip install -r requirements-test.txt

# Run tests in watch mode
pytest-watch tests/

# Check code style
flake8 src/ tests/

# Type checking
mypy src/
```

### Adding New Tests

Place test files in `tests/unit/` or `tests/integration/`:

```python
import pytest
from src.module import function

class TestFunction:
    def test_case(self):
        result = function()
        assert result == expected
```

### Adding New Feeds

1. Verify the feed URL works: `curl -I <URL>`
2. Add to `feeds.yaml`:
   ```yaml
   feeds:
     - https://existing-feed.com/rss
     - https://new-feed.com/atom  # Add new feed
   ```
3. Run tests to validate
4. Commit and push

## License

See [LICENSE](LICENSE) file for details.

## Support & Contribution

- **Issues**: Report bugs via GitHub Issues
- **Contributions**: Pull requests welcome
- **Questions**: Check existing issues or create new discussion

## Related Files

- [feeds.yaml](feeds.yaml) - Feed configuration
- [requirements.txt](requirements.txt) - Python dependencies
- [pytest.ini](pytest.ini) - Test configuration
- [.github/workflows/rss-bot.yml](.github/workflows/rss-bot.yml) - GitHub Actions workflow

## Quick Reference

```bash
# Install
python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt

# Test
pytest tests/ -v

# Run
export TELEGRAM_BOT_TOKEN="..." && export TELEGRAM_CHANNEL_ID="..." && python -m src.main

# Deploy
# Push to GitHub with secrets configured
```

---

**Status**: ✅ Production Ready | **Tests**: 132/132 Passing | **Coverage**: 5.28x Code Ratio
