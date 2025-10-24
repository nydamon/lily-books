"""Draft2Digital upload integration.

STUB IMPLEMENTATION: Documents the API structure for Draft2Digital.

For production use:
1. Create Draft2Digital account (free)
2. Generate API key from settings
3. Implement API calls using requests library

Draft2Digital provides the easiest API for ebook distribution.
Docs: https://draft2digital.com/api/
"""

from datetime import datetime
from typing import Any

from lily_books.models import FlowState, UploadResult


class Draft2DigitalUploader:
    """Stub uploader for Draft2Digital."""

    def upload(self, state: FlowState) -> UploadResult:
        """
        Upload to Draft2Digital.

        STUB: This is a placeholder implementation.
        Returns instructions for setting up Draft2Digital integration.
        """

        # Find universal edition (used for D2D)
        universal_edition = None
        if state.get("edition_files"):
            for edition in state["edition_files"]:
                if edition["retailer"] == "draft2digital":
                    universal_edition = edition
                    break

        if not universal_edition:
            return UploadResult(
                retailer="draft2digital",
                status="error",
                message="No D2D edition found",
                timestamp=datetime.now().isoformat(),
            )

        # In a real implementation, this would:
        # 1. Authenticate with D2D API key
        # 2. Create book entry
        # 3. Upload EPUB manuscript
        # 4. Upload cover
        # 5. Set pricing and distribution channels
        # 6. Publish to selected retailers
        # 7. Return D2D book ID and free ISBN

        setup_instructions = """
Draft2Digital API Setup:

1. CREATE ACCOUNT:
   - Sign up at https://draft2digital.com/
   - Free account, instant access
   - No approval required

2. GENERATE API KEY:
   - Go to Settings → API Access
   - Generate new API key
   - Set DRAFT2DIGITAL_API_KEY=your_api_key

3. INSTALL DEPENDENCIES:
   - pip install requests

4. API USAGE (Python):
   import requests

   headers = {{
       "Authorization": "Bearer YOUR_API_KEY",
       "Content-Type": "application/json"
   }}

   # Create book
   book_data = {{
       "title": "{title}",
       "authors": ["{author}"],
       "description": "{description}",
       "price": {{"amount": {price}, "currency": "USD"}},
       "distribution": {{
           "apple": True,
           "kobo": True,
           "barnes_noble": True,
           "scribd": True,
           "overdrive": True
       }}
   }}

   response = requests.post(
       "https://www.draft2digital.com/api/v1/books",
       headers=headers,
       json=book_data
   )

   book_id = response.json()["book"]["id"]
   free_isbn = response.json()["book"]["isbn"]  # D2D assigns free ISBN

   # Upload EPUB
   with open("{epub_file}", "rb") as f:
       files = {{"file": f}}
       requests.post(
           f"https://www.draft2digital.com/api/v1/books/{{book_id}}/manuscript",
           headers={{"Authorization": "Bearer YOUR_API_KEY"}},
           files=files
       )

   # Upload cover
   with open("{cover_file}", "rb") as f:
       files = {{"file": f}}
       requests.post(
           f"https://www.draft2digital.com/api/v1/books/{{book_id}}/cover",
           headers={{"Authorization": "Bearer YOUR_API_KEY"}},
           files=files
       )

   # Publish
   requests.post(
       f"https://www.draft2digital.com/api/v1/books/{{book_id}}/publish",
       headers=headers
   )

5. DISTRIBUTION:
   - Apple Books: 7-14 days
   - Kobo: 1-3 days
   - Barnes & Noble: 5-10 days
   - Scribd, OverDrive, 24symbols: varies

6. UNIVERSAL BOOK LINK:
   - D2D creates books2read.com link
   - One link for all retailers

For detailed API docs:
https://draft2digital.com/api/
""".format(
            title=state.get("publishing_metadata", {}).get("title", ""),
            author=state.get("publishing_metadata", {}).get("original_author", ""),
            description=state.get("retail_metadata", {}).get("description_short", ""),
            price=state.get("pricing", {}).get("base_price_usd", 2.99),
            epub_file=universal_edition["file_path"],
            cover_file=state.get("cover_path", ""),
        )

        return UploadResult(
            retailer="draft2digital",
            status="pending",
            message="Draft2Digital API setup required. See instructions.",
            error_details=setup_instructions,
            timestamp=datetime.now().isoformat(),
        )


def upload_to_d2d_node(state: FlowState) -> dict[str, Any]:
    """LangGraph node for Draft2Digital upload."""

    print("\n📤 Draft2Digital Upload (API)")
    print("=" * 70)

    uploader = Draft2DigitalUploader()
    result = uploader.upload(state)

    # Update state
    upload_results = state.get("upload_results", {})
    upload_results["draft2digital"] = result.model_dump()

    upload_status = state.get("upload_status", {})
    upload_status["draft2digital"] = result.status

    # Display setup instructions
    if result.status == "pending":
        print(result.error_details)

    print("=" * 70 + "\n")

    return {
        "upload_results": upload_results,
        "upload_status": upload_status,
    }
