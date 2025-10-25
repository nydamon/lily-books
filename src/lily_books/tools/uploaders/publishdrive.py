"""PublishDrive upload integration - PRIMARY DISTRIBUTION PLATFORM.

⭐ RECOMMENDED: PublishDrive is the primary distribution aggregator.

STUB IMPLEMENTATION: Manual upload required (Selenium automation planned).

PublishDrive distributes to 400+ stores including:
- Amazon KDP
- Apple Books
- Google Play Books
- Kobo
- Barnes & Noble
- And many more

Benefits:
- Free ISBN from PublishDrive
- Single upload for all retailers
- Unified analytics dashboard
- No exclusivity requirements
- Multi-currency pricing

Docs: https://publishdrive.com/
"""

from datetime import datetime
from typing import Any

from lily_books.models import FlowState, PublishingMetadata, UploadResult


class PublishDriveUploader:
    """Stub uploader for PublishDrive (manual upload required)."""

    def upload(self, state: FlowState) -> UploadResult:
        """
        Upload to PublishDrive.

        STUB: This is a placeholder implementation.
        Returns manual upload instructions for PublishDrive.
        """

        # Find universal edition
        universal_edition = self._find_universal_edition(state)

        if not universal_edition:
            return UploadResult(
                retailer="publishdrive",
                status="error",
                message="No universal edition found for PublishDrive",
                timestamp=datetime.now().isoformat(),
            )

        # In a real implementation (future Selenium automation), this would:
        # 1. Launch Selenium WebDriver
        # 2. Login to PublishDrive
        # 3. Fill metadata form
        # 4. Upload EPUB manuscript
        # 5. Upload cover
        # 6. Select distribution channels
        # 7. Set pricing
        # 8. Submit for distribution
        # 9. Extract free ISBN
        # 10. Return success with identifiers

        # For now, return instructions for manual upload
        pub_meta = state.get("publishing_metadata")
        if isinstance(pub_meta, PublishingMetadata):
            pub_meta_dict = pub_meta.model_dump()
        else:
            pub_meta_dict = pub_meta or {}

        retail_meta = state.get("retail_metadata", {})

        manual_steps = self._generate_upload_instructions(
            pub_meta_dict, retail_meta, universal_edition, state
        )

        return UploadResult(
            retailer="publishdrive",
            status="pending",
            message="Manual upload required. See upload instructions below.",
            error_details=manual_steps,
            timestamp=datetime.now().isoformat(),
        )

    def _find_universal_edition(self, state: FlowState) -> dict | None:
        """Find the universal edition for PublishDrive upload."""
        if not state.get("edition_files"):
            return None

        for edition in state["edition_files"]:
            if edition["retailer"] == "publishdrive":
                return edition

        # Fallback: Look for universal in filename
        for edition in state["edition_files"]:
            if "universal" in edition["file_path"].lower():
                return edition

        return None

    def _generate_upload_instructions(
        self,
        pub_meta: dict,
        retail_meta: dict,
        edition: dict,
        state: FlowState,
    ) -> str:
        """Generate detailed manual upload instructions for PublishDrive."""

        return f"""
PublishDrive Manual Upload Instructions
========================================

⭐ PublishDrive distributes to 400+ stores in ONE upload:
   Amazon KDP, Apple Books, Google Play, Kobo, B&N, and more

STATUS: Manual upload required (Selenium automation planned for future)

STEP 1: CREATE ACCOUNT
-----------------------
1. Go to https://publishdrive.com/
2. Sign up for free account
3. Complete publisher profile (name, address, tax info)
4. Verify email address

STEP 2: ADD NEW BOOK
--------------------
1. Log in to PublishDrive dashboard
2. Click "Add New Book" or "Upload Book"
3. Select "eBook" format

STEP 3: BOOK DETAILS
--------------------
Title: {pub_meta.get('title', 'N/A')}
Subtitle: {pub_meta.get('subtitle', 'N/A')}
Author: {pub_meta.get('original_author', 'N/A')}
Publisher: {pub_meta.get('publisher', 'Modernized Classics Press')}

Description (Short - for search results):
{retail_meta.get('description_short', 'See retail_metadata for full description')}

Description (Long - full product page):
{retail_meta.get('description_long', 'See retail_metadata for full HTML description')}

Keywords: {', '.join(retail_meta.get('keywords', [])[:20])}

Categories/BISAC Codes: {', '.join(retail_meta.get('bisac_categories', [])[:3])}

Language: English

STEP 4: UPLOAD FILES
--------------------
Upload EPUB: {edition['file_path']}
Upload Cover: {state.get('cover_path', 'N/A')}

STEP 5: PRICING
---------------
Base Price: ${state.get('pricing', {}).get('base_price_usd', 2.99)} USD

PublishDrive will automatically convert to local currencies for each store.

STEP 6: DISTRIBUTION CHANNELS
------------------------------
Select ALL available stores (recommended for maximum reach):

Primary Retailers:
✓ Amazon (via KDP) - Global
✓ Apple Books - Global
✓ Google Play Books - Global
✓ Kobo - Global
✓ Barnes & Noble - US

Secondary Retailers:
✓ Scribd - Subscription service
✓ OverDrive - Library distribution
✓ Tolino - European market
✓ 24symbols - European subscription
✓ And 400+ more stores worldwide

STEP 7: ISBN (FREE!)
--------------------
⭐ PublishDrive provides FREE ISBN - select this option.

You do NOT need to purchase an ISBN separately.
PublishDrive will assign one during the upload process.

STEP 8: RIGHTS & TERRITORIES
-----------------------------
Publishing Rights: Worldwide
Age Rating: General Audiences (or specify if needed)
DRM Protection: No DRM recommended (better reader experience)

STEP 9: REVIEW & PUBLISH
-------------------------
1. Review all book details carefully
2. Preview the EPUB if desired
3. Click "Publish" or "Submit for Distribution"
4. PublishDrive will begin distributing to selected stores

TIMELINES (Approximate):
------------------------
- Upload to PublishDrive: Immediate
- Amazon KDP: 24-72 hours
- Apple Books: 7-14 days
- Google Play Books: 3-5 days
- Kobo: 1-3 days
- Barnes & Noble: 5-10 days
- Other retailers: 1-4 weeks

WHAT YOU'LL RECEIVE:
--------------------
After successful upload and distribution:
- ✓ Free ISBN from PublishDrive
- ✓ Universal book link (works on all stores)
- ✓ Access to unified sales dashboard
- ✓ Monthly sales reports
- ✓ Direct payment deposits (monthly or quarterly)

NEXT STEPS:
-----------
1. Complete the manual upload following steps above
2. Wait for distribution to complete (timelines above)
3. Monitor sales in PublishDrive dashboard
4. Update book metadata anytime via PublishDrive (changes sync to all stores)

ADVANTAGES OVER INDIVIDUAL UPLOADS:
------------------------------------
✓ ONE upload instead of 3-4 separate uploads
✓ FREE ISBN (saves $125+ if purchased separately)
✓ Unified analytics across all retailers
✓ Single interface for updates (no need to update Amazon, Apple, Google separately)
✓ Wider distribution (400+ stores vs 1-3 stores)
✓ Multi-currency pricing handled automatically

SUPPORT:
--------
PublishDrive Support: support@publishdrive.com
Documentation: https://publishdrive.com/help/

========================================
""".format(
            title=pub_meta.get("title", ""),
            subtitle=pub_meta.get("subtitle", ""),
            author=pub_meta.get("original_author", ""),
            publisher=pub_meta.get("publisher", "Modernized Classics Press"),
            description_short=retail_meta.get("description_short", ""),
            keywords=", ".join(retail_meta.get("keywords", [])[:20]),
            categories=", ".join(retail_meta.get("bisac_categories", [])[:3]),
            epub_file=edition["file_path"],
            cover_file=state.get("cover_path", ""),
            price=state.get("pricing", {}).get("base_price_usd", 2.99),
        )


def upload_to_publishdrive_node(state: FlowState) -> dict[str, Any]:
    """LangGraph node for PublishDrive upload - PRIMARY DISTRIBUTION PLATFORM."""

    print("\n" + "=" * 70)
    print("📤 PublishDrive Upload (RECOMMENDED)".center(70))
    print("=" * 70)
    print("\n⭐ PublishDrive distributes to 400+ stores in ONE upload!")
    print("   Amazon, Apple, Google, Kobo, B&N, and more\n")

    uploader = PublishDriveUploader()
    result = uploader.upload(state)

    # Update state
    upload_results = state.get("upload_results", {})
    upload_results["publishdrive"] = result.model_dump()

    upload_status = state.get("upload_status", {})
    upload_status["publishdrive"] = result.status

    # Display manual upload instructions
    if result.status == "pending":
        print(result.error_details)
    elif result.status == "error":
        print(f"\n❌ PublishDrive upload error: {result.message}")
        if result.error_details:
            print(f"Details: {result.error_details}")

    print("=" * 70 + "\n")

    return {
        "upload_results": upload_results,
        "upload_status": upload_status,
    }
