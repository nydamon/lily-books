"""Amazon KDP upload integration - LEGACY/BACKUP IMPLEMENTATION.

⚠️  DEPRECATED: PublishDrive is now the recommended distribution platform.
    This integration is maintained as a backup option for direct Amazon access.

STUB IMPLEMENTATION: Documents the upload process for Amazon KDP.

For production use, implement either:
1. Selenium WebDriver automation (fragile, requires maintenance)
2. Manual upload following documented steps
3. Third-party service (Publisher Rocket, etc.)

Amazon does not provide an official public API for KDP uploads.
"""

from datetime import datetime
from typing import Any

from lily_books.models import FlowState, PublishingMetadata, UploadResult


class AmazonKDPUploader:
    """Stub uploader for Amazon KDP."""

    def upload(self, state: FlowState) -> UploadResult:
        """
        Upload to Amazon KDP.

        STUB: This is a placeholder implementation.
        Returns a stub result documenting the manual upload process.
        """

        # Find Kindle edition
        kindle_edition = None
        if state.get("edition_files"):
            for edition in state["edition_files"]:
                if edition["retailer"] == "amazon_kdp":
                    kindle_edition = edition
                    break

        if not kindle_edition:
            return UploadResult(
                retailer="amazon_kdp",
                status="error",
                message="No Kindle edition found",
                timestamp=datetime.now().isoformat(),
            )

        # In a real implementation, this would:
        # 1. Launch Selenium WebDriver
        # 2. Login to KDP
        # 3. Fill metadata form
        # 4. Upload EPUB manuscript
        # 5. Upload cover
        # 6. Set pricing
        # 7. Submit for review
        # 8. Return ASIN (if available immediately)

        # For now, return instructions for manual upload
        pub_meta = state.get("publishing_metadata")
        if isinstance(pub_meta, PublishingMetadata):
            pub_meta_dict = pub_meta.model_dump()
        else:
            pub_meta_dict = pub_meta or {}

        manual_steps = """
Amazon KDP Manual Upload Steps:

1. Go to https://kdp.amazon.com/
2. Sign in with your KDP account
3. Click "Create" → "Kindle eBook"

4. PAPERBACK & EBOOK DETAILS:
   - Language: English
   - Book Title: {title}
   - Subtitle: {subtitle}
   - Author: {author}
   - Description: {description}
   - Keywords (7 max): {keywords}
   - Categories: Select 2 categories
   - Public domain: Yes (if applicable)

5. CONTENT:
   - Upload manuscript: {epub_file}
   - Upload cover: {cover_file}
   - Preview book online

6. PRICING:
   - Territories: Worldwide rights
   - Pricing: ${price}
   - 70% Royalty (if >= $2.99)

7. PUBLISH:
   - Click "Publish your Kindle eBook"
   - Wait 24-72 hours for review
   - ASIN will be assigned after approval
""".format(
            title=pub_meta_dict.get("title", ""),
            subtitle=pub_meta_dict.get("subtitle", ""),
            author=pub_meta_dict.get("original_author", ""),
            description=state.get("retail_metadata", {}).get("description_short", ""),
            keywords=", ".join(state.get("retail_metadata", {}).get("amazon_keywords", [])[:7]),
            epub_file=kindle_edition["file_path"],
            cover_file=state.get("cover_path", ""),
            price=state.get("pricing", {}).get("base_price_usd", 2.99),
        )

        return UploadResult(
            retailer="amazon_kdp",
            status="pending",
            message="Manual upload required. See upload instructions.",
            error_details=manual_steps,
            timestamp=datetime.now().isoformat(),
        )


def upload_to_kdp_node(state: FlowState) -> dict[str, Any]:
    """LangGraph node for Amazon KDP upload - LEGACY/BACKUP IMPLEMENTATION."""

    print("\n⚠️  WARNING: Amazon KDP direct upload is a LEGACY/BACKUP option.")
    print("    Recommended: Use PublishDrive which includes Amazon distribution.\n")

    print("\n📤 Amazon KDP Upload (LEGACY/BACKUP - Manual)")
    print("=" * 70)

    uploader = AmazonKDPUploader()
    result = uploader.upload(state)

    # Update state
    upload_results = state.get("upload_results", {})
    upload_results["amazon"] = result.model_dump()

    upload_status = state.get("upload_status", {})
    upload_status["amazon"] = result.status

    # Display manual upload instructions
    if result.status == "pending":
        print(result.error_details)

    print("=" * 70 + "\n")

    return {
        "upload_results": upload_results,
        "upload_status": upload_status,
    }
