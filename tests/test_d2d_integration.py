"""Integration tests for Draft2Digital API.

NOTE: These tests require a valid D2D API key and will create real books
in your Draft2Digital account. Use with caution!

To run:
    pytest tests/test_d2d_integration.py -v --d2d-live

The --d2d-live flag is required to prevent accidental API calls.
"""

import os
from pathlib import Path

import pytest

from lily_books.models import FlowState, PricingInfo, RetailMetadata
from lily_books.tools.uploaders.draft2digital import (
    Draft2DigitalAPI,
    Draft2DigitalUploader,
)


def pytest_addoption(parser):
    """Add custom pytest options."""
    parser.addoption(
        "--d2d-live",
        action="store_true",
        default=False,
        help="Run live Draft2Digital API tests (creates real books!)",
    )


def pytest_configure(config):
    """Configure pytest."""
    config.addinivalue_line(
        "markers", "d2d_live: mark test as requiring live Draft2Digital API access"
    )


def pytest_collection_modifyitems(config, items):
    """Skip tests marked as d2d_live unless --d2d-live is provided."""
    if config.getoption("--d2d-live"):
        return

    skip_d2d = pytest.mark.skip(reason="need --d2d-live option to run")
    for item in items:
        if "d2d_live" in item.keywords:
            item.add_marker(skip_d2d)


@pytest.fixture
def d2d_api():
    """Create Draft2Digital API client."""
    api_key = os.getenv("DRAFT2DIGITAL_API_KEY")
    if not api_key:
        pytest.skip("DRAFT2DIGITAL_API_KEY not set")

    return Draft2DigitalAPI(api_key)


@pytest.fixture
def mock_state(tmp_path):
    """Create mock FlowState for testing."""

    # Create mock EPUB file
    epub_path = tmp_path / "test_book.epub"
    epub_path.write_bytes(b"mock epub content")

    # Create mock cover
    cover_path = tmp_path / "test_cover.jpg"
    cover_path.write_bytes(b"mock cover image")

    state: FlowState = {
        "slug": "test-book",
        "book_id": None,
        "paths": {},
        "raw_text": None,
        "chapters": None,
        "rewritten": None,
        "qa_text_ok": None,
        "audio_ok": None,
        "epub_path": str(epub_path),
        "epub_quality_score": None,
        "requested_chapters": None,
        "audio_files": None,
        "mastered_files": None,
        # Publishing metadata
        "publishing_metadata": {
            "title": "Test Book: A Draft2Digital Integration Test",
            "subtitle": "Testing the D2D API Integration",
            "original_author": "Test Author",
            "author": "Test Modernizer",
            "publisher": "Test Publisher",
        },
        "cover_design": None,
        "cover_path": str(cover_path),
        # Edition files
        "edition_files": [
            {
                "edition_name": "Universal Edition",
                "retailer": "draft2digital",
                "file_path": str(epub_path),
                "identifier_type": "ISBN",
            }
        ],
        # Retail metadata
        "retail_metadata": RetailMetadata(
            description_short="A test book for D2D API integration testing",
            description_long="This is a comprehensive test of the Draft2Digital API integration. It should be deleted after testing.",
            keywords=[
                "test",
                "draft2digital",
                "api integration",
                "automated testing",
            ],
            bisac_categories=["FIC000000"],  # Fiction / General
            amazon_keywords=["test", "d2d", "api"],
        ),
        # Pricing
        "pricing": PricingInfo(
            base_price_usd=0.99,  # Minimum price for testing
        ),
        # Distribution
        "target_retailers": ["draft2digital"],
        "identifiers": None,
        "requires_two_editions": None,
        "edition_metadata": None,
        "upload_status": {},
        "upload_results": {},
        "errors": None,
        "metadata_validated": True,
        "epub_validated": True,
        "human_approved": True,
        "human_feedback": None,
        "validation_reports": None,
    }

    return state


class TestDraft2DigitalAPI:
    """Test Draft2Digital API client methods."""

    @pytest.mark.d2d_live
    def test_api_initialization(self):
        """Test API client initialization."""
        api_key = os.getenv("DRAFT2DIGITAL_API_KEY")
        api = Draft2DigitalAPI(api_key)

        assert api.api_key == api_key
        assert api.BASE_URL == "https://www.draft2digital.com/api/v1"
        assert "Authorization" in api.session.headers

    def test_api_initialization_without_key(self):
        """Test API initialization fails without key."""
        with pytest.raises(ValueError, match="API key required"):
            Draft2DigitalAPI(api_key=None)

    @pytest.mark.d2d_live
    def test_create_book(self, d2d_api):
        """
        Test book creation via API.

        WARNING: This creates a real book in your D2D account!
        Delete it manually after testing.
        """
        result = d2d_api.create_book(
            title="API Test Book - DELETE ME",
            authors=["Test Author"],
            description="This is a test book created by automated testing. Please delete.",
            keywords=["test", "automated", "delete"],
            categories=["FIC000000"],
            price_usd=0.99,
            distribution_channels={"apple": False, "kobo": False},  # Don't distribute
        )

        assert "book_id" in result
        assert "isbn" in result
        assert result["book_id"] is not None

        print(f"\n✓ Created test book (ID: {result['book_id']}, ISBN: {result['isbn']})")
        print("⚠ IMPORTANT: Delete this book from your D2D dashboard!")

    @pytest.mark.d2d_live
    def test_retry_logic_on_server_error(self, d2d_api, monkeypatch):
        """Test retry logic handles server errors."""
        # Mock session.request to simulate server error on first call, success on second
        call_count = 0
        original_request = d2d_api.session.request

        def mock_request(*args, **kwargs):
            nonlocal call_count
            call_count += 1

            if call_count == 1:
                # Simulate server error
                import requests

                response = requests.Response()
                response.status_code = 503
                raise requests.HTTPError("Service unavailable", response=response)

            # Success on retry
            return original_request(*args, **kwargs)

        monkeypatch.setattr(d2d_api.session, "request", mock_request)

        # This should succeed after retry
        result = d2d_api.create_book(
            title="Retry Test Book - DELETE ME",
            authors=["Test Author"],
            description="Testing retry logic",
            keywords=["test"],
            categories=["FIC000000"],
            price_usd=0.99,
            distribution_channels={"apple": False},
        )

        assert call_count == 2  # Failed once, succeeded on retry
        assert "book_id" in result


class TestDraft2DigitalUploader:
    """Test Draft2Digital uploader."""

    @pytest.mark.d2d_live
    def test_full_upload_flow(self, mock_state):
        """
        Test complete upload flow: create book, upload EPUB, upload cover, publish.

        WARNING: This creates a real book in your D2D account!
        Delete it manually after testing.
        """
        uploader = Draft2DigitalUploader()
        result = uploader.upload(mock_state)

        assert result.status == "success"
        assert result.identifier_assigned is not None  # Free ISBN
        assert result.universal_book_link is not None
        assert "books2read.com" in result.universal_book_link

        print(f"\n✓ Full upload test successful!")
        print(f"  ISBN: {result.identifier_assigned}")
        print(f"  Universal link: {result.universal_book_link}")
        print(f"⚠ IMPORTANT: Delete this book from your D2D dashboard!")

    def test_upload_without_api_key(self, mock_state, monkeypatch):
        """Test upload fails gracefully without API key."""
        monkeypatch.setenv("DRAFT2DIGITAL_API_KEY", "")

        uploader = Draft2DigitalUploader()
        result = uploader.upload(mock_state)

        assert result.status == "error"
        assert "API key not configured" in result.message

    def test_upload_without_edition_files(self, mock_state):
        """Test upload fails without edition files."""
        mock_state["edition_files"] = None

        uploader = Draft2DigitalUploader()
        result = uploader.upload(mock_state)

        assert result.status == "error"
        assert "No universal edition found" in result.message


# Example usage documentation
"""
Example: Manual test of D2D API integration

1. Set your API key:
   export DRAFT2DIGITAL_API_KEY=your-api-key-here

2. Run tests:
   pytest tests/test_d2d_integration.py -v --d2d-live

3. Clean up:
   - Go to https://draft2digital.com/books
   - Delete test books manually (they have "DELETE ME" in title)

Note: The free ISBN assigned during testing is yours to keep, but you should
delete the test book entries to avoid clutter in your D2D account.
"""
