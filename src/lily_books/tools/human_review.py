"""Human review gate for publishing pipeline.

Presents book for human review before uploading to retailers.
Shows cover, metadata, pricing, validation status, etc.
"""

from typing import Any

from lily_books.models import EditionInfo, FlowState


class HumanReviewGate:
    """Human review gate before publishing."""

    def review_book(self, state: FlowState) -> FlowState:
        """
        Present book for human review before publishing.

        Shows:
        - Cover image path
        - Metadata
        - Pricing
        - Edition info
        - Validation status
        - Sample content
        """

        print("\n" + "=" * 70)
        print("HUMAN REVIEW REQUIRED".center(70))
        print("=" * 70)

        # Basic info
        pub_meta = state.get("publishing_metadata", {})
        print(f"\nTitle: {pub_meta.get('title', 'N/A')}")
        print(f"Author: {pub_meta.get('original_author', 'N/A')}")
        print(f"Modernized by: {pub_meta.get('author', 'N/A')}")

        # Pricing
        pricing = state.get("pricing", {})
        print(f"\nPrice: ${pricing.get('base_price_usd', 0.00):.2f} USD")

        # Target retailers
        target_retailers = state.get("target_retailers", [])
        print(f"\nTarget Retailers: {', '.join(target_retailers)}")

        # Editions
        if state.get("identifiers"):
            print(f"\nEditions:")
            for edition_dict in state["identifiers"]["editions"]:
                edition = EditionInfo(**edition_dict)
                print(f"  - {edition.name}: {edition.identifier.identifier_type} via {edition.retailer}")
                if edition.distribution_to:
                    print(f"    Distribution: {', '.join(edition.distribution_to)}")

        # Validation status
        print(f"\nValidation Status:")
        print(f"  Metadata: {'✓ PASS' if state.get('metadata_validated') else '✗ FAIL'}")
        print(f"  EPUB: {'✓ PASS' if state.get('epub_validated') else '✗ FAIL'}")

        # Cover
        if state.get("cover_path"):
            print(f"\nCover: {state['cover_path']}")

        # EPUB files
        if state.get("edition_files"):
            print(f"\nEPUB Files:")
            for edition in state["edition_files"]:
                print(f"  - {edition['edition_name']}: {edition['file_path']}")

        # Description preview
        retail_meta = state.get("retail_metadata", {})
        if retail_meta:
            print(f"\nDescription Preview:")
            desc_short = retail_meta.get("description_short", "")
            print(f"{desc_short[:200]}...")

            keywords = retail_meta.get("keywords", [])
            if keywords:
                print(f"\nKeywords (sample): {', '.join(keywords[:10])}...")

        # Validation errors
        if state.get("epub_validation_errors"):
            print(f"\n⚠ EPUB Validation Errors:")
            for error in state["epub_validation_errors"]:
                print(f"  - {error}")

        # Prompt for approval
        print("\n" + "-" * 70)

        # Check if human review is required
        from lily_books.config import settings

        if not settings.enable_human_review:
            print("Human review disabled in config, auto-approving...")
            state["human_approved"] = True
            state["human_feedback"] = "Auto-approved (ENABLE_HUMAN_REVIEW=false)"
        else:
            response = input("Approve for publishing? (yes/no): ").strip().lower()

            state["human_approved"] = response in ["yes", "y"]

            if not state["human_approved"]:
                feedback = input("What needs to be fixed? ")
                state["human_feedback"] = feedback
                print(f"\n❌ Publishing cancelled. Feedback: {feedback}")
            else:
                print(f"\n✓ Approved for publishing")

        print("=" * 70 + "\n")

        return state


def human_review_node(state: FlowState) -> dict[str, Any]:
    """LangGraph node for human review gate."""
    gate = HumanReviewGate()
    state = gate.review_book(state)

    return {
        "human_approved": state["human_approved"],
        "human_feedback": state.get("human_feedback"),
    }
