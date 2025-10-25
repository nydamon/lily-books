"""Draft2Digital upload integration - LEGACY/BACKUP IMPLEMENTATION.

⚠️  DEPRECATED: PublishDrive is now the recommended distribution platform.
    This integration is maintained as a backup option.

Fully functional API integration for Draft2Digital distribution.

Features:
- API key authentication
- Book creation with metadata
- EPUB manuscript upload
- Cover image upload
- Publishing to selected retailers
- Free ISBN extraction
- Comprehensive error handling
- Retry logic with exponential backoff

Docs: https://draft2digital.com/api/
"""

import time
from datetime import datetime
from pathlib import Path
from typing import Any

import requests

from lily_books.config import settings
from lily_books.models import FlowState, PublishingMetadata, UploadResult


class Draft2DigitalAPI:
    """Draft2Digital API client with full integration."""

    BASE_URL = "https://www.draft2digital.com/api/v1"

    def __init__(self, api_key: str | None = None):
        """Initialize D2D API client.

        Args:
            api_key: D2D API key (falls back to settings.draft2digital_api_key)
        """
        self.api_key = api_key or settings.draft2digital_api_key

        if not self.api_key:
            raise ValueError(
                "Draft2Digital API key required. Set DRAFT2DIGITAL_API_KEY in .env"
            )

        self.session = requests.Session()
        self.session.headers.update({"Authorization": f"Bearer {self.api_key}"})

    def create_book(
        self,
        title: str,
        authors: list[str],
        description: str,
        keywords: list[str],
        categories: list[str],
        price_usd: float,
        distribution_channels: dict[str, bool],
    ) -> dict:
        """
        Create a new book entry in Draft2Digital.

        Args:
            title: Book title
            authors: List of author names
            description: Book description
            keywords: SEO keywords
            categories: BISAC category codes
            price_usd: Price in USD
            distribution_channels: Dict of retailer: enabled

        Returns:
            Dict with book_id and free_isbn

        Raises:
            requests.HTTPError: If API request fails
        """
        payload = {
            "title": title,
            "authors": authors,
            "description": description,
            "keywords": ",".join(keywords),
            "categories": categories,
            "language": "en",
            "price": {"amount": price_usd, "currency": "USD"},
            "distribution": distribution_channels,
        }

        response = self._request_with_retry(
            "POST", f"{self.BASE_URL}/books", json=payload
        )

        data = response.json()

        book_id = data["book"]["id"]
        free_isbn = data["book"].get("isbn")  # D2D assigns free ISBN

        print(f"  ✓ Book created (ID: {book_id}, ISBN: {free_isbn})")

        return {"book_id": book_id, "isbn": free_isbn, "response": data}

    def upload_manuscript(self, book_id: str, epub_path: Path) -> dict:
        """
        Upload EPUB manuscript to Draft2Digital.

        Args:
            book_id: D2D book ID
            epub_path: Path to EPUB file

        Returns:
            API response data

        Raises:
            requests.HTTPError: If upload fails
            FileNotFoundError: If EPUB doesn't exist
        """
        if not epub_path.exists():
            raise FileNotFoundError(f"EPUB not found: {epub_path}")

        # D2D expects multipart/form-data
        with open(epub_path, "rb") as f:
            files = {
                "file": (epub_path.name, f, "application/epub+zip")
            }

            # Remove Content-Type from headers for multipart
            headers = {"Authorization": f"Bearer {self.api_key}"}

            response = self._request_with_retry(
                "POST",
                f"{self.BASE_URL}/books/{book_id}/manuscript",
                files=files,
                headers=headers,
            )

        print(f"  ✓ EPUB uploaded: {epub_path.name}")

        return response.json()

    def upload_cover(self, book_id: str, cover_path: Path) -> dict:
        """
        Upload cover image to Draft2Digital.

        Args:
            book_id: D2D book ID
            cover_path: Path to cover image (JPEG or PNG)

        Returns:
            API response data

        Raises:
            requests.HTTPError: If upload fails
            FileNotFoundError: If cover doesn't exist
        """
        if not cover_path.exists():
            raise FileNotFoundError(f"Cover not found: {cover_path}")

        # Determine MIME type
        mime_type = "image/jpeg" if cover_path.suffix.lower() in [".jpg", ".jpeg"] else "image/png"

        with open(cover_path, "rb") as f:
            files = {
                "file": (cover_path.name, f, mime_type)
            }

            headers = {"Authorization": f"Bearer {self.api_key}"}

            response = self._request_with_retry(
                "POST",
                f"{self.BASE_URL}/books/{book_id}/cover",
                files=files,
                headers=headers,
            )

        print(f"  ✓ Cover uploaded: {cover_path.name}")

        return response.json()

    def publish_book(self, book_id: str) -> dict:
        """
        Publish book to selected retailers.

        Args:
            book_id: D2D book ID

        Returns:
            API response data

        Raises:
            requests.HTTPError: If publishing fails
        """
        response = self._request_with_retry(
            "POST", f"{self.BASE_URL}/books/{book_id}/publish"
        )

        print(f"  ✓ Published to retailers")

        return response.json()

    def get_book_status(self, book_id: str) -> dict:
        """
        Get book status and details.

        Args:
            book_id: D2D book ID

        Returns:
            Book details including ISBN, distribution status, etc.
        """
        response = self._request_with_retry(
            "GET", f"{self.BASE_URL}/books/{book_id}"
        )

        return response.json()

    def _request_with_retry(
        self,
        method: str,
        url: str,
        max_retries: int = 3,
        initial_delay: float = 2.0,
        **kwargs,
    ) -> requests.Response:
        """
        Make HTTP request with exponential backoff retry.

        Args:
            method: HTTP method (GET, POST, etc.)
            url: Request URL
            max_retries: Maximum retry attempts
            initial_delay: Initial retry delay in seconds
            **kwargs: Additional arguments for requests

        Returns:
            Response object

        Raises:
            requests.HTTPError: If all retries fail
        """
        delay = initial_delay

        for attempt in range(max_retries + 1):
            try:
                response = self.session.request(method, url, timeout=60, **kwargs)
                response.raise_for_status()
                return response

            except requests.HTTPError as e:
                if attempt == max_retries:
                    # Final attempt failed
                    raise

                status_code = e.response.status_code if e.response else 0

                # Don't retry client errors (4xx) except 429 (rate limit)
                if 400 <= status_code < 500 and status_code != 429:
                    raise

                # Retry on server errors (5xx) or rate limit (429)
                print(
                    f"  ⚠ Request failed (attempt {attempt + 1}/{max_retries + 1}): {e}"
                )
                print(f"  ⏳ Retrying in {delay:.1f}s...")
                time.sleep(delay)
                delay *= 2  # Exponential backoff

            except requests.RequestException as e:
                if attempt == max_retries:
                    raise

                print(
                    f"  ⚠ Network error (attempt {attempt + 1}/{max_retries + 1}): {e}"
                )
                print(f"  ⏳ Retrying in {delay:.1f}s...")
                time.sleep(delay)
                delay *= 2


class Draft2DigitalUploader:
    """Full Draft2Digital uploader implementation."""

    # Default distribution channels
    DEFAULT_DISTRIBUTION = {
        "apple": True,
        "kobo": True,
        "barnes_noble": True,
        "scribd": True,
        "overdrive": True,  # Library distribution
        "tolino": True,  # EU market
        "vivlio": True,
        "palace": True,
        "bibliotheca": True,
        "twentyfour_symbols": False,  # Often requires separate agreement
    }

    def __init__(self):
        """Initialize uploader."""
        self.api = None

    def upload(self, state: FlowState) -> UploadResult:
        """
        Upload book to Draft2Digital.

        Full implementation with:
        - Book creation
        - EPUB upload
        - Cover upload
        - Publishing
        - Free ISBN extraction
        """

        try:
            # Initialize API client
            self.api = Draft2DigitalAPI()

        except ValueError as e:
            # API key not configured
            return UploadResult(
                retailer="draft2digital",
                status="error",
                message="D2D API key not configured",
                error_details=str(e),
                timestamp=datetime.now().isoformat(),
            )

        try:
            # Find universal edition
            universal_edition = self._find_universal_edition(state)

            if not universal_edition:
                return UploadResult(
                    retailer="draft2digital",
                    status="error",
                    message="No universal edition found for D2D",
                    timestamp=datetime.now().isoformat(),
                )

            # Extract metadata
            pub_meta = state.get("publishing_metadata")
            if isinstance(pub_meta, PublishingMetadata):
                pub_meta_dict = pub_meta.model_dump()
            else:
                pub_meta_dict = pub_meta or {}
            retail_meta = state.get("retail_metadata", {})
            pricing = state.get("pricing", {})

            title = pub_meta_dict.get("title", "Untitled")
            authors = [pub_meta_dict.get("original_author", "Unknown")]
            description = retail_meta.get("description_long", "")
            keywords = retail_meta.get("keywords", [])[:20]  # D2D accepts many
            categories = retail_meta.get("bisac_categories", [])
            price_usd = pricing.get("base_price_usd", 2.99)

            # Get cover path
            cover_path = Path(state.get("cover_path", ""))

            print(f"\n  📚 Uploading: {title}")
            print(f"  💰 Price: ${price_usd:.2f}")

            # Step 1: Create book entry
            print(f"\n  1️⃣ Creating book entry...")
            book_result = self.api.create_book(
                title=title,
                authors=authors,
                description=description,
                keywords=keywords,
                categories=categories,
                price_usd=price_usd,
                distribution_channels=self.DEFAULT_DISTRIBUTION,
            )

            book_id = book_result["book_id"]
            free_isbn = book_result["isbn"]

            # Step 2: Upload EPUB
            print(f"\n  2️⃣ Uploading EPUB...")
            epub_path = Path(universal_edition["file_path"])
            self.api.upload_manuscript(book_id, epub_path)

            # Step 3: Upload cover
            print(f"\n  3️⃣ Uploading cover...")
            if cover_path.exists():
                self.api.upload_cover(book_id, cover_path)
            else:
                print(f"  ⚠ Cover not found, skipping")

            # Step 4: Publish
            print(f"\n  4️⃣ Publishing to retailers...")
            self.api.publish_book(book_id)

            # Step 5: Get final status
            book_status = self.api.get_book_status(book_id)

            # Generate universal book link
            universal_link = f"https://books2read.com/u/{book_id}"

            print(f"\n  ✅ Upload complete!")
            print(f"  📖 Book ID: {book_id}")
            print(f"  🔖 Free ISBN: {free_isbn}")
            print(f"  🔗 Universal link: {universal_link}")

            return UploadResult(
                retailer="draft2digital",
                status="success",
                message=f"Successfully uploaded to Draft2Digital",
                identifier_assigned=free_isbn,
                preview_link=None,  # D2D doesn't provide preview links
                universal_book_link=universal_link,
                timestamp=datetime.now().isoformat(),
            )

        except requests.HTTPError as e:
            error_msg = f"D2D API error: {e.response.status_code}"
            error_details = e.response.text if e.response else str(e)

            print(f"\n  ❌ Upload failed: {error_msg}")
            print(f"  Details: {error_details}")

            return UploadResult(
                retailer="draft2digital",
                status="error",
                message=error_msg,
                error_details=error_details,
                timestamp=datetime.now().isoformat(),
            )

        except Exception as e:
            print(f"\n  ❌ Unexpected error: {str(e)}")

            return UploadResult(
                retailer="draft2digital",
                status="error",
                message=f"Upload failed: {str(e)}",
                error_details=str(e),
                timestamp=datetime.now().isoformat(),
            )

    def _find_universal_edition(self, state: FlowState) -> dict | None:
        """Find the universal edition for D2D upload."""
        if not state.get("edition_files"):
            return None

        for edition in state["edition_files"]:
            if edition["retailer"] == "draft2digital":
                return edition

        # Fallback: Look for universal in filename
        for edition in state["edition_files"]:
            if "universal" in edition["file_path"].lower():
                return edition

        return None


def upload_to_d2d_node(state: FlowState) -> dict[str, Any]:
    """LangGraph node for Draft2Digital upload - LEGACY/BACKUP IMPLEMENTATION."""

    print("\n⚠️  WARNING: Draft2Digital is a LEGACY/BACKUP option.")
    print("    Recommended: Use PublishDrive for wider distribution.\n")

    print("\n" + "=" * 70)
    print("📤 Draft2Digital Upload (LEGACY/BACKUP)".center(70))
    print("=" * 70)

    uploader = Draft2DigitalUploader()
    result = uploader.upload(state)

    # Update state
    upload_results = state.get("upload_results", {})
    upload_results["draft2digital"] = result.model_dump()

    upload_status = state.get("upload_status", {})
    upload_status["draft2digital"] = result.status

    if result.status == "success":
        print(f"\n✅ Draft2Digital upload successful!")
        print(f"📦 Distribution to: Apple Books, Kobo, B&N, Scribd, OverDrive, etc.")
        print(f"⏱️  Timeline: Apple Books (7-14 days), Kobo (1-3 days)")
    else:
        print(f"\n❌ Draft2Digital upload failed")
        print(f"Error: {result.message}")

    print("=" * 70 + "\n")

    return {
        "upload_results": upload_results,
        "upload_status": upload_status,
    }
